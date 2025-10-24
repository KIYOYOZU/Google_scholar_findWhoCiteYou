from __future__ import annotations

import datetime as dt
import html
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd


DATA_DIR = Path("data")
REPORTS_DIR = Path("reports")
CSV_PATH = DATA_DIR / "citations.csv"
RAW_JSON_PATH = DATA_DIR / "citations_raw.json"
OUTPUT_PATH = REPORTS_DIR / "openalex_citation_report.html"

MISSING_VALUE = "信息缺失"


def _safe(text: object) -> str:
    if text is None:
        return MISSING_VALUE
    if isinstance(text, float) and pd.isna(text):
        return MISSING_VALUE
    value = str(text)
    if not value:
        return MISSING_VALUE
    return html.escape(value)


def load_dataframe() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df.columns = [
        "index",
        "title",
        "authors",
        "author_aff_map",
        "aff_summary",
        "year",
        "source_link",
        "doi",
        "venue",
        "notes",
    ]
    return df


def deduplicate_affiliations(aff_summary: str) -> list[str]:
    if pd.isna(aff_summary) or aff_summary == MISSING_VALUE:
        return []
    return [aff.strip() for aff in aff_summary.split(";") if aff.strip()]


def split_authors(authors: str) -> list[str]:
    if pd.isna(authors) or not authors:
        return []
    return [author.strip() for author in authors.split(";") if author.strip()]


