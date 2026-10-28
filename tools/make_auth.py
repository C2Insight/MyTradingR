"""
투자 리서치 허브 잠금 설정 — dsm/auth.json 생성.

잠금 화면 비밀번호로 메모 저장소(GitHub 비공개 저장소) 접근 정보를 암호화한다.
  PBKDF2-SHA256(비밀번호, salt, 600,000회) → AES-256-GCM({"repo", "token"})
허브는 입력한 비밀번호로 이 파일을 풀어 보고, 풀리면 잠금을 연다.
비밀번호는 어디에도 저장하지 않고, 토큰은 암호문으로만 공개 저장소에 올라간다.

  python tools/make_auth.py [--repo C2Insight/MyTradingR-memo] [--out dsm/auth.json]
  → 비밀번호(2회)와 메모 저장소 토큰을 묻고, 토큰으로 저장소 읽기·쓰기를 확인한 뒤 파일을 쓴다.
  비밀번호나 토큰을 바꿀 때도 다시 실행한다 (기존 메모는 그대로).

  python tools/make_auth.py --check
  → 로그인이 안 될 때: 비밀번호를 물어 지금 사이트에 올라간 auth.json 이 풀리는지 확인한다 (비밀번호는 출력하지 않음).

필요 패키지: cryptography, requests
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import sys
from pathlib import Path

import requests
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERATIONS = 600_000
API = "https://api.github.com"
SITE_AUTH = "https://c2insight.github.io/MyTradingR/dsm/auth.json"


def typing_issues(pw: str) -> list[str]:
    """웹 비밀번호 칸에서 똑같이 입력할 수 없는 문자 (비밀번호 칸은 한글 입력기가 꺼진다)."""
    issues = []
    if any(ord(c) > 127 for c in pw):
        issues.append("한글 등 영문이 아닌 문자 (설정할 때 한/영 키가 한글 상태였을 수 있음)")
    if any(ord(c) < 32 or ord(c) == 127 for c in pw):
        issues.append("보이지 않는 제어 문자 (붙여넣기가 글자 대신 들어갔을 수 있음)")
    if pw != pw.strip():
        issues.append("앞이나 뒤의 공백")
    return issues


def check_repo(repo: str, token: str) -> None:
    """비공개 저장소인지, 토큰으로 읽고 쓸 수 있는지 (memos/.keep 을 만들어 확인)."""
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    r = requests.get(f"{API}/repos/{repo}", headers=h, timeout=15)
    if r.status_code != 200:
        sys.exit(f"메모 저장소에 접근할 수 없습니다 ({r.status_code}) — 저장소 이름과 토큰의 저장소 범위를 확인하세요")
    if not r.json().get("private"):
        sys.exit(f"{repo} 가 공개(public) 저장소입니다 — 메모가 공개되므로 비공개로 바꿔 주세요")
    keep = f"{API}/repos/{repo}/contents/memos/.keep"
    if requests.get(keep, headers=h, timeout=15).status_code == 404:
        r = requests.put(keep, headers=h, timeout=15,
                         json={"message": "메모 폴더", "content": base64.b64encode(b"").decode()})
        if r.status_code not in (200, 201):
            sys.exit(f"메모 저장소에 쓸 수 없습니다 ({r.status_code}) — 토큰 권한 Contents 를 Read and write 로 주세요")


def encrypt(password: str, repo: str, token: str) -> dict:
    """auth.json 내용 — memo.js unlock() 이 같은 방식으로 푼다."""
    salt, iv = os.urandom(16), os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, 32)
    ct = AESGCM(key).encrypt(iv, json.dumps({"repo": repo, "token": token}).encode("utf-8"), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITERATIONS, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


def decrypt(password: str, auth: dict) -> "dict | None":
    """auth.json 을 비밀번호로 풀기 — 틀리면 None (memo.js unlock() 과 같은 계산)."""
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(auth["salt"]), auth["iter"], 32)
    try:
        return json.loads(AESGCM(key).decrypt(base64.b64decode(auth["iv"]), base64.b64decode(auth["ct"]), None))
    except InvalidTag:
        return None


def check() -> None:
    """로그인이 안 될 때 — 지금 사이트의 auth.json 이 이 비밀번호로 풀리는지."""
    r = requests.get(SITE_AUTH, params={"v": os.urandom(4).hex()}, headers={"Cache-Control": "no-cache"}, timeout=15)
    r.raise_for_status()
    auth = r.json()
    pw = getpass.getpass("사이트에서 입력하는 비밀번호 (입력이 보이지 않습니다): ")
    issues = typing_issues(pw)
    print(f"입력 길이 {len(pw)}자")
    if decrypt(pw, auth):
        if issues:
            print("이 비밀번호로 풀리지만, 웹 비밀번호 칸에서는 같은 값을 칠 수 없습니다: " + ", ".join(issues))
            print("→ 한/영 키를 영문 상태로 두고 make_auth.py 를 다시 실행해 주세요.")
        else:
            print("✅ 비밀번호가 맞습니다 (사이트 파일과 일치). 브라우저 쪽 문제입니다:")
            print("   · Ctrl+F5 로 새로고침하거나 시크릿 창에서 열기 (예전 잠금 화면이 남아 있을 수 있음)")
            print("   · 입력칸에 자동완성된 옛 비밀번호를 지우고 직접 입력 · 한/영 키와 Caps Lock 확인")
    else:
        print("❌ 이 비밀번호로는 풀리지 않습니다 — 설정할 때 다른 값이 들어갔습니다 (한/영 상태·오타).")
        if issues:
            print("   지금 입력에도 " + ", ".join(issues) + " 이(가) 있습니다.")
        print("→ 한/영 키를 영문 상태로 두고 make_auth.py 를 다시 실행해 주세요.")


def main() -> None:
    ap = argparse.ArgumentParser(description="투자 리서치 허브 잠금 설정 (dsm/auth.json)")
    ap.add_argument("--repo", default="C2Insight/MyTradingR-memo", help="메모 저장소 (비공개)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "dsm" / "auth.json"))
    ap.add_argument("--check", action="store_true", help="로그인이 안 될 때: 사이트의 auth.json 이 이 비밀번호로 풀리는지 확인")
    args = ap.parse_args()
    if args.check:
        check()
        return

    print("※ 한/영 키를 영문 상태로 두고 입력하세요 (웹 비밀번호 칸에서는 한글을 칠 수 없습니다)")
    pw = getpass.getpass("잠금 화면 비밀번호 (입력이 보이지 않습니다): ")
    if len(pw) < 10:
        sys.exit("10자 이상으로 정해 주세요 (이 비밀번호가 메모를 지킵니다)")
    if typing_issues(pw):
        sys.exit("비밀번호에 " + ", ".join(typing_issues(pw)) + " 이(가) 있습니다 — 영문·숫자·기호로만 정해 주세요")
    if getpass.getpass("비밀번호 한 번 더: ") != pw:
        sys.exit("두 비밀번호가 다릅니다")
    token = getpass.getpass(f"{args.repo} 토큰 (github_pat_…, 입력이 보이지 않습니다): ").strip()
    check_repo(args.repo, token)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(encrypt(pw, args.repo, token), indent=1) + "\n", encoding="utf-8")
    print(f"완료: {out}\n메모 저장소 {args.repo} 읽기·쓰기 확인. 이 파일을 커밋·푸시하면 새 비밀번호가 적용됩니다.")


if __name__ == "__main__":
    main()
