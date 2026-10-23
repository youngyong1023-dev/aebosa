"""영상 분류 규칙(제목·채널 이름 키워드). build_catalog_v3.py(2026-10-23)에서 옮겨 와 fetch_youtube.py가 함께 쓴다.

- 작품: 채널 이름(WORKS)으로 정하고, 한 채널에 여러 작품이 올라온 경우만 제목(TITLE_WORKS)으로 나눈다.
- 형식(format): 본편·이야기 / 동요 / 율동·체조 / 자장가·수면 / 수업·강의 / 장난감 놀이.
- 모음(comp): 제목에 모음 표시가 있거나 30분 이상.
"""
import re

def secs(s):
    t = 0
    for p in s.split(':') if s else []:
        t = t * 60 + int(p)
    return t

WORKS = [  # 채널 이름 → 작품 (영어판 채널도 같은 작품으로). v3(2026-10-23)에서 빠진 작품 27개를 더함(플레이보드 한국 차트 상위 6개 포함)
    (r'까투리|KATURI|Katuri', '엄마 까투리'), (r'뽀로로|뽀롱뽀롱|Pororo', '뽀로로'), (r'타요|Tayo', '꼬마버스 타요'),
    (r'핑크퐁|아기상어|Baby Shark|Pinkfong|Hogi|다이노링스', '핑크퐁·아기상어'), (r'콩순이|Kongsuni', '콩순이'),
    (r'베베핀|Bebefinn', '베베핀'), (r'슈퍼윙스|Super Wings', '슈퍼윙스'),
    (r'로보카\s*폴리|Robocar\s*POLI', '로보카폴리'), (r'꼬모', '토닥토닥 꼬모'), (r'주니토니|JunyTony', '주니토니'),
    (r'코코비|Cocobi', '코코비'), (r'띠띠뽀|Titipo', '띠띠뽀'), (r'미니특공대|Miniforce', '미니특공대'),
    (r'티니핑|Teenieping', '티니핑'), (r'헬로카봇|[Cc]arbot', '헬로카봇'), (r'브레드이발소|브레드TV|Bread Barbershop', '브레드이발소'),
    (r'베이비버스|BabyBus', '베이비버스'), (r'코코멜론|CoComelon|Cocomelon', '코코멜론'), (r'블루이|Bluey', '블루이'),
    (r'페파\s*피그|Peppa Pig', '페파피그'), (r'퍼피\s*구조대|PAW Patrol', '퍼피구조대'), (r'옥토넛|Octonauts', '옥토넛'),
    (r'파자마\s*삼총사|PJ Masks', '파자마 삼총사'), (r'텔레토비|Teletubbies', '꼬꼬마 텔레토비'),
    (r'넘버블록스|Numberblocks', '넘버블록스'), (r'알파블록스|Alphablocks', '알파블록스'),
    (r'티디키즈|Tidi Kids', '티디키즈'), (r'깨비키즈|KEBIKIDS', '깨비키즈'), (r'리아차차|LiaChaCha', '리아차차'), (r'톰토미|TOMTOMI', '톰토미'),
    (r'코리리|KORIRI', '내 친구 코리리'), (r'마샤와\s*곰|Masha', '마샤와 곰'),
    (r'Super Simple', 'Super Simple Songs'), (r'리틀팍스|Little Fox', '리틀팍스'),
]
# 한 채널에 여러 작품이 올라온 경우: 그 채널 영상만 제목으로 작품을 정한다
# 띠띠뽀는 대부분 '꼬마버스 타요' 채널에, 방귀대장 뿡뿡이·딩동댕유치원은 'EBS 키즈' 채널에 올라와 있다
TITLE_WORKS = [(r'띠띠뽀|Titipo', '띠띠뽀', r'타요|Tayo'), (r'뿡뿡이', '방귀대장 뿡뿡이', r'^EBS'), (r'딩동댕', '딩동댕유치원', r'^EBS')]
# 유아 채널 = 채널 이름에 유아용 표시(키즈·동요·동화 등)가 있거나 방송사·출판사·제작사 채널. 그 밖의 개인·모음 채널은 '확인 안 됨'
KIDS_CH = (r'Cartoon Network|^EBS|주니토니|지니키즈|티디키즈|리아차차|키즈팝|송송키즈|코코비|톰토미|유라야놀자|망둥이키즈|깨비키즈|대발이TV|치타부|키즈멜로디|Bebepop|yearim|케어멜로디'
           r'|베이비버스|BabyBus|래브라도 경장|토닥토닥 꼬모|똑똑키즈|TokTok Kids|모야몽|리틀신비|루루키즈|KBSKids|슈퍼액션스터디'
           r'|Twinkle Little Songs|The Wiggles|Kids Carnival|BusSongs|Little Baby Bum|Nursery Rhymes TV|Ms Rachel|Mr Tumble'
           r'|웅진빅박스|KIVAJOY|마이리틀타이거|엘키즈 동화|잠자리 동화')
