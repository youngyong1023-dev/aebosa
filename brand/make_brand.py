"""애보사 로고 파일 묶음 만들기(브랜드 정책 v2.0 6절, 방향 '포근한 아침').

앱 머리글의 상징(초성 집: ㅅ 지붕·ㅇ 얼굴·ㅂ 요람)을 그대로 파일로 뽑는다.
글자('애보사' Pretendard 800, '애 보는 사람들' Pretendard 500)는 글꼴이 없는 곳에서도 같게 보이도록 윤곽선(path)으로 바꾼다.

만드는 파일(이 폴더):
  aebosa-symbol.svg        상징만(흰 바탕 위에 쓰는 기본 색)
  aebosa-logo.svg          기본형: 상징 왼쪽 + 두 줄 글자 오른쪽(앱 머리글과 같은 비율 30 : 20/12)
  aebosa-logo-480.png      기본형 PNG(높이 480, 바탕 투명) · aebosa-logo-on-paper-480.png(흰 바탕)
  icon.svg                 앱 아이콘(ink 바탕 + 흰 선 집 + 살구 점)
  icon-192.png · icon-512.png · icon-maskable-512.png · apple-touch-icon.png(180) · favicon-16.png · favicon-32.png · favicon.ico
  og-image.png(1200×630) · og-square.png(1080×1080)   링크를 공유할 때 보이는 그림
  manifest.webmanifest     홈 화면에 추가할 때 쓰는 정보

실행: python3 brand/make_brand.py   (글꼴은 _fonts/에 받아 둔다. 저장소에는 올리지 않는다)
"""
import json
import pathlib
import shutil
import urllib.request
import zipfile

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = pathlib.Path(__file__).parent
FONTS = HERE / '_fonts'
FONTS.mkdir(exist_ok=True)

# 색 토큰(정책 v2.0 7절). 파일로 내보내는 로고라 값으로 적는다
INK, PAPER, MUTED, LINE, LABEL, SOFT = '#2a2633', '#ffffff', '#6e6878', '#ede5da', '#f0824f', '#fff6ec'
SITE = 'youngyong1023-dev.github.io/aebosa'
ONE_LINE = '0~5세 아이를 키우는 보호자가 지금 필요한 것을 짧게 찾도록 정리해 두는 웹 앱'
TABS = ['영상', '성장', '고민', '병원·약국', '핫딜']

GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl/'
PRETENDARD_ZIP = 'https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip'
LOCAL_FONTS = pathlib.Path.home() / 'Library' / 'Fonts'


def font_file(name, url_path):
    """글꼴 파일을 _fonts/에서 찾고, 없으면 내 컴퓨터 글꼴 폴더에서 복사하고, 그것도 없으면 Google Fonts 저장소(OFL)에서 받는다."""
    p = FONTS / name
    if p.exists():
        return p
    if (LOCAL_FONTS / name).exists():
        shutil.copy(LOCAL_FONTS / name, p)
        return p
    print('글꼴 받기', GF + url_path)
    urllib.request.urlretrieve(GF + url_path, p)
    return p


def pretendard(name):
    """Pretendard(OFL)는 Google Fonts에 없어 GitHub 배포 zip에서 꺼낸다(처음 한 번, 약 47MB)."""
    p = FONTS / name
    if p.exists():
        return p
    z = FONTS / 'Pretendard.zip'
    if not z.exists():
        print('Pretendard 받기', PRETENDARD_ZIP)
        urllib.request.urlretrieve(PRETENDARD_ZIP, z)
    with zipfile.ZipFile(z) as zf:
        for m in zf.namelist():
            if m.endswith('/' + name):
                p.write_bytes(zf.read(m))
                break
    if not p.exists():
        raise SystemExit(f'zip 안에 {name} 없음')
    return p


gowun = font_file('GowunDodum-Regular.ttf', 'gowundodum/GowunDodum-Regular.ttf')
pt_var = pretendard('PretendardVariable.ttf')
WORDMARK = TTFont(pretendard('Pretendard-ExtraBold.otf'))
SUBMARK = TTFont(pretendard('Pretendard-Medium.otf'))


def metrics(font):
    """브라우저가 줄 상자를 잡는 방식대로 올림·내림 값을 고른다(OS/2 USE_TYPO_METRICS가 켜져 있으면 typo, 아니면 hhea)."""
    os2, hhea = font['OS/2'], font['hhea']
    if os2.fsSelection & (1 << 7):
        return os2.sTypoAscender, os2.sTypoDescender
    return hhea.ascent, hhea.descent


