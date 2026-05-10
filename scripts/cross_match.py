import json
from collections import defaultdict

JP_US_FILE = '/home/nakagawa/FoodCrawler/mext_usda_llm_matched.json'
US_JP_FILE = '/home/nakagawa/FoodCrawler/usda_mext_llm_matched.json'
OUTPUT_FILE = '/home/nakagawa/FoodCrawler/cross_matched.json'

with open(JP_US_FILE) as f:
    jp_us = json.load(f)
with open(US_JP_FILE) as f:
    us_jp = json.load(f)

# JP->US: food_id -> fdc_id
jp_to_us = {}
for r in jp_us:
    if r.get('matched'):
        jp_to_us[r['food_id']] = r['fdc_id']

# US->JP: fdc_id -> food_id
us_to_jp = {}
for r in us_jp:
    if r.get('matched'):
        us_to_jp[r['fdc_id']] = r['food_id']

# JP->USの結果をfdc_idでインデックス化
jp_us_by_fdc = {r['fdc_id']: r for r in jp_us if r.get('matched')}
us_jp_by_fdc = {r['fdc_id']: r for r in us_jp if r.get('matched')}
jp_us_by_food = {r['food_id']: r for r in jp_us if r.get('matched')}

# 双方向一致（A->B かつ B->Aが同じペア）
mutual = []
jp_only = []
us_only = []

for food_id, fdc_id in jp_to_us.items():
    if us_to_jp.get(fdc_id) == food_id:
        # 双方向一致
        jp_r = jp_us_by_food[food_id]
        us_r = us_jp_by_fdc[fdc_id]
        mutual.append({
            'food_id': food_id,
            'food_name_jp': jp_r['food_name_jp'],
            'fdc_id': fdc_id,
            'food_name_en': jp_r['food_name_en'],
            'category_jp': jp_r.get('category_l1', ''),
            'category_en': jp_r.get('usda_category', ''),
            'confidence_jp_us': jp_r.get('confidence', ''),
            'confidence_us_jp': us_r.get('confidence', ''),
            'energy_diff_pct': jp_r.get('energy_diff_pct'),
            'mext_energy': jp_r.get('mext_energy'),
            'usda_energy': jp_r.get('usda_energy'),
            'diff_fat': jp_r.get('diff_fat'),
            'diff_protein': jp_r.get('diff_protein'),
            'diff_carb': jp_r.get('diff_carb'),
            'diff_salt_eq': jp_r.get('diff_salt_eq'),
        })
    else:
        jp_only.append({
            'food_id': food_id,
            'food_name_jp': jp_us_by_food[food_id]['food_name_jp'],
            'fdc_id': fdc_id,
            'food_name_en': jp_us_by_food[food_id]['food_name_en'],
            'us_jp_match': us_to_jp.get(fdc_id, 'NO_MATCH'),
        })

for fdc_id, food_id in us_to_jp.items():
    if jp_to_us.get(food_id) != fdc_id:
        us_only.append({
            'fdc_id': fdc_id,
            'food_name_en': us_jp_by_fdc[fdc_id]['food_name_en'],
            'food_id': food_id,
            'food_name_jp': us_jp_by_fdc[fdc_id]['food_name_jp'],
        })

result = {
    'summary': {
        'mutual_match': len(mutual),
        'jp_us_only': len(jp_only),
        'us_jp_only': len(us_only),
    },
    'mutual': mutual,
    'jp_us_only': jp_only,
    'us_jp_only': us_only,
}

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f'=== 双方向突合結果 ===')
print(f'双方向一致（共通語候補）: {len(mutual)}件')
print(f'JP->USのみマッチ: {len(jp_only)}件')
print(f'US->JPのみマッチ: {len(us_only)}件')
print()

# カテゴリ別集計
from collections import Counter
cat_count = Counter(m['category_jp'] for m in mutual)
print('=== 双方向一致 カテゴリ別 ===')
for cat, n in cat_count.most_common():
    print(f'  {cat}: {n}件')

print(f'\n→ {OUTPUT_FILE}')

# 栄養素差分の平均を再計算
import json
with open('/home/nakagawa/FoodCrawler/cross_matched.json') as f:
    result = json.load(f)
mutual = result['mutual']

NUT_KEYS = [
    'energy_kcal','protein','fat','carb','fiber',
    'Ca','Fe','K','Zn','vit_C','vit_A_RAE',
    'vit_B1','vit_B2','vit_D','vit_B12','salt_eq',
]

print('=== 栄養素差分平均（USDA - 八訂）456件 ===')
for k in NUT_KEYS:
    vals = [m[f'diff_{k}'] for m in mutual if m.get(f'diff_{k}') is not None]
    if vals:
        avg = sum(vals) / len(vals)
        print(f'  {k:12s}: {avg:+.3f}  (n={len(vals)})')
    else:
        print(f'  {k:12s}: データなし')
