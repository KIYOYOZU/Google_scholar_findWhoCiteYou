"""
Use the OpenAlex API to collect citation metadata for
"An entropy-stable hybrid scheme for simulations of transcritical real-fluid flows".

Workflow:
1. Resolve the target paper's OpenAlex ID (by DOI).
2. Pull all works that cite it via the `cites:` filter (with pagination).
3. Filter out self-citations from the original author list.
4. Transform the data into CSV/Markdown outputs mirroring the previous pipeline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

TARGET_DOI = "https://doi.org/10.1016/j.jcp.2017.03.022"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"

DATA_DIR = Path("data")
REPORTS_DIR = Path("reports")
RAW_JSON_PATH = DATA_DIR / "citations_raw.json"
CSV_OUTPUT_PATH = DATA_DIR / "citations.csv"
MARKDOWN_OUTPUT_PATH = REPORTS_DIR / "citations_summary.md"

HEADERS = {
    "User-Agent": "CitationCollector/0.2 (+https://example.org; mailto:codex-agent@example.com)"
}

ORIGINAL_AUTHORS = {
    "peter c ma",
    "pc ma",
    "p c ma",
    "peter ma",
    "yu lv",
    "y lv",
    "matthias ihme",
    "m ihme",
}


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #


def ensure_directories() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def normalize_author_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    return normalize_whitespace(name)


def format_author_entry(name: str, affiliations: Iterable[str]) -> Tuple[str, List[str]]:
    clean_name = name or "信息缺失"
    affs = sorted({normalize_whitespace(aff) for aff in affiliations if aff})
    summary = affs if affs else []
    if affs:
        return f"{clean_name} ({'; '.join(affs)})", summary
    return f"{clean_name} (信息缺失)", summary


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------- #
# OpenAlex API helpers
# --------------------------------------------------------------------------- #


def fetch_target_work(session: requests.Session) -> Dict[str, Any]:
    url = f"{OPENALEX_WORKS_URL}/{TARGET_DOI}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_citing_works(session: requests.Session, work_id: str, sleep: float = 0.2) -> List[Dict[str, Any]]:
    citing_records: List[Dict[str, Any]] = []
    cursor = "*"
    while cursor:
        params = {"filter": f"cites:{work_id}", "per-page": 200, "cursor": cursor}
        response = session.get(OPENALEX_WORKS_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        citing_records.extend(payload.get("results", []))
        cursor = payload.get("meta", {}).get("next_cursor")
        if cursor:
            time.sleep(sleep)
    return citing_records


# --------------------------------------------------------------------------- #
# Transformation logic
# --------------------------------------------------------------------------- #


def extract_authors(record: Dict[str, Any]) -> Tuple[List[str], List[List[str]]]:
    authors: List[str] = []
    affiliations: List[List[str]] = []

    for authorship in record.get("authorships", []):
        author = authorship.get("author", {}) or {}
        name = normalize_whitespace(author.get("display_name") or "")
        institutions = [
            normalize_whitespace(inst.get("display_name") or "")
            for inst in authorship.get("institutions", [])
            if inst.get("display_name")
        ]
        if name:
            authors.append(name)
            affiliations.append([aff for aff in institutions if aff])

    return authors, affiliations


def should_exclude_self_citation(authors: Iterable[str]) -> bool:
    normalized = {normalize_author_name(name) for name in authors if name}
    return bool(normalized.intersection(ORIGINAL_AUTHORS))


def record_to_output_row(index: int, record: Dict[str, Any]) -> Dict[str, Any]:
    authors, author_affiliations = extract_authors(record)

    author_entries: List[str] = []
    aggregated_affs: List[str] = []
    for name, affs in zip(authors, author_affiliations):
        entry, aff_list = format_author_entry(name, affs)
        author_entries.append(entry)
        aggregated_affs.extend(aff_list)

    missing_value = "\u4fe1\u606f\u7f3a\u5931"
    aggregated_unique = "; ".join(sorted({aff for aff in aggregated_affs if aff})) or missing_value

    doi = record.get("doi") or (record.get("ids") or {}).get("doi") or ""
    primary_location = record.get("primary_location") or {}
    landing_url = primary_location.get("landing_page_url")
    if not landing_url:
        host_venue = record.get("host_venue") or {}
        landing_url = host_venue.get("url")
    if not landing_url:
        landing_url = record.get("id", missing_value)

    host_venue = record.get("host_venue") or {}
    notes = ["data_source=openalex"]

    return {
        "\u7f16\u53f7": index,
        "\u5f15\u7528\u8bba\u6587\u9898\u76ee": record.get("display_name") or missing_value,
        "\u5168\u4f53\u4f5c\u8005": "; ".join(authors) if authors else missing_value,
        "\u4f5c\u8005-\u5355\u4f4d\u6620\u5c04": " | ".join(author_entries) if author_entries else missing_value,
        "\u4f5c\u8005\u5355\u4f4d\uff08\u6c47\u603b\uff09": aggregated_unique,
        "\u53d1\u8868\u5e74\u4efd": record.get("publication_year") or missing_value,
        "\u6765\u6e90\u94fe\u63a5": landing_url or missing_value,
        "DOI": doi.replace("https://doi.org/", "").lower(),
        "\u671f\u520a/\u4f1a\u8bae": host_venue.get("display_name") or missing_value,
        "\u5907\u6ce8": "; ".join(notes),
    }


def build_markdown_summary(df: pd.DataFrame, total_records: int, filtered_records: int) -> str:
    affiliation_column = "\u4f5c\u8005\u5355\u4f4d\uff08\u6c47\u603b\uff09"
    if df.empty:
        lines = [
            "# \u5f15\u6587\u7edf\u8ba1\u6458\u8981",
            "",
            f"- OpenAlex \u8fd4\u56de\u5f15\u7528\u8bb0\u5f55\u603b\u6570\uff1a{total_records}",
            "- \u8fc7\u6ee4\u540e\u6709\u6548\u8bb0\u5f55\uff1a0",
            "",
            "\u7531\u4e8e\u672a\u83b7\u53d6\u5230\u6709\u6548\u5f15\u7528\u6570\u636e\uff0c\u62a5\u544a\u4e2d\u4e0d\u5305\u542b\u8fdb\u4e00\u6b65\u7edf\u8ba1\u3002",
        ]
        return "\n".join(lines)

    valid_affs = (
        df[affiliation_column]
        .loc[df[affiliation_column] != "信息缺失"]
        .str.split("; ")
        .explode()
        .str.strip()
        .replace("", pd.NA)
        .dropna()
    )

    total_unique_affs = valid_affs.nunique()
    top_affiliations = valid_affs.value_counts().head(10)
    missing_affiliation_count = (df[affiliation_column] == "信息缺失").sum()

    lines = [
        "# \u5f15\u6587\u7edf\u8ba1\u6458\u8981",
        "",
        f"- OpenAlex \u8fd4\u56de\u5f15\u7528\u8bb0\u5f55\u603b\u6570\uff1a{total_records}",
        f"- \u5254\u9664\u4f5c\u8005\u81ea\u5f15\u540e\u7684\u8bb0\u5f55\u6570\uff1a{filtered_records}",
        f"- \u5199\u5165 CSV \u7684\u8bb0\u5f55\u6570\uff1a{len(df)}",
        f"- \u6709\u6548\u4f5c\u8005\u5355\u4f4d\u6570\u91cf\uff1a{int(total_unique_affs) if pd.notna(total_unique_affs) else 0}",
        f"- \u7f3a\u5931\u4f5c\u8005\u5355\u4f4d\u7684\u8bb0\u5f55\u6570\uff1a{int(missing_affiliation_count)}",
        "",
        "## \u4f5c\u8005\u5355\u4f4d Top 10",
        "",
    ]

    if top_affiliations.empty:
        lines.append("\u6682\u65e0\u8db3\u591f\u7684\u5355\u4f4d\u4fe1\u606f\u7528\u4e8e\u7edf\u8ba1\u3002")
    else:
        lines.append("| \u6392\u540d | \u5355\u4f4d | \u9891\u6b21 |")
        lines.append("| --- | --- | --- |")
        for idx, (aff, count) in enumerate(top_affiliations.items(), start=1):
            lines.append(f"| {idx} | {aff} | {count} |")

    lines.extend(
        [
            "",
            "## \u8bf4\u660e",
            "",
            "- \u6570\u636e\u6765\u6e90\uff1aOpenAlex `cites:` \u8fc7\u6ee4\u7ed3\u679c\u3002",
            "- \u7b5b\u9664\u903b\u8f91\uff1a\u82e5\u5f15\u7528\u6587\u7684\u4f5c\u8005\u59d3\u540d\u4e2d\u5305\u542b\u539f\u8bba\u6587\u4f5c\u8005\uff0c\u5219\u89c6\u4e3a\u81ea\u5f15\u5e76\u79fb\u9664\u3002",
            "- \u4f5c\u8005-\u5355\u4f4d\u5173\u7cfb\u5b57\u6bb5\u91c7\u7528 `Name (Aff1; Aff2)` \u4e0e `|` \u7ec4\u5408\uff0c\u4ee5\u4fbf\u4eba\u5de5\u6838\u67e5\u3002",
        ]
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Main orchestration
# --------------------------------------------------------------------------- #


def main(output_json: Path = RAW_JSON_PATH, force_refresh: bool = False) -> None:
    ensure_directories()

    session = requests.Session()
    session.headers.update(HEADERS)

    if not force_refresh:
        cached = load_json(output_json)
        if cached:
            # 尝试直接使用缓存数据
            citing_records = cached
        else:
            target_work = fetch_target_work(session)
            citing_records = fetch_citing_works(session, target_work["id"].split("/")[-1])
    else:
        target_work = fetch_target_work(session)
        citing_records = fetch_citing_works(session, target_work["id"].split("/")[-1])

    output_json.write_text(
        json.dumps(citing_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    filtered_records: List[Dict[str, Any]] = []
    for record in citing_records:
        authors, _ = extract_authors(record)
        if should_exclude_self_citation(authors):
            continue
        filtered_records.append(record)

    rows = [
        record_to_output_row(idx, record)
        for idx, record in enumerate(filtered_records, start=1)
    ]
    df = pd.DataFrame(rows)
    df.to_csv(CSV_OUTPUT_PATH, index=False, encoding="utf-8-sig")

    summary = build_markdown_summary(
        df,
        total_records=len(citing_records),
        filtered_records=len(filtered_records),
    )
    MARKDOWN_OUTPUT_PATH.write_text(summary, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect citations via OpenAlex.")
    parser.add_argument("--force-refresh", action="store_true", help="Ignore缓存重新抓取。")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=RAW_JSON_PATH,
        help="原始引用数据的输出路径。",
    )
    args = parser.parse_args()
    try:
        main(output_json=args.output_json, force_refresh=args.force_refresh)
    except requests.HTTPError as exc:
        sys.stderr.write(f"HTTP 请求失败: {exc}\n")
        sys.exit(1)
    except requests.RequestException as exc:
        sys.stderr.write(f"网络请求异常: {exc}\n")
        sys.exit(1)