def text_path(font, text, size, x, baseline):
    """글자를 윤곽선 path d 문자열로. 반환: (d, 끝 x)."""
    upem = font['head'].unitsPerEm
    s = size / upem
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    hmtx = font['hmtx']
    parts, cx = [], x
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            raise SystemExit(f'글꼴에 없는 글자: {ch!r}')
        pen = SVGPathPen(gs, ntos=lambda v: f'{v:.2f}'.rstrip('0').rstrip('.'))
        gs[gname].draw(TransformPen(pen, (s, 0, 0, -s, cx, baseline)))
        d = pen.getCommands()
        if d:
            parts.append(d)
        cx += hmtx[gname][0] * s
    return ' '.join(parts), cx


def baseline_in_box(font, size, line_height):
    asc, desc = metrics(font)
    s = size / font['head'].unitsPerEm
    content = (asc - desc) * s
    return (line_height - content) / 2 + asc * s


# ---------- 상징(초성 집): 앱 머리글 .logo와 같은 좌표 ----------
HOUSE = '<path d="M13 24L32 8L51 24"/><path d="M17 30V57H47V30M17 47H47"/>'
SYMBOL_INNER = (f'<g fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">{HOUSE}</g>'
                f'<circle cx="32" cy="37" r="6" fill="{LABEL}"/>')
SYM_VB = 64
symbol_svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="애보사 상징: 지붕 아래 아이">'
              + SYMBOL_INNER + '</svg>\n')
(HERE / 'aebosa-symbol.svg').write_text(symbol_svg, encoding='utf-8')

# ---------- 기본형(앱 머리글 비율: 상징 30 · 사이 8 · 글자 20/12, 줄 높이 1.2/1.3) ----------
SYM, GAP, WORD, SUB = 30.0, 8.0, 20.0, 12.0
word_lh, sub_lh = WORD * 1.2, SUB * 1.3
col_h = word_lh + sub_lh
sym_top = (col_h - SYM) / 2
tx = SYM + GAP
word_d, word_end = text_path(WORDMARK, '애보사', WORD, tx, baseline_in_box(WORDMARK, WORD, word_lh))
sub_d, sub_end = text_path(SUBMARK, '애 보는 사람들', SUB, tx, word_lh + baseline_in_box(SUBMARK, SUB, sub_lh))
W = max(word_end, sub_end)
lockup_inner = (f'<g transform="translate(0 {sym_top:.2f}) scale({SYM / SYM_VB:.4f})">{SYMBOL_INNER}</g>'
                f'<path fill="{INK}" d="{word_d}"/>'
                f'<path fill="{MUTED}" d="{sub_d}"/>')
logo_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.2f} {col_h:.2f}" width="{W:.2f}" height="{col_h:.2f}" '
            f'role="img" aria-label="애보사, 애 보는 사람들">{lockup_inner}</svg>\n')
(HERE / 'aebosa-logo.svg').write_text(logo_svg, encoding='utf-8')


# ---------- 앱 아이콘: ink 바탕 + 흰 선 집 + 살구 점 ----------
def house(stroke, scale, dx):
    return (f'<g transform="translate({dx} {dx}) scale({scale})" fill="none" stroke="{stroke}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">'
            f'{HOUSE}<circle cx="32" cy="37" r="6" fill="{LABEL}" stroke="none"/></g>')


icon_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="애보사">'
            f'<rect width="64" height="64" rx="14" fill="{INK}"/>{house(PAPER, .78, 7.0)}</svg>\n')
(HERE / 'icon.svg').write_text(icon_svg, encoding='utf-8')
# 마스크용: 바탕을 꽉 채우고 상징은 가운데 60%에(가장자리가 잘려도 상징이 남게)
mask_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
            f'<rect width="64" height="64" fill="{INK}"/>{house(PAPER, .6, 12.8)}</svg>')

