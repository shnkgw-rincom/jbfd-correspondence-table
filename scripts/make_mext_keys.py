#!/usr/bin/env python3
"""
八訂（MEXT）全品目の全栄養素キーファイルを生成
LLMマッチング用インプット
"""
import pandas as pd
import numpy as np
import json

EXCEL = '20201225-mxt_kagsei-mext_01110_012.xlsx'
OUTPUT = 'mext_all_keys.json'

# 列マッピング（成分識別子→列番号→キー名）
COL_MAP = {
    6:  'energy_kcal',
    7:  'water',
    9:  'protein',
    10: 'fat',
    11: 'cholesterol',
    13: 'carb',
    18: 'fiber',
    21: 'organic_acid',
    22: 'ash',
    24: 'K',
    25: 'Ca',
    26: 'Mg',
    27: 'P',
    28: 'Fe',
    29: 'Zn',
    30: 'Cu',
    31: 'Mn',
    33: 'I',
    34: 'Se',
    35: 'Cr',
    36: 'Mo',
    37: 'vit_A_retinol',
    41: 'vit_A_RAE',
    43: 'vit_D',
    44: 'vit_E',
    48: 'vit_K',
    49: 'vit_B1',
    50: 'vit_B2',
    51: 'niacin',
    53: 'vit_B6',
    54: 'vit_B12',
    55: 'folate',
    56: 'pantothenic_acid',
    57: 'biotin',
    58: 'vit_C',
    60: 'salt_eq',
}

# 八訂大分類→中分類マッピング
SHEET_CAT = {
    '1穀類': ('穀類', 'Cereals'),
    '2いも及びでん粉類': ('いも・でん粉類', 'Potatoes and starches'),
    '3砂糖及び甘味類': ('砂糖・甘味類', 'Sugars and sweeteners'),
    '4豆類': ('豆類', 'Legumes'),
    '5種実類': ('種実類', 'Nuts and seeds'),
    '6野菜類': ('野菜類', 'Vegetables'),
    '7果実類': ('果実類', 'Fruits'),
    '8きのこ類': ('きのこ類', 'Mushrooms'),
    '9藻類': ('藻類', 'Algae/Seaweeds'),
    '10魚介類': ('魚介類', 'Fish and shellfish'),
    '11肉類': ('肉類', 'Meat'),
    '12鶏卵': ('卵類', 'Eggs'),
    '13乳類': ('乳類', 'Dairy'),
    '14油脂類': ('油脂類', 'Fats and oils'),
    '15菓子類': ('菓子類', 'Confectionery'),
    '16し好飲料': ('し好飲料類', 'Beverages'),
    '17調味料及び香辛料': ('調味料・香辛料類', 'Seasonings and spices'),
    '18調理済み流通食品類': ('調理加工食品類', 'Processed foods'),
}

def safe_num(val):
    if pd.isna(val): return None
    s = str(val).replace('(','').replace(')','').strip()
    if s in ['*','-','Tr','','nan']: return None
    try: return float(s)
    except: return None

xl = pd.ExcelFile(EXCEL)
all_items = []

for sheet_name in xl.sheet_names[1:]:
    if sheet_name not in SHEET_CAT:
        continue
    cat_jp, cat_en = SHEET_CAT[sheet_name]
    
    df = pd.read_excel(EXCEL, sheet_name=sheet_name, header=None)
    valid = df.iloc[12:][df.iloc[12:][0].notna() & df.iloc[12:][3].notna()]
    
    for _, row in valid.iterrows():
        food_id = str(row[1]).strip()
        food_name_jp = str(row[3]).strip()
        
        # 中分類の推定（食品名に括弧で囲まれた部分）
        import re
        sub_cat = ''
        m = re.match(r'[＜<](.+?)[＞>]', food_name_jp)
        if m:
            sub_cat = m.group(1)
        elif food_name_jp.startswith('（'):
            m2 = re.match(r'（(.+?)）', food_name_jp)
            if m2:
                sub_cat = m2.group(1)
        
        # 全栄養素読み込み
        nutrients = {}
        for col, key in COL_MAP.items():
            if col < len(row):
                nutrients[key] = safe_num(row[col])
        
        item = {
            'food_id': food_id,
            'food_name_jp': food_name_jp,
            'category_l1_jp': cat_jp,
            'category_l1_en': cat_en,
            'category_l2': sub_cat,
        }
        item.update(nutrients)
        all_items.append(item)

print(f'総品目数: {len(all_items)}')
print(f'大分類別:')
from collections import Counter
cats = Counter(d['category_l1_jp'] for d in all_items)
for cat, n in sorted(cats.items()):
    print(f'  {cat}: {n}件')

# 栄養素の充填率確認
print(f'\n主要栄養素の充填率:')
for key in ['energy_kcal','protein','fat','carb','K','Ca','Fe','vit_C','vit_B1','salt_eq']:
    filled = sum(1 for d in all_items if d.get(key) is not None)
    print(f'  {key}: {filled}/{len(all_items)} ({filled/len(all_items)*100:.1f}%)')

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(all_items, f, ensure_ascii=False, indent=2)

print(f'\n→ {OUTPUT} 保存完了')

# サンプル表示
print('\nサンプル（アマランサス）:')
print(json.dumps(all_items[0], ensure_ascii=False, indent=2))
