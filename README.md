# 애보사(샘플)

애보사는 '애 보는 사람들'의 줄임말입니다.

0~5세 아이를 키우는 보호자가 아이에게 틀어 줄 영상, 키·몸무게 기록, 고민 메모, 지금 갈 수 있는 병원·약국, 기저귀·물티슈 가격을 한곳에서 찾는 웹 앱 샘플입니다.

- 올리는 방법과 필요한 키: [README_자체주소.md](README_자체주소.md)
- 빌드: `python3 build.py` → `site/index.html`, 병원·약국 자료: `python3 fetch_clinics.py`
- 로고·앱 아이콘·링크 공유 그림: `brand/` (다시 만들기: `python3 brand/make_brand.py`) · 홍보 영상: `brand/promo/aebosa_promo_9x16.mp4`, `aebosa_promo_16x9.mp4` (다시 만들기: `brand/promo/make_promo.py` 맨 위 설명)
