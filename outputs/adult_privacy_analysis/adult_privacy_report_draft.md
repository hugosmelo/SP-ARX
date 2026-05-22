# Adult Dataset Privacy/Risk/Utility Analysis

## Dataset And Attribute Roles

The analysis uses `new/data/adult/adult.data`, with 32,561 rows and 15 columns. The release scenario assumes demographic and work attributes may be known by an attacker, while financial outcomes are private.

| Attribute | Role | Distinct | Missing | Distinction | Separation |
|---|---|---:|---:|---:|---:|
| `age` | Quasi-identifier | 73 | 0 | 0.002242 | 0.978678 |
| `workclass` | Quasi-identifier | 9 | 1836 | 0.000276 | 0.497130 |
| `fnlwgt` | Insensitive/excluded | 21648 | 0 | 0.664844 | 0.999962 |
| `education` | Quasi-identifier | 16 | 0 | 0.000491 | 0.809605 |
| `education-num` | Insensitive/excluded | 16 | 0 | 0.000491 | 0.809605 |
| `marital-status` | Quasi-identifier | 7 | 0 | 0.000215 | 0.660129 |
| `occupation` | Quasi-identifier | 15 | 1843 | 0.000461 | 0.902887 |
| `relationship` | Quasi-identifier | 6 | 0 | 0.000184 | 0.732145 |
| `race` | Quasi-identifier | 5 | 0 | 0.000154 | 0.259841 |
| `sex` | Quasi-identifier | 2 | 0 | 0.000061 | 0.442753 |
| `capital-gain` | Sensitive | 119 | 0 | 0.003655 | 0.159318 |
| `capital-loss` | Sensitive | 92 | 0 | 0.002825 | 0.091015 |
| `hours-per-week` | Quasi-identifier | 94 | 0 | 0.002887 | 0.762472 |
| `native-country` | Quasi-identifier | 42 | 583 | 0.001290 | 0.196558 |
| `income` | Sensitive | 2 | 0 | 0.000061 | 0.365652 |

No direct identifiers are present. The QID set is `age, workclass, education, marital-status, occupation, relationship, race, sex, hours-per-week, native-country`. The sensitive attributes are `income`, `capital-gain`, and `capital-loss`; `income` is the primary sensitive attribute used by l-diversity and t-closeness.

## Original Re-identification Risk

Using the exact QID values, the original data has 27515 equivalence classes. 24802 records are unique on the QID set, so the original fraction of unique rows is 76.17%. The maximum prosecutor risk is 100.00%, because at least one QID class has size 1.

## Anonymization Models

Model A combines `k`-anonymity with distinct `l=2` diversity on `income`. This means each released QID group must contain at least `k` rows and both income values. It directly addresses identity disclosure and simple attribute disclosure.

Model B combines `k`-anonymity with `t`-closeness on `income`. This means each released QID group must contain at least `k` rows and have an income distribution close to the whole dataset. It is stricter against skewed groups than l-diversity.

Both models use the same global recoding hierarchies. Numeric QIDs move from exact values to small bands, broad bands, semantic groups, and finally `*`. Categorical QIDs move from exact categories to semantic groups, broad groups, and finally `*`.

## Balanced Configuration Results

The balanced comparison uses `k=5` and a 10% suppression limit.

| Model | Suppression | Info loss | Distribution drift | Max prosecutor risk | Avg risk | Profile |
|---|---:|---:|---:|---:|---:|---|
| k + l-diversity | 7.50% | 0.830 | 0.013 | 20.00% | 0.004 | `age:3; workclass:2; education:2; marital-status:2; occupation:3; relationship:2; race:2; sex:1; hours-per-week:3; native-country:2` |
| k + t-closeness | 0.00% | 0.975 | 0.000 | 0.02% | 0.000 | `age:4; workclass:3; education:3; marital-status:3; occupation:3; relationship:2; race:2; sex:1; hours-per-week:3; native-country:3` |

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
