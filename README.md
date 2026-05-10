# Japan–US Food Composition Correspondence Table, Version 0.1

**Bidirectional LLM-matched pairs between the Japanese Standard Tables of Food Composition 2020 (8th edition) and the USDA FoodData Central**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20103327.svg)](https://doi.org/10.5281/zenodo.20103327)

---

## Overview

This repository provides the first systematic correspondence table between two of the world's most widely used national food composition databases:

- **MEXT**: Standard Tables of Food Composition in Japan 2020 (8th edition) — Ministry of Education, Culture, Sports, Science and Technology, Japan
- **USDA FDC**: USDA FoodData Central (Foundation Foods + SR Legacy) — U.S. Department of Agriculture

The table was generated using a bidirectional large language model (LLM)-based matching pipeline and contains **435 confirmed food pairs** validated by bidirectional consensus matching.

This is **Version 0.1**. Individual matches may contain errors. Users are encouraged to verify entries and report discrepancies via [GitHub Issues](../../issues).

---

## Data

### `data/correspondence_v0.1.csv`

| Column | Description |
|--------|-------------|
| `food_id` | MEXT food ID (8th edition) |
| `category_l1_jp` | MEXT major food category (Japanese) |
| `food_name_jp` | Food name (Japanese) |
| `fdc_id` | USDA FoodData Central FDC ID |
| `food_name_en` | Food name (English) |
| `usda_category` | USDA food category |
| `jp_energy_kcal` | Energy, MEXT (kcal/100g) |
| `us_energy_kcal` | Energy, USDA FDC (kcal/100g) |
| `jp_protein` | Protein, MEXT (g/100g) |
| `us_protein` | Protein, USDA FDC (g/100g) |
| `jp_fat` | Fat, MEXT (g/100g) |
| `us_fat` | Fat, USDA FDC (g/100g) |
| `jp_carb` | Carbohydrate, MEXT (g/100g) |
| `us_carb` | Carbohydrate, USDA FDC (g/100g) |
| `jp_fiber` | Dietary fiber, MEXT (g/100g) |
| `us_fiber` | Dietary fiber, USDA FDC (g/100g) |
| `jp_Ca` | Calcium, MEXT (mg/100g) |
| `us_Ca` | Calcium, USDA FDC (mg/100g) |
| `jp_Fe` | Iron, MEXT (mg/100g) |
| `us_Fe` | Iron, USDA FDC (mg/100g) |
| `jp_K` | Potassium, MEXT (mg/100g) |
| `us_K` | Potassium, USDA FDC (mg/100g) |
| `jp_Zn` | Zinc, MEXT (mg/100g) |
| `us_Zn` | Zinc, USDA FDC (mg/100g) |
| `jp_vit_C` | Vitamin C, MEXT (mg/100g) |
| `us_vit_C` | Vitamin C, USDA FDC (mg/100g) |
| `jp_vit_A_RAE` | Vitamin A as RAE, MEXT (μg/100g) |
| `us_vit_A_RAE` | Vitamin A as RAE, USDA FDC (μg/100g) |
| `jp_vit_B1` | Vitamin B1, MEXT (mg/100g) |
| `us_vit_B1` | Vitamin B1, USDA FDC (mg/100g) |
| `jp_vit_B2` | Vitamin B2, MEXT (mg/100g) |
| `us_vit_B2` | Vitamin B2, USDA FDC (mg/100g) |
| `jp_vit_D` | Vitamin D, MEXT (μg/100g) |
| `us_vit_D` | Vitamin D, USDA FDC (μg/100g) |
| `jp_vit_B12` | Vitamin B12, MEXT (μg/100g) |
| `us_vit_B12` | Vitamin B12, USDA FDC (μg/100g) |
| `jp_salt_eq` | Salt equivalent, MEXT (g/100g) |
| `us_salt_eq` | Salt equivalent, USDA FDC (g/100g) |

---

## Methods

Matching was performed using a three-step pipeline:

1. **Category pre-filtering**: Manual mapping between MEXT major food categories and USDA food categories
2. **Nutrient distance ranking**: Top 25 candidates selected by Euclidean distance over 17 normalized nutrient variables
3. **LLM judgment**: Claude Haiku (Anthropic) selected the best conceptual and nutritional match, or designated NO_MATCH

Bidirectional matching was performed independently (MEXT→FDC and FDC→MEXT). Only pairs confirmed in both directions were included. USDA Survey (FNDDS) data were excluded.

Full methodological details are provided in the accompanying paper (see Citation).

---

## Key Findings

Analysis of the 435 confirmed pairs revealed systematic cross-national differences:

| Nutrient | Mean difference (FDC − MEXT) | Direction |
|----------|------------------------------|-----------|
| Calcium | +6.0 mg/100g | FDC higher (12/13 categories) |
| Potassium | −3.7 mg/100g | MEXT higher (9/13 categories) |
| Vitamin A | −3.7 μg RAE/100g | MEXT higher (8/13 categories) |

These patterns likely reflect structural differences in food supply, agricultural practices, and fortification policies between Japan and the United States.

---

## Limitations and Version History

**Version 0.1 (May 2026)**
- 435 bidirectional consensus pairs across 13 MEXT food categories
- 5 categories yielded no matches (Japan-specific food groups: seaweeds, mushrooms, starchy roots/starches, sugars, eggs)
- Individual matches have not been manually verified
- Known issues and corrections are tracked in [GitHub Issues](../../issues)

We welcome error reports and corrections from the research community. Verified corrections will be incorporated in future versions.

---

## Citation

If you use this correspondence table, please cite:

> Nakagawa S, Yamamoto A. Establishing a Bidirectional Correspondence Table between the Japanese Standard Tables of Food Composition 2020 (8th Edition) and the USDA FoodData Central Using Large Language Model-Based Matching. *Journal of Food Composition and Analysis*. 2026 (in press).

For the dataset itself:

> Nakagawa S, Yamamoto A. Japan–US Food Composition Correspondence Table, Version 0.1. Zenodo. 2026. https://doi.org/10.5281/zenodo.20103327

---

## Data Sources

- MEXT: https://www.mext.go.jp/a_menu/syokuhinseibun/mext_01110.html
- USDA FoodData Central: https://fdc.nal.usda.gov/

---

## License

This dataset is released under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/).

---

## Contact

Shin-ichi Nakagawa  
Research Institute of Info-Communication Medicine (RinCOM)  
GitHub Issues: https://github.com/shnkgw-rincom/jbfd-correspondence-table/issues
