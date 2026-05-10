#!/usr/bin/env python3
"""
USDA FoodData Central から Survey (FNDDS) を除外して
Foundation Foods + SR Legacy のみを抽出する
"""
import json

input_file = 'usda_all_keys.json'
output_file = 'usda_filtered_keys.json'

with open(input_file) as f:
    data = json.load(f)

filtered = [d for d in data if d.get('data_type') in ('Foundation', 'SR Legacy')]

print(f'元: {len(data)}件')
print(f'除外後: {len(filtered)}件（Foundation + SR Legacy）')
print(f'除外: {len(data)-len(filtered)}件（Survey/FNDDS）')

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(filtered, f, ensure_ascii=False)

print(f'→ {output_file}')
