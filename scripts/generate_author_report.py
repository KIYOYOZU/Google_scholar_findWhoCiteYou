from __future__ import annotations

import datetime as dt
import html
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd

DATA_DIR = Path("data")
REPORTS_DIR = Path("reports")
CSV_PATH = DATA_DIR / "citations.csv"
OUTPUT_PATH = REPORTS_DIR / "openalex_authors_report.html"

MISSING_VALUE = "信息缺失"


def normalize_text(value: str) -> str:
    if not value:
        return MISSING_VALUE
    return value.strip() or MISSING_VALUE


def parse_author_affiliations(author_aff_map: str) -> Dict[str, Set[str]]:
    """Parse the `作者-单位映射`字段，返回作者到单位集合的映射。"""
    mapping: Dict[str, Set[str]] = defaultdict(set)
    if not isinstance(author_aff_map, str) or not author_aff_map:
        return mapping

    parts = [part.strip() for part in author_aff_map.split("|") if part.strip()]
    for part in parts:
        if "(" in part and ")" in part:
            name_part, _, rest = part.partition("(")
            affiliations_part, _, _ = rest.partition(")")
            name = name_part.strip()
            affiliations = [aff.strip() for aff in affiliations_part.split(";") if aff.strip()]
        else:
            name = part.strip()
            affiliations = []

        if not name:
            continue
        if not affiliations:
            mapping[name].add(MISSING_VALUE)
        else:
            mapping[name].update(affiliations)
    return mapping


def parse_authors_list(authors: str) -> List[str]:
    if not isinstance(authors, str) or not authors:
        return []
    return [author.strip() for author in authors.split(";") if author.strip()]


def build_author_index(df: pd.DataFrame) -> Dict[str, Dict[str, object]]:
    author_data: Dict[str, Dict[str, object]] = {}

    for _, row in df.iterrows():
        authors = parse_authors_list(row["authors"])
        mapping = parse_author_affiliations(row["author_aff_map"])
        title = str(row["title"]).strip()
        year = row["year"]
        year_display = str(year) if pd.notna(year) else MISSING_VALUE

        for author in authors:
            if author not in author_data:
                author_data[author] = {
                    "affiliations": set(),  # type: ignore[arg-type]
                    "articles": [],
                }

            author_entry = author_data[author]
            author_entry["articles"].append((title, year_display))

            affs = mapping.get(author)
            if affs:
                author_entry["affiliations"].update(affs)  # type: ignore[arg-type]

    return author_data


def build_html(author_index: Dict[str, Dict[str, object]]) -> str:
    generated_ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_authors = len(author_index)

    # sort authors by number of articles desc then name
    sorted_authors = sorted(
        author_index.items(),
        key=lambda item: (-len(item[1]["articles"]), item[0].lower()),
    )

    author_sections: List[str] = []
    for idx, (author, data) in enumerate(sorted_authors, start=1):
        affiliations = data["affiliations"]
        articles = data["articles"]

        affiliations_text = (
            "; ".join(sorted(affiliations)) if affiliations else MISSING_VALUE
        )

        articles_rows = "\n".join(
            f"<tr><td>{i}</td><td>{html.escape(title)}</td><td>{html.escape(str(year))}</td></tr>"
            for i, (title, year) in enumerate(articles, start=1)
        )

        section_html = f"""
        <div class="author-block">
            <h3>{idx}. {html.escape(author)}</h3>
            <p><strong>作者单位：</strong>{html.escape(affiliations_text)}</p>
            <table>
                <thead>
                    <tr><th>#</th><th>文章题目</th><th>年份</th></tr>
                </thead>
                <tbody>
                    {articles_rows}
                </tbody>
            </table>
        </div>
        """
        author_sections.append(section_html)

    authors_html = "\n".join(author_sections)

    html_output = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenAlex Citation Authors Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
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
            margin-top: 20px;
            margin-bottom: 15px;
        }}

        h3 {{
            color: #2c3e50;
            margin-top: 20px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}

        th, td {{
            border: 1px solid #ecf0f1;
            padding: 8px 10px;
            text-align: left;
        }}

        th {{
            background: #3498db;
            color: white;
        }}

        tr:nth-child(even) {{
            background: #f8f9fa;
        }}

        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #95a5a6;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OpenAlex 引用作者明细</h1>
        <p>以下列表基于 OpenAlex 数据源统计，共涉及 <strong>{total_authors}</strong> 位作者。每位作者条目包含其关联单位（若有）及参与的引用文章题目与年份。</p>

        {authors_html}

        <div class="footer">
            <p>报告生成时间：{generated_ts}</p>
            <p>数据来源：OpenAlex API（cites:W2602295025）</p>
        </div>
    </div>
</body>
</html>
"""
    return html_output


def main() -> None:
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

    author_index = build_author_index(df)
    html_content = build_html(author_index)
    OUTPUT_PATH.write_text(html_content, encoding="utf-8")


if __name__ == "__main__":
    main()
