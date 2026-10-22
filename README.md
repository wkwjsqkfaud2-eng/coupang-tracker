# 쿠팡 최저가 추적기

쿠팡 파트너스 API로 **1시간마다 자동으로 가격을 수집**하고,
평소보다 싸진 상품을 골라 **가격 그래프 웹페이지**로 보여줍니다.
카드를 누르면 그래프가 열리고, **[카톡 문구 복사]** 버튼으로 단톡방에 바로 올릴 수 있어요
(파트너스 링크 + 대가성 문구 자동 포함).

컴퓨터를 켜둘 필요 없이 **GitHub(무료)** 에서 돌아갑니다.

---

## 처음 한 번만 하는 설정 (약 15분)

### 1. GitHub 가입 & 저장소 만들기
1. https://github.com 에서 가입
2. 오른쪽 위 **+** → **New repository**
3. 이름: `coupang-tracker` / **Public** 선택 / **Create repository**
   (무료 계정은 Public이어야 웹페이지 기능을 쓸 수 있어요. API 키는 아래 3번처럼 따로 숨겨서 저장하니 노출되지 않아요.)

### 2. 파일 올리기
1. 만든 저장소 화면에서 **uploading an existing file** 클릭
2. 압축 푼 폴더 안의 파일·폴더(`config.py`, `coupang_api.py`, `tracker.py`, `template.html`, `README.md`, `docs` 폴더)를 끌어다 놓고 **Commit changes**
3. 자동 실행 파일은 숨김 폴더라 따로 만들어요:
   **Add file → Create new file** → 파일 이름 칸에 `.github/workflows/track.yml` 입력
   → 압축 폴더의 `.github/workflows/track.yml` 내용을 복사해 붙여넣기 → **Commit changes**
   (Mac에서 숨김 폴더가 안 보이면 Finder에서 `Cmd + Shift + .`)

### 3. API 키 등록 (비밀로 저장됨)
**Settings → Secrets and variables → Actions → New repository secret** 을 두 번:
| Name | Secret |
|---|---|
| `COUPANG_ACCESS_KEY` | 파트너스 Access Key |
| `COUPANG_SECRET_KEY` | 파트너스 Secret Key |

### 4. 웹페이지 켜기
**Settings → Pages** → Branch: `main`, 폴더: `/docs` → **Save**
1~2분 뒤 `https://내아이디.github.io/coupang-tracker/` 주소가 생겨요. 휴대폰 홈 화면에 추가해두면 앱처럼 쓸 수 있어요.

### 5. 첫 실행
**Actions** 탭 → (처음이면 초록 버튼으로 활성화) → **쿠팡 가격 수집** → **Run workflow**
초록 체크가 뜨면 성공! 이후엔 1시간마다 자동으로 돌아요.

---

## 사용 팁
- **처음 2~3일은 핫딜이 거의 안 떠요.** "평소 가격"을 알려면 기록이 쌓여야 해서요. 그동안은 [전체] 탭에서 인기 상품을 보세요.
- **검색어 바꾸기**: 저장소에서 `config.py` 클릭 → 연필 아이콘 → `KEYWORDS` 목록 수정 → Commit
- **핫딜 기준 바꾸기**: `config.py`의 `HOT_DROP_PERCENT` (기본 10%)
- 실패하면 **Actions** 탭에서 빨간 X를 눌러 오류 내용을 확인하세요.

## 꼭 지켜야 할 것
- 쿠팡 **검색 API는 1시간에 10번 제한**이 있어요. `KEYWORDS_PER_RUN`을 10 넘게 올리지 마세요 (연속 실패 시 계정 정지 위험).
  프로그램은 검색이 한 번 실패하면 그 회차 검색을 바로 멈추도록 되어 있어요.
- 단톡방에 올릴 때 **"쿠팡 파트너스 활동의 일환으로…" 문구는 법적 의무**예요. 복사 버튼에 자동으로 들어가니 지우지 마세요.
- API 키를 `config.py`나 다른 파일에 직접 적지 마세요. 반드시 3번처럼 Secrets에만 넣으세요.

## 내 컴퓨터에서 미리보기 (선택)
Python 설치 후:
```
python tracker.py --demo
```
→ `docs/index.html` 을 더블클릭하면 가짜 데이터로 화면을 볼 수 있어요.
