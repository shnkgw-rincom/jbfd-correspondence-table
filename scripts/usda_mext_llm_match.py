#!/usr/bin/env python3
"""
USDA Foundation Foods → 八訂(MEXT) 逆方向マッチング
- US→JP方向でUS only食品を特定
- 八訂大分類をカテゴリとして使用
- 全栄養素ベクトル距離で候補選定
"""
import json
import time
import os
import requests
import re
import math
from collections import defaultdict

USDA_FILE = '/home/nakagawa/FoodCrawler/usda_filtered_keys.json'
MEXT_FILE = '/home/nakagawa/FoodCrawler/mext_all_keys.json'
OUTPUT_FILE = '/home/nakagawa/FoodCrawler/usda_mext_llm_matched.json'
CHECKPOINT_FILE = '/home/nakagawa/FoodCrawler/usda_mext_llm_checkpoint.json'

API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MODEL = 'claude-haiku-4-5-20251001'
MAX_CANDIDATES = 25
SLEEP = 0.3

# USDAカテゴリ → 八訂大分類対応表（JP→USの逆）
USDA_TO_MEXT = {
    'Cereal Grains and Pasta':      '穀類',
    'Baked Products':               '穀類',
    'Breakfast Cereals':            '穀類',
    'Legumes and Legume Products':  '豆類',
    'Nut and Seed Products':        '種実類',
    'Vegetables and Vegetable Products': '野菜類',
    'Fruits and Fruit Juices':      '果実類',
    'Finfish and Shellfish Products': '魚介類',
    'Beef Products':                '肉類',
    'Pork Products':                '肉類',
    'Poultry Products':             '肉類',
    'Lamb, Veal, and Game Products':'肉類',
    'Sausages and Luncheon Meats':  '肉類',
    'Meat mixed dishes':            '調理加工食品類',
    'Dairy and Egg Products':       '乳類',
    'Fats and Oils':                '油脂類',
    'Sweets':                       '菓子類',
    'Snacks':                       '菓子類',
    'Beverages':                    'し好飲料類',
    'Soups, Sauces, and Gravies':   '調味料・香辛料類',
    'Spices and Herbs':             '調味料・香辛料類',
    'Fast Foods':                   '調理加工食品類',
    'Baby Foods':                   None,  # 八訂に対応なし→US only候補
    'American Indian/Alaska Native Foods': None,
    'Pasta mixed dishes, excludes macaroni and cheese': '調理加工食品類',
    'Chicken, whole pieces':        '肉類',
    'Eggs and omelets':             '卵類',
    'Other vegetables and combinations': '野菜類',
    'Rice mixed dishes':            '調理加工食品類',
    'Restaurant Foods':             '調理加工食品類',
}

NUT_SCALE = {
    'energy_kcal': 900,
    'protein':      50,
    'fat':          90,
    'carb':         90,
    'fiber':        15,
    'Ca':           1200,
    'Fe':           20,
    'K':            3000,
    'Zn':           15,
    'vit_C':        200,
    'vit_A_RAE':    1500,
    'vit_B1':       2,
    'vit_B2':       2,
    'vit_D':        20,
    'vit_B12':      10,
    'salt_eq':      20,
}

def dist(item_a, item_b):
    diffs = []
    for k, s in NUT_SCALE.items():
        a = item_a.get(k)
        b = item_b.get(k)
        if a is not None and b is not None:
            diffs.append(((a - b) / s) ** 2)
    return math.sqrt(sum(diffs)) if diffs else float('inf')

