#!/usr/bin/env python3
"""
八訂(MEXT) × USDA Foundation Foods LLMマッチング
- 翻訳不要：食品名(JP)+大分類+全栄養素ベクトルで判断
- 八訂大分類→USDAカテゴリに絞って候補提示
- NO_MATCH選択肢あり（日本固有食品を適切に検出）
"""
import json
import time
import os
import requests
import re
from collections import defaultdict

MEXT_FILE = '/home/nakagawa/FoodCrawler/mext_all_keys.json'
USDA_FILE = '/home/nakagawa/FoodCrawler/usda_filtered_keys.json'
OUTPUT_FILE = '/home/nakagawa/FoodCrawler/mext_usda_llm_matched.json'
CHECKPOINT_FILE = '/home/nakagawa/FoodCrawler/mext_usda_llm_checkpoint.json'

API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MODEL = 'claude-haiku-4-5-20251001'
MAX_CANDIDATES = 25
SLEEP = 0.3

# 八訂大分類 → USDAカテゴリ対応表
CAT_MAP = {
    '穀類': [
        'Cereal Grains and Pasta',
        'Baked Products',
        'Breakfast Cereals',
    ],
    'いも・でん粉類': [
        'Vegetables and Vegetable Products',
    ],
    '砂糖・甘味類': [
        'Sweets',
    ],
    '豆類': [
        'Legumes and Legume Products',
    ],
    '種実類': [
        'Nut and Seed Products',
    ],
    '野菜類': [
        'Vegetables and Vegetable Products',
        'Soups, Sauces, and Gravies',
    ],
    '果実類': [
        'Fruits and Fruit Juices',
    ],
    'きのこ類': [
        'Vegetables and Vegetable Products',
    ],
    '藻類': [
        'Vegetables and Vegetable Products',
        'Finfish and Shellfish Products',
    ],
    '魚介類': [
        'Finfish and Shellfish Products',
        'Soups, Sauces, and Gravies',
    ],
    '肉類': [
        'Beef Products',
        'Pork Products',
        'Poultry Products',
        'Lamb, Veal, and Game Products',
        'Sausages and Luncheon Meats',
        'Meat mixed dishes',
    ],
    '卵類': [
        'Dairy and Egg Products',
    ],
    '乳類': [
        'Dairy and Egg Products',
    ],
    '油脂類': [
        'Fats and Oils',
    ],
    '菓子類': [
        'Sweets',
        'Snacks',
        'Baked Products',
    ],
    'し好飲料類': [
        'Beverages',
    ],
    '調味料・香辛料類': [
        'Soups, Sauces, and Gravies',
        'Spices and Herbs',
        'Fats and Oils',
    ],
    '調理加工食品類': [
        'Fast Foods',
        'Soups, Sauces, and Gravies',
        'Meat mixed dishes',
    ],
}

# 日本固有食品（NO_MATCH候補）
JP_UNIQUE = [
    '納豆', 'こんにゃく', 'こんにゃく', 'ふ', 'みそ', 'しょうゆ', 'だし',
    '海藻', 'のり', 'わかめ', 'こんぶ', 'ひじき', 'もずく',
    '米菓', 'せんべい', 'おかき', '和菓子', 'あんこ', '餅',
    '水産練り製品', 'かまぼこ', 'ちくわ', 'さつま揚げ', 'はんぺん',
    'つくだ煮', 'ぬか漬け', 'たくあん', 'きりたんぽ',
    'だし巻き', '茶碗蒸し',
]

def fmt_nut(val, unit=''):
    if val is None: return 'N/A'
    return f'{val}{unit}'

