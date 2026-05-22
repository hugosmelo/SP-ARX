#!/usr/bin/env python3
"""Reproducible Adult dataset privacy/risk/utility analysis.

This script intentionally uses only the Python standard library. It implements
ARX-style global recoding hierarchies for the Adult dataset, evaluates two
privacy-model families, and writes CSV tables, SVG plots, anonymized datasets,
and a concise Markdown report.
"""

from __future__ import annotations

import csv
import html
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "new" / "data" / "adult" / "adult.data"
OUT_DIR = ROOT / "outputs" / "adult_privacy_analysis"

COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education-num",
    "marital-status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
    "native-country",
    "income",
]

QIDS = [
    "age",
    "workclass",
    "education",
    "marital-status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "hours-per-week",
    "native-country",
]
SENSITIVE = ["income", "capital-gain", "capital-loss"]
INSENSITIVE = ["fnlwgt", "education-num"]

MAX_LEVEL = {
    "age": 4,
    "workclass": 3,
    "education": 3,
    "marital-status": 3,
    "occupation": 3,
    "relationship": 2,
    "race": 2,
    "sex": 1,
    "hours-per-week": 4,
    "native-country": 3,
}

SELECTED_DISTRIBUTIONS = [
    "income",
    "age",
    "education",
    "occupation",
    "race",
    "sex",
    "native-country",
]


def load_adult() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with DATA_PATH.open(newline="") as handle:
        reader = csv.reader(handle, skipinitialspace=True)
        for row in reader:
            if not row:
                continue
            if len(row) != len(COLUMNS):
                raise ValueError(f"Expected {len(COLUMNS)} columns, found {len(row)}")
            cleaned = [value.strip().rstrip(".") for value in row]
            rows.append(dict(zip(COLUMNS, cleaned)))
    return rows


def int_value(value: str) -> int:
    return int(value)


