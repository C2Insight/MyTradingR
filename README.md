# 📊 투자 리서치 허브

개인 전용 투자 분석 아카이브 — GitHub Pages 기반

---

## 📁 디렉터리 구조

```
📁 repository/
├── index.html                    ← 메인 허브 (비밀번호 보호)
├── data/
│   └── site-index.json           ← 자동 생성 인덱스 (직접 수정 불필요)
├── daily/                        ← ★ 매일 특징주 파일 업로드
│   └── YYYY/
│       └── MM/
│           └── YYYYMMDD.html
├── journal/                      ← 추후: 매매 일지
│   └── YYYY/
│       └── MM/
│           └── YYYYMMDD_종목명.html
├── reports/                      ← 추후: 종목 리포트
│   └── TICKER/
│       └── YYYYMMDD_종목명.html
├── scripts/
│   └── generate_index.py         ← 인덱스 생성 스크립트
└── .github/
    └── workflows/
        └── update-index.yml      ← CI: 파일 푸시 시 자동 인덱스 갱신
```

---

## 🚀 초기 설정 (1회)

### 1단계 — 레포지터리 생성

```bash
# GitHub에서 새 레포지터리 생성 후
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# 이 파일들 전체를 복사한 뒤
git add .
git commit -m "초기 설정"
git push
```

### 2단계 — GitHub Pages 활성화

1. GitHub 레포지터리 → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `/ (root)` 선택 → **Save**
4. 몇 분 뒤 `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/` 에서 접근 가능

> **공개/비공개 선택:**
> - **무료 (Public repo)**: GitHub Pages 무료 지원. index.html 비밀번호로 보호됨.
>   파일 URL을 직접 알면 접근 가능하므로 "소프트 프라이버시" 수준.
> - **GitHub Pro ($4/월) + Private repo**: 완전한 비공개. GitHub Pages on private repo 지원.

### 3단계 — 비밀번호 변경 (중요)

기본 비밀번호는 `invest2026` 입니다. 반드시 변경하세요.

```bash
# 원하는 비밀번호의 SHA-256 해시 생성
python3 -c "import hashlib; print(hashlib.sha256('YOUR_NEW_PASSWORD'.encode()).hexdigest())"
```

생성된 해시를 `index.html` 상단 `CONFIG` 블록에 붙여넣기:

```javascript
const CONFIG = {
  passwordHash: "여기에_새_해시값_붙여넣기",
  ...
};
```

---

## 📅 매일 파일 업로드 방법

### 방법 A — GitHub 웹 UI (가장 간단)

1. `https://github.com/YOUR_USERNAME/YOUR_REPO_NAME` 접속
2. `daily/` → `2026/` → `04/` 폴더로 이동
3. **Add file** → **Upload files**
4. `20260410.html` 드래그 & 드롭
5. Commit → 약 1분 후 인덱스 자동 갱신

### 방법 B — Git CLI

```bash
# 파일을 올바른 경로에 복사
cp 20260415.html daily/2026/04/20260415.html

# 커밋 & 푸시
git add daily/2026/04/20260415.html
git commit -m "특징주 2026-04-15 추가"
git push
```
→ GitHub Actions가 자동으로 `data/site-index.json` 갱신

### 방법 C — Python 스크립트 직접 실행

```bash
# 파일 복사 후 로컬에서 인덱스 갱신
python3 scripts/generate_index.py

git add data/site-index.json daily/2026/04/20260415.html
git commit -m "특징주 2026-04-15 추가"
git push
```

---

## 🔮 향후 확장

### 매매 일지 추가

```
journal/2026/04/20260415_덕산네오룩스_매수.html
```
포맷: `YYYYMMDD_종목명_액션.html`

### 종목 리포트 추가

```
reports/005290/20260415_덕산네오룩스_심층분석.html
```
포맷: `reports/종목코드/YYYYMMDD_종목명.html`

두 섹션은 `index.html`의 탭에 이미 준비되어 있으며,  
파일을 위 경로로 업로드하면 자동으로 목록에 표시됩니다.

---

## ⚙️ GitHub Actions 권한 설정

Actions가 인덱스를 자동 커밋하려면:

1. **Settings** → **Actions** → **General**
2. **Workflow permissions** → **Read and write permissions** 선택
3. Save

---

## 🔒 보안 참고사항

- `index.html`의 비밀번호 해시는 SHA-256으로 저장됩니다 (평문 저장 없음)
- 세션은 브라우저 탭을 닫으면 자동 만료됩니다 (sessionStorage)
- 완전한 보안이 필요한 경우 Private repo + GitHub Pro 구독 권장