def make_prompt(mext_item, candidates):
    """LLMへのプロンプト生成"""
    name = mext_item['food_name_jp']
    cat = mext_item['category_l1_jp']
    cat_en = mext_item['category_l1_en']
    sub = mext_item.get('category_l2', '')

    # 栄養素サマリー（主要17項目）
    nut_lines = []
    nut_map = [
        ('energy_kcal', 'Energy', 'kcal'),
        ('protein', 'Protein', 'g'),
        ('fat', 'Fat', 'g'),
        ('carb', 'Carb', 'g'),
        ('fiber', 'Fiber', 'g'),
        ('Ca', 'Ca', 'mg'),
        ('Fe', 'Fe', 'mg'),
        ('K', 'K', 'mg'),
        ('Zn', 'Zn', 'mg'),
        ('vit_C', 'VitC', 'mg'),
        ('vit_A_RAE', 'VitA', 'μg'),
        ('vit_B1', 'VitB1', 'mg'),
        ('vit_B2', 'VitB2', 'mg'),
        ('vit_D', 'VitD', 'μg'),
        ('vit_B12', 'VitB12', 'μg'),
        ('salt_eq', 'Salt', 'g'),
    ]
    for key, label, unit in nut_map:
        v = mext_item.get(key)
        if v is not None:
            nut_lines.append(f'{label}={v}{unit}')

    nut_str = ', '.join(nut_lines)

    # 候補リスト
    cand_lines = []
    for i, c in enumerate(candidates):
        cn = c['food_name_en'][:60]
        ce = fmt_nut(c.get('energy_kcal'), 'kcal')
        cp = fmt_nut(c.get('protein'), 'g')
        cf = fmt_nut(c.get('fat'), 'g')
        cc = fmt_nut(c.get('carb'), 'g')
        cs = fmt_nut(c.get('salt_eq'), 'g')
        cand_lines.append(
            f'{i+1}. [{c["food_category"]}] {cn} '
            f'(E={ce}, P={cp}, F={cf}, C={cc}, Salt={cs})'
        )
    cand_str = '\n'.join(cand_lines)

    prompt = f"""You are a food scientist matching Japanese food items to USDA food database entries.

Japanese food item:
- Name (JP): {name}
- Category: {cat} ({cat_en}){f" > {sub}" if sub else ""}
- Nutrients per 100g: {nut_str}

USDA candidates:
{cand_str}
{len(candidates)+1}. NO_MATCH (no equivalent exists in US food supply)

Instructions:
- Select the single best match based on BOTH food category/name AND nutrient profile similarity
- Prefer exact or near-exact food concept matches over nutrient similarity alone
- Choose NO_MATCH for Japan-specific foods (natto, miso, konnyaku, seaweed products, fish paste products, traditional Japanese confectionery, dashi, etc.)
- Choose NO_MATCH if no candidate is nutritionally or conceptually close

Respond in JSON only:
{{"match_number": <1-{len(candidates)+1}>, "confidence": "<high|medium|low>", "reason": "<one line>"}}"""

    return prompt

