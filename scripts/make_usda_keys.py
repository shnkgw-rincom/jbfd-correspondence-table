#!/usr/bin/env python3
"""
USDA Foundation Foods全品目のキーファイルを生成
八訂と共通の栄養素項目に統一
"""
import json

INPUT = '/home/nakagawa/usda_foundation_all.json'
OUTPUT = '/home/nakagawa/FoodCrawler/usda_all_keys.json'

with open(INPUT) as f:
    data = json.load(f)

print(f'USDA総品目数: {len(data)}')

items = []
for d in data:
    # Na(mg) → 食塩相当量(g)
    na = d.get('sodium_mg')
    salt = round(na * 2.54 / 1000, 3) if na is not None else None

    item = {
        'fdc_id': d.get('fdc_id'),
        'food_name_en': d.get('description', ''),
        'food_category': d.get('food_category', ''),
        'data_type': d.get('data_type', ''),
        # 共通栄養素（八訂と同じキー名に統一）
        'energy_kcal': d.get('energy_kcal'),
        'protein':     d.get('protein_g'),
        'fat':         d.get('fat_g'),
        'carb':        d.get('carb_g'),
        'fiber':       d.get('fiber_g'),
        'cholesterol': d.get('cholesterol_mg'),
        'Ca':          d.get('calcium_mg'),
        'Fe':          d.get('iron_mg'),
        'K':           d.get('potassium_mg'),
        'Zn':          d.get('zinc_mg'),
        'vit_C':       d.get('vit_c_mg'),
        'vit_A_RAE':   d.get('vit_a_ug'),
        'vit_B1':      d.get('vit_b1_mg'),
        'vit_B2':      d.get('vit_b2_mg'),
        'vit_B12':     d.get('vit_b12_ug'),
        'vit_D':       d.get('vit_d_ug'),
        'salt_eq':     salt,
    }
    items.append(item)

# カテゴリ別品目数
from collections import Counter
cats = Counter(d['food_category'] for d in items)
print(f'\nUSDAカテゴリ数: {len(cats)}')
print('主要カテゴリ（上位20）:')
for cat, n in cats.most_common(20):
    print(f'  {n:5d}件  {cat}')

# 栄養素充填率
print('\n主要栄養素の充填率:')
keys = ['energy_kcal','protein','fat','carb','K','Ca','Fe','Zn','vit_C','vit_B1','salt_eq']
for key in keys:
    filled = sum(1 for d in items if d.get(key) is not None)
    print(f'  {key}: {filled}/{len(items)} ({filled/len(items)*100:.1f}%)')

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f'\n→ {OUTPUT} 保存完了')
print('\nサンプル:')
print(json.dumps(items[0], ensure_ascii=False, indent=2))
