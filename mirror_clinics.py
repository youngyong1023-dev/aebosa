"""병원·약국 자료 받기에 실패했을 때, 지금 배포된 자료(meta.json의 cellList)를 그대로 내려받아 site/data/clinics/에 다시 둔다.
공공데이터포털이 GitHub 서버의 요청에 응답하지 않는 날에도 앱 배포가 멈추지 않게 하려는 것이다. 사용: python3 mirror_clinics.py <배포된 자료 주소>
GitHub Pages는 짧은 시간에 요청이 몰리면 429로 막으므로, 칸 목록에 있는 칸만 4개씩 나눠 받고 막히면 기다렸다 다시 받는다."""
import concurrent.futures
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

base = sys.argv[1].rstrip('/') + '/'
out = pathlib.Path(__file__).parent / 'site' / 'data' / 'clinics'


def get(url, tries=6):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500 or i == tries - 1:
                raise
            wait = int(e.headers.get('Retry-After') or 0) or 5 * 2 ** i
        except urllib.error.URLError:
            if i == tries - 1:
                raise
            wait = 5 * 2 ** i
        time.sleep(min(wait, 120))


meta = json.loads(get(base + 'meta.json'))
cells = meta.get('cellList')
if not cells:
    sys.exit('배포된 자료에 칸 목록(cellList)이 없어 그대로 다시 쓸 수 없습니다')
out.mkdir(parents=True, exist_ok=True)


def grab(c):
    (out / f'{c}.json').write_bytes(get(f'{base}{c}.json'))


with concurrent.futures.ThreadPoolExecutor(4) as ex:
    list(ex.map(grab, cells))
(out / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
print(f'배포된 자료 {len(cells)}칸을 그대로 다시 씁니다({meta.get("updatedText", "")} 받은 자료)')
