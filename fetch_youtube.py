"""공식 채널에 올라온 영상 전체를 YouTube Data API v3로 받아 catalog.json을 다시 만든다.

사용: python3 fetch_youtube.py            (키: 환경 변수 YOUTUBE_API_KEY 또는 .keys/youtube_api_key.txt, 값은 출력하지 않는다)
      python3 fetch_youtube.py --dry      (받기만 하고 catalog.json은 바꾸지 않는다)

1. 지금 catalog.json에서 '작품 공식' 영상의 채널을 찾는다(videos.list, 50편에 1단위).
2. 채널마다 업로드 목록 전체를 받는다(channels.list → playlistItems.list, 50편에 1단위).
3. 영상마다 길이·설명·조회수를 받는다(videos.list). 60초 이하(쇼츠)와 라이브·예정 영상은 뺀다.
4. catalog_rules.classify로 작품·형식(본편·동요 등)·모음을 정한다. 한 채널에 여러 작품이 올라오는 채널(EBS 키즈 등)은
   제목으로 작품이 정해지는 영상만 남긴다. 한국어·영어가 아닌 언어 판(중국어·일본어·스페인어·인도네시아어 등)은
   catalog_rules.other_lang으로 가려 뺀다(2026-10-23 결정).
5. 설명란의 챕터(0:00부터 시작하는 시각 3개 이상)를 구간으로 붙인다: 'ch': [[시작 초, 구간 이름], ...].
6. 공식 채널이 아닌 영상(유아 채널·수면 음악 등)은 지금 목록 그대로 둔다.
7. 결과(2026-10-23 결정): 작품별 전체 목록은 data/works/(작품마다 파일 하나, 자체 주소 판이 작품 화면을 열 때 불러옴),
   첫 화면용 catalog.json에는 작품마다 조회수 상위 CORE_N편만 담는다. 자동 생성 음원 채널(' - Topic')과 라이브 다시보기 채널은 뺀다.
받은 원자료는 _yt_cache/에만 둔다(저장소에 올리지 않음).
"""
import collections
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))  # python3 -I로 돌려도 같은 폴더의 분류 규칙을 읽는다
import catalog_rules as R  # noqa: E402
CACHE = HERE / '_yt_cache'
API = 'https://www.googleapis.com/youtube/v3/'
MIN_SEC = 61  # 60초 이하는 쇼츠로 보고 뺀다
CORE_N = 30   # 첫 화면 목록(catalog.json)에 작품마다 담는 편수: 조회수 상위. 지금 앱 크기(영상 969편)와 비슷하게 맞춘 값
EXCLUDE_CH = re.compile(r' - Topic$|^Super Simple Live')  # 유튜브 자동 생성 음원 채널·라이브 다시보기 채널(2026-10-23 결정)
# 동요 채널(채널 이름에 동요·Songs·노래·Music)의 영상은 제목에 '동요'가 없어도 대부분 노래라, 회차·이야기 표시가 없으면 동요로 본다
SONG_CH = re.compile(r'동요|Songs|노래해요|Music|키즈송|Nursery|Rhymes', re.I)
STORY_CUE = re.compile(r'\d+\s*화|에피소드|Episode|\bEP\.?\s*\d|시즌|Season|\bS\d+|본편|이야기|동화|Story|Stories|애니메이션|Animation|Cartoon', re.I)
WORKS_DIR = HERE / 'data' / 'works'
FMT = ['본편·이야기', '동요', '율동·체조', '자장가·수면', '수업·강의', '장난감 놀이']
LANG = ['한국어', '한국어+영어', '영어', '말 없음']


def kind_of(v):
    """작품 화면의 묶음: 본편 / 동요 / 모음 / 그 밖"""
    if v['comp']:
        return '모음'
    if v['format'] == '본편·이야기':
        return '본편'
    if v['format'] in ('동요', '율동·체조', '자장가·수면'):
        return '동요'
    return '그 밖'


def slug(work):
    return 'w' + hashlib.sha1(work.encode('utf-8')).hexdigest()[:8]


def pack(items):
    """작품 파일을 작게: 채널 이름은 표로 빼고, 영상마다 배열 하나. 앱(unpackWork)이 같은 순서로 푼다."""
    chans = sorted({v['channel'] for v in items})
    ci = {c: i for i, c in enumerate(chans)}
    rows = []
    for v in items:
        flags = (1 if v['sub'] else 0) | (2 if v['audioOnly'] else 0) | (4 if v['scary'] else 0) | (8 if v['comp'] else 0)
        rows.append([v['id'], v['title'], ci[v['channel']], v['sec'], flags, v['season'], v['ep'], FMT.index(v['format']),
                     LANG.index(v['lang']), v['level'] or 0, v['situ'] or 0, v['learn'] or 0, v['theme'] or 0, v.get('ch') or 0])
    return {'c': chans, 'v': rows}


