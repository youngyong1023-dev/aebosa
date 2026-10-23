"""방향 1안 '포근한 아침' + 로고 B(초성 집)을 app.template.html에 적용한다(문자열 치환만, JS·탭 마크업은 손대지 않음).
다시 실행해도 안전하다(이미 바뀐 곳은 건너뜀). 실행: python3 brand/redesign/apply_design.py"""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
p = ROOT / 'app.template.html'
s = p.read_text(encoding='utf-8')
orig = s
done, skipped = [], []

def rep(old, new, name, count=1):
    global s
    if new in s and old not in s:
        skipped.append(name); return
    if old not in s:
        sys.exit(f'치환 실패(원문 없음): {name}')
    s = s.replace(old, new, count); done.append(name)

# 1. 글꼴: 제목 고운돋움(Google Fonts) + 본문 Pretendard(jsDelivr 공식 배포)
rep('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@700&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">',
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap">\n'
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.css">', '글꼴 링크')

# 2. 토큰
old_root = s[s.index(':root {'):s.index('}', s.index(':root {')) + 1]
new_root = """:root {
  --paper: #ffffff;
  --ink: #2a2633;
  --muted: #6e6878;
  --line: #ede5da;
  --field: #8f847a;
  --soft: #fff6ec;
  --label: #f0824f;
  --label-soft: #ffe9dc;
  --label-ink: #8a3e1e;
  --tint-1: #ffe3d0;
  --tint-1-ink: #b84e22;
  --tint-2: #dcefe9;
  --tint-2-ink: #2f7f69;
  --tint-3: #dde8fa;
  --tint-3-ink: #3c68b8;
  --tint-4: #fff1c9;
  --tint-4-ink: #8a6500;
  --tint-5: #ebe3f7;
  --tint-5-ink: #6a4ba3;
  --tint-6: #ece9e4;
  --tint-6-ink: #5e5a66;
  --link: #3c68b8;
  --ok: #2f7f69;
  --warn: #c23b3b;
  --scrim: rgba(42, 38, 51, .45);
  --shadow: 0 -8px 24px rgba(42, 38, 51, .12);
  --f-display: "Gowun Dodum", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  --f-body: "Pretendard Variable", Pretendard, "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  --t12: 12px;
  --t13: 13.5px;
  --t15: 15px;
  --t17: 17px;
  --t20: 20px;
  --t24: 24px;
  --t-chart: 14px;
  --tabbar: 64px;
  color-scheme: light;
}"""
if old_root != new_root:
    if '--tint-1' in old_root: skipped.append('토큰')
    else: s = s.replace(old_root, new_root, 1); done.append('토큰')
rep("브랜드 정책 v1.3(results/2026-10-23_애보사_브랜드정책.md)의 토큰.", "브랜드 정책 v2.0(results/2026-10-23_애보사_브랜드정책.md, '포근한 아침')의 토큰.", '정책 주석')

# 3. 머리글 로고 B(초성 집)와 워드마크
rep('.brand { margin: 0; display: flex; align-items: center; gap: 8px; white-space: nowrap; font-family: var(--f-display); font-weight: 700; font-size: var(--t20); line-height: 1.2; }',
    '.brand { margin: 0; display: flex; align-items: center; gap: 8px; white-space: nowrap; font-family: var(--f-body); font-weight: 800; font-size: var(--t20); line-height: 1.2; letter-spacing: -0.01em; }', '브랜드 글자')
rep('.logo { width: 24px; height: 24px; flex: none; margin-right: 2px; }\n.logo .lg-line { fill: none; stroke: var(--ink); stroke-width: 2.4; stroke-linecap: round; }\n.logo .lg-dot { fill: var(--label); stroke: var(--ink); stroke-width: 1.8; }',
    '.logo { width: 30px; height: 30px; flex: none; }\n.logo .lg-line { fill: none; stroke: var(--ink); stroke-width: 7; stroke-linecap: round; stroke-linejoin: round; }\n.logo .lg-dot { fill: var(--label); }', '로고 CSS')
rep('<svg class="logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false"><circle class="lg-line" cx="11.5" cy="10.5" r="4.5"/><path class="lg-line" d="M4 26.5a7.5 7.5 0 0 1 15 0"/><circle class="lg-dot" cx="24.5" cy="16.5" r="3.3"/><path class="lg-line" d="M20 26.5a4.5 4.5 0 0 1 9 0"/></svg>',
    '<svg class="logo" viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path class="lg-line" d="M13 24L32 8L51 24"/><path class="lg-line" d="M17 30V57H47V30M17 47H47"/><circle class="lg-dot" cx="32" cy="37" r="6"/></svg>', '로고 SVG')

# 4. 제목: 고운돋움은 400 한 가지라 굵기 400·크기 24
rep('.view h2 { margin: 0; font-family: var(--f-display); font-weight: 700; font-size: var(--t20); line-height: 1.35; text-wrap: balance; }',
    '.view h2 { margin: 0; font-family: var(--f-display); font-weight: 400; font-size: var(--t24); line-height: 1.3; letter-spacing: -0.01em; -webkit-text-stroke: 0.3px currentColor; text-wrap: balance; }', '화면 제목')
rep('.guide h2 { margin: 0; font-family: var(--f-display); font-weight: 700; font-size: var(--t20); }',
    '.guide h2 { margin: 0; font-family: var(--f-display); font-weight: 400; font-size: var(--t24); }', '안내 제목')

# 5. 부품: 칩 선택 = 살구 채움 + ink 글자, 상황 카드 = 크림 면 + 색 아이콘, 상자 모서리 20
rep('.chipbtn[aria-pressed="true"] { background: var(--ink); border-color: var(--ink); color: var(--paper); }',
    '.chipbtn[aria-pressed="true"] { background: var(--label); border-color: var(--label); color: var(--ink); font-weight: 700; }', '칩 선택')
rep('.situ button { position: relative; display: grid; grid-template-columns: 24px minmax(0, 1fr); column-gap: 8px; row-gap: 2px; align-content: start; min-height: 76px; padding: 12px; border: 2px solid var(--line); border-radius: 12px; background: var(--paper); text-align: left; }\n'
    '.situ button svg { grid-row: 1 / span 3; width: 24px; height: 24px; color: var(--ink); }',
    '.situ button { position: relative; display: grid; grid-template-columns: minmax(0, 1fr); row-gap: 2px; align-content: start; min-height: 112px; padding: 14px; border: 0; border-radius: 18px; background: var(--soft); text-align: left; box-shadow: inset 0 0 0 2px var(--soft); }\n'
    '.situ button svg { width: 36px; height: 36px; padding: 8px; box-sizing: border-box; border-radius: 12px; margin-bottom: 6px; background: var(--tint-6); color: var(--tint-6-ink); }\n'
    '.situ button:nth-child(1) svg { background: var(--tint-1); color: var(--tint-1-ink); }\n.situ button:nth-child(2) svg { background: var(--tint-2); color: var(--tint-2-ink); }\n'
    '.situ button:nth-child(3) svg { background: var(--tint-3); color: var(--tint-3-ink); }\n.situ button:nth-child(4) svg { background: var(--tint-4); color: var(--tint-4-ink); }\n'
    '.situ button:nth-child(5) svg { background: var(--tint-5); color: var(--tint-5-ink); }', '상황 카드')
rep('.situ button em { font-style: normal; font-size: var(--t12); font-weight: 600; color: var(--muted); font-variant-numeric: tabular-nums; }',
    '.situ button em { font-style: normal; font-size: var(--t13); font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; margin-top: 4px; }', '상황 카드 개수')
rep('.situ button[aria-pressed="true"] { border-color: var(--ink); background: var(--label-soft); }',
    '.situ button[aria-pressed="true"] { box-shadow: inset 0 0 0 2px var(--ink); background: var(--label-soft); }', '상황 카드 선택')
rep('.panel { display: grid; gap: 12px; border: 1px solid var(--line); border-radius: 16px; padding: 16px; min-width: 0; }',
    '.panel { display: grid; gap: 12px; border: 1px solid var(--line); border-radius: 20px; padding: 16px; min-width: 0; }', '묶음 상자')
rep('.card, .mini { display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: 12px; align-items: start; width: 100%; padding: 8px; border: 1px solid var(--line); border-radius: 12px;',
    '.card, .mini { display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: 12px; align-items: start; width: 100%; padding: 8px; border: 1px solid var(--line); border-radius: 14px;', '영상 카드')
rep('input:not([type="checkbox"]), select, textarea { width: 100%; min-width: 0; min-height: 48px; border: 1px solid var(--field); border-radius: 12px;',
    'input:not([type="checkbox"]), select, textarea { width: 100%; min-width: 0; min-height: 48px; border: 1px solid var(--field); border-radius: 14px;', '입력칸')
rep('.listbar { border: 1px solid var(--line); border-radius: 16px; padding: 4px 16px; }', '.listbar { border: 1px solid var(--line); border-radius: 20px; padding: 4px 16px; }', '조건 칸 모서리')
rep('.tabs button[aria-current="page"] .ti { background: var(--label); }',
    '.tabs button[aria-current="page"] .ti { background: var(--label); color: var(--ink); }', '탭 활성')

if s != orig:
    p.write_text(s, encoding='utf-8')
print('적용:', ', '.join(done) or '없음', '| 이미 적용됨:', ', '.join(skipped) or '없음')
