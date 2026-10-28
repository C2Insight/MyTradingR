# 📊 투자 리서치 허브

Daily-Stock-Movers 봇의 일일 리포트를 모아 **거래대금 Top 3 달력**으로 보는 개인 사이트 (GitHub Pages).
예전 콘텐츠(특징주 일지·종목 리포트·데이터)는 `legacy` 브랜치에 보관되어 있다.

## 구성

```
index.html                     잠금 화면 + 1·3·6·12개월 Top 3 달력 · 기간 집중 종목 · 리포트 패널
dsm/memo.js                    잠금 해제 · 메모 저장소 읽기/쓰기 (허브와 리포트가 함께 씀)
dsm/auth.json                  잠금 비밀번호로 암호화한 메모 저장소 접근 정보 (tools/make_auth.py)
dsm/YYYY.json                  연도별 일일 기록 — 봇이 거래일 20:15 리포트 뒤 올림
dsm/YYYY/DSM_YYYY-MM-DD.html   일일 리포트 — 봇이 올림
tools/make_auth.py             잠금 설정 생성 (비밀번호·메모 토큰 변경 시)
```

- **데이터는 봇만 쓴다.** `dsm/YYYY.json` 과 리포트는 Daily-Stock-Movers 봇(`publish.py`)이 GitHub API 로 커밋한다.
  하루 한 커밋 `DSM YYYY-MM-DD (N종목)`. 직접 고치지 않는다.
- **Top 3** = 그날 20:15 회차에 4개 조건을 모두 충족한 종목 중 거래대금 1~3위.
- **검색 엔진 차단**: 모든 페이지에 `noindex, nofollow`. (프로젝트 사이트라 `robots.txt` 는 효과가 없다.)

## 잠금과 메모

- 잠금 화면 비밀번호로 `dsm/auth.json` 을 복호화(PBKDF2-SHA256 600,000회 → AES-256-GCM)해 풀리면 열린다.
  비밀번호는 어디에도 저장되지 않는다. 열린 상태는 그 탭에만 유지된다 (탭을 닫으면 다시 잠김).
- **메모**는 리포트의 종목 카드에서 쓴다. 입력이 멈추면 비공개 저장소 `C2Insight/MyTradingR-memo` 의
  `memos/YYYY.json` 에 자동 저장되어 어느 기기에서나 같은 메모가 보인다. 저장 전 입력은 그 기기에 보관했다가 다시 보낸다.
- 이 저장소는 공개라 **리포트·기록 파일은 주소를 알면 누구나 볼 수 있다** (잠금은 화면만 가림). 메모는 비공개 저장소에만 있다.

### 비밀번호나 메모 토큰 바꾸기

```powershell
# 메모 저장소 전용 토큰: GitHub → Settings → Developer settings → Fine-grained tokens
#   Repository access: Only MyTradingR-memo · Permissions: Contents = Read and write
..\Daily-Stock-Movers-bot\.venv\Scripts\python tools\make_auth.py     # 비밀번호 2회 + 토큰 입력
git add dsm/auth.json; git commit -m "잠금 설정 변경"; git push
```