SLEEP_CH = r'Kinopost|Piano Latte|Castle Brock|마비뮤|힐링트리|Beautiful Relaxation|DanalEntertainment'

def work_of(ch):
    for pat, w in WORKS:
        if re.search(pat, ch):
            return w
    return None

def channel_class(ch, work):
    if work:
        return '작품 공식'
    if re.search(KIDS_CH, ch):
        return '유아 채널'
    if re.search(SLEEP_CH, ch):
        return '수면 음악'
    return '확인 안 됨'   # 장난감 리뷰·팬 영상·모음 재업로드·어른용 강의·관련 없는 영상

def any_of(t, pairs):
    return sorted({name for name, pat in pairs if re.search(pat, t, re.I)})

def en_text(t):
    # [영어자막]은 소리가 한국어이고, '슈퍼파닉스한글'은 한글 학습이라 영어 판단에서 뺀다
    return re.sub(r'영어\s*자막', '', t).replace('파닉스한글', '한글')

SITU = [('차에서', r'차에서|드라이브'), ('자기 전', r'자기 전|잠잘|잠자리|낮잠|자장가(?!\s*,)|꿀잠|수면|새근|Bedtime|Lullab'),
        ('집에서', r'(?<!어린이)집에서|집콕'), ('병원에서', r'병원에서'), ('나들이', r'나들이')]
LEARN = [('한글', r'한글|가나다|쌍자음|모음 모아'), ('숫자', r'숫자|세어|Counting|Numbers?\b'),
         ('영어', r'영어\s*(?:배[우워]|공부|학습|단어|듣기|흘려듣기|교육|말문|기초|노출)|영어로\s*배[우워]|흘려듣기|파닉스|Phonics|알파벳|\bABC\b|생활영어|학습.*영어|영어.*학습'),
         ('색깔·모양', r'색깔|모양|컬러|Colou?rs?\b|Shapes?\b'),
         ('생활습관', r'생활\s*습관|습관|양치|오줌|배변|건강교육|아프지|시간을 지켜|안전|감정|사회성|약속|규칙|정리하|감사하기|Healthy Habits|Good Habit|Potty|Brush Your Teeth|Safety|Emergency Tips'),
         ('말놀이', r'의성어|한글송'), ('자연·지식', r'사우루스|공룡 이름|공룡이 궁금|공룡\s*학습')]
THEME = [('탈것', r'자동차|(?<!베이비)버스|소방차|경찰차|구급차|병원차|중장비|굴착기|기차|비행기|붕붕|부릉|미니카|토이카|탁송차|레스큐|소방구조대|자동차 구조대|슈퍼구조대|탈것|탈 것|스포츠카|지하철|견인차|트럭|뚜뚜|칙칙\s*폭폭'
                   r'|\bCars?\b|\bBus\b|\bTrucks?\b|\bTrains?\b|\bBicycle\b|\bBike\b|\bBoat\b|Ambulance|Rescue'),
         ('공룡', r'공룡|티라노|사우루스|다이노|\bDino|T-?Rex'),
         ('동물', r'동물|상어|사자|토끼|고양이|강아지|농장|고래|코끼리|늑대|악어|벌 한|오리|(?<![가-힣])양\b|원숭이|기린|호랑이|고릴라|낙타|병아리|거북|돼지'
                  r'|Animals?\b|Ducks?\b|Monkeys?\b|\bFarm\b|MacDonald|Spider|Bunn(?:y|ies)|Shark|Rabbit|\bDogs?\b|\bCats?\b|\bPigs?\b|Whale|\bLions?\b|Elephant|\bBirds?\b|Chicken|\bBats?\b'),
         ('병원놀이', r'병원놀이|의사(?!소통)|(?<!불면증)치료|Doctors?\b|Hospital|Boo Boo|Emergency|Cavity'),
         ('장난감', r'장난감|미니카|토이|\bToys?\b'),
         ('먹기', r'먹방|냠냠|요리|주스|둥근빵|과일|간식|\bEat|\bFood|Snack|Juice|Fruit|Carrots?|Banana')]
