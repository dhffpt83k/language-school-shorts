# Language School Shorts · 스마트폰 앱 배포 키트

엑셀만 고쳐서 GitHub에 올리면 **1~2분 뒤 모든 사람의 앱에 바로 반영**되는 구조예요.
앱 스토어 심사도 없고, 비용도 들지 않아요.

```
엑셀 수정 → GitHub에 올림 → (자동) 검사 → 게임 데이터 생성 → 배포 → 사용자 앱에 반영
```

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `index.html` | 게임 본체 |
| `sw.js` | 오프라인 실행 + 최신 파일 우선으로 받기 |
| `manifest.webmanifest`, `icons/` | 홈 화면에 앱으로 설치되게 하는 정보와 아이콘 |
| `content/Language_School_All_Dialogues.xlsx` | **여기만 고치면 돼요** |
| `tools/build_data.py` | 엑셀 → `data/*.json` 변환 + 검사 |
| `data/` | 변환된 게임 데이터 (자동 생성, 직접 고칠 필요 없음) |
| `.github/workflows/deploy.yml` | 올릴 때마다 자동으로 검사하고 배포하는 설정 |

---

## 처음 한 번만: 설정

### 1. GitHub 저장소 만들기
- GitHub에서 **New repository** → 이름 예: `language-school-shorts` → **Public** 선택 → Create.
- 무료 계정은 **공개 저장소만** GitHub Pages로 배포할 수 있어요. 비공개 저장소로 배포하려면 GitHub Pro(유료)가 필요해요.

### 2. 파일 올리기
**방법 A — GitHub Desktop (추천)**
저장소를 내 컴퓨터로 Clone → 이 폴더의 파일을 전부 복사해 넣기 → Commit → Push.

**방법 B — 웹에서 올리기**
1. 저장소 화면에서 **Add file → Upload files** → 이 폴더 안의 파일과 폴더를 끌어다 놓기 → Commit.
2. `.github` 폴더는 숨김 폴더라 빠질 수 있어요. 빠졌다면
   **Add file → Create new file** → 파일 이름 칸에 `.github/workflows/deploy.yml` 입력 →
   이 키트의 `deploy.yml` 내용을 그대로 붙여 넣기 → Commit.

### 3. Pages 켜기
저장소 **Settings → Pages → Build and deployment → Source** 를 **GitHub Actions** 로 바꿔요.

### 4. 첫 배포 확인
**Actions** 탭에서 "앱 배포"가 초록색 ✓ 가 되면 끝이에요.
주소는 `https://<내 GitHub 아이디>.github.io/language-school-shorts/` 예요.
(처음 한 번은 Actions 탭에서 **Run workflow** 를 눌러야 할 수도 있어요.)

---

## 스마트폰에 설치하기

| 폰 | 방법 |
|---|---|
| 안드로이드 (Chrome) | 주소 열기 → 오른쪽 위 ⋮ → **앱 설치** 또는 **홈 화면에 추가** |
| 아이폰 (Safari) | 주소 열기 → 아래 공유 버튼 → **홈 화면에 추가** |

설치하면 주소창 없이 앱처럼 전체 화면으로 열리고, 인터넷이 없어도 마지막으로 받은 내용으로 실행돼요.

---

## 업데이트하는 법 (매번)

1. `content/Language_School_All_Dialogues.xlsx` 를 고쳐요. (파일 이름은 그대로)
2. GitHub에 올려요. 웹이라면 `content` 폴더 → **Add file → Upload files** → 같은 이름으로 덮어쓰기 → Commit.
3. 1~2분 뒤 **Actions** 탭에 초록색 ✓ 가 뜨면 배포 완료예요.

사용자 쪽에서는
- 앱을 새로 열면 바로 새 내용이 나오고 "✨ 업데이트 완료!" 알림이 떠요.
- 앱을 켜 둔 채였다면, 다시 앱으로 돌아올 때 위쪽에 **"🔄 새 업데이트가 있어요"** 버튼이 떠요.

게임 화면(`index.html`)을 고쳐서 올려도 똑같이 바로 반영돼요.

### 빨간색 ✗ 가 뜨면
엑셀에 문제가 있어서 **배포를 멈춘 거예요.** 사용자 앱은 이전 버전 그대로라 안전해요.
Actions → 실패한 항목 → "엑셀 검사 + 게임 데이터 만들기"를 열면
`엑셀 152행: 오답 'Here.'에 피드백이 없음` 처럼 고칠 곳이 나와요. 고쳐서 다시 올리면 돼요.

내 컴퓨터에서 미리 검사하려면:
```
pip install openpyxl
python tools/build_data.py
```

---

## 알아 둘 점

- **진행 기록**(XP, 도감, 연속 일수)은 각 폰의 브라우저 안에만 저장돼요. 업데이트해도 지워지지 않지만, 앱을 지우거나 브라우저 데이터를 삭제하면 초기화돼요. 기기를 바꿔도 이어 하려면 로그인과 서버가 필요해요.
- **Play 스토어에 올리고 싶어지면**: PWABuilder(pwabuilder.com)에 이 주소를 넣으면 안드로이드 앱(TWA)으로 포장해 줘요. 스토어 앱도 내용은 이 주소에서 받아 오기 때문에 **업데이트는 지금처럼 바로 적용**돼요. 스토어 등록비(1회 25달러)가 들어요.
- **App Store**는 웹을 감싸기만 한 앱을 심사에서 거절하는 경우가 많아요. 아이폰은 "홈 화면에 추가"로 쓰는 걸 추천해요.
