"""다나와 '쇼핑몰 상품리뷰'(여러 몰 리뷰를 다나와가 모아 보여 주는 곳)에서 핫딜 제품마다 최신순 50건을 받아 둔다.

- 제품: deals_checked.json의 다나와 상품 번호(pcode). 같은 상품의 다른 매수 구성 리뷰도 다나와 화면처럼 함께 받는다.
- 저장: _review_evidence/danawa_reviews_YYYY-MM-DD.json(저장소에 올리지 않음). 작성자 아이디는 저장하지 않는다.
- 이 파일을 사람이(또는 Claude가) 읽고 평가 요소별로 센 결과는 review_labels_YYYY-MM-DD.json에 두고 count_reviews.py로 합친다.
"""
import datetime
import html
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).parent
OUT = HERE / '_review_evidence'
READ_N = 50
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
      'Referer': 'https://prod.danawa.com/'}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode('utf-8', 'replace')


def text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def reviews(pcode, cate1):
    page = get(f'https://prod.danawa.com/info/?pcode={pcode}')
    m = re.search(r'productCodes:\s*["\']([\d,]+)["\']', page)
    codes = m.group(1) if m else pcode
    q = urllib.parse.urlencode({'prodCode': pcode, 'cate1Code': cate1, 'page': 1, 'limit': READ_N, 'score': 0, 'sortType': 'NEW',
                                'onlyPhotoReview': '', 'usefullScore': 'Y', 'innerKeyword': '', 'subjectWord': 0,
                                'subjectWordString': '', 'subjectSimilarWordString': '', 'productCodes': codes})
    body = get('https://prod.danawa.com/info/dpg/ajax/companyProductReview.ajax.php?' + q)
    hm = re.search(r'쇼핑몰 상품리뷰\s*([\d,]+)\s*([\d.]+)\s*점', text(body.split('danawa-prodBlog-companyReview-clazz-more')[0]))
    items = []
    for block in body.split('class="danawa-prodBlog-companyReview-clazz-more"')[1:]:
        rid = re.search(r'companyReview-button-side-(\d+)', block)
        score = re.search(r'class="star_mask"[^>]*>(\d+)점', block)
        mall = re.search(r'class="mall">.*?<span[^>]*>([^<]+)</span>', block, re.S)
        date = re.search(r'class="date">([^<]+)<', block)
        atc = re.search(r'class="atc">(.*?)</div>', block, re.S)
        items.append({'id': rid.group(1) if rid else '', 'score': int(score.group(1)) // 20 if score else None,
                      'mall': mall.group(1).strip() if mall else '', 'date': date.group(1).strip().rstrip('.') if date else '',
                      'text': text(atc.group(1)) if atc else ''})
    return {'codes': codes, 'total': int(hm.group(1).replace(',', '')) if hm else 0,
            'avg': float(hm.group(2)) if hm else None, 'items': items}


def main():
    deals = json.loads((HERE / 'deals_checked.json').read_text(encoding='utf-8'))
    OUT.mkdir(exist_ok=True)
    day = datetime.date.today().isoformat()
    res = {'source': '다나와 쇼핑몰 상품리뷰(최신순)', 'fetchedAt': day, 'readPerItem': READ_N, 'products': []}
    for g in deals['groups']:
        for d in g.get('items') or g.get('rows'):
            qs = dict(re.findall(r'([a-z0-9_]+)=([^&]+)', d['link']))
            r = reviews(qs['pcode'], qs['cate1'])
            res['products'].append({'kind': g['kind'], 'title': d['title'], 'pcode': qs['pcode'], **r})
            print(f"{g['kind']} {d['title']}: 리뷰 {r['total']}건 · 평점 {r['avg']} · 받은 {len(r['items'])}건")
            time.sleep(1)
    path = OUT / f'danawa_reviews_{day}.json'
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(path.name, sum(len(p['items']) for p in res['products']), '건')


if __name__ == '__main__':
    main()