# ---------- manifest ----------
manifest = {
    'name': '애보사', 'short_name': '애보사', 'description': ONE_LINE, 'lang': 'ko',
    'start_url': '../', 'scope': '../', 'display': 'standalone',
    'background_color': PAPER, 'theme_color': PAPER,
    'icons': [
        {'src': 'icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
        {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
        {'src': 'icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
    ],
}
(HERE / 'manifest.webmanifest').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# ---------- PNG: Chromium으로 그린다(글꼴은 파일로 직접 붙여 어디서 돌려도 같게) ----------
from playwright.sync_api import sync_playwright  # noqa: E402

FONT_CSS = f"""
@font-face {{ font-family: 'Gowun Dodum'; font-weight: 400; src: url('file://{gowun}') format('truetype'); }}
@font-face {{ font-family: 'Pretendard'; font-weight: 100 900; src: url('file://{pt_var}') format('truetype'); }}
"""


def svg_fixed(svg, w, h):
    return svg.replace('width="64" height="64"', f'width="{w}" height="{h}"', 1)


def shot(page, html, w, h, out, transparent=True):
    page.set_viewport_size({'width': w, 'height': h})
    page.set_content(f'<!doctype html><html><head><meta charset="utf-8"><style>{FONT_CSS}'
                     f'html,body{{margin:0;padding:0;background:{"transparent" if transparent else PAPER}}}</style></head><body>{html}</body></html>')
    page.wait_for_timeout(150)
    page.screenshot(path=str(out), omit_background=transparent, clip={'x': 0, 'y': 0, 'width': w, 'height': h})


def og_html(w, h, square):
    logo_h = 150 if square else 132
    scale = logo_h / col_h
    logo = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.2f} {col_h:.2f}" width="{W * scale:.1f}" height="{logo_h}" aria-hidden="true">{lockup_inner}</svg>')
    chips = ''.join(f'<span class="chip">{t}</span>' for t in TABS)
    pad = 96 if square else 88
    return f"""
<style>
.og{{position:relative;width:{w}px;height:{h}px;background:{PAPER};color:{INK};font-family:'Pretendard',sans-serif;box-sizing:border-box;padding:{pad}px;display:flex;flex-direction:column;justify-content:space-between;word-break:keep-all;overflow:hidden}}
.og .line{{font-family:'Gowun Dodum',sans-serif;font-size:{46 if square else 42}px;font-weight:400;line-height:1.45;max-width:{w - pad * 2}px;margin:0;-webkit-text-stroke:0.4px {INK}}}
.og .chips{{display:flex;flex-wrap:wrap;gap:14px}}
.og .chip{{display:inline-block;padding:10px 24px;border-radius:999px;font-size:{30 if square else 28}px;font-weight:700;line-height:1.3;color:{INK};background:{SOFT}}}
.og .foot{{display:flex;justify-content:space-between;align-items:flex-end;color:{MUTED};font-size:{28 if square else 26}px;font-weight:500}}
</style>
<div class="og">
  <div>{logo}</div>
  <p class="line">{ONE_LINE}</p>
  <div class="chips">{chips}</div>
  <div class="foot"><span>{SITE}</span><span>아이 정보는 적게 받습니다</span></div>
</div>"""


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(device_scale_factor=1)
    for size, name in [(192, 'icon-192.png'), (512, 'icon-512.png'), (180, 'apple-touch-icon.png'), (32, 'favicon-32.png'), (16, 'favicon-16.png'), (48, '_favicon-48.png')]:
        shot(page, svg_fixed(icon_svg, size, size), size, size, HERE / name)
    shot(page, svg_fixed(mask_svg, 512, 512), 512, 512, HERE / 'icon-maskable-512.png', transparent=False)
    lw = round(W / col_h * 480)
    logo_big = logo_svg.replace(f'width="{W:.2f}" height="{col_h:.2f}"', f'width="{lw}" height="480"', 1)
    shot(page, logo_big, lw, 480, HERE / 'aebosa-logo-480.png')
    shot(page, logo_big, lw, 480, HERE / 'aebosa-logo-on-paper-480.png', transparent=False)
    shot(page, og_html(1200, 630, False), 1200, 630, HERE / 'og-image.png', transparent=False)
    shot(page, og_html(1080, 1080, True), 1080, 1080, HERE / 'og-square.png', transparent=False)
    b.close()

# favicon.ico: 48을 바탕으로 32·16을 붙인다(Pillow는 바탕보다 큰 크기를 건너뛴다)
from PIL import Image  # noqa: E402
imgs = [Image.open(HERE / n).convert('RGBA') for n in ('_favicon-48.png', 'favicon-32.png', 'favicon-16.png')]
imgs[0].save(HERE / 'favicon.ico', format='ICO', sizes=[(48, 48), (32, 32), (16, 16)], append_images=imgs[1:])
(HERE / '_favicon-48.png').unlink()
print('로고 파일 묶음 완료:', ', '.join(sorted(p.name for p in HERE.iterdir() if p.is_file() and not p.name.startswith('_') and p.suffix != '.py')))
print(f'기본형 크기 {W:.2f}×{col_h:.2f} (상징 30, 글자 20/12)')
