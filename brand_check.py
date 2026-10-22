"""브랜드 정책 검사(results/2026-10-23_육아정리함_브랜드정책.md 11절). build.py가 빌드 전에 부른다.

1. 색 값과 사용자 정의 속성(--이름)은 :root 토큰 블록에만 쓴다. 색 속성과 SVG 칠(fill·stroke)에 이름 색(white 등)도 쓰지 않는다.
2. 글꼴은 정책의 두 가지(Hahmlet, IBM Plex Sans KR)만 쓰고, font-family는 토큰으로만 지정한다.
3. 글자 크기는 크기 토큰(--t…)으로만, 굵기는 400·500·600·700만 쓴다(Hahmlet은 700만).
4. 화면 문구에 금지 표현(판정·과장·은유·느낌표)을 쓰지 않고, 파일 어디에도 이모지를 쓰지 않는다.
걸리면 줄 번호와 함께 알리고 빌드를 멈춘다.
"""
import re

FONTS_OK = {'Hahmlet': {'700'}, 'IBM+Plex+Sans+KR': {'400', '500', '600', '700'}}
WEIGHTS_OK = {'400', '500', '600', '700', 'inherit'}
COLOR = re.compile(r'(?<![\w&/="\'-])#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(')
NAMED = re.compile(r'\b(?:white|black|red|green|blue|yellow|orange|gr[ae]y|purple|pink|brown|navy|teal|silver|gold|maroon|olive|lime|aqua|fuchsia|cyan|magenta)\b', re.I)
COLOR_PROP = re.compile(r'(?<![\w-])(?:color|background(?:-color)?|border(?:-[a-z]+)*|outline(?:-color)?|fill|stroke|box-shadow|accent-color|caret-color|text-decoration-color|stop-color)\s*:\s*([^;}"\n]+)')
SVG_PAINT = re.compile(r'\b(?:fill|stroke|stop-color)="([^"]*)"')
PAINT_OK = re.compile(r'none|currentColor|transparent|inherit|url\(#[\w-]+\)|var\(--[\w-]+\)')
# 그림 문자·기호 이모지(별·도형·시계 등). ✓(2713)·✕(2715)는 선택·지우기 표시로, 화살표(2190~21FF)는 글자로 허용
EMOJI = re.compile('[\U0001F000-\U0001FAFF⌀-⏿■-◿☀-✒✔✖-➿⬀-⯿‼⁉〰〽㊗㊙️]')
BANNED = [
    (r'안전한 영상|적합한 영상|추천 영상|좋은 영상', '판정 표현'),
    (r'최고의?|완벽|무조건|꼭 ', '과장 표현'),
    (r'처방|열쇠|경보|레버|관문|밀어 올리|손에 쥐|샌다|새어 나|자극|임계|순증|닿[아는다았]|묶[어는다었]', '은유·금지어'),
    (r'귀속|모집단|분모', '분석 은어'),
    (r'!', '느낌표'),
]


def blank(m):
    """주석을 같은 길이의 빈칸으로 바꿔 줄 번호를 지킨다."""
    return re.sub(r'[^\n]', ' ', m.group())


def ui_strings(src):
    """HTML 글자·속성과 JS 문자열(주석 제외)에서 한국어가 든 문구를 (줄, 문구)로 뽑는다."""
    rows, n = [], len(src)
    H = re.compile(r'[가-힣]')

    def add(pos, text):
        text = re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', text)).strip()
        if H.search(text):
            rows.append((src.count('\n', 0, pos) + 1, text))
    k = src.index('<script>')
    h = re.sub(r'<!--.*?-->|<style>.*?</style>', lambda m: ' ' * len(m.group()), src[:k], flags=re.S)
    for m in re.finditer(r'(?:placeholder|aria-label|title)="([^"]*)"', h):
        add(m.start(), m.group(1))
    for m in re.finditer(r'>([^<>]+)<', h):
        add(m.start(), m.group(1))

    def code(i, stop):
        depth, prev = 0, '('
        while i < n:
            c = src[i]
            if src.startswith('</script>', i):
                return n
            if c == '/' and src[i + 1:i + 2] == '/':
                j = src.find('\n', i); i = n if j < 0 else j; continue
            if c == '/' and src[i + 1:i + 2] == '*':
                j = src.find('*/', i + 2); i = n if j < 0 else j + 2; continue
            if c in '\'"':
                j, buf = i + 1, ''
                while j < n and src[j] != c:
                    if src[j] == '\\':
                        buf += src[j + 1:j + 2]; j += 2; continue
                    buf += src[j]; j += 1
                add(i, buf); i, prev = j + 1, 'a'; continue
            if c == '`':
                i, prev = template(i + 1), 'a'; continue
            if c == '/' and prev in '(,=:[!&|?{};+-*%<>~^':
                j, cls = i + 1, False
                while j < n and src[j] != '\n':
                    ch = src[j]
                    if ch == '\\':
                        j += 2; continue
                    if ch == '[': cls = True
                    elif ch == ']': cls = False
                    elif ch == '/' and not cls: break
                    j += 1
                i = j + 1
                while i < n and src[i].isalpha(): i += 1
                prev = 'a'; continue
            if c == '{': depth += 1
            elif c == '}':
                if stop and depth == 0: return i + 1
                depth -= 1
            if not c.isspace():
                prev = 'a' if (c.isalnum() or c in '_$') else c
            i += 1
        return i

    def template(i):
        buf, start = '', i
        while i < n:
            c = src[i]
            if c == '\\':
                buf += src[i + 1:i + 2]; i += 2; continue
            if c == '`':
                add(start, buf); return i + 1
            if c == '$' and src[i + 1:i + 2] == '{':
                buf += '${…}'; i = code(i + 2, True); continue
            buf += c; i += 1
        return i
    code(k + len('<script>'), False)
    return rows