def call_llm(prompt):
    """Claude API呼び出し"""
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
    with open(MEXT_FILE) as f:
        mext_items = json.load(f)
    with open(USDA_FILE) as f:
        usda_items = json.load(f)

    print(f'八訂: {len(mext_items)}件, USDA: {len(usda_items)}件')

    # USDAをカテゴリ別にインデックス化
    usda_by_cat = defaultdict(list)
    for u in usda_items:
        usda_by_cat[u['food_category']].append(u)

    # チェックポイント読み込み
    results = []
    done_ids = set()
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            results = json.load(f)
        done_ids = {r['food_id'] for r in results}
        print(f'チェックポイント再開: {len(done_ids)}件処理済み')

    matched = sum(1 for r in results if r.get('matched'))
    no_match = sum(1 for r in results if r.get('no_match'))
    errors = sum(1 for r in results if r.get('error'))

    for i, mext in enumerate(mext_items):
        if mext['food_id'] in done_ids:
            continue

        cat = mext['category_l1_jp']
        usda_cats = CAT_MAP.get(cat, [])

        # 候補収集
        candidates = []
        for uc in usda_cats:
            candidates.extend(usda_by_cat.get(uc, []))

        # 候補なし → NO_MATCH確定
        if not candidates:
            results.append({
                'food_id': mext['food_id'],
                'food_name_jp': mext['food_name_jp'],
                'category': cat,
                'matched': False,
                'no_match': True,
                'reason': 'No USDA category mapped',
            })
            no_match += 1
            done_ids.add(mext['food_id'])
            continue

        # エネルギーで候補をソート（近い順）して上位N件
        mext_e = mext.get('energy_kcal') or 0
        candidates_sorted = sorted(
            [c for c in candidates if c.get('energy_kcal') is not None],
            key=lambda c: abs(c['energy_kcal'] - mext_e)
        )[:MAX_CANDIDATES]

        if not candidates_sorted:
            candidates_sorted = candidates[:MAX_CANDIDATES]

        # LLM呼び出し
        try:
            prompt = make_prompt(mext, candidates_sorted)
            result = call_llm(prompt)
            time.sleep(SLEEP)

            if result is None:
                results.append({
                    'food_id': mext['food_id'],
                    'food_name_jp': mext['food_name_jp'],
                    'category': cat,
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
                        'food_id': mext['food_id'],
                        'food_name_jp': mext['food_name_jp'],
                        'category': cat,
                        'matched': False,
                        'no_match': True,
                        'confidence': confidence,
                        'reason': reason,
                    })
                    no_match += 1
                    print(f'[{i+1}] NO_MATCH: {mext["food_name_jp"]} ({reason})')
                else:
                    usda_match = candidates_sorted[match_num - 1]

                    # エネルギー差計算
                    mext_e2 = mext.get('energy_kcal')
                    usda_e2 = usda_match.get('energy_kcal')
                    diff_pct = None
                    if mext_e2 and usda_e2 and mext_e2 > 0:
                        diff_pct = round(abs(mext_e2 - usda_e2) / mext_e2 * 100, 1)

                    # 栄養素差分計算（共通17項目）
                    nut_keys = ['energy_kcal','protein','fat','carb','fiber',
                                'Ca','Fe','K','Zn','vit_C','vit_A_RAE',
                                'vit_B1','vit_B2','vit_D','vit_B12','salt_eq']
                    nut_diff = {}
                    for k in nut_keys:
                        mv = mext.get(k)
                        uv = usda_match.get(k)
                        if mv is not None and uv is not None:
                            nut_diff[f'diff_{k}'] = round(uv - mv, 3)

                    results.append({
                        'food_id': mext['food_id'],
                        'food_name_jp': mext['food_name_jp'],
                        'category_l1': cat,
                        'category_l2': mext.get('category_l2', ''),
                        'matched': True,
                        'no_match': False,
                        'fdc_id': usda_match['fdc_id'],
                        'food_name_en': usda_match['food_name_en'],
                        'usda_category': usda_match['food_category'],
                        'confidence': confidence,
                        'reason': reason,
                        'energy_diff_pct': diff_pct,
                        'mext_energy': mext_e2,
                        'usda_energy': usda_e2,
                        **nut_diff,
                    })
                    matched += 1
                    flag = '✓' if confidence == 'high' else '△'
                    print(f'[{i+1}] {flag} {mext["food_name_jp"][:20]} → {usda_match["food_name_en"][:30]} ({confidence}, ΔE={diff_pct}%)')

        except Exception as e:
            results.append({
                'food_id': mext['food_id'],
                'food_name_jp': mext['food_name_jp'],
                'category': cat,
                'error': True,
                'reason': str(e),
            })
            errors += 1
            print(f'[{i+1}] ERROR: {mext["food_name_jp"]} - {e}')

        done_ids.add(mext['food_id'])

        # 100件ごとにチェックポイント保存
        if len(results) % 100 == 0:
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
    print(f'→ {OUTPUT_FILE}')

    # ── JP only カテゴリ（NO_MATCHの大分類・中分類集計）──
    from collections import Counter
    no_match_items = [r for r in results if r.get('no_match')]
    jp_only_l1 = Counter(r['category'] if 'category' in r else r.get('category_l1','') for r in no_match_items)
    jp_only_l2 = Counter(r.get('category_l2','（不明）') for r in no_match_items if r.get('category_l2'))

    jp_only_output = '/home/nakagawa/FoodCrawler/jp_only_categories.json'
    jp_only_data = {
        'total_no_match': len(no_match_items),
        'by_category_l1': dict(jp_only_l1.most_common()),
        'by_category_l2': dict(jp_only_l2.most_common(30)),
        'examples': [
            {'food_id': r['food_id'], 'name': r['food_name_jp'],
             'category': r.get('category', r.get('category_l1','')),
             'reason': r.get('reason','')}
            for r in no_match_items[:50]
        ]
    }
    with open(jp_only_output, 'w', encoding='utf-8') as f:
        json.dump(jp_only_data, f, ensure_ascii=False, indent=2)
    print(f'\n=== JP only カテゴリ（NO_MATCH {len(no_match_items)}件） ===')
    for cat, n in jp_only_l1.most_common():
        pct = n / total * 100
        print(f'  {cat}: {n}件 ({pct:.1f}%)')
    print(f'→ {jp_only_output}')

    # ── US only カテゴリ（マッチされなかったUSDAカテゴリ）──
    matched_usda_cats = Counter(r.get('usda_category','') for r in results if r.get('matched'))
    all_usda_cats = Counter(u['food_category'] for u in usda_items)
    us_only_cats = {cat: n for cat, n in all_usda_cats.items()
                    if matched_usda_cats.get(cat, 0) == 0}
    us_low_cats = {cat: (matched_usda_cats.get(cat,0), n)
                   for cat, n in all_usda_cats.items()
                   if matched_usda_cats.get(cat,0) < 3 and n > 10}

    us_only_output = '/home/nakagawa/FoodCrawler/us_only_categories.json'
    us_only_data = {
        'total_usda_categories': len(all_usda_cats),
        'matched_usda_categories': len(matched_usda_cats),
        'unmatched_usda_categories': len(us_only_cats),
        'us_only': dict(sorted(us_only_cats.items(), key=lambda x: -x[1])),
        'low_match': {cat: {'matched': v[0], 'total': v[1]}
                      for cat, v in sorted(us_low_cats.items(), key=lambda x: -x[1][1])},
    }
    with open(us_only_output, 'w', encoding='utf-8') as f:
        json.dump(us_only_data, f, ensure_ascii=False, indent=2)
    print(f'\n=== US only カテゴリ（八訂に対応なし） ===')
    print(f'USDAカテゴリ総数: {len(all_usda_cats)}')
    print(f'マッチされたUSDAカテゴリ: {len(matched_usda_cats)}')
    print(f'全くマッチなし: {len(us_only_cats)}カテゴリ')
    for cat, n in sorted(us_only_cats.items(), key=lambda x: -x[1])[:20]:
        print(f'  {cat}: {n}件')
    print(f'→ {us_only_output}')

if __name__ == '__main__':
    main()
