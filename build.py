"""app.template.html + catalog.json → app.html(공개 링크용 본문) · index.html(로컬 미리보기용 전체 문서)
· site/index.html(자체 주소 판: 앱 안 지도와 가까운 곳 목록을 켠다. 병원·약국 자료는 fetch_clinics.py가 site/data/clinics/에 쓴다)."""
import json
import os
import pathlib
import shutil
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).parent))  # -I로 실행해도 옆의 brand_check.py를 쓴다
import brand_check  # noqa: E402

here = pathlib.Path(__file__).parent
catalog = json.loads((here / 'catalog.json').read_text(encoding='utf-8'))
keep = ['id', 'title', 'label', 'channel', 'work', 'chClass', 'sec', 'len', 'comp', 'season', 'ep', 'format', 'lang', 'sub', 'audioOnly', 'level', 'ageText', 'situ', 'learn', 'theme', 'scary']
slim = [{**{k: v[k] for k in keep}, **({'ch': v['ch']} if v.get('ch') else {})} for v in catalog]  # ch: 챕터 구간(모음 영상)
src = (here / 'app.template.html').read_text(encoding='utf-8')
brand_check.run(src)  # 브랜드 정책 검사: 걸리면 여기서 멈춘다
body = src.replace(
    '/*__CATALOG__*/[]', json.dumps(slim, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
who = here / 'who_growth.json'  # WHO 성장 기준(0~24개월) L·M·S. 없으면 앱이 백분위를 비워 둔다
if who.exists():
    body = body.replace('/*__WHO__*/null', who.read_text(encoding='utf-8').strip())
deals = here / 'deals_checked.json'  # 핫딜 '지금 가격'(몰 상품 페이지에서 직접 확인해 적은 값). 없으면 앱이 빈 안내를 보여 준다
if deals.exists():
    body = body.replace('/*__DEALS__*/null', json.dumps(json.loads(deals.read_text(encoding='utf-8')), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
# 핫딜 리뷰(판매처 평점 + 평가 요소별 언급 건수, 사람이 직접 읽고 센 값). 없으면 리뷰 칸을 그리지 않는다. 시험할 때만 REVIEWS_FILE로 다른 파일을 쓴다
reviews = pathlib.Path(os.environ.get('REVIEWS_FILE') or here / 'reviews_checked.json')
if reviews.exists():
    body = body.replace('/*__REVIEWS__*/null', json.dumps(json.loads(reviews.read_text(encoding='utf-8')), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
(here / 'app.html').write_text(body, encoding='utf-8')
# 로컬 미리보기용 아이콘: 브랜드 로고 상징(정책 6절)과 같은 그림
FAVICON = ('<link rel="icon" href="data:image/svg+xml,' + urllib.parse.quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#1b2333"/>'
    '<g transform="translate(3.2 3.6) scale(.8)" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round">'
    '<circle cx="11.5" cy="10.5" r="4.5"/><path d="M4 26.5a7.5 7.5 0 0 1 15 0M20 26.5a4.5 4.5 0 0 1 9 0"/>'
    '<circle cx="24.5" cy="16.5" r="3.3" fill="#ffc83d" stroke="none"/></g></svg>') + '">\n')
head = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + FAVICON)
def full_doc(b):
    t = b.index('</title>') + len('</title>')
    return head + b[:t] + '\n</head>\n<body>\n' + b[t:] + '\n</body>\n</html>\n'


doc = full_doc(body)
(here / 'index.html').write_text(doc, encoding='utf-8')
# 자체 주소 판: 카카오맵 JavaScript 키는 환경 변수 KAKAO_JS_KEY 또는 .keys/kakao_js_key.txt에서 읽는다(값은 출력하지 않는다).
# 이 키는 카카오에 등록한 도메인에서만 동작하는 공개용 키라 페이지 안에 들어간다
key_file = here / '.keys' / 'kakao_js_key.txt'
map_key = os.environ.get('KAKAO_JS_KEY', '').strip() or (key_file.read_text(encoding='utf-8').strip() if key_file.exists() else '')
site_cfg = {'selfHosted': True, 'mapKey': map_key or None, 'dataBase': 'data/clinics/'}
# 작품별 전체 영상(fetch_youtube.py가 data/works/에 씀): 자체 주소 판만 작품 화면을 열 때 불러온다. 첫 화면 숫자를 위해 목차는 페이지에 넣는다
works_dir = here / 'data' / 'works'
if (works_dir / 'index.json').exists():
    site_cfg['worksBase'] = 'data/works/'
    site_cfg['works'] = json.loads((works_dir / 'index.json').read_text(encoding='utf-8'))
    shutil.rmtree(here / 'site' / 'data' / 'works', ignore_errors=True)
    shutil.copytree(works_dir, here / 'site' / 'data' / 'works')
site_doc = full_doc(body.replace('/*__SITE__*/null', json.dumps(site_cfg, ensure_ascii=False)))
(here / 'site').mkdir(exist_ok=True)
(here / 'site' / 'index.html').write_text(site_doc, encoding='utf-8')
print('app.html', len(body.encode()), 'bytes · index.html', len(doc.encode()), 'bytes · 영상', len(slim),
      f"· 작품별 전체 {sum(x['n'] for x in site_cfg['works']['works'].values())}편" if 'works' in site_cfg else '· 작품별 전체 목록 없음',
      '· site/index.html(카카오맵 키', f'있음, {len(map_key)}자 — JavaScript 키는 32자)' if map_key else '없음)')
