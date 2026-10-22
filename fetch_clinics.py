"""병원·약국 자료 받기(자체 주소 판 전용). build.py 다음에 실행한다.

국립중앙의료원 공공데이터 API에서 소아청소년과(진료과목 D002)·약국·달빛어린이병원 목록을 받아, 0.1도 격자 칸마다
작은 JSON 파일로 site/data/clinics/에 쓴다. 앱은 보호자가 '내 위치로 가까운 곳 보기'를 누르면 내 위치 칸과 둘레 8칸 파일만
받아 기기 안에서 거리와 '지금 열림'을 계산한다(위치를 서버로 보내지 않는다).

- 인증키: 환경 변수 DATA_GO_KR_KEY(공공데이터포털 '일반 인증키(Decoding)') 또는 .keys/data_go_kr.txt. 키 값은 출력하지 않는다.
- 하루 호출 수: 쪽당 1,000건씩 소아청소년과·약국·달빛어린이병원을 모두 받아도 수십 번이라 개발 계정 한도(하루 1,000회) 안이다.
- 확인 필요(키를 받은 뒤 첫 실행에서): 진료과목 D002 = 소아청소년과와 응답 필드 이름(dutyName·dutyTel1·dutyAddr·dutyDivNam·dutyInf·
  dutyTime1s~8c·wgs84Lat·wgs84Lon·hpid)은 이용 사례 기준이다. 달빛어린이병원 목록 오퍼레이션 이름은 공공데이터포털 상세기능 목록에
  있으나 이름은 명세서로 확인해야 해서, 받지 못하면 건너뛰고 dutyInf에 '달빛'이 적힌 곳만 표시한다.
"""
import datetime
import json
import math
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).parent
OUT = HERE / 'site' / 'data' / 'clinics'
BASE = 'https://apis.data.go.kr/B552657'
ROWS = 1000
OPS = {
    'peds': ('HsptlAsembySearchService/getHsptlMdcncListInfoInqire', {'QD': 'D002'}),  # 병·의원 목록, 진료과목 D002(소아청소년과)
    'pharm': ('ErmctInsttInfoInqireService/getParmacyListInfoInqire', {}),            # 약국 목록
    'moon': ('HsptlAsembySearchService/getBabyListInfoInqire', {}),                    # 달빛어린이병원 및 소아전문센터 목록(이름 확인 필요)
}


def service_key():
    f = HERE / '.keys' / 'data_go_kr.txt'
    k = os.environ.get('DATA_GO_KR_KEY', '').strip() or (f.read_text(encoding='utf-8').strip() if f.exists() else '')
    if not k:
        sys.exit('공공데이터포털 인증키가 없습니다. DATA_GO_KR_KEY 환경 변수나 .keys/data_go_kr.txt에 일반 인증키(Decoding)를 넣어 주세요.')
    return urllib.parse.unquote(k) if '%' in k else k  # Encoding 키를 넣었으면 Decoding 키로 되돌린다(요청할 때 다시 인코딩한다)


def call(op, params, page, key):
    """한 쪽을 받아 (항목 목록, 전체 건수)를 돌려준다. 오류 메시지에는 키를 넣지 않는다."""
    url = f'{BASE}/{op}?' + urllib.parse.urlencode(dict(params, serviceKey=key, pageNo=page, numOfRows=ROWS))
    last = None
    for attempt in range(3):
        try:
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    root = ET.fromstring(r.read())
            except urllib.error.HTTPError as e:  # 인증 오류는 401·403과 함께 XML로 이유를 보낸다
                body = e.read()
                try:
                    root = ET.fromstring(body)
                except ET.ParseError:
                    raise RuntimeError(f'HTTP {e.code}: {body[:200].decode("utf-8", "replace")}')
                if not root.findtext('.//returnAuthMsg'):
                    raise RuntimeError(f'HTTP {e.code}')
            auth = root.findtext('.//returnAuthMsg')  # 인증 오류 응답(OpenAPI_ServiceResponse)
            if auth:
                raise RuntimeError(f'인증 오류: {auth} / {root.findtext(".//errMsg")} (코드 {root.findtext(".//returnReasonCode")})')
            code = (root.findtext('.//resultCode') or '').strip()
            if code not in ('', '0', '00'):
                raise RuntimeError(f'결과 코드 {code}: {root.findtext(".//resultMsg")}')
            items = [{c.tag: (c.text or '').strip() for c in it} for it in root.iter('item')]
            return items, int(root.findtext('.//totalCount') or len(items))
        except Exception as e:  # 네트워크·서버 오류는 2번 더 시도한다
            last = RuntimeError(str(e).replace(key, '***'))
            time.sleep(2 * (attempt + 1))
    raise last


