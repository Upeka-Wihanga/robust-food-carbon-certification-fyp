# Dataset audit

All 14 listed handoff entries and the three raw-source files passed SHA-256 and byte-length checks. The exact filenames and raw byte identities are recorded in the source manifest. The historical experiment preparation also checked 78 Stage 18 and 27 Stage 24 archived file entries. [Source manifest](../data/manifests/source_files.json)

## FCID/WWEIA

The snapshot contains 129,863 rows and 7,154 distinct food codes, with zero exact duplicate rows and 40 rows missing a commodity code or mass. The active loader retained all rows across 12,069 food/modification groups. It normalized 12,029 groups, marked 40 as missing composition, and identified zero source-order violations. The historical positive-weight baseline used 64,225 rows, of which 1,547 rows across 111 distinct commodity codes and 272 affected foods lacked a linkage. Full legacy FCID100 selection and the derivation of the historical impact-variance comparator use supplied identities/results. [EPA recipe database](https://fcid.foodrisk.org/dbc/)

## dataFIELD

The archived linkage audit found 354 usable unique commodity links, two zero factors, zero negative factors and one missing scaled SD. Active normalization kept the same 354 observations across 999 examined worksheet rows, recording 645 blank rows. Factors used in the model retain the source kg CO₂e per kg unit and category/proxy flags. The source-based standard-deviation boxes are variability scenarios. [University of Michigan dataFIELD](https://css.umich.edu/page/datafield)

## Guan61 and the secondary cohorts

- Parsed 308 of 320 source recipe rows. Independent reconstruction retained 61 recipes across eight cuisines and matched all 222 frozen within-cuisine pairs. Maximum retained relative source-production reconstruction error was 0.000607925.
- Under the positive-mass archival convention there were 147 direct major, 251 direct minor and 219 fallback minor occurrences. The audit reports excluded major ingredients and recipe-level exclusion reasons, including unmapped production factors. Equal duplicate names for duck and red bell pepper were observed in the normalized factor table.
- The Stage 26 frozen rebuild retains 14 explicit zero-mass occurrences. It has 210 unique M2 factor keys versus 207 with positive mass only. This is a material rank/factor-state difference between the two conventions. Stage 26 hashes match its previously frozen recipe and pair IDs, and the audit preserves both conventions. Its minor fallback limits are 1.14500 and 4.76300.
- The source includes production, post-farmgate, and cooking estimates. The cohort fidelity check uses the production field. Guan86 remains a secondary mapping-complete sensitivity cohort. [Guan et al. source and workbook description](https://pmc.ncbi.nlm.nih.gov/articles/PMC13737097/)

Exact byte identities establish alignment with the archived intake. The audit did not separately download and hash three fresh publisher distributions. Raw datasets and review packets remain in ignored local directories. Output includes the full exclusions and linkage summary in `.cache/windows-datasets.json`.
