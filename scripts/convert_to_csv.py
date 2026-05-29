"""
convert_to_csv.py
-----------------
Converts the UCI Adult (Census Income) dataset files into properly
formatted CSV files with headers.

Input files expected in the same directory as this script:
  - adult.data  (training set, ~32 561 rows)
  - adult.test  (test set,     ~16 281 rows)

Output files written to the same directory:
  - adult_train.csv
  - adult_test.csv
"""

import csv
import pathlib
import sys

# ------------------------------------------------------------------
# Column names (from adult.names)
# ------------------------------------------------------------------
COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education_num",
    "marital_status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital_gain",
    "capital_loss",
    "hours_per_week",
    "native_country",
    "income",           # label: <=50K or >50K
]

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def parse_row(raw: str) -> list[str] | None:
    """Strip whitespace / trailing period from every field.
    Returns None for blank lines."""
    raw = raw.strip()
    if not raw:
        return None
    fields = [f.strip().rstrip(".") for f in raw.split(",")]
    if len(fields) != len(COLUMNS):
        return None          # skip malformed rows silently
    return fields


def convert(src: pathlib.Path, dst: pathlib.Path, *, skip_header_rows: int = 0) -> int:
    """Convert one raw data file to a proper CSV.

    Args:
        src:              Path to the source .data / .test file.
        dst:              Path for the output .csv file.
        skip_header_rows: Number of leading lines to skip (the test file
                          starts with one '|'-prefixed comment line).

    Returns:
        Number of data rows written.
    """
    written = 0
    skipped = 0

    with src.open(encoding="utf-8", errors="replace") as fin, \
         dst.open("w", newline="", encoding="utf-8") as fout:

        writer = csv.writer(fout)
        writer.writerow(COLUMNS)          # header

        for i, line in enumerate(fin):
            if i < skip_header_rows:
                continue                  # skip leading metadata / blank lines

            row = parse_row(line)
            if row is None:
                skipped += 1
                continue

            writer.writerow(row)
            written += 1

    print(f"  {src.name:20s}  ->  {dst.name}  "
          f"({written:,} rows written, {skipped} skipped)", flush=True)
    return written


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    base = pathlib.Path(__file__).parent

    jobs = [
        # (source file,       output file,         leading rows to skip)
        ("adult.data", "adult_train.csv", 0),
        ("adult.test", "adult_test.csv",  1),   # test file has 1 header line
    ]

    total = 0
    for src_name, dst_name, skip in jobs:
        src = base / src_name
        dst = base / dst_name

        if not src.exists():
            print(f"[WARNING] {src} not found – skipping.", file=sys.stderr)
            continue

        total += convert(src, dst, skip_header_rows=skip)

    print(f"\nDone. {total:,} total rows written across {len(jobs)} file(s).")


if __name__ == "__main__":
    main()