def run(src):
    errors = []
    line_of = lambda pos: src.count('\n', 0, pos) + 1
    a = src.index(':root {'); b = src.index('}', a)
    in_root = lambda pos: a <= pos <= b
    # 주석을 지운 사본(줄 번호는 그대로). 토큰·색·글자 검사는 이 사본으로 한다
    code = re.sub(r'<!--.*?-->|/\*.*?\*/', blank, src, flags=re.S)
    for m in COLOR.finditer(code):
        if not in_root(m.start()):
            errors.append((line_of(m.start()), '토큰 밖 색 값', code[m.start():m.start() + 24].split('\n')[0]))
    for m in COLOR_PROP.finditer(code):
        if not in_root(m.start()) and NAMED.search(m.group(1)):
            errors.append((line_of(m.start()), '이름 색', m.group(0)[:40]))
    for m in SVG_PAINT.finditer(code):
        if not PAINT_OK.fullmatch(m.group(1).strip()):
            errors.append((line_of(m.start()), 'SVG 칠 색 값', m.group(0)[:40]))
    for m in re.finditer(r'(?<![\w-])--[\w-]+\s*:', code):
        if not in_root(m.start()):
            errors.append((line_of(m.start()), ':root 밖 토큰 정의', m.group(0)))
    for m in re.finditer(r'fonts\.googleapis\.com/css2\?([^"]+)"', src):
        for fam, spec in re.findall(r'family=([^:&]+)(?::wght@([\d;]+))?', m.group(1)):
            if fam not in FONTS_OK:
                errors.append((line_of(m.start()), '정하지 않은 글꼴', fam))
            elif spec and set(spec.split(';')) - FONTS_OK[fam]:
                errors.append((line_of(m.start()), '정하지 않은 굵기', f'{fam} {spec}'))
    for m in re.finditer(r'font-family:\s*([^;}]+)', code):
        if not re.fullmatch(r'\s*(var\(--f-(display|body)\)|inherit)\s*', m.group(1)):
            errors.append((line_of(m.start()), '토큰 아닌 글꼴 지정', m.group(1).strip()[:40]))
    for m in re.finditer(r'font-size\s*:\s*([^;}"]+)|font-size="([^"]*)"', code):
        v = (m.group(1) or m.group(2) or '').strip()
        if m.group(2) is not None or not re.fullmatch(r'var\(--t[\w-]*\)|inherit', v):
            errors.append((line_of(m.start()), '크기 토큰 아닌 글자 크기', v[:30]))
    for m in re.finditer(r'font-weight\s*:\s*([^;}"]+)|font-weight="([^"]*)"', code):
        v = (m.group(1) or m.group(2) or '').strip()
        if v not in WEIGHTS_OK:
            errors.append((line_of(m.start()), '정하지 않은 굵기', v))
    for m in EMOJI.finditer(src):
        errors.append((line_of(m.start()), '이모지', repr(m.group())))
    for ln, text in ui_strings(src):
        for rx, why in BANNED:
            if re.search(rx, text):
                errors.append((ln, why, text[:60]))
    if errors:
        for e in errors:
            print(f'  {e[0]:>5}줄  {e[1]}: {e[2]}')
        raise SystemExit(f'브랜드 정책 검사 실패 {len(errors)}건 — 고친 뒤 다시 빌드하세요.')
    print('브랜드 정책 검사 통과(색·토큰·글꼴·글자 크기·굵기·금지 표현·이모지)')