def make_prompt(usda_item, candidates):
    name = usda_item['food_name_en']
    cat = usda_item['food_category']

    nut_lines = []
    nut_map = [
        ('energy_kcal','Energy','kcal'),('protein','Protein','g'),
        ('fat','Fat','g'),('carb','Carb','g'),('fiber','Fiber','g'),
        ('Ca','Ca','mg'),('Fe','Fe','mg'),('K','K','mg'),('Zn','Zn','mg'),
        ('vit_C','VitC','mg'),('vit_A_RAE','VitA','μg'),
        ('vit_B1','VitB1','mg'),('vit_B2','VitB2','mg'),
        ('vit_D','VitD','μg'),('vit_B12','VitB12','μg'),('salt_eq','Salt','g'),
    ]
    for key, label, unit in nut_map:
        v = usda_item.get(key)
        if v is not None:
            nut_lines.append(f'{label}={v}{unit}')
    nut_str = ', '.join(nut_lines)

    cand_lines = []
    for i, c in enumerate(candidates):
        cn = c['food_name_jp'][:40]
        ce = c.get('energy_kcal','N/A')
        cp = c.get('protein','N/A')
        cf = c.get('fat','N/A')
        cc = c.get('carb','N/A')
        cs = c.get('salt_eq','N/A')
        cat_jp = c.get('category_l1_jp','')
        cand_lines.append(
            f'{i+1}. [{cat_jp}] {cn} '
            f'(E={ce}kcal, P={cp}g, F={cf}g, C={cc}g, Salt={cs}g)'
        )
    cand_str = '\n'.join(cand_lines)

    prompt = f"""You are a food scientist matching US food items to Japanese food composition table entries.

US food item:
- Name (EN): {name}
- Category: {cat}
- Nutrients per 100g: {nut_str}

Japanese food composition table (八訂) candidates:
{cand_str}
{len(candidates)+1}. NO_MATCH (no equivalent exists in Japanese food composition table)

Instructions:
- Select the single best match based on BOTH food concept AND nutrient profile similarity
- Common vegetables, fruits, grains, meats, dairy, and basic ingredients available globally
  MUST be matched even if not traditional Japanese foods (okra, mushrooms, mustard greens, etc.)
- Choose NO_MATCH ONLY for foods truly unique to American culture with no Japanese equivalent:
  (e.g., ranch dressing, corn dogs, American BBQ sauce, Native American foods,
   highly processed American snacks with no Japanese counterpart)
- Choose NO_MATCH if no candidate is nutritionally or conceptually close

Respond in JSON only:
{{"match_number": <1-{len(candidates)+1}>, "confidence": "<high|medium|low>", "reason": "<one line>"}}"""

    return prompt

def call_llm(prompt):
    r = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'x-api-key': API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        json={
            'model': MODEL,
            'max_tokens': 150,
            'messages': [{'role': 'user', 'content': prompt}]
        },
        timeout=30
    )
    r.raise_for_status()
    text = r.json()['content'][0]['text'].strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        return json.loads(m.group())
    return None

