"""애보사 홍보 영상 만들기(세로 1080×1920 · 가로 1920×1080, 30fps, 내레이션 포함).

장면은 브랜드 정책의 색·글꼴 토큰으로 그린 HTML이고, 앱 화면은 로컬 서버(http://127.0.0.1:8765)에서 휴대폰 크기로 찍은 캡처다.
프레임은 Chromium(Playwright)으로 한 장씩 그려 ffmpeg로 묶고, 내레이션은 macOS 한국어 음성(Yuna, `say`)으로 만든다.

사용: python3 brand/promo/make_promo.py shots | audio | preview | render 9x16 | render 16x9
  shots    앱 화면 캡처 → shots/ (서버가 켜져 있어야 한다: python3 -m http.server 8765 --bind 127.0.0.1)
  audio    소리 트랙(_audio/track.wav)과 장면 길이표 timeline.json. 내레이션 모드면 자막 aebosa_promo.srt도 만든다
  music    음악 베드 미리 듣기: python3 make_promo.py music "Summers End" → _audio/music_<묶음>.mp3
           소리 모드는 환경 변수 AEBOSA_TTS: 'none'(기본, 음악만) · 'supertonic:F1' · 'say'. 음악 묶음은 AEBOSA_MUSIC(기본 'Soft Waves')
  preview  장면별 대표 프레임 PNG → _preview/ (검수용)
  render   전체 프레임 → mp4 (aebosa_promo_9x16.mp4 / aebosa_promo_16x9.mp4)
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent.parent
FONTS = HERE.parent / '_fonts'
SHOTS = HERE / 'shots'
AUDIO = HERE / '_audio'
SCRATCH = pathlib.Path('/private/tmp/claude-501/-Users-youngkim-Desktop-AI-prompt---CODE--/6491806a-b9d5-4010-a145-b58b32eeb8a0/scratchpad/promo_frames')
FPS = 30
SITE = 'youngyong1023-dev.github.io/aebosa'

# 장면: id · 최소 길이(초) · 내레이션. 실제 길이 = max(최소, 0.5 앞 여유 + 내레이션 + 0.9 뒤 여유)
SCENES = [
    ('s1', 4.0, "애보사. '애 보는 사람들'을 줄인 말이에요."),
    ('s2', 4.5, '아이를 안은 채 한 손으로, 지금 필요한 것 하나만 얼른 찾고 싶을 때가 있죠.'),
    ('s3', 6.5, '영상은 상황으로 골라요. 밥 준비할 때, 차를 탔을 때, 기다릴 때. 몇 편 볼지 정해 두면, 다 본 뒤에 알려 드려요.'),
    ('s4', 5.0, '성장 탭에 키와 몸무게를 적으면, 또래 아이들 사이에서 어디쯤인지 한눈에 보여요.'),
    ('s5', 5.5, '병원과 약국은 지금 갈 수 있는 곳부터 찾아요. 위치는 버튼을 누를 때만 쓰고, 어디에도 저장하거나 보내지 않아요.'),
    ('s6', 5.5, '기저귀와 물티슈는 한 장당 가격이 싼 순서로 보여요. 언제 확인했는지, 어디서 파는지도 같이 적어 두고요.'),
    ('s7', 6.0, '애보사의 약속이에요. 짧게 보여 주고, 근거를 함께 적고, 판정은 하지 않고, 아이 정보는 적게 받아요.'),
    ('s8', 4.5, '애보사. 휴대폰 브라우저에서 바로 열려요.'),
]
LEAD, TAIL = 0.5, 0.7
# 내레이션 엔진: 'supertonic:<음성이름>'(F1~F5·M1~M5, 기본) 또는 'say'(맥 내장 유나). 환경 변수 AEBOSA_TTS로 바꾼다
TTS_ENGINE = os.environ.get('AEBOSA_TTS', 'none')
# 음악: 맥의 GarageBand에 든 Apple Loops(한 묶음 안의 악기 루프는 같은 템포·조성)를 이어 붙여 베드를 만든다.
# 애플 약관상 루프로 만든 사운드트랙은 영상에 써서 배포할 수 있고, 루프 파일 자체를 따로 나눠 주지만 않으면 된다
LOOPS = pathlib.Path('/Library/Audio/Apple Loops/Apple/07 Chillwave')
MUSIC_KIT = os.environ.get('AEBOSA_MUSIC', 'Soft Waves')
MUSIC_LEVEL = [('Beat', 0.45), ('Lead', 0.5), ('Pad', 0.55), ('Synth', 0.55), ('Bass', 0.7), ('Guitar', 1.0), ('Layers', 0.8)]
# 내레이션이 없을 때 장면 길이(초): 자막을 읽을 시간 기준
SILENT_DUR = {'s1': 4.5, 's2': 5.5, 's3': 7.5, 's4': 6.0, 's5': 6.5, 's6': 6.5, 's7': 7.5, 's8': 5.0}


def music_bed(kit, total, out):
    """한 묶음의 루프를 전부 겹쳐 total초 베드를 만든다(처음 1.5초 페이드인, 끝 3초 페이드아웃, -18 LUFS)."""
    files = sorted(LOOPS.glob(f'{kit}*.caf'))
    if not files:
        raise SystemExit(f'루프 묶음 없음: {kit} ({LOOPS})')
    args, chain = [], ''
    for i, f in enumerate(files):
        lvl = next((v for k, v in MUSIC_LEVEL if k.lower() in f.stem.lower()), 0.8)
        args += ['-stream_loop', '-1', '-i', str(f)]
        chain += f'[{i}:a]volume={lvl}[a{i}];'
    chain += ''.join(f'[a{i}]' for i in range(len(files))) + (f'amix=inputs={len(files)}:normalize=0,' if len(files) > 1 else '')
    # loudnorm이 끝부분을 조금 잘라내므로 3초 길게 만든 뒤 정확히 total초로 자른다
    # 페이드는 loudnorm 뒤에 둔다(앞에 두면 loudnorm이 줄어든 음량을 도로 키워 페이드가 사라진다)
    chain += (f'atrim=0:{total + 3},loudnorm=I=-18:TP=-1.5:LRA=9,aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,'
              f'afade=t=in:d=1.5,afade=t=out:st={total - 3}:d=3[out]')
    tmp = out.with_name(out.stem + '.long.wav')
    sh('ffmpeg', '-y', '-loglevel', 'error', *args, '-filter_complex', chain, '-map', '[out]', '-t', str(total + 3), str(tmp))
    sh('ffmpeg', '-y', '-loglevel', 'error', '-i', str(tmp), '-t', str(total), '-c', 'copy', str(out))
    tmp.unlink()
    return [f.stem for f in files]
_ST = None


def synth(text, wav):
    """한 장면의 내레이션을 48kHz 모노 wav로 만든다."""
    global _ST
    if TTS_ENGINE.startswith('supertonic'):
        name = TTS_ENGINE.split(':', 1)[1] if ':' in TTS_ENGINE else 'F3'
        if _ST is None:
            from supertonic import TTS
            _ST = TTS('supertonic-3')
        style = _ST.get_voice_style(name)
        audio, _ = _ST.synthesize(text, style, lang='ko', speed=1.08, silence_duration=0.25)
        raw = wav.with_name(wav.stem + '.raw.wav')
        _ST.save_audio(audio, str(raw))
        sh('ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-ar', '48000', '-ac', '1', str(wav))
        raw.unlink()
        return f'수퍼톤 {name}'
    aiff = wav.with_suffix('.aiff')
    sh('say', '-v', say_voice(), '-r', '172', '-o', str(aiff), text)
    sh('ffmpeg', '-y', '-loglevel', 'error', '-i', str(aiff), '-ar', '48000', '-ac', '1', str(wav))
    return '맥 내장 ' + say_voice()


def say_voice():
    """맥 내장 음성: 프리미엄 → 고급 → 기본 순으로 실제 설치된 것(say는 없는 음성을 주면 조용히 기본으로 바꾸므로 결과를 비교해 판별)."""
    AUDIO.mkdir(exist_ok=True)
    probe = AUDIO / '_probe'
    sh('say', '-v', 'com.apple.voice.compact.ko-KR.Yuna', '-o', f'{probe}_compact.aiff', '애보사')
    base = pathlib.Path(f'{probe}_compact.aiff').read_bytes()
    for cand in ['com.apple.voice.premium.ko-KR.Yuna', 'com.apple.voice.enhanced.ko-KR.Yuna']:
        sh('say', '-v', cand, '-o', f'{probe}_try.aiff', '애보사')
        if pathlib.Path(f'{probe}_try.aiff').read_bytes() != base:
            return cand
    print('경고: 유나(프리미엄)·유나(고급)이 설치돼 있지 않아 기본(compact) 유나로 만듭니다.')
    return 'com.apple.voice.compact.ko-KR.Yuna'


def sh(*cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


# ---------- 1. 앱 화면 캡처 ----------
def shots():
    from playwright.sync_api import sync_playwright
    SHOTS.mkdir(exist_ok=True)
    profile = {"birth": "2024-12", "works": ["엄마 까투리", "뽀로로"], "themes": ["탈것"], "lang": "both",
               "avoid": {"scary": True, "toy": True, "unverified": True}, "example": False, "consent": True}
    child = {"sex": "F", "birthDate": "2024-12-05"}
    growth = [{"id": "p1", "date": "2026-04-20", "h": 82.5, "w": 10.8, "hc": None},
              {"id": "p2", "date": "2026-07-20", "h": 85.0, "w": 11.4, "hc": None},
              {"id": "p3", "date": "2026-10-20", "h": 87.2, "w": 12.0, "hc": None}]
    init = ''.join(f"localStorage.setItem('aijy2:{k}', {json.dumps(json.dumps(v, ensure_ascii=False), ensure_ascii=False)});"
                   for k, v in [('profile', profile), ('child', child), ('growth', growth)])
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, locale="ko-KR", timezone_id="Asia/Seoul",
                            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
        ctx.add_init_script(init)
        pg = ctx.new_page()
        pg.goto('http://127.0.0.1:8765/site/index.html', wait_until='networkidle', timeout=60000)
        pg.wait_for_timeout(1200)
        # 유튜브 썸네일(남의 저작물)은 홍보 영상에 그대로 싣지 않고 흐리게 처리한다
        pg.add_style_tag(content='.thumb img, .wtile img, .rcard img { filter: blur(10px); }')
        def tab(name):
            pg.click(f'#tabs button[data-tab="{name}"]'); pg.wait_for_timeout(700)
        tab('video')
        pg.evaluate("window.scrollTo(0, document.querySelector('#situT').getBoundingClientRect().top + window.scrollY - 20)"); pg.wait_for_timeout(500)
        pg.screenshot(path=str(SHOTS / 'video.png'))
        tab('growth')
        pg.evaluate("""(() => { const h = [...document.querySelectorAll('h2,h3,summary')].find(e => e.textContent.includes('성장 그래프'));
                       if (h) window.scrollTo(0, h.getBoundingClientRect().top + window.scrollY - 20); })()"""); pg.wait_for_timeout(500)
        pg.screenshot(path=str(SHOTS / 'growth.png'))
        tab('clinic'); pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(300)
        pg.screenshot(path=str(SHOTS / 'clinic.png'))
        tab('deals'); pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(300)
        pg.screenshot(path=str(SHOTS / 'deals.png'))
        b.close()
    print('캡처 완료:', sorted(p.name for p in SHOTS.iterdir()))


# ---------- 2. 내레이션·길이표·자막 ----------
def audio():
    AUDIO.mkdir(exist_ok=True)
    rows, t = [], 0.0
    if TTS_ENGINE == 'none':
        for sid, min_dur, text in SCENES:
            dur = SILENT_DUR[sid]
            rows.append({'id': sid, 'start': round(t, 2), 'dur': dur, 'narr': 0, 'text': text})
            t += dur
        used = music_bed(MUSIC_KIT, round(t, 2), AUDIO / 'track.wav')
        (HERE / 'timeline.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
        srt = HERE / 'aebosa_promo.srt'
        if srt.exists():
            srt.unlink()
        print(f'음악만: {MUSIC_KIT} 묶음 {len(used)}개 루프({", ".join(used)}) · 전체 {round(t, 2)}초 · 자막 파일 없음')
        for r in rows:
            print(f"  {r['id']} {r['start']:6.2f}s +{r['dur']:5.2f}s")
        return
    engine = None
    for sid, min_dur, text in SCENES:
        wav = AUDIO / f'{sid}.wav'
        engine = synth(text, wav)
        n = float(sh('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(wav)).stdout.strip())
        dur = round(max(min_dur, LEAD + n + TAIL), 2)
        rows.append({'id': sid, 'start': round(t, 2), 'dur': dur, 'narr': round(n, 2), 'text': text})
        t += dur
    print('내레이션 엔진:', engine)
    (HERE / 'timeline.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
    # 자막(SRT): 내레이션이 나오는 구간
    def ts(x):
        h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
        return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')
    srt = ''.join(f"{i + 1}\n{ts(r['start'] + LEAD)} --> {ts(r['start'] + LEAD + r['narr'])}\n{r['text']}\n\n" for i, r in enumerate(rows))
    (HERE / 'aebosa_promo.srt').write_text(srt, encoding='utf-8')
    # 장면마다 0.5초 뒤에 시작하고 장면 길이만큼 채운 뒤 이어 붙인다
    inputs, chain = [], ''
    for i, r in enumerate(rows):
        inputs += ['-i', str(AUDIO / f"{r['id']}.wav")]
        chain += f"[{i}:a]adelay={int(LEAD * 1000)}:all=1,apad=whole_dur={r['dur']}[a{i}];"
    chain += ''.join(f'[a{i}]' for i in range(len(rows))) + f'concat=n={len(rows)}:v=0:a=1,loudnorm=I=-16:TP=-1.5:LRA=11[out]'
    sh('ffmpeg', '-y', '-loglevel', 'error', *inputs, '-filter_complex', chain, '-map', '[out]', '-ar', '48000', str(AUDIO / 'track.wav'))
    print('내레이션 완료. 전체', round(t, 2), '초')
    for r in rows:
        print(f"  {r['id']} {r['start']:6.2f}s +{r['dur']:5.2f}s (말 {r['narr']:.2f}s)")


def music_preview(kit):
    AUDIO.mkdir(exist_ok=True)
    wav = AUDIO / f'music_{kit.replace(" ", "_")}.wav'
    used = music_bed(kit, 30, wav)
    mp3 = wav.with_suffix('.mp3')
    sh('ffmpeg', '-y', '-loglevel', 'error', '-i', str(wav), '-codec:a', 'libmp3lame', '-b:a', '160k', str(mp3))
    print(f'{kit}: {len(used)}개 루프({", ".join(used)}) → {mp3}')


# ---------- 3. 장면 HTML ----------
def html(aspect):
    rows = json.loads((HERE / 'timeline.json').read_text(encoding='utf-8'))
    W, H = (1080, 1920) if aspect == '9x16' else (1920, 1080)
    v = aspect == '9x16'
    logo_svg = (HERE.parent / 'aebosa-logo.svg').read_text(encoding='utf-8')
    lockup_inner = logo_svg[logo_svg.index('>') + 1:logo_svg.rindex('</svg>')]
    import re
    vb = re.search(r'viewBox="([^"]+)"', logo_svg).group(1)
    def lockup(h):
        w0, h0 = [float(x) for x in vb.split()[2:]]
        return f'<svg viewBox="{vb}" width="{w0 / h0 * h:.1f}" height="{h}" aria-hidden="true">{lockup_inner}</svg>'
    img = lambda n: f'file://{SHOTS / n}'
    fonts = ''.join(f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url('file://{FONTS / f}') format('truetype')}}"
                    for fam, wt, f in [('Gowun Dodum', 400, 'GowunDodum-Regular.ttf'), ('Pretendard', '100 900', 'PretendardVariable.ttf')])
    css = f"""
{fonts}
:root{{--paper:#ffffff;--ink:#2a2633;--muted:#6e6878;--line:#ede5da;--soft:#fff6ec;--label:#f0824f;--label-soft:#ffe9dc;--label-ink:#8a3e1e;
--f-display:'Gowun Dodum',sans-serif;--f-body:'Pretendard',sans-serif}}
html,body{{margin:0;background:var(--paper)}}
#stage{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:var(--paper);color:var(--ink);font-family:var(--f-body);word-break:keep-all;line-height:1.5}}
.scene{{position:absolute;inset:0;display:none}}
.cap{{position:absolute;left:{96 if v else 120}px;top:{170 if v else 290}px;width:{W - 192 if v else 860}px}}
.cap h2{{font-family:var(--f-display);font-weight:400;font-size:{76 if v else 68}px;line-height:1.25;margin:0 0 26px;-webkit-text-stroke:0.5px currentColor}}
.cap p{{font-size:{40 if v else 36}px;line-height:1.55;font-weight:500;margin:0 0 14px}}
.cap p.m{{color:var(--muted);font-weight:400}}
.chip{{display:inline-block;padding:8px 26px;border-radius:999px;background:var(--label-soft);color:var(--label-ink);font-weight:600;font-size:{32 if v else 28}px;line-height:1.4;margin-bottom:28px}}
.phone{{position:absolute;{'left:200px;top:690px;width:680px;height:1472px;border-radius:64px' if v else 'right:140px;top:60px;width:444px;height:960px;border-radius:44px'};border:3px solid var(--line);overflow:hidden;background:var(--paper)}}
.phone img{{display:block;width:100%}}
.center{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 {96 if v else 200}px}}
.big{{font-size:{62 if v else 56}px;font-weight:600;line-height:1.5;margin:0}}
.big.m{{color:var(--muted);font-weight:400}}
.sym .ln{{fill:none;stroke:var(--ink);stroke-width:7;stroke-linecap:round;stroke-linejoin:round}}
.sym .dot{{fill:var(--label);transform-box:fill-box;transform-origin:center}}
.lock{{display:flex;align-items:center;gap:{80 if v else 64}px}}
.lock .word{{display:flex;flex-direction:column;text-align:left}}
.lock .word b{{font-family:var(--f-body);font-weight:800;font-size:{160 if v else 128}px;line-height:1.2;letter-spacing:-0.01em}}
.lock .word small{{font-size:{96 if v else 76}px;font-weight:500;line-height:1.3;color:var(--muted)}}
.promise{{display:flex;flex-direction:column;gap:{30 if v else 22}px;text-align:left;margin-top:40px}}
.promise div{{display:flex;align-items:center;gap:24px;font-size:{54 if v else 46}px;font-weight:600}}
.promise span{{display:inline-flex;align-items:center;justify-content:center;width:{72 if v else 60}px;height:{72 if v else 60}px;border-radius:999px;background:var(--label);color:var(--ink);font-size:{44 if v else 36}px;font-weight:800}}
.url{{font-size:{44 if v else 40}px;font-weight:600;margin:48px 0 12px}}
.note{{font-size:{34 if v else 30}px;color:var(--muted);font-weight:400;margin:0}}
"""
    def cap(chip, h2, ps):
        return (f'<div class="cap"><div class="chip" data-in="0.1">{chip}</div><h2 data-in="0.25">{h2}</h2>'
                + ''.join(f'<p class="{c}" data-in="{0.5 + i * 0.3:.2f}">{t}</p>' for i, (c, t) in enumerate(ps)) + '</div>')
    phone = lambda n, pan: f'<div class="phone" data-phone><img src="{img(n)}" data-pan="{pan if v else 0}"></div>'
    pan = 300
    scenes = {
        's1': f'''<div class="center"><div class="lock">
            <svg class="sym" viewBox="0 0 64 64" width="{240 if v else 192}" height="{240 if v else 192}" aria-hidden="true">
              <path class="ln dash" data-t0="0.2" d="M13 24L32 8L51 24"/><path class="ln dash" data-t0="0.6" d="M17 30V57H47V30M17 47H47"/>
              <circle class="dot" data-pop="1.5" cx="32" cy="37" r="6"/></svg>
            <div class="word"><b data-in="1.7">애보사</b><small data-in="2.2">애 보는 사람들</small></div></div></div>''',
        's2': '<div class="center"><p class="big" data-in="0.2">아이를 안고, 한 손으로.</p><p class="big" data-in="1.4">지금 필요한 것 하나만</p><p class="big m" data-in="1.9">빨리 찾고 싶을 때가 있습니다.</p></div>',
        's3': cap('영상', '지금 어떤 때인가요?', [('', '밥 준비할 때 · 차를 탔을 때 · 병원·식당에서 기다릴 때'), ('m', '몇 편 볼까요? 다 봤을 때 알려 드려요.')]) + phone('video.png', pan),
        's4': cap('성장', '우리 아이 성장', [('', '키와 몸무게를 적으면 같은 나이 아이들과 비교해 보여 드려요.')]) + phone('growth.png', pan),
        's5': cap('병원·약국', '지금 갈 수 있는 곳', [('', '위치는 버튼을 누를 때만 씁니다.'), ('m', '저장하거나 보내지 않습니다.')]) + phone('clinic.png', pan),
        's6': cap('핫딜', '기저귀·물티슈 핫딜', [('', '한 장당 가격이 싼 순서로'), ('m', '확인한 시각과 출처를 함께 적습니다.')]) + phone('deals.png', pan),
        's7': ('<div class="center"><h2 class="cap-h" data-in="0.1" style="font-family:var(--f-display);font-weight:400;font-size:' + ('76' if v else '68') + 'px;margin:0;-webkit-text-stroke:0.5px currentColor">애보사의 약속</h2><div class="promise">'
               + ''.join(f'<div data-in="{0.9 + i * 0.95:.2f}"><span>✓</span>{t}</div>' for i, t in enumerate(['짧게', '근거를 보인다', '판정하지 않는다', '아이 정보는 적게'])) + '</div></div>'),
        's8': f'<div class="center"><div data-in="0.1">{lockup(176 if v else 140)}</div><p class="url" data-in="0.7">{SITE}</p><p class="note" data-in="1.1">휴대폰 브라우저에서 바로 열립니다.</p><p class="note" data-in="1.4">지금은 샘플로 열려 있습니다.</p></div>',
    }
    body = ''.join(f'<section class="scene" id="{sid}">{scenes[sid]}</section>' for sid, _, _ in SCENES)
    js = """