SCARY = (r'할로윈|좀비|몬스터|귀신|괴물|유령|으스스|으시시|오싹|무시무시|마녀|드라큘라|악당|무서운'
         r'|Halloween|Zombie|Monster(?!\s*Truck)|Haunted|Spooky|Ghosts?\b|Witch|Vampire|Scary')
COMP = (r'(?<![단중])모음(?!\s*자음)|모아보기|이어보기|연속|몰아보기|총집합|BEST|베스트|TOP|Top|특집|전편|전체|이어듣기|무한반복|반복재생|메들리|\d+\s*시간|\[\d+분\]|\d+분\)|\d+\s*[-~]\s*\d+\s*(?:화|회|편)|\d+\s*(?:화|회|편)\s*[-~]\s*\d+|\d+회\s*~|\d+\s*곡'
        r'|Compilation|\+\s*More|and more|Full Episodes|Episodes? \d+\s*[-~]|E\d+\s*~\s*E?\d+|EP\s*\d+\s*~\s*\d+|Ep\.\s*\d+\s*~\s*\d+|Collection|LIVE|All-Day|\d+\s*(?:min|Minutes)')

def fmt_of(t):
    if re.search(r'영어 읽는 법|가르치는 방법|어른들을 위한|왕초보|총정리|한 번에 정리|생활영어\s*\d+\s*문장', t): return '수업·강의'
    if re.search(r'자장가(?!\s*,)|수면|낮잠동요|낮잠 동요|피아노|오르골|클래식|잠자리\s*동화|잠자리동화|Lullab|[Bb]edtime', t): return '자장가·수면'
    if re.search(r'율동|체조|댄스(?!파티|\s*,)|따라 해|\bDance\b|Exercise|With Actions', t, re.I): return '율동·체조'
    if re.search(r'장난감\s*놀이|놀아보|#장난감|TOY\]|토이\b', t): return '장난감 놀이'
    if re.search(r'동요|노래|(?<![방탁송])송(?!송)|Song|뮤직|뮤지컬|Musical|Rhymes|Sing\b|Sing-?Along|BINGO|Old MacDonald|\d+\s*곡', t, re.I): return '동요'
    return '본편·이야기'

def season_ep(t):
    if re.search(r'뽀로로와\s*노래해요\s*\d+\s*기', t):
        season = None          # 노래 시리즈의 '기'는 본편 시즌과 다르다
    else:
        s = re.search(r'(?:\bS|시즌\s*|Season\s*)(\d+)\b|(\d+)\s*기\b|엄마\s*까투리\s*(\d)(?=\s*(?:\]|이어보기))|KATURI(\d)\]', t)
        season = int(next(g for g in s.groups() if g)) if s else None
    if re.search(r'\d+\s*[-~]\s*\d+\s*(?:화|회|편)|\d+\s*(?:화|회|편)\s*[-~]\s*\d+|\d+회\s*~|(?:EP|Ep\.?|\bE)\s*\d+\s*~\s*E?\d+', t):
        return season, None
    e = re.search(r'제?\s*(\d+)\s*화|#\s*(\d+)\b|\bEp(?:isode)?\.?\s*(\d+)\b|\bEP\s*(\d+)\b', t)
    return season, (int(next(g for g in e.groups() if g)) if e else None)

def label_of(t):
    t = re.sub(r'[\U00010000-\U0010FFFF☀-➿️‍⭐★☆♪♬♫🎵]', '', t)
    parts = [p.strip(' ・-') for p in re.split(r'\s[|lㅣ│｜]\s|\||ㅣ|│|｜', t) if p.strip(' ・-')]
    skip = re.compile(r'^(?:Katuri|KATURI\d?|Pororo|Best|BEST|S\d+|Season \d+|Ep\.?\s*\d+|EP\s*\d+|LIVE.*|영어\s*자막|영어듣기 훈련|흘려듣기)$')
    keep = [p for p in parts if not skip.match(p)] or parts
    head = keep[0] if keep else t
    if len(head) < 8 and len(keep) > 1:
        head = head + ' · ' + keep[1]
    head = re.sub(r'\s+', ' ', head).strip()
    return head[:46] + ('…' if len(head) > 46 else '')