def main():
    with open(USDA_FILE) as f:
        usda_items = json.load(f)
    with open(MEXT_FILE) as f:
        mext_items = json.load(f)

    print(f'USDA: {len(usda_items)}件, 八訂: {len(mext_items)}件')

    # 八訂を大分類別にインデックス化
    mext_by_cat = defaultdict(list)
    for m in mext_items:
        mext_by_cat[m['category_l1_jp']].append(m)

    # チェックポイント読み込み
    results = []
    done_ids = set()
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            results = json.load(f)
        done_ids = {r['fdc_id'] for r in results}
        print(f'チェックポイント再開: {len(done_ids)}件処理済み')

    matched = sum(1 for r in results if r.get('matched'))
    no_match = sum(1 for r in results if r.get('no_match'))
    errors = sum(1 for r in results if r.get('error'))

    for i, usda in enumerate(usda_items):
        if usda['fdc_id'] in done_ids:
            continue

        cat = usda['food_category']
        mext_cat = USDA_TO_MEXT.get(cat)

        # 対応する八訂カテゴリなし → US only確定
        if mext_cat is None:
            results.append({
                'fdc_id': usda['fdc_id'],
                'food_name_en': usda['food_name_en'],
                'usda_category': cat,
                'matched': False,
                'no_match': True,
                'us_only': True,
                'reason': f'No MEXT category mapped for {cat}',
            })
            no_match += 1
            done_ids.add(usda['fdc_id'])
            continue

        # 候補収集（対応する八訂大分類から）
        candidates = mext_by_cat.get(mext_cat, [])

        if not candidates:
            results.append({
                'fdc_id': usda['fdc_id'],
                'food_name_en': usda['food_name_en'],
                'usda_category': cat,
                'matched': False,
                'no_match': True,
                'reason': 'No MEXT candidates found',
            })
            no_match += 1
            done_ids.add(usda['fdc_id'])
            continue

        # 全栄養素ベクトル距離で候補をソート
        candidates_sorted = sorted(
            [c for c in candidates if c.get('energy_kcal') is not None],
            key=lambda c: dist(usda, c)
        )[:MAX_CANDIDATES]

        if not candidates_sorted:
            candidates_sorted = candidates[:MAX_CANDIDATES]

        # LLM呼び出し
        try:
            prompt = make_prompt(usda, candidates_sorted)
            result = call_llm(prompt)
            time.sleep(SLEEP)

            if result is None:
                results.append({
                    'fdc_id': usda['fdc_id'],
                    'food_name_en': usda['food_name_en'],
                    'usda_category': cat,
                    'error': True,
                    'reason': 'LLM parse error',
                })
                errors += 1
            else:
                match_num = result.get('match_number', len(candidates_sorted)+1)
                confidence = result.get('confidence', 'low')
                reason = result.get('reason', '')
                is_no_match = (match_num > len(candidates_sorted))

                if is_no_match:
                    results.append({
                        'fdc_id': usda['fdc_id'],
                        'food_name_en': usda['food_name_en'],
                        'usda_category': cat,
                        'matched': False,
                        'no_match': True,
                        'confidence': confidence,
                        'reason': reason,
                    })
                    no_match += 1
                    print(f'[{i+1}] NO_MATCH: {usda["food_name_en"][:50]} ({reason[:60]})')
                else:
                    mext_match = candidates_sorted[match_num - 1]
                    mext_e = mext_match.get('energy_kcal')
                    usda_e = usda.get('energy_kcal')
                    diff_pct = None
                    if mext_e and usda_e and mext_e > 0 and usda_e > 0:
                        mean_e = (mext_e + usda_e) / 2
                        diff_pct = round(abs(mext_e - usda_e) / mean_e * 100, 1)

                    nut_keys = ['energy_kcal','protein','fat','carb','fiber',
                                'Ca','Fe','K','Zn','vit_C','vit_A_RAE',
                                'vit_B1','vit_B2','vit_D','vit_B12','salt_eq']
                    nut_diff = {}
                    for k in nut_keys:
                        mv = mext_match.get(k)
                        uv = usda.get(k)
                        if mv is not None and uv is not None:
                            nut_diff[f'diff_{k}'] = round(uv - mv, 3)

                    results.append({
                        'fdc_id': usda['fdc_id'],
                        'food_name_en': usda['food_name_en'],
                        'usda_category': cat,
                        'matched': True,
                        'no_match': False,
                        'food_id': mext_match['food_id'],
                        'food_name_jp': mext_match['food_name_jp'],
                        'mext_category': mext_match['category_l1_jp'],
                        'confidence': confidence,
                        'reason': reason,
                        'energy_diff_pct': diff_pct,
                        'usda_energy': usda_e,
                        'mext_energy': mext_e,
                        **nut_diff,
                    })
                    matched += 1
                    flag = '✓' if confidence == 'high' else '△'
                    print(f'[{i+1}] {flag} {usda["food_name_en"][:40]} → {mext_match["food_name_jp"][:25]} ({confidence}, ΔE={diff_pct}%)')

        except Exception as e:
            results.append({
                'fdc_id': usda['fdc_id'],
                'food_name_en': usda['food_name_en'],
                'usda_category': cat,
                'error': True,
                'reason': str(e),
            })
            errors += 1
            print(f'[{i+1}] ERROR: {usda["food_name_en"][:40]} - {e}')

        done_ids.add(usda['fdc_id'])

        if len(results) % 200 == 0:
            with open(CHECKPOINT_FILE, 'w') as f:
                json.dump(results, f, ensure_ascii=False)
            total = len(results)
            print(f'\n--- {total}件処理 | マッチ={matched} NO_MATCH={no_match} エラー={errors} ---\n')

    # 最終保存
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total = len(results)
    print(f'\n=== 完了 ===')
    print(f'総件数: {total}')
    print(f'マッチ成功: {matched}件 ({matched/total*100:.1f}%)')
    print(f'NO_MATCH: {no_match}件 ({no_match/total*100:.1f}%)')
    print(f'エラー: {errors}件')

    # US only カテゴリ集計
    from collections import Counter
    no_match_items = [r for r in results if r.get('no_match')]
    us_only_by_cat = Counter(r['usda_category'] for r in no_match_items)

    us_only_output = '/home/nakagawa/FoodCrawler/us_only_foods.json'
    us_only_data = {
        'total_no_match': len(no_match_items),
        'by_usda_category': dict(us_only_by_cat.most_common()),
        'examples': [
            {'fdc_id': r['fdc_id'], 'name': r['food_name_en'],
             'category': r['usda_category'], 'reason': r.get('reason','')}
            for r in no_match_items[:100]
        ]
    }
    with open(us_only_output, 'w', encoding='utf-8') as f:
        json.dump(us_only_data, f, ensure_ascii=False, indent=2)

    print(f'\n=== US only カテゴリ（NO_MATCH {len(no_match_items)}件） ===')
    for cat, n in us_only_by_cat.most_common(20):
        pct = n / total * 100
        print(f'  {cat}: {n}件 ({pct:.1f}%)')
    print(f'→ {us_only_output}')
    print(f'→ {OUTPUT_FILE}')

if __name__ == '__main__':
    main()