const T = __ROWS__;
const ease = x => 1 - Math.pow(1 - x, 3);
const io = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const cl = (v, a, b) => Math.max(a, Math.min(b, v));
const pr = (lt, t0, d) => ease(cl((lt - t0) / d, 0, 1));
document.querySelectorAll('.dash').forEach(e => { const L = e.getTotalLength(); e.dataset.len = L; e.style.strokeDasharray = L; });
function setT(t) {
  for (const r of T) {
    const el = document.getElementById(r.id), lt = t - r.start, vis = lt >= 0 && lt < r.dur;
    el.style.display = vis ? 'block' : 'none';
    if (!vis) continue;
    el.style.opacity = Math.min(pr(lt, 0, .45), 1 - pr(lt, r.dur - .4, .4));
    el.querySelectorAll('[data-in]').forEach(e => { const p = pr(lt, +e.dataset.in, .55); e.style.opacity = p; e.style.transform = `translateY(${(1 - p) * 26}px)`; });
    el.querySelectorAll('[data-phone]').forEach(e => { const p = pr(lt, .15, .9); e.style.transform = `translateY(${(1 - p) * 180}px)`; e.style.opacity = p; });
    el.querySelectorAll('[data-pan]').forEach(e => { const p = io(cl((lt - 1.3) / Math.max(r.dur - 2.4, .1), 0, 1)); e.style.transform = `translateY(${-p * (+e.dataset.pan)}px)`; });
    el.querySelectorAll('.dash').forEach(e => { e.style.strokeDashoffset = (+e.dataset.len) * (1 - pr(lt, +e.dataset.t0, 1.1)); });
    el.querySelectorAll('[data-pop]').forEach(e => { const p = pr(lt, +e.dataset.pop, .45); e.style.transform = `scale(${p})`; e.style.opacity = p; });
  }
}
window.setT = setT; setT(0);
"""
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>{css}</style></head><body><div id="stage">{body}</div>'
            f'<script>{js.replace("__ROWS__", json.dumps(rows, ensure_ascii=False))}</script></body></html>'), W, H, rows


def open_page(p, aspect):
    doc, W, H, rows = html(aspect)
    (HERE / f'promo_{aspect}.html').write_text(doc, encoding='utf-8')
    b = p.chromium.launch()
    page = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
    page.goto(f'file://{HERE / f"promo_{aspect}.html"}', wait_until='load')
    page.wait_for_timeout(400)
    return b, page, W, H, rows


def preview():
    from playwright.sync_api import sync_playwright
    out = HERE / '_preview'; out.mkdir(exist_ok=True)
    with sync_playwright() as p:
        for aspect in ('9x16', '16x9'):
            b, page, W, H, rows = open_page(p, aspect)
            for r in rows:
                for k, off in (('a', 1.2), ('b', max(r['dur'] - 1.0, 1.5))):
                    page.evaluate(f"setT({r['start'] + off})")
                    page.screenshot(path=str(out / f"{aspect}_{r['id']}{k}.png"), clip={'x': 0, 'y': 0, 'width': W, 'height': H})
            b.close()
    print('미리보기:', len(list(out.iterdir())), '장 →', out)


def render(aspect):
    from playwright.sync_api import sync_playwright
    frames = SCRATCH / aspect
    shutil.rmtree(frames, ignore_errors=True); frames.mkdir(parents=True)
    with sync_playwright() as p:
        b, page, W, H, rows = open_page(p, aspect)
        total = rows[-1]['start'] + rows[-1]['dur']
        n = int(round(total * FPS))
        for k in range(n):
            page.evaluate(f'setT({k / FPS})')
            page.screenshot(path=str(frames / f'f{k:05d}.png'), clip={'x': 0, 'y': 0, 'width': W, 'height': H})
            if k % 300 == 0:
                print(f'  프레임 {k}/{n}', flush=True)
        b.close()
    out = HERE / f'aebosa_promo_{aspect}.mp4'
    sh('ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(frames / 'f%05d.png'), '-i', str(AUDIO / 'track.wav'),
       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-r', str(FPS),
       '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(out))
    shutil.rmtree(frames, ignore_errors=True)
    print('영상 완료:', out, out.stat().st_size // 1024, 'KB ·', n, '프레임 ·', round(total, 2), '초')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    if cmd == 'music':
        music_preview(sys.argv[2])
    else:
        {'shots': shots, 'audio': audio, 'preview': preview}.get(cmd, lambda: render(sys.argv[2]))()