def fetch_all(name, key):
    op, params = OPS[name]
    items, total = call(op, params, 1, key)
    for page in range(2, math.ceil(total / ROWS) + 1):
        more, _ = call(op, params, page, key)
        items += more
        time.sleep(0.3)
    print(f'{name}: {len(items)}건 (전체 {total}건)')
    return items


def hours(it):
    """8칸(월~일, 공휴일). 'HHMM-HHMM' 또는 ''(쉬는 날·정보 없음)."""
    out = []
    for d in range(1, 9):
        s, c = it.get(f'dutyTime{d}s', ''), it.get(f'dutyTime{d}c', '')
        out.append(f'{s}-{c}' if s.isdigit() and c.isdigit() else '')
    return out


def norm(it, kind):
    try:
        y, x = float(it['wgs84Lat']), float(it['wgs84Lon'])
    except (KeyError, ValueError):
        return None  # 좌표가 없으면 지도에 놓을 수 없어 뺀다
    if not (33 <= y <= 39 and 124 <= x <= 132):
        return None
    row = {'id': it.get('hpid', ''), 'n': it.get('dutyName', ''), 'k': kind, 't': it.get('dutyTel1', ''),
           'a': it.get('dutyAddr', '')[:48], 'y': round(y, 6), 'x': round(x, 6), 'h': hours(it)}
    if '달빛' in it.get('dutyInf', ''):
        row['m'] = 1
    return row


def main():
    key = service_key()
    rows = {}
    got = {}
    for name in ('peds', 'pharm'):  # 병·의원과 약국은 활용신청이 따로라, 하나가 막혀도 다른 하나의 상태를 함께 보여 준다
        try:
            got[name] = fetch_all(name, key)
        except Exception as e:
            print(f'{name}: 받지 못했습니다 — {e}')
    if len(got) < 2:
        sys.exit('병·의원과 약국 목록을 모두 받아야 배포합니다. 받지 못한 API의 활용신청 승인 상태와 인증키를 확인해 주세요.')
    for it in got['peds']:
        r = norm(it, 'c' if it.get('dutyDivNam', '') == '의원' else 'h')
        if r and r['id']:
            rows[r['id']] = r
    for it in got['pharm']:
        r = norm(it, 'p')
        if r and r['id']:
            rows[r['id']] = r
    moon_ok = True
    try:
        for it in fetch_all('moon', key):
            r = norm(it, 'h')
            if r and r['id']:
                rows.setdefault(r['id'], r)['m'] = 1
    except Exception as e:  # 오퍼레이션 이름이 다르면 여기서 건너뛴다
        moon_ok = False
        print('달빛어린이병원 목록을 받지 못했습니다:', e)
    if not rows:
        sys.exit('받은 자료가 없습니다. 활용신청 승인 상태와 인증키를 확인해 주세요.')
    cells = {}
    for r in rows.values():
        cells.setdefault(f'{math.floor(r["y"] * 10)}_{math.floor(r["x"] * 10)}', []).append(r)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob('*.json'):
        old.unlink()
    for k, v in cells.items():
        (OUT / f'{k}.json').write_text(json.dumps(v, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    counts = {k: sum(r['k'] == k for r in rows.values()) for k in ('c', 'h', 'p')}
    counts['m'] = sum(bool(r.get('m')) for r in rows.values())
    meta = {'updatedAt': now.isoformat(timespec='minutes'), 'updatedText': f'{now.month}월 {now.day}일 {now:%H:%M}',
            'source': '국립중앙의료원 전국 병·의원 찾기 서비스·전국 약국 정보 조회 서비스(공공데이터포털)',
            'cell': 0.1, 'cells': len(cells), 'counts': counts, 'moonList': moon_ok}
    (OUT / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
    print(f'칸 {len(cells)}개 · 소아청소년과 의원 {counts["c"]} · 병원 {counts["h"]} · 약국 {counts["p"]} · 달빛 {counts["m"]}')


if __name__ == '__main__':
    main()
