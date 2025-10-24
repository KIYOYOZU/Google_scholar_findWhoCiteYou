"""
Collect citation metadata for the paper
"An entropy-stable hybrid scheme for simulations of transcritical real-fluid flows".

The script performs the following steps:
1. Scrape the Google Scholar citations page using Playwright.
2. Filter out self-citations from the original authors.
3. Enrich each record with affiliation information via the Crossref REST API.
4. Persist results to CSV and Markdown summary files.

The scraping logic intentionally uses Playwright to mimic a real browser in order
to avoid triggering aggressive bot protection on Google Scholar.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import random
import re
import time
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from playwright.async_api import ElementHandle, Page, async_playwright

# Constants --------------------------------------------------------------------

BASE_CITATION_URL = (
    "https://scholar.google.com/scholar"
    "?oi=bibs&hl=zh-CN&cites=4750462768145396511&as_sdt=5"
)
RESULTS_PER_PAGE = 10

ORIGINAL_AUTHORS = {
    "peter c ma",
    "pc ma",
    "p c ma",
    "yu lv",
    "y lv",
    "matthias ihme",
    "m ihme",
}

DATA_DIR = Path("data")
REPORTS_DIR = Path("reports")
RAW_SCHOLAR_JSON = DATA_DIR / "citations_raw.json"
CROSSREF_CACHE_PATH = DATA_DIR / "crossref_cache.json"
CSV_OUTPUT_PATH = DATA_DIR / "citations.csv"
MARKDOWN_OUTPUT_PATH = REPORTS_DIR / "citations_summary.md"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUESTS_AGENT = (
    "CitationCollector/0.1 (+https://example.org; mailto:codex-agent@example.com)"
)


# Data structures --------------------------------------------------------------


@dataclass
class ScholarRecord:
    title: str
    url: Optional[str]
    authors_raw: str
    snippet: str
    raw_meta: str
    year: Optional[int]
    cluster_id: Optional[str]
    page_index: int
    authors_list: List[str] = field(default_factory=list)
    authors_truncated: bool = False


@dataclass
class EnrichedRecord(ScholarRecord):
    first_author: Optional[str] = None
    first_author_affiliations: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    crossref_year: Optional[int] = None
    journal: Optional[str] = None
    crossref_score: Optional[float] = None
    crossref_status: str = "unqueried"
    authors_crossref: List[str] = field(default_factory=list)
    authors_crossref_affiliations: List[List[str]] = field(default_factory=list)
    final_authors: List[str] = field(default_factory=list)
    final_author_affiliations: List[List[str]] = field(default_factory=list)
    author_source: str = "unknown"


# Helper functions -------------------------------------------------------------


def ensure_directories() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)


def load_cached_records() -> List[ScholarRecord]:
    if not RAW_SCHOLAR_JSON.exists():
        return []
    try:
        data = json.loads(RAW_SCHOLAR_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    records: List[ScholarRecord] = []
    for item in data:
        try:
            records.append(ScholarRecord(**item))
        except TypeError:
            # Skip malformed entries
            continue
    return records


def persist_raw_records(records: List[ScholarRecord]) -> None:
    RAW_SCHOLAR_JSON.write_text(
        json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def normalize_author_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    return normalize_whitespace(name)


def parse_authors(authors_raw: str) -> List[str]:
    if not authors_raw:
        return []
    # Only keep the first section before the first dash to avoid journal info
    authors_segment = authors_raw.split("-", 1)[0]
    candidates = [normalize_whitespace(part) for part in authors_segment.split(",")]
    cleaned = [c for c in candidates if c and c not in {"…", "..."}]
    return cleaned


def extract_year(meta: str) -> Optional[int]:
    if not meta:
        return None
    match = re.search(r"(19|20|21)\d{2}", meta)
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            return None
    return None


def sequence_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def normalize_title(title: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", title.lower())
    return normalize_whitespace(cleaned)


def record_key(record: ScholarRecord) -> str:
    if record.cluster_id:
        return f"cluster:{record.cluster_id}"
    return f"title:{normalize_title(record.title)}"


async def get_element_text(handle: ElementHandle, selector: str) -> Optional[str]:
    target = await handle.query_selector(selector)
    if target is None:
        return None
    return await target.inner_text()


async def get_element_href(handle: ElementHandle, selector: str) -> Optional[str]:
    target = await handle.query_selector(selector)
    if target is None:
        return None
    return await target.get_attribute("href")


# Scholar scraping -------------------------------------------------------------


async def fetch_page_entries(page: Page, base_url: str, start: int) -> Tuple[List[ScholarRecord], Optional[int]]:
    target_url = f"{base_url}&start={start}"
    await page.goto(target_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(random.randint(2000, 3500))

    # Extract total results (only available on the first page)
    total_results: Optional[int] = None
    if start == 0:
        try:
            summary_text = await page.text_content("#gs_ab_md")
            if summary_text:
                summary_text = normalize_whitespace(summary_text)
                digits = re.findall(r"\d+", summary_text)
                if digits:
                    numbers = [int(d) for d in digits]
                    total_results = max(numbers) if numbers else None
        except Exception:
            total_results = None

    entry_handles = await page.query_selector_all("div.gs_r.gs_or.gs_scl")
    records: List[ScholarRecord] = []

    for index, handle in enumerate(entry_handles):
        try:
            title = await get_element_text(handle, "h3.gs_rt")
            if not title:
                continue
            title = normalize_whitespace(title)
            url = await get_element_href(handle, "h3.gs_rt a")
            authors_raw = await get_element_text(handle, ".gs_a")
            snippet = await get_element_text(handle, ".gs_rs")
            cluster_id = await handle.get_attribute("data-cid")

            raw_meta = normalize_whitespace(authors_raw or "")
            truncated = False
            if authors_raw:
                raw_lower = authors_raw.lower()
                truncated = any(marker in authors_raw for marker in ["…", "..."]) or ("等" in raw_lower)
            year = extract_year(raw_meta)
            authors_list = parse_authors(authors_raw or "")

            record = ScholarRecord(
                title=title,
                url=url,
                authors_raw=raw_meta,
                snippet=normalize_whitespace(snippet or ""),
                raw_meta=raw_meta,
                year=year,
                cluster_id=cluster_id,
                page_index=start // RESULTS_PER_PAGE,
                authors_list=authors_list,
                authors_truncated=truncated,
            )
            records.append(record)
        except Exception:
            continue

    return records, total_results


async def scrape_years(years: List[Optional[int]]) -> Dict[Optional[int], List[ScholarRecord]]:
    ensure_directories()
    results: Dict[Optional[int], List[ScholarRecord]] = {}

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        await page.wait_for_timeout(random.randint(2000, 4000))

        for year in years:
            base_url = BASE_CITATION_URL
            if year is not None:
                base_url = f"{base_url}&as_ylo={year}&as_yhi={year}"

            collected: List[ScholarRecord] = []
            start = 0
            total_expected: Optional[int] = None

            while True:
                records, total_results = await fetch_page_entries(page, base_url, start)
                if total_expected is None and total_results:
                    total_expected = total_results

                if not records:
                    break

                collected.extend(records)
                start += RESULTS_PER_PAGE

                if total_expected is not None and start >= total_expected:
                    break

                await page.wait_for_timeout(random.randint(4000, 6500))

            results[year] = collected
            await page.wait_for_timeout(random.randint(4500, 7000))

        await browser.close()

    return results


# Crossref enrichment ----------------------------------------------------------


def load_crossref_cache() -> Dict[str, Dict[str, Any]]:
    if CROSSREF_CACHE_PATH.exists():
        try:
            data = json.loads(CROSSREF_CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return {}
    return {}


def save_crossref_cache(cache: Dict[str, Dict[str, Any]]) -> None:
    CROSSREF_CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def query_crossref(title: str, session: requests.Session, cache: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    norm_title = normalize_title(title)
    if norm_title in cache:
        return cache[norm_title]

    params = {
        "query.bibliographic": title,
        "rows": 5,
    }
    headers = {
        "User-Agent": REQUESTS_AGENT,
    }

    try:
        response = session.get("https://api.crossref.org/works", params=params, headers=headers, timeout=30)
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
    except Exception as exc:
        cache[norm_title] = {
            "status": "error",
            "error": str(exc),
        }
        return cache[norm_title]

    best_item: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for item in items:
        title_list = item.get("title") or []
        if not title_list:
            continue
        item_title = title_list[0]
        score = sequence_score(normalize_title(item_title), norm_title)
        if score > best_score:
            best_score = score
            best_item = item

    if best_item is None or best_score < 0.6:
        cache[norm_title] = {
            "status": "no_match",
            "score": best_score,
        }
        return cache[norm_title]

    authors = best_item.get("author", []) or []
    authors_full: List[str] = []
    authors_affiliations: List[List[str]] = []
    first_author = None
    first_affiliations: List[str] = []

    for idx, author in enumerate(authors):
        given = author.get("given", "")
        family = author.get("family", "")
        literal_name = author.get("name", "")
        name_parts = [part for part in [given, family] if part]
        if name_parts:
            name = normalize_whitespace(" ".join(name_parts))
        else:
            name = normalize_whitespace(literal_name)
        if not name:
            name = "信息缺失"
        aff_list = [
            normalize_whitespace(aff.get("name", ""))
            for aff in author.get("affiliation", [])
            if aff.get("name")
        ]
        authors_full.append(name)
        authors_affiliations.append(aff_list)
        if idx == 0:
            first_author = name if name != "信息缺失" else None
            first_affiliations = aff_list

    issued = best_item.get("issued", {}).get("date-parts", [])
    crossref_year = issued[0][0] if issued and issued[0] else None

    result = {
        "status": "ok",
        "score": best_score,
        "doi": best_item.get("DOI"),
        "journal": (best_item.get("container-title") or [None])[0],
        "year": crossref_year,
        "first_author": first_author,
        "first_affiliations": first_affiliations,
        "authors": authors_full,
        "authors_affiliations": authors_affiliations,
    }
    cache[norm_title] = result
    return result


def enrich_records(records: List[ScholarRecord]) -> List[EnrichedRecord]:
    session = requests.Session()
    cache = load_crossref_cache()
    enriched: List[EnrichedRecord] = []

    for idx, record in enumerate(records, start=1):
        info = query_crossref(record.title, session, cache)
        enriched_record = EnrichedRecord(**asdict(record))
        enriched_record.crossref_status = info.get("status", "unknown")
        enriched_record.crossref_score = info.get("score")
        enriched_record.doi = info.get("doi")
        enriched_record.journal = info.get("journal")
        enriched_record.crossref_year = info.get("year")

        crossref_authors = info.get("authors") or []
        crossref_affiliations = info.get("authors_affiliations") or [[] for _ in crossref_authors]
        if crossref_affiliations and len(crossref_affiliations) != len(crossref_authors):
            # Align lengths defensively
            crossref_affiliations = crossref_affiliations[: len(crossref_authors)]
            while len(crossref_affiliations) < len(crossref_authors):
                crossref_affiliations.append([])

        enriched_record.authors_crossref = crossref_authors
        enriched_record.authors_crossref_affiliations = crossref_affiliations

        final_authors: List[str] = []
        final_affiliations: List[List[str]] = []

        if crossref_authors:
            final_authors = crossref_authors
            final_affiliations = crossref_affiliations
            enriched_record.author_source = "crossref"
        elif record.authors_list:
            final_authors = record.authors_list
            final_affiliations = [[] for _ in final_authors]
            enriched_record.author_source = "scholar_truncated" if record.authors_truncated else "scholar"
        else:
            final_authors = []
            final_affiliations = []
            enriched_record.author_source = "unknown"

        enriched_record.final_authors = final_authors
        enriched_record.final_author_affiliations = final_affiliations

        if final_authors:
            enriched_record.first_author = final_authors[0]
            if final_affiliations:
                enriched_record.first_author_affiliations = final_affiliations[0]

        if enriched_record.crossref_year is None:
            enriched_record.crossref_year = record.year

        enriched.append(enriched_record)

        # Respectful delay to avoid hitting Crossref rate limits
        time.sleep(0.8)

    save_crossref_cache(cache)
    return enriched


# Filtering and output ---------------------------------------------------------


def filter_self_citations(records: List[EnrichedRecord]) -> List[EnrichedRecord]:
    filtered: List[EnrichedRecord] = []
    for record in records:
        author_names = record.final_authors or record.authors_list
        normalized = {normalize_author_name(author) for author in author_names if author}
        if normalized.intersection(ORIGINAL_AUTHORS):
            continue
        filtered.append(record)
    return filtered


def format_author_entry(name: str, affiliations: List[str]) -> str:
    clean_name = name or "信息缺失"
    clean_affs = sorted({normalize_whitespace(aff) for aff in affiliations if aff})
    if clean_affs:
        return f"{clean_name} ({'; '.join(clean_affs)})"
    return f"{clean_name} (信息缺失)"


def record_to_output_row(index: int, record: EnrichedRecord) -> Dict[str, Any]:
    author_entries: List[str] = []
    aggregated_affiliations: set[str] = set()

    for name, affs in zip(record.final_authors, record.final_author_affiliations):
        affs_clean = [normalize_whitespace(aff) for aff in affs if aff]
        author_entries.append(format_author_entry(name, affs_clean))
        aggregated_affiliations.update(affs_clean)

    authors_str = "; ".join(record.final_authors) if record.final_authors else "信息缺失"
    author_aff_str = " | ".join(author_entries) if author_entries else "信息缺失"
    affiliation_summary = "; ".join(sorted(aggregated_affiliations)) if aggregated_affiliations else "信息缺失"

    source_link = record.url
    if not source_link and record.cluster_id:
        source_link = f"https://scholar.google.com/scholar?cluster={record.cluster_id}"

    publish_year = record.crossref_year or record.year
    notes = []
    if record.crossref_status != "ok":
        notes.append(f"crossref_status={record.crossref_status}")
    if record.crossref_score is not None:
        notes.append(f"score={record.crossref_score:.2f}")
    if not record.final_authors:
        notes.append("missing_authors")
    if record.author_source != "crossref":
        notes.append(f"author_source={record.author_source}")
    if record.authors_truncated and record.author_source != "crossref":
        notes.append("scholar_authors_may_be_truncated")

    row = {
        "序号": index,
        "引用文献标题": record.title,
        "全部作者": authors_str,
        "作者-单位对应": author_aff_str,
        "作者单位（汇总）": affiliation_summary,
        "发表年份": publish_year or "信息缺失",
        "来源链接": source_link or "信息缺失",
        "DOI": record.doi or "",
        "Crossref期刊": record.journal or "",
        "备注": "; ".join(notes),
    }
    return row


def build_markdown_summary(
    df: pd.DataFrame,
    total_records: int,
    filtered_records: int,
) -> str:
    affiliation_column = "作者单位（汇总）"
    total_unique_affiliations = (
        df[affiliation_column]
        .loc[df[affiliation_column] != "信息缺失"]
        .str.split("; ")
        .explode()
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .nunique()
    )

    top_affiliations = (
        df[affiliation_column]
        .loc[df[affiliation_column] != "信息缺失"]
        .str.split("; ")
        .explode()
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(10)
    )

    missing_affiliation_count = (df[affiliation_column] == "信息缺失").sum()

    lines = [
        "# 引用统计概览",
        "",
        f"- Google Scholar 总引用记录：{total_records}",
        f"- 排除原作者后的引用记录：{filtered_records}",
        f"- 生成数据表条目：{len(df)}",
        f"- 有效作者单位数量：{total_unique_affiliations}",
        f"- 作者单位缺失条目：{missing_affiliation_count}",
        "",
        "## 作者单位 Top 10",
        "",
    ]

    if top_affiliations.empty:
        lines.append("暂无足够的单位信息可供统计。")
    else:
        lines.append("| 序号 | 单位 | 计数 |")
        lines.append("| --- | --- | --- |")
        for idx, (affiliation, count) in enumerate(top_affiliations.items(), start=1):
            lines.append(f"| {idx} | {affiliation} | {count} |")

    lines.extend(
        [
            "",
            "## 数据说明",
            "",
            "- 若 Crossref 未找到匹配条目或缺失机构信息，则以“信息缺失”标注。",
            "- Crossref 匹配置信度以 SequenceMatcher 得到的相似度衡量，详见 CSV 中的备注列。",
            "- “作者-单位对应” 列使用 `|` 分隔各作者，括号内列出其全部可识别的单位；若无单位信息则标记为“信息缺失”。",
        ]
    )

    return "\n".join(lines)


# Main orchestration -----------------------------------------------------------


def main() -> None:
    ensure_directories()
    current_year = datetime.date.today().year
    years = list(range(2016, current_year + 1))
    scrape_targets: List[Optional[int]] = years + [None]

    scraped_by_year = asyncio.run(scrape_years(scrape_targets))

    combined_records: List[ScholarRecord] = []
    seen_keys: set[str] = set()

    def record_key(record: ScholarRecord) -> str:
        if record.cluster_id:
            return f"cluster:{record.cluster_id}"
        return f"title:{normalize_title(record.title)}"

    for year in years:
        yearly_records = scraped_by_year.get(year, [])
        print(f"Fetched {len(yearly_records)} records for {year}")
        for record in yearly_records:
            key = record_key(record)
            if key in seen_keys:
                continue
            combined_records.append(record)
            seen_keys.add(key)

    fallback_records = scraped_by_year.get(None, [])
    print(f"Fetched {len(fallback_records)} records for fallback query")
    for record in fallback_records:
        key = record_key(record)
        if key in seen_keys:
            continue
        combined_records.append(record)
        seen_keys.add(key)

    RAW_SCHOLAR_JSON.write_text(
        json.dumps([asdict(record) for record in combined_records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    enriched_records = enrich_records(combined_records)
    filtered_records = filter_self_citations(enriched_records)

    output_rows = [
        record_to_output_row(idx, record)
        for idx, record in enumerate(filtered_records, start=1)
    ]

    df = pd.DataFrame(output_rows)
    df.to_csv(CSV_OUTPUT_PATH, index=False, encoding="utf-8-sig")

    summary_md = build_markdown_summary(
        df,
        total_records=len(combined_records),
        filtered_records=len(filtered_records),
    )
    MARKDOWN_OUTPUT_PATH.write_text(summary_md, encoding="utf-8")


if __name__ == "__main__":
    main()
