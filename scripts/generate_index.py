#!/usr/bin/env python3
"""
generate_index.py
─────────────────
daily/, journal/, reports/ 폴더를 스캔하여
data/site-index.json 을 자동 생성합니다.

사용법:
  python3 scripts/generate_index.py

GitHub Actions 에서도 자동으로 실행됩니다.
"""
import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent  # repository root

def count_stocks(html_path: Path) -> int:
    """HTML 파일에서 평가 종목 수를 추출합니다."""
    try:
        text = html_path.read_text(encoding='utf-8', errors='ignore')
        # "평가 종목: 49개" 패턴 파싱
        m = re.search(r'평가\s*종목[:\s：]+(\d+)', text)
        if m:
            return int(m.group(1))
        # <tbody> 안의 <tr> 수로 대략 추정
        rows = text.count('<tr>') - 1  # header row 제외
        return max(0, rows)
    except Exception:
        return 0

def scan_daily() -> list:
    """daily/YYYY/MM/YYYYMMDD.html 파일을 스캔합니다."""
    entries = []
    base = ROOT / "daily"
    if not base.exists():
        return entries

    for html in sorted(base.rglob("*.html"), reverse=True):
        rel = html.relative_to(ROOT)
        parts = rel.parts  # ('daily', '2026', '04', '20260410.html')
        if len(parts) != 4:
            continue

        stem = html.stem  # '20260410'
        if not re.fullmatch(r'\d{8}', stem):
            continue

        date_str = f"{stem[0:4]}-{stem[4:6]}-{stem[6:8]}"
        entries.append({
            "date":   date_str,
            "path":   str(rel).replace("\\", "/"),
            "stocks": count_stocks(html)
        })

    return entries

def scan_journal() -> list:
    """journal/YYYY/MM/YYYYMMDD_*.html 파일을 스캔합니다."""
    entries = []
    base = ROOT / "journal"
    if not base.exists():
        return entries

    for html in sorted(base.rglob("*.html"), reverse=True):
        rel = html.relative_to(ROOT)
        stem = html.stem
        m = re.match(r'(\d{8})_(.*)', stem)
        if not m:
            continue
        raw_date, title = m.group(1), m.group(2)
        date_str = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        entries.append({
            "date":  date_str,
            "title": title.replace('_', ' '),
            "path":  str(rel).replace("\\", "/")
        })

    return entries

def scan_reports() -> list:
    """reports/YYYY/MM/DD/*.html 파일을 스캔합니다.
    
    경로 구조:
      reports/2026/04/13/삼성전자.html
      reports/2026/04/13/덕산네오룩스.html
    """
    entries = []
    base = ROOT / "reports"
    if not base.exists():
        return entries

    for html in sorted(base.rglob("*.html"), reverse=True):
        rel  = html.relative_to(ROOT)
        parts = rel.parts  # ('reports', '2026', '04', '13', '삼성전자.html')
        if len(parts) != 5:
            continue

        year_str, month_str, day_str = parts[1], parts[2], parts[3]

        # 유효한 날짜 폴더인지 확인
        if not (re.fullmatch(r'\d{4}', year_str) and
                re.fullmatch(r'\d{2}', month_str) and
                re.fullmatch(r'\d{2}', day_str)):
            continue

        date_str = f"{year_str}-{month_str}-{day_str}"
        title = html.stem.replace('_', ' ')

        entries.append({
            "date":  date_str,
            "title": title,
            "path":  str(rel).replace("\\", "/")
        })

    return entries

def main():
    daily   = scan_daily()
    journal = scan_journal()
    reports = scan_reports()

    index = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "daily":     daily,
        "journal":   journal,
        "reports":   reports
    }

    out = ROOT / "data" / "site-index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"✅ site-index.json 생성 완료")
    print(f"   특징주 일지: {len(daily)}개")
    print(f"   매매 일지:   {len(journal)}개")
    print(f"   종목 리포트: {len(reports)}개")

if __name__ == "__main__":
    main()