def bucket(sec):
    if sec == 0: return '라이브'
    if sec < 300: return '5분 미만'
    if sec < 1800: return '5~30분'
    if sec < 3600: return '30분~1시간'
    return '1시간 이상'

def lang_of(t, ch_class, fmt):
    if ch_class == '수면 음악' or (fmt == '자장가·수면' and re.search(r'피아노|오르골|Piano|Music Box|연주|클래식|Relax', t)):
        return '말 없음'
    te = en_text(t)
    if re.search(r'영어|English|\(EN\)|Nursery Rhymes|널서리|너서리|마더구스|파닉스|Phonics|알파벳|\bABC\b|원어민|bedtime story', te, re.I):
        return '영어'
    body = re.sub(r'\[[^\]]*\]|\([^)]*\)', '', te)   # [KONGSUNI AND FRIENDS S8 ANIMATION]·피노키오(Pinocchio)처럼 괄호 속 표기는 세지 않음
    latin, hangul = len(re.findall(r'[A-Za-z]', body)), len(re.findall(r'[가-힣]', body))
    if latin and (hangul == 0 or latin > hangul * 1.5):
        return '영어'
    return '한국어'

EN_STRONG = r'영어\S*\s*(?:잠자리\s*)?(?:동요|동화|노래)|흘려듣기|원어민|오디오북|English|\(EN\)|Nursery Rhymes|널서리|너서리|마더구스|bedtime story|영어\s*드라마'

def lang_check(t, lang):
    if lang != '영어':
        return False
    te = en_text(t)
    body = re.sub(r'\[[^\]]*\]|\([^)]*\)', '', te)
    latin, hangul = len(re.findall(r'[A-Za-z]', body)), len(re.findall(r'[가-힣]', body))
    mostly_latin = latin and (hangul == 0 or latin > hangul * 1.5)
    return not (re.search(EN_STRONG, te, re.I) or mostly_latin)

AGE_TEXT = r'\d+\s*[-~]\s*\d+\s*세|\d+\s*살\s*수준|\d+\s*-\s*\d+\s*Years|Toddlers?\b|Preschoolers?\b|유치원|초등\s*입학\s*준비|초등입학준비'
LEVEL = r'리틀팍스\s*\d\s*단계|영어 듣기 훈련\s*\d\s*단계'


def classify(vid, t, ch, sec, query=''):
    """영상 한 편 → 앱 카탈로그 항목(build_catalog_v3.py와 같은 결과)."""
    work = work_of(ch)
    for pat, w, ch_pat in TITLE_WORKS:
        if re.search(pat, t) and re.search(ch_pat, ch):
            work = w
    ch_class = channel_class(ch, work)
    season, ep = season_ep(t)
    fmt = fmt_of(t)
    lang = lang_of(t, ch_class, fmt)
    if lang_check(t, lang):
        lang = '한국어+영어'
    comp = bool(re.search(COMP, t)) or sec >= 1800
    lv = re.search(LEVEL, t)
    return {
        'id': vid, 'title': t, 'label': label_of(t), 'channel': ch, 'work': work or '기타',
        'chClass': ch_class, 'sec': sec, 'len': bucket(sec), 'comp': comp,
        'season': season, 'ep': None if comp or fmt != '본편·이야기' else ep, 'format': fmt, 'lang': lang,
        'sub': '영어 자막' if re.search(r'영어\s*자막', t) else '',
        'audioOnly': bool(re.search(r'검은\s*화면|검은화면|Black\s*[Ss]creen|블랙스크린|화면 없이', t)),
        'level': re.sub(r'\s+', ' ', lv.group(0)) if lv else '',
        'ageText': '·'.join(dict.fromkeys(m.group(0) for m in re.finditer(AGE_TEXT, t))),
        'situ': any_of(t, SITU), 'learn': any_of(en_text(t), LEARN), 'theme': any_of(t, THEME),
        'scary': bool(re.search(SCARY, t, re.I)), 'query': query,
    }