def range_label(value: int, width: int) -> str:
    start = (value // width) * width
    end = start + width - 1
    return f"{start}-{end}"


def age_stage(value: int) -> str:
    if value < 30:
        return "young-adult"
    if value < 45:
        return "adult"
    if value < 65:
        return "older-adult"
    return "senior"


def hours_stage(value: int) -> str:
    if value < 35:
        return "part-time"
    if value <= 45:
        return "full-time"
    return "long-hours"


def country_region(value: str) -> str:
    europe = {
        "England",
        "Germany",
        "Greece",
        "Italy",
        "Poland",
        "Portugal",
        "Ireland",
        "France",
        "Hungary",
        "Scotland",
        "Yugoslavia",
        "Holand-Netherlands",
    }
    asia = {
        "Cambodia",
        "India",
        "Japan",
        "China",
        "Iran",
        "Philippines",
        "Vietnam",
        "Laos",
        "Taiwan",
        "Thailand",
        "Hong",
    }
    latin_america = {
        "Puerto-Rico",
        "Cuba",
        "Honduras",
        "Jamaica",
        "Mexico",
        "Dominican-Republic",
        "Ecuador",
        "Haiti",
        "Columbia",
        "Guatemala",
        "Nicaragua",
        "El-Salvador",
        "Trinadad&Tobago",
        "Peru",
    }
    north_america = {"United-States", "Canada", "Outlying-US(Guam-USVI-etc)"}
    if value == "?":
        return "unknown-country"
    if value in north_america:
        return "North-America"
    if value in europe:
        return "Europe"
    if value in asia:
        return "Asia"
    if value in latin_america:
        return "Latin-America"
    return "Other-region"


def education_group(value: str) -> str:
    less_than_hs = {
        "Preschool",
        "1st-4th",
        "5th-6th",
        "7th-8th",
        "9th",
        "10th",
        "11th",
        "12th",
    }
    some_college = {"Some-college", "Assoc-acdm", "Assoc-voc"}
    graduate = {"Masters", "Prof-school", "Doctorate"}
    if value in less_than_hs:
        return "less-than-high-school"
    if value == "HS-grad":
        return "high-school"
    if value in some_college:
        return "some-college-or-associate"
    if value == "Bachelors":
        return "bachelors"
    if value in graduate:
        return "graduate"
    return "other-education"


def occupation_group(value: str) -> str:
    professional = {"Prof-specialty", "Exec-managerial", "Tech-support"}
    office_sales = {"Adm-clerical", "Sales"}
    manual = {
        "Craft-repair",
        "Machine-op-inspct",
        "Handlers-cleaners",
        "Transport-moving",
    }
    service = {"Other-service", "Priv-house-serv", "Protective-serv"}
    agriculture = {"Farming-fishing"}
    military = {"Armed-Forces"}
    if value == "?":
        return "unknown-occupation"
    if value in professional:
        return "professional-managerial"
    if value in office_sales:
        return "office-sales"
    if value in manual:
        return "manual-technical"
    if value in service:
        return "service"
    if value in agriculture:
        return "agriculture"
    if value in military:
        return "military"
    return "other-occupation"


def workclass_group(value: str) -> str:
    if value == "?":
        return "unknown-workclass"
    if value == "Private":
        return "private"
    if value in {"Federal-gov", "Local-gov", "State-gov"}:
        return "government"
    if value in {"Self-emp-not-inc", "Self-emp-inc"}:
        return "self-employed"
    if value in {"Without-pay", "Never-worked"}:
        return "not-in-paid-work"
    return "other-workclass"


def generalize(attr: str, value: str, level: int) -> str:
    level = min(level, MAX_LEVEL[attr])
    if level <= 0:
        return value
    if attr == "age":
        age = int_value(value)
        if level == 1:
            return range_label(age, 5)
        if level == 2:
            return range_label(age, 10)
        if level == 3:
            return age_stage(age)
        return "*"
    if attr == "hours-per-week":
        hours = int_value(value)
        if level == 1:
            return range_label(hours, 5)
        if level == 2:
            return range_label(hours, 10)
        if level == 3:
            return hours_stage(hours)
        return "*"
    if attr == "education":
        if level == 1:
            return education_group(value)
        if level == 2:
            group = education_group(value)
            if group in {"less-than-high-school", "high-school"}:
                return "non-tertiary"
            if group in {"some-college-or-associate", "bachelors", "graduate"}:
                return "tertiary"
            return group
        return "*"
    if attr == "occupation":
        if level == 1:
            return occupation_group(value)
        if level == 2:
            group = occupation_group(value)
            if group in {"professional-managerial", "office-sales"}:
                return "white-collar"
            if group in {"manual-technical", "agriculture"}:
                return "blue-collar"
            if group == "service":
                return "service"
            return "other-or-unknown-occupation"
        return "*"
    if attr == "workclass":
        if level == 1:
            return workclass_group(value)
        if level == 2:
            group = workclass_group(value)
            if group in {"private", "government", "self-employed"}:
                return "employed"
            return "not-employed-or-unknown"
        return "*"
    if attr == "marital-status":
        if level == 1:
            if value in {"Married-civ-spouse", "Married-AF-spouse"}:
                return "married-present"
            if value == "Married-spouse-absent":
                return "married-absent"
            if value in {"Divorced", "Separated", "Widowed"}:
                return "formerly-married"
            return "never-married"
        if level == 2:
            if value in {"Married-civ-spouse", "Married-AF-spouse", "Married-spouse-absent"}:
                return "married"
            return "not-married"
        return "*"
    if attr == "relationship":
        if level == 1:
            if value in {"Husband", "Wife", "Own-child", "Other-relative"}:
                return "family-household"
            return "non-family-household"
        return "*"
    if attr == "race":
        if level == 1:
            return "White" if value == "White" else "Non-White"
        return "*"
    if attr == "sex":
        return "*"
    if attr == "native-country":
        if level == 1:
            return country_region(value)
        if level == 2:
            if value == "?":
                return "unknown-country"
            return "United-States" if value == "United-States" else "Non-US"
        return "*"
    raise KeyError(attr)


def attribute_profile(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    n = len(rows)
    pair_total = n * (n - 1) / 2
    roles = {
        **{attr: "Quasi-identifier" for attr in QIDS},
        **{attr: "Sensitive" for attr in SENSITIVE},
        **{attr: "Insensitive/excluded" for attr in INSENSITIVE},
    }
    output = []
    for attr in COLUMNS:
        counts = Counter(row[attr] for row in rows)
        same_pairs = sum(count * (count - 1) / 2 for count in counts.values())
        distinction = len(counts) / n
        separation = 1 - same_pairs / pair_total
        output.append(
            {
                "attribute": attr,
                "role": roles[attr],
                "distinct_values": str(len(counts)),
                "missing_values": str(counts.get("?", 0)),
                "distinction": f"{distinction:.6f}",
                "separation": f"{separation:.6f}",
                "top_values": "; ".join(f"{value}={count}" for value, count in counts.most_common(3)),
            }
        )
    return output


def qid_tuple(row: dict[str, str], profile: dict[str, int]) -> tuple[str, ...]:
    return tuple(generalize(attr, row[attr], profile.get(attr, 0)) for attr in QIDS)


def grouped_indices(rows: list[dict[str, str]], profile: dict[str, int]) -> dict[tuple[str, ...], list[int]]:
    groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[qid_tuple(row, profile)].append(index)
    return groups


def distribution(values: list[str]) -> dict[str, float]:
    if not values:
        return {}
    counts = Counter(values)
    total = len(values)
    return {key: value / total for key, value in counts.items()}


def total_variation(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return 0.5 * sum(abs(a.get(key, 0.0) - b.get(key, 0.0)) for key in keys)


def risk_from_groups(groups: dict[tuple[str, ...], list[int]], total_rows: int) -> dict[str, float]:
    if not groups:
        return {
            "equivalence_classes": 0.0,
            "unique_rows": 0.0,
            "fraction_unique": 0.0,
            "min_class_size": 0.0,
            "max_prosecutor_risk": 0.0,
            "average_equivalence_risk": 0.0,
        }
    sizes = [len(indices) for indices in groups.values()]
    unique_rows = sum(size for size in sizes if size == 1)
    min_size = min(sizes)
    return {
        "equivalence_classes": float(len(groups)),
        "unique_rows": float(unique_rows),
        "fraction_unique": unique_rows / total_rows,
        "min_class_size": float(min_size),
        "max_prosecutor_risk": 1 / min_size,
        "average_equivalence_risk": sum((size / total_rows) * (1 / size) for size in sizes),
    }


def candidate_profiles() -> list[dict[str, int]]:
    profiles: list[dict[str, int]] = []
    priority = [
        "age",
        "hours-per-week",
        "occupation",
        "native-country",
        "education",
        "workclass",
        "marital-status",
        "relationship",
        "race",
        "sex",
    ]

    def add(levels: dict[str, int]) -> None:
        profile = {attr: min(levels.get(attr, 0), MAX_LEVEL[attr]) for attr in QIDS}
        if profile not in profiles:
            profiles.append(profile)

    for base in range(0, 5):
        base_profile = {attr: min(base, MAX_LEVEL[attr]) for attr in QIDS}
        add(base_profile)
        for count in range(1, len(priority) + 1):
            levels = dict(base_profile)
            for attr in priority[:count]:
                levels[attr] = min(levels[attr] + 1, MAX_LEVEL[attr])
            add(levels)
        for attr in priority:
            levels = dict(base_profile)
            levels[attr] = min(levels[attr] + 1, MAX_LEVEL[attr])
            add(levels)
        for pair in combinations(priority[:6], 2):
            levels = dict(base_profile)
            for attr in pair:
                levels[attr] = min(levels[attr] + 1, MAX_LEVEL[attr])
            add(levels)

    tuned = [
        {"age": 1, "hours-per-week": 1},
        {"age": 1, "hours-per-week": 1, "occupation": 1, "native-country": 1},
        {"age": 2, "hours-per-week": 1, "occupation": 1, "education": 1, "native-country": 1},
        {"age": 2, "hours-per-week": 2, "occupation": 1, "education": 1, "workclass": 1, "native-country": 1},
        {"age": 2, "hours-per-week": 2, "occupation": 2, "education": 1, "workclass": 1, "native-country": 2},
        {"age": 3, "hours-per-week": 3, "occupation": 2, "education": 2, "workclass": 2, "native-country": 2},
        {"age": 3, "hours-per-week": 3, "occupation": 3, "education": 2, "workclass": 2, "native-country": 3},
    ]
    for profile in tuned:
        add(profile)
    add({attr: MAX_LEVEL[attr] for attr in QIDS})
    return profiles


def prepare_profile_stats(
    rows: list[dict[str, str]],
    profiles: list[dict[str, int]],
) -> list[dict[str, object]]:
    overall_income = distribution([row["income"] for row in rows])
    stats = []
    for profile in profiles:
        groups = grouped_indices(rows, profile)
        group_info = []
        for indices in groups.values():
            income_counts = Counter(rows[index]["income"] for index in indices)
            class_income = {key: value / len(indices) for key, value in income_counts.items()}
            group_info.append(
                {
                    "indices": indices,
                    "size": len(indices),
                    "income_distinct": len(income_counts),
                    "t_distance": total_variation(class_income, overall_income),
                }
            )
        stats.append(
            {
                "profile": profile,
                "groups": groups,
                "group_info": group_info,
                "generation_loss": generation_loss(profile),
            }
        )
    return stats


def generation_loss(profile: dict[str, int]) -> float:
    return sum(profile[attr] / MAX_LEVEL[attr] for attr in QIDS) / len(QIDS)


def failing_rows(
    rows: list[dict[str, str]],
    groups: dict[tuple[str, ...], list[int]],
    model: str,
    k: int,
    l_value: int,
    t_value: float,
    overall_income: dict[str, float],
) -> set[int]:
    failed: set[int] = set()
    for indices in groups.values():
        incomes = [rows[index]["income"] for index in indices]
        income_counts = Counter(incomes)
        bad = len(indices) < k
        if model == "k_l" and len(income_counts) < l_value:
            bad = True
        if model == "k_t":
            class_income = {key: value / len(indices) for key, value in income_counts.items()}
            if total_variation(class_income, overall_income) > t_value:
                bad = True
        if bad:
            failed.update(indices)
    return failed


def distribution_drift(
    rows: list[dict[str, str]],
    kept_indices: list[int],
    profile: dict[str, int],
) -> float:
    if not kept_indices:
        return 1.0
    drifts = []
    for attr in SELECTED_DISTRIBUTIONS:
        if attr in QIDS:
            original_values = [generalize(attr, row[attr], profile[attr]) for row in rows]
            kept_values = [generalize(attr, rows[index][attr], profile[attr]) for index in kept_indices]
        else:
            original_values = [row[attr] for row in rows]
            kept_values = [rows[index][attr] for index in kept_indices]
        drifts.append(total_variation(distribution(original_values), distribution(kept_values)))
    return sum(drifts) / len(drifts)


def discernibility(groups: dict[tuple[str, ...], list[int]], failed: set[int], total_rows: int) -> float:
    score = 0
    for indices in groups.values():
        kept = [index for index in indices if index not in failed]
        if kept:
            score += len(kept) ** 2
    score += len(failed) * total_rows
    return score / (total_rows**2)


def evaluate_config(
    rows: list[dict[str, str]],
    profile_stats: list[dict[str, object]],
    model: str,
    k: int,
    suppression_limit: float,
    l_value: int = 2,
    t_value: float = 0.2,
) -> tuple[dict[str, str], dict[str, int], set[int], dict[tuple[str, ...], list[int]]]:
    n = len(rows)
    overall_income = distribution([row["income"] for row in rows])
    best = None
    best_failed: set[int] = set()
    best_groups: dict[tuple[str, ...], list[int]] = {}

    for stats in profile_stats:
        profile = stats["profile"]
        groups = stats["groups"]
        group_info = stats["group_info"]
        assert isinstance(profile, dict)
        assert isinstance(groups, dict)
        assert isinstance(group_info, list)
        failed_count = 0
        for info in group_info:
            assert isinstance(info, dict)
            bad = info["size"] < k
            if model == "k_l" and info["income_distinct"] < l_value:
                bad = True
            if model == "k_t" and info["t_distance"] > t_value:
                bad = True
            if bad:
                failed_count += int(info["size"])
        suppression_rate = failed_count / n
        gen_loss = float(stats["generation_loss"])
        total_loss = gen_loss + suppression_rate * (1 - gen_loss)
        feasible = suppression_rate <= suppression_limit
        overflow = max(0.0, suppression_rate - suppression_limit)
        rank = (0 if feasible else 1, overflow, total_loss, suppression_rate, gen_loss)
        if best is None or rank < best[0]:
            best = (rank, profile, groups, suppression_rate, gen_loss, total_loss)

    assert best is not None
    _, best_profile, best_groups, suppression_rate, gen_loss, total_loss = best
    assert isinstance(best_profile, dict)
    assert isinstance(best_groups, dict)
    best_failed = failing_rows(rows, best_groups, model, k, l_value, t_value, overall_income)
    kept_indices = [index for index in range(n) if index not in best_failed]
    kept_groups = {
        key: [index for index in indices if index not in best_failed]
        for key, indices in best_groups.items()
        if any(index not in best_failed for index in indices)
    }
    risk = risk_from_groups(kept_groups, n)
    row = {
        "model": model,
        "k": str(k),
        "l": str(l_value if model == "k_l" else ""),
        "t": str(t_value if model == "k_t" else ""),
        "suppression_limit": f"{suppression_limit:.2f}",
        "suppression_rate": f"{suppression_rate:.6f}",
        "generalization_loss": f"{gen_loss:.6f}",
        "total_information_loss": f"{total_loss:.6f}",
        "discernibility_penalty": f"{discernibility(best_groups, best_failed, n):.6f}",
        "distribution_drift": f"{distribution_drift(rows, kept_indices, best_profile):.6f}",
        "equivalence_classes": str(int(risk["equivalence_classes"])),
        "unique_rows": str(int(risk["unique_rows"])),
        "fraction_unique": f"{risk['fraction_unique']:.6f}",
        "min_class_size": str(int(risk["min_class_size"])),
        "max_prosecutor_risk": f"{risk['max_prosecutor_risk']:.6f}",
        "average_equivalence_risk": f"{risk['average_equivalence_risk']:.6f}",
        "profile": profile_label(best_profile),
        "feasible": str(suppression_rate <= suppression_limit),
    }
    return row, best_profile, best_failed, best_groups


def profile_label(profile: dict[str, int]) -> str:
    return "; ".join(f"{attr}:{profile[attr]}" for attr in QIDS)


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def anonymized_rows(
    rows: list[dict[str, str]],
    profile: dict[str, int],
    failed: set[int],
) -> list[dict[str, str]]:
    output = []
    for index, row in enumerate(rows):
        if index in failed:
            continue
        anon = {}
        for attr in COLUMNS:
            if attr in QIDS:
                anon[attr] = generalize(attr, row[attr], profile[attr])
            elif attr in INSENSITIVE:
                anon[attr] = ""
            elif attr in {"capital-gain", "capital-loss"}:
                value = int_value(row[attr])
                anon[attr] = "0" if value == 0 else "positive"
            else:
                anon[attr] = row[attr]
        output.append(anon)
    return output


def svg_line_plot(
    path: Path,
    title: str,
    series: list[tuple[str, list[tuple[float, float]]]],
    x_label: str,
    y_label: str,
) -> None:
    width, height = 760, 460
    left, right, top, bottom = 70, 30, 55, 70
    colors = ["#246BFE", "#D53F8C", "#2F855A", "#B7791F", "#5A67D8"]
    xs = [x for _, points in series for x, _ in points]
    ys = [y for _, points in series for _, y in points]
    if not xs or not ys:
        return
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if min_x == max_x:
        max_x += 1
    if min_y == max_y:
        max_y += 1
    y_pad = (max_y - min_y) * 0.08
    min_y = max(0.0, min_y - y_pad)
    max_y += y_pad

    def sx(x: float) -> float:
        return left + (x - min_x) / (max_x - min_x) * (width - left - right)

    def sy(y: float) -> float:
        return height - bottom - (y - min_y) / (max_y - min_y) * (height - top - bottom)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-family="Arial" font-size="18" font-weight="700">{html.escape(title)}</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#222"/>',
    ]
    for tick in range(6):
        y = min_y + (max_y - min_y) * tick / 5
        py = sy(y)
        parts.append(f'<line x1="{left-4}" y1="{py:.1f}" x2="{left}" y2="{py:.1f}" stroke="#222"/>')
        parts.append(f'<text x="{left-8}" y="{py+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{y:.2f}</text>')
    for tick in range(6):
        x = min_x + (max_x - min_x) * tick / 5
        px = sx(x)
        parts.append(f'<line x1="{px:.1f}" y1="{height-bottom}" x2="{px:.1f}" y2="{height-bottom+4}" stroke="#222"/>')
        parts.append(f'<text x="{px:.1f}" y="{height-bottom+20}" text-anchor="middle" font-family="Arial" font-size="11">{x:g}</text>')
    parts.append(f'<text x="{width / 2}" y="{height-22}" text-anchor="middle" font-family="Arial" font-size="13">{html.escape(x_label)}</text>')
    parts.append(f'<text transform="translate(18 {height / 2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="13">{html.escape(y_label)}</text>')

    legend_x, legend_y = left + 8, top + 6
    for idx, (name, points) in enumerate(series):
        color = colors[idx % len(colors)]
        coords = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in sorted(points))
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y in points:
            parts.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4" fill="{color}"/>')
        ly = legend_y + idx * 19
        parts.append(f'<rect x="{legend_x}" y="{ly-9}" width="12" height="12" fill="{color}"/>')
        parts.append(f'<text x="{legend_x+18}" y="{ly+2}" font-family="Arial" font-size="12">{html.escape(name)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def svg_scatter_plot(path: Path, title: str, points: list[dict[str, str]]) -> None:
    width, height = 760, 460
    left, right, top, bottom = 75, 30, 55, 70
    colors = {"k_l": "#246BFE", "k_t": "#D53F8C"}
    parsed = [
        (
            row["model"],
            float(row["total_information_loss"]),
            float(row["max_prosecutor_risk"]),
            row["k"],
        )
        for row in points
        if row["feasible"] == "True"
    ]
    if not parsed:
        return
    max_x = max(x for _, x, _, _ in parsed) * 1.08
    max_y = max(y for _, _, y, _ in parsed) * 1.08

    def sx(x: float) -> float:
        return left + x / max_x * (width - left - right)

    def sy(y: float) -> float:
        return height - bottom - y / max_y * (height - top - bottom)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-family="Arial" font-size="18" font-weight="700">{html.escape(title)}</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#222"/>',
        f'<text x="{width / 2}" y="{height-22}" text-anchor="middle" font-family="Arial" font-size="13">Total information loss</text>',
        f'<text transform="translate(18 {height / 2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="13">Max prosecutor risk</text>',
    ]
    for tick in range(6):
        x = max_x * tick / 5
        px = sx(x)
        parts.append(f'<text x="{px:.1f}" y="{height-bottom+20}" text-anchor="middle" font-family="Arial" font-size="11">{x:.2f}</text>')
        y = max_y * tick / 5
        py = sy(y)
        parts.append(f'<text x="{left-8}" y="{py+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{y:.2f}</text>')
    for model, x, y, k_value in parsed:
        color = colors[model]
        parts.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="5" fill="{color}" opacity="0.75"/>')
        parts.append(f'<text x="{sx(x)+7:.1f}" y="{sy(y)+4:.1f}" font-family="Arial" font-size="10">k={html.escape(k_value)}</text>')
    parts.append('<rect x="85" y="60" width="12" height="12" fill="#246BFE"/><text x="103" y="71" font-family="Arial" font-size="12">k + l-diversity</text>')
    parts.append('<rect x="85" y="79" width="12" height="12" fill="#D53F8C"/><text x="103" y="90" font-family="Arial" font-size="12">k + t-closeness</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def original_risk_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    exact_profile = {attr: 0 for attr in QIDS}
    groups = grouped_indices(rows, exact_profile)
    risk = risk_from_groups(groups, len(rows))
    return [
        {
            "qid_set": ", ".join(QIDS),
            "rows": str(len(rows)),
            "equivalence_classes": str(int(risk["equivalence_classes"])),
            "unique_rows": str(int(risk["unique_rows"])),
            "fraction_unique": f"{risk['fraction_unique']:.6f}",
            "min_class_size": str(int(risk["min_class_size"])),
            "max_prosecutor_risk": f"{risk['max_prosecutor_risk']:.6f}",
            "average_equivalence_risk": f"{risk['average_equivalence_risk']:.6f}",
        }
    ]


def make_sweeps(rows: list[dict[str, str]], profiles: list[dict[str, int]]) -> tuple[list[dict[str, str]], dict[str, tuple[dict[str, int], set[int]]]]:
    results: list[dict[str, str]] = []
    selected_outputs: dict[str, tuple[dict[str, int], set[int]]] = {}
    profile_stats = prepare_profile_stats(rows, profiles)
    k_values = [2, 5, 10, 20, 50]
    suppression_limits = [0.00, 0.01, 0.05, 0.10, 0.20]
    t_values = [0.05, 0.10, 0.20, 0.30, 0.50]

    for limit in suppression_limits:
        for k in k_values:
            row, profile, failed, _ = evaluate_config(rows, profile_stats, "k_l", k, limit, l_value=2)
            results.append(row)
            if k == 5 and abs(limit - 0.10) < 1e-9:
                selected_outputs["model_a_k_l"] = (profile, failed)
            row, profile, failed, _ = evaluate_config(rows, profile_stats, "k_t", k, limit, t_value=0.20)
            results.append(row)
            if k == 5 and abs(limit - 0.10) < 1e-9:
                selected_outputs["model_b_k_t"] = (profile, failed)

    for t_value in t_values:
        row, _, _, _ = evaluate_config(rows, profile_stats, "k_t", 5, 0.10, t_value=t_value)
        row["sweep"] = "t_sweep"
        results.append(row)

    for row in results:
        row.setdefault("sweep", "k_suppression_sweep")
    return results, selected_outputs


def write_plots(results: list[dict[str, str]]) -> None:
    balanced = [
        row
        for row in results
        if row["sweep"] == "k_suppression_sweep" and row["suppression_limit"] == "0.10"
    ]
    for metric, title, ylabel in [
        ("max_prosecutor_risk", "Risk vs k, 10% suppression limit", "Max prosecutor risk"),
        ("total_information_loss", "Utility loss vs k, 10% suppression limit", "Total information loss"),
        ("suppression_rate", "Suppression vs k, 10% suppression limit", "Suppression rate"),
    ]:
        series = []
        for model, label in [("k_l", "k + l-diversity"), ("k_t", "k + t-closeness")]:
            points = [
                (float(row["k"]), float(row[metric]))
                for row in balanced
                if row["model"] == model
            ]
            series.append((label, points))
        svg_line_plot(OUT_DIR / f"{metric}_vs_k.svg", title, series, "k", ylabel)

    t_rows = [row for row in results if row["sweep"] == "t_sweep"]
    svg_line_plot(
        OUT_DIR / "t_closeness_sweep.svg",
        "t-closeness parameter sweep, k=5",
        [
            ("risk", [(float(row["t"]), float(row["max_prosecutor_risk"])) for row in t_rows]),
            ("utility loss", [(float(row["t"]), float(row["total_information_loss"])) for row in t_rows]),
        ],
        "t",
        "Metric value",
    )
    svg_scatter_plot(OUT_DIR / "risk_utility_tradeoff.svg", "Risk and utility tradeoff", balanced)


def write_report(
    rows: list[dict[str, str]],
    attribute_rows: list[dict[str, str]],
    original_risk: list[dict[str, str]],
    sweep_rows: list[dict[str, str]],
) -> None:
    best_a = next(
        row
        for row in sweep_rows
        if row["model"] == "k_l" and row["k"] == "5" and row["suppression_limit"] == "0.10"
    )
    best_b = next(
        row
        for row in sweep_rows
        if row["model"] == "k_t" and row["k"] == "5" and row["suppression_limit"] == "0.10"
    )
    original = original_risk[0]
    top_profile_rows = "\n".join(
        f"| `{row['attribute']}` | {row['role']} | {row['distinct_values']} | {row['missing_values']} | {row['distinction']} | {row['separation']} |"
        for row in attribute_rows
    )
    report = f"""# Adult Dataset Privacy/Risk/Utility Analysis

## Dataset And Attribute Roles

The analysis uses `new/data/adult/adult.data`, with {len(rows):,} rows and {len(COLUMNS)} columns. The release scenario assumes demographic and work attributes may be known by an attacker, while financial outcomes are private.

| Attribute | Role | Distinct | Missing | Distinction | Separation |
|---|---|---:|---:|---:|---:|
{top_profile_rows}

No direct identifiers are present. The QID set is `{', '.join(QIDS)}`. The sensitive attributes are `income`, `capital-gain`, and `capital-loss`; `income` is the primary sensitive attribute used by l-diversity and t-closeness.

## Original Re-identification Risk

Using the exact QID values, the original data has {original['equivalence_classes']} equivalence classes. {original['unique_rows']} records are unique on the QID set, so the original fraction of unique rows is {float(original['fraction_unique']):.2%}. The maximum prosecutor risk is {float(original['max_prosecutor_risk']):.2%}, because at least one QID class has size {original['min_class_size']}.

## Anonymization Models

Model A combines `k`-anonymity with distinct `l=2` diversity on `income`. This means each released QID group must contain at least `k` rows and both income values. It directly addresses identity disclosure and simple attribute disclosure.

Model B combines `k`-anonymity with `t`-closeness on `income`. This means each released QID group must contain at least `k` rows and have an income distribution close to the whole dataset. It is stricter against skewed groups than l-diversity.

Both models use the same global recoding hierarchies. Numeric QIDs move from exact values to small bands, broad bands, semantic groups, and finally `*`. Categorical QIDs move from exact categories to semantic groups, broad groups, and finally `*`.

## Balanced Configuration Results

The balanced comparison uses `k=5` and a 10% suppression limit.

| Model | Suppression | Info loss | Distribution drift | Max prosecutor risk | Avg risk | Profile |
|---|---:|---:|---:|---:|---:|---|
| k + l-diversity | {float(best_a['suppression_rate']):.2%} | {float(best_a['total_information_loss']):.3f} | {float(best_a['distribution_drift']):.3f} | {float(best_a['max_prosecutor_risk']):.2%} | {float(best_a['average_equivalence_risk']):.3f} | `{best_a['profile']}` |
| k + t-closeness | {float(best_b['suppression_rate']):.2%} | {float(best_b['total_information_loss']):.3f} | {float(best_b['distribution_drift']):.3f} | {float(best_b['max_prosecutor_risk']):.2%} | {float(best_b['average_equivalence_risk']):.3f} | `{best_b['profile']}` |

## Plots

- `max_prosecutor_risk_vs_k.svg`: re-identification risk as `k` changes.
- `total_information_loss_vs_k.svg`: utility loss as `k` changes.
- `suppression_rate_vs_k.svg`: suppression needed as `k` changes.
- `risk_utility_tradeoff.svg`: combined privacy/utility comparison.
- `t_closeness_sweep.svg`: effect of the `t` parameter for Model B.

## Recommendation

Use Model B when the report wants the stronger sensitive-attribute disclosure argument, because t-closeness checks the income distribution inside each QID group. Use Model A when the priority is a simpler explanation and easier comparison with classic k-anonymity. In both cases, increasing `k` or using stricter `t` tends to reduce re-identification and attribute-disclosure risk, but it increases generalization and may increase suppression.

## AI/Tooling Note

This report draft and its supporting script were produced with AI assistance and then generated from local dataset files. The script uses only standard Python libraries and can be rerun to reproduce the tables and plots.
"""
    (OUT_DIR / "adult_privacy_report_draft.md").write_text(report)


def validate(rows: list[dict[str, str]], selected_outputs: dict[str, tuple[dict[str, int], set[int]]]) -> None:
    assert len(rows) == 32561, f"Unexpected row count: {len(rows)}"
    assert set(rows[0]) == set(COLUMNS)
    for key, (profile, failed) in selected_outputs.items():
        groups = grouped_indices(rows, profile)
        kept_groups = [
            [index for index in indices if index not in failed]
            for indices in groups.values()
        ]
        kept_groups = [indices for indices in kept_groups if indices]
        assert min(len(indices) for indices in kept_groups) >= 5, key
        if key == "model_a_k_l":
            assert all(len({rows[index]["income"] for index in indices}) >= 2 for indices in kept_groups), key
        if key == "model_b_k_t":
            overall_income = distribution([row["income"] for row in rows])
            for indices in kept_groups:
                incomes = Counter(rows[index]["income"] for index in indices)
                class_income = {income: count / len(indices) for income, count in incomes.items()}
                assert total_variation(class_income, overall_income) <= 0.2 + 1e-9, key


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_adult()
    profiles = candidate_profiles()

    attr_rows = attribute_profile(rows)
    original_rows = original_risk_rows(rows)
    sweep_rows, selected_outputs = make_sweeps(rows, profiles)

    validate(rows, selected_outputs)

    write_csv(OUT_DIR / "attribute_profile.csv", attr_rows)
    write_csv(OUT_DIR / "original_risk.csv", original_rows)
    write_csv(OUT_DIR / "sweep_results.csv", sweep_rows)

    for name, (profile, failed) in selected_outputs.items():
        write_csv(OUT_DIR / f"{name}_anonymized.csv", anonymized_rows(rows, profile, failed), COLUMNS)

    write_plots(sweep_rows)
    write_report(rows, attr_rows, original_rows, sweep_rows)

    print(f"Wrote analysis outputs to {OUT_DIR.relative_to(ROOT)}")
    print(f"Rows: {len(rows)}")
    print(f"Candidate hierarchy profiles evaluated: {len(profiles)}")
    print(f"Original unique QID fraction: {float(original_rows[0]['fraction_unique']):.2%}")


if __name__ == "__main__":
    main()
