"""다나와 쇼핑몰 리뷰(fetch_danawa_reviews.py로 받은 것)와 리뷰마다 적은 평가 요소 분류를 합쳐 reviews_checked.json을 만든다.

사용: python3 count_reviews.py 2026-10-23
- 분류 파일: _review_evidence/review_labels_날짜.json — {상품번호: {리뷰 순번: "S+ Z-" 처럼 요소 기호와 +(좋았다)/-(아쉬웠다)}}
- 같은 글이 여러 번 올라온 것(다나와가 여러 몰·구성의 리뷰를 모으며 생김)은 한 번만 센다. 글이 없는 리뷰는 읽은 수에 넣지 않는다.
- 리뷰 한 건이 여러 요소를 말하면 요소마다, 한 요소에서 좋은 말·아쉬운 말이 둘 다 나오면 양쪽에 센다.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
EV = HERE / '_review_evidence'
CODES = {
    '기저귀': {'S': '샘', 'P': '피부', 'Z': '사이즈·밴드', 'H': '흡수', 'T': '두께·통기'},
    '물티슈': {'D': '두께', 'M': '물기', 'I': '성분·향', 'C': '뽑기·캡', 'B': '보풀·잔여감'},
}
EXTRA = {'K': '크기'}  # 물티슈 리뷰에 자주 나와 따로 센 말(앱에는 아직 안 보임)


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else None
    if not day:
        sys.exit('사용: python3 count_reviews.py 2026-10-23')
    raw = json.loads((EV / f'danawa_reviews_{day}.json').read_text(encoding='utf-8'))
    labels = json.loads((EV / f'review_labels_{day}.json').read_text(encoding='utf-8'))
    items, missing = [], []
    for p in raw['products']:
        if not p['items']:
            continue
        lab = labels.get(p['pcode'])
        if lab is None:
            missing.append(p['title'])
            continue
        codes = CODES[p['kind']]
        aspects = {name: [0, 0] for name in codes.values()}
        extra = {name: [0, 0] for name in EXTRA.values()}
        seen, read = set(), 0
        for i, r in enumerate(p['items']):
            t = r['text'].strip()
            if not t or t in seen:
                continue
            seen.add(t)
            read += 1
            for tok in lab.get(str(i), '').split():
                code, sign = tok[:-1], tok[-1]
                bucket = aspects.get(codes.get(code)) or extra.get(EXTRA.get(code))
                if bucket is None or sign not in '+-':
                    sys.exit(f'{p["title"]} {i}번 분류 "{tok}"을 알 수 없습니다')
                bucket[0 if sign == '+' else 1] += 1
        items.append({'title': p['title'], 'kind': p['kind'], 'source': '다나와 쇼핑몰 리뷰', 'checkedAt': raw['fetchedAt'],
                      'checkedAtText': f"{int(raw['fetchedAt'][5:7])}월 {int(raw['fetchedAt'][8:10])}일",
                      'rating': p['avg'], 'ratingCount': p['total'], 'got': len(p['items']), 'read': read,
                      'aspects': aspects, 'extra': {k: v for k, v in extra.items() if any(v)}})
    if missing:
        sys.exit('분류가 없는 제품: ' + ', '.join(missing))
    out = {'source': '다나와 쇼핑몰 상품리뷰(여러 몰 리뷰 모음), 최신순 50건을 Claude가 읽고 셈', 'readPerItem': raw['readPerItem'], 'items': items}
    (HERE / 'reviews_checked.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for it in items:
        a = ' · '.join(f'{k} {g}/{b}' for k, (g, b) in it['aspects'].items() if g or b) or '요소 언급 없음'
        x = ' · '.join(f'{k} {g}/{b}' for k, (g, b) in it['extra'].items())
        print(f"{it['kind']} {it['title']}: 평점 {it['rating']}({it['ratingCount']:,}건) · 받은 {it['got']} · 글 있는 리뷰 {it['read']} · {a}{' · [따로] ' + x if x else ''}")
    print(f'reviews_checked.json: {len(items)}개 제품')


if __name__ == '__main__':
    main()