def api_key():
    f = HERE / '.keys' / 'youtube_api_key.txt'
    k = os.environ.get('YOUTUBE_API_KEY', '').strip() or (f.read_text(encoding='utf-8').strip() if f.exists() else '')
    if not k:
        sys.exit('YouTube Data API 키가 없습니다. YOUTUBE_API_KEY 환경 변수나 .keys/youtube_api_key.txt에 넣어 주세요.')
    print(f'API 키 형식: {len(k)}자')  # 값은 출력하지 않는다
    return k


UNITS = 0


def api(key, endpoint, **params):
    global UNITS
    url = API + endpoint + '?' + urllib.parse.urlencode(dict(params, key=key))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                UNITS += 1
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace').replace(key, '***')
            if e.code in (400, 403):  # 키·사용량·권한 문제는 다시 해도 같다
                sys.exit(f'YouTube API 오류 {e.code}: {body[:300]}')
            last = f'HTTP {e.code}'
        except Exception as e:
            last = str(e).replace(key, '***')
        time.sleep(2 * (attempt + 1))
    sys.exit(f'YouTube API를 부르지 못했습니다: {last}')


def chunks(xs, n=50):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def iso_sec(d):
    m = re.fullmatch(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', d or '')
    if not m:
        return 0
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


TS = re.compile(r'(?<![\d:])((?:\d{1,2}:)?\d{1,2}:\d{2})(?![\d:])')


def chapters(desc, sec):
    """설명란 챕터 → [[시작 초, 이름], ...]. 유튜브 챕터 조건처럼 0:00으로 시작하고 3개 이상, 시각이 늘어나는 줄만 쓴다."""
    out = []
    for line in (desc or '').splitlines():
        m = TS.search(line)
        if not m:
            continue
        parts = [int(x) for x in m.group(1).split(':')]
        t = parts[0] * 3600 + parts[1] * 60 + parts[2] if len(parts) == 3 else parts[0] * 60 + parts[1]
        name = (line[:m.start()] + ' ' + line[m.end():])
        name = re.sub(r'\[\s*\]|\(\s*\)', ' ', name)              # [00:00]처럼 시각을 감싼 괄호가 비면 지운다
        name = re.sub(r'^\s*\[\s*\d+\s*\]', ' ', name)              # 앞의 [1] 같은 번호
        name = re.sub(r'^[\s\-–—:|.]+|[\s\-–—:|.]+$', '', name)
        name = re.sub(r'\s+', ' ', name)[:60]
        if out and t <= out[-1][0]:
            continue  # 시각이 거꾸로 가면 챕터 목록이 아닌 줄(예: 다른 영상 시각)로 본다
        out.append([t, name or f'{len(out) + 1}번 구간'])
    if len(out) < 3 or out[0][0] != 0 or (sec and out[-1][0] >= sec):
        return []
    return out


def main():
    dry = '--dry' in sys.argv
    key = api_key()
    CACHE.mkdir(exist_ok=True)
    day = datetime.date.today().isoformat()
    old = json.loads((HERE / 'catalog.json').read_text(encoding='utf-8'))

    # 1) 공식 채널 찾기
    seed = [v['id'] for v in old if v['chClass'] == '작품 공식']
    chan = {}
    for ids in chunks(seed):
        for it in api(key, 'videos', part='snippet', id=','.join(ids), maxResults=50).get('items', []):
            sn = it['snippet']
            chan[sn['channelId']] = sn['channelTitle']
    dropped = sorted(t for t in chan.values() if EXCLUDE_CH.search(t))
    chan = {c: t for c, t in chan.items() if not EXCLUDE_CH.search(t)}
    print(f'공식 채널 {len(chan)}개(뺀 채널: {", ".join(dropped) or "없음"}):', ', '.join(sorted(chan.values())))

    # 2) 채널마다 업로드 목록
    uploads = {}
    for ids in chunks(list(chan)):
        for it in api(key, 'channels', part='contentDetails,snippet', id=','.join(ids), maxResults=50).get('items', []):
            uploads[it['id']] = it['contentDetails']['relatedPlaylists']['uploads']
    vids = {}
    for cid, pl in uploads.items():
        token, n = None, 0
        while True:
            r = api(key, 'playlistItems', part='contentDetails', playlistId=pl, maxResults=50, **({'pageToken': token} if token else {}))
            for it in r.get('items', []):
                vids[it['contentDetails']['videoId']] = cid
                n += 1
            token = r.get('nextPageToken')
            if not token:
                break
        print(f'  {chan[cid]}: 업로드 {n}편')

    # 3) 영상 정보
    raw = {}
    for ids in chunks(list(vids)):
        for it in api(key, 'videos', part='snippet,contentDetails,statistics', id=','.join(ids), maxResults=50).get('items', []):
            sn, cd, st = it['snippet'], it['contentDetails'], it.get('statistics', {})
            raw[it['id']] = {'title': sn['title'], 'channel': sn['channelTitle'], 'desc': sn.get('description', ''),
                             'live': sn.get('liveBroadcastContent', 'none'), 'sec': iso_sec(cd.get('duration')),
                             'views': int(st.get('viewCount', 0) or 0), 'published': sn.get('publishedAt', '')[:10]}
    (CACHE / f'uploads_{day}.json').write_text(json.dumps(raw, ensure_ascii=False), encoding='utf-8')

    # 4) 분류
    new, skipped = {}, {'쇼츠': 0, '라이브·예정': 0, '다른 작품(같은 채널)': 0, '다른 언어': 0}
    for vid, r in raw.items():
        if r['live'] != 'none':
            skipped['라이브·예정'] += 1
            continue
        if r['sec'] < MIN_SEC:
            skipped['쇼츠'] += 1
            continue
        if R.other_lang(r['title']):
            skipped['다른 언어'] += 1
            continue
        item = R.classify(vid, r['title'], r['channel'], r['sec'], 'YouTube Data API 채널 업로드')
        if item['chClass'] != '작품 공식':
            skipped['다른 작품(같은 채널)'] += 1
            continue
        if item['format'] == '본편·이야기' and SONG_CH.search(r['channel']) and not STORY_CUE.search(r['title']):
            item['format'], item['ep'] = '동요', None
        item['views'] = r['views']
        item['published'] = r['published']
        ch = chapters(r['desc'], r['sec']) if item['comp'] else []
        if ch:
            item['ch'] = ch
        new[vid] = item
    keep = [v for v in old if v['chClass'] != '작품 공식' and v['id'] not in new and not R.other_lang(v['title'])]
    by_work = collections.defaultdict(list)
    for v in new.values():
        by_work[v['work']].append(v)
    for vs in by_work.values():
        vs.sort(key=lambda v: -v['views'])
    core = [v for vs in by_work.values() for v in vs[:CORE_N]]
    kinds = collections.Counter(kind_of(v) for v in new.values())
    print(f'API 사용 {UNITS}단위 · 받은 영상 {len(raw)}편 · 뺀 영상 {skipped}')
    print(f'공식 채널 영상 {len(new)}편(챕터 있는 모음 {sum(1 for v in new.values() if v.get("ch"))}편) · 그 밖의 채널 {len(keep)}편')
    print('묶음:', dict(kinds))
    print('작품별:', ', '.join(f'{w} {len(vs)}' for w, vs in sorted(by_work.items(), key=lambda x: -len(x[1]))))
    print(f'첫 화면 목록: 작품마다 상위 {CORE_N}편 → {len(core)}편 + 그 밖의 채널 {len(keep)}편')
    index = {}
    sizes = 0
    files = {}
    for w, vs in by_work.items():
        data = json.dumps(pack(vs), ensure_ascii=False, separators=(',', ':'))
        files[slug(w)] = data
        sizes += len(data.encode('utf-8'))
        k = collections.Counter(kind_of(v) for v in vs)
        index[w] = {'f': slug(w), 'n': len(vs), 'k': {x: k[x] for x in ('본편', '동요', '모음', '그 밖') if k[x]},
                    'chp': sum(1 for v in vs if v.get('ch'))}
    print(f'작품별 파일 {len(files)}개 · 합계 {sizes / 1e6:.1f}MB · 가장 큰 파일 {max(len(d.encode()) for d in files.values()) / 1e6:.1f}MB')
    if dry:
        print('--dry: catalog.json·data/works는 바꾸지 않았습니다')
        return
    WORKS_DIR.mkdir(parents=True, exist_ok=True)
    for f in WORKS_DIR.glob('w*.json'):
        f.unlink()
    for name, data in files.items():
        (WORKS_DIR / f'{name}.json').write_text(data, encoding='utf-8')
    (WORKS_DIR / 'index.json').write_text(json.dumps({'fetchedAt': day, 'works': index}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for v in core:
        v.pop('views', None); v.pop('published', None)
    (HERE / 'catalog.json').write_text(json.dumps(core + keep, ensure_ascii=False, indent=0), encoding='utf-8')
    print('catalog.json과 data/works/를 새로 썼습니다')


if __name__ == '__main__':
    main()