def build_html(
    df: pd.DataFrame,
    raw_count: int,
    filtered_count: int,
    unique_institutions: int,
    missing_affiliations: int,
    top_institutions: list[tuple[str, int]],
    top_authors: list[tuple[str, int]],
    year_distribution: dict[int, int],
    generated_at: dt.datetime,
) -> str:
    stats_grid = f"""
        <div class="stat-grid">
            <div class="stat-item">
                <div class="stat-label">OpenAlex 返回引用总数</div>
                <div class="stat-value">{raw_count}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">过滤后有效记录</div>
                <div class="stat-value">{filtered_count}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">覆盖作者单位数量</div>
                <div class="stat-value">{unique_institutions}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">缺失单位的记录</div>
                <div class="stat-value">{missing_affiliations}</div>
            </div>
        </div>
    """

    year_rows = "\n".join(
        f"<tr><td>{year}</td><td>{count}</td></tr>"
        for year, count in sorted(year_distribution.items())
    )

    top_inst_rows = "\n".join(
        f"<tr><td>{idx}</td><td>{html.escape(name)}</td><td>{count}</td></tr>"
        for idx, (name, count) in enumerate(top_institutions, start=1)
    ) or "<tr><td colspan='3'>暂无机构数据</td></tr>"

    top_author_rows = "\n".join(
        f"<tr><td>{idx}</td><td>{html.escape(name)}</td><td>{count}</td></tr>"
        for idx, (name, count) in enumerate(top_authors, start=1)
    ) or "<tr><td colspan='3'>暂无作者数据</td></tr>"

    article_items = []
    for _, row in df.iterrows():
        link_html = ""
        link_value = row["source_link"]
        if isinstance(link_value, str) and link_value and link_value != MISSING_VALUE:
            link_html = f'<a href="{html.escape(link_value)}" class="article-link" target="_blank">访问原文</a>'
        doi_html = ""
        if isinstance(row["doi"], str) and row["doi"]:
            doi_display = row["doi"]
            if not doi_display.startswith("10"):
                doi_display = row["doi"]
            doi_html = f'<div class="article-meta"><strong>DOI:</strong> {html.escape(doi_display)}</div>'

        article_items.append(
            f"""
            <div class="article-item">
                <div class="article-title">{int(row['index'])}. {html.escape(str(row['title']))}</div>
                <div class="article-meta"><strong>作者：</strong> {html.escape(str(row['authors']))}</div>
                <div class="article-meta"><strong>作者-单位：</strong> {html.escape(str(row['author_aff_map']))}</div>
                <div class="article-meta"><strong>作者单位（汇总）：</strong> {html.escape(str(row['aff_summary']))}</div>
                <div class="article-meta"><strong>发表年份：</strong> {html.escape(str(row['year']))}</div>
                <div class="article-meta"><strong>期刊/会议：</strong> {html.escape(str(row['venue']))}</div>
                {doi_html}
                {link_html}
            </div>
            """
        )

    articles_html = "\n".join(article_items)

    generated_ts = generated_at.strftime("%Y-%m-%d %H:%M:%S")

    html_output = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenAlex Citation Analysis Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}

        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            border-left: 5px solid #3498db;
            padding-left: 15px;
        }}

        h3 {{
            color: #7f8c8d;
            margin-top: 25px;
            margin-bottom: 15px;
        }}

        .summary-box {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}

        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}

        .stat-item {{
            background: white;
            padding: 15px;
            border-left: 4px solid #3498db;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        .stat-label {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}

        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        th {{
            background: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .article-item {{
            background: white;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #3498db;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        .article-title {{
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
            font-size: 1.1em;
        }}

        .article-meta {{
            color: #7f8c8d;
            font-size: 0.95em;
            margin: 4px 0;
        }}

        .article-link {{
            display: inline-block;
            margin-top: 8px;
            color: #3498db;
            text-decoration: none;
            font-weight: 600;
        }}

        .article-link:hover {{
            text-decoration: underline;
        }}

        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #95a5a6;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OpenAlex Citation Analysis Report</h1>

        <div class="summary-box">
            <p>本报告基于 OpenAlex 数据源，对论文 <strong>An entropy-stable hybrid scheme for simulations of transcritical real-fluid flows</strong> 的引用情况进行了统计与整理。引用数据更新日期：{generated_ts}。</p>
            <p>引用条目经过原作者自引过滤，并补充了作者-机构映射、DOI 以及来源链接等信息，便于后续分析与追踪。</p>
        </div>

        {stats_grid}

        <h2>年度引用分布</h2>
        <table>
            <thead>
                <tr><th>年份</th><th>引用篇数</th></tr>
            </thead>
            <tbody>
                {year_rows}
            </tbody>
        </table>

        <h2>作者单位 Top 10</h2>
        <table>
            <thead>
                <tr><th>排名</th><th>单位</th><th>出现次数</th></tr>
            </thead>
            <tbody>
                {top_inst_rows}
            </tbody>
        </table>

        <h2>高频作者 Top 10</h2>
        <table>
            <thead>
                <tr><th>排名</th><th>作者</th><th>出现次数</th></tr>
            </thead>
            <tbody>
                {top_author_rows}
            </tbody>
        </table>

        <h2>引用文献清单（共 {filtered_count} 篇）</h2>
        {articles_html}

        <div class="footer">
            <p>报告生成时间：{generated_ts}</p>
            <p>数据来源：OpenAlex API（访问方式：cites:W2602295025）</p>
        </div>
    </div>
</body>
</html>"""
    return html_output


def main() -> None:
    df = load_dataframe()
    raw_records = json.loads(RAW_JSON_PATH.read_text(encoding="utf-8"))
    raw_count = len(raw_records)

    filtered_count = len(df)

    institution_counter: Counter[str] = Counter()
    for summary in df["aff_summary"]:
        for inst in deduplicate_affiliations(summary):
            institution_counter[inst] += 1

    unique_institutions = len(institution_counter)
    missing_affiliations = int((df["aff_summary"] == MISSING_VALUE).sum())

    top_institutions = institution_counter.most_common(10)

    author_counter: Counter[str] = Counter()
    for author_field in df["authors"]:
        for author in split_authors(author_field):
            author_counter[author] += 1
    top_authors = author_counter.most_common(10)

    year_distribution: dict[int, int] = {}
    for year in df["year"]:
        if pd.isna(year):
            continue
        year_int = int(year)
        year_distribution[year_int] = year_distribution.get(year_int, 0) + 1

    html_content = build_html(
        df=df,
        raw_count=raw_count,
        filtered_count=filtered_count,
        unique_institutions=unique_institutions,
        missing_affiliations=missing_affiliations,
        top_institutions=top_institutions,
        top_authors=top_authors,
        year_distribution=year_distribution,
        generated_at=dt.datetime.now(),
    )

    OUTPUT_PATH.write_text(html_content, encoding="utf-8")


if __name__ == "__main__":
    main()
