# Google Scholar Citation Tracker

基于 OpenAlex API 的引用采集与统计工具，用于快速整理某篇论文的引用列表、作者单位分布以及详细引用条目信息。本仓库包含采集脚本、报告生成脚本以及配套的工作流文档，可一键生成结构化数据和 HTML 报告。

---

## 🌟 特性速览

- **自动采集**：调用 OpenAlex `cites:` 过滤器，抓取目标论文的所有引用记录。  
- **自引过滤**：内置原作者名单，自动剔除自引条目。  
- **数据持久化**：同时输出原始 JSON、整理后的 CSV，便于复查与二次分析。  
- **报告生成**：
  - `openalex_citation_report.html`：总体统计 + 年度分布 + 机构/作者 Top 10 + 98 篇引用条目。
  - `openalex_authors_report.html`：374 位作者的单位信息与参与文章明细。
- **工作流文档**：`citation_workflow.md` 详细记录标准流程、HTML 模板、备选方案及踩坑经验。

---

## 🗂️ 目录结构

```
.
├── data/
│   ├── citations_raw.json        # OpenAlex API 原始响应
│   └── citations.csv             # 清洗 / 去重 / 自引过滤后的数据
├── reports/
│   ├── openalex_citation_report.html   # 总体统计报告
│   ├── openalex_authors_report.html    # 作者明细报告
│   ├── data_collection_log.md          # 数据采集日志
│   ├── final_summary.md                # 最终说明
│   └── ...（历史脚本与报告）
├── scripts/
│   ├── openalex_citations.py           # 采集与清洗主脚本
│   ├── generate_openalex_report.py     # 生成总体 HTML 报告
│   └── generate_author_report.py       # 生成作者 HTML 报告
├── citation_workflow.md                # 全流程工作流指南（含 HTML 示例）
└── todo.md                             # 项目任务追踪
```

---

## 🚀 快速开始

```powershell
# 1. 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt   # 若无 requirements.txt，可直接 pip install pandas requests beautifulsoup4 lxml

# 3. 拉取引用数据
.\.venv\Scripts\python.exe .\scripts\openalex_citations.py --force-refresh

# 4. 生成报告
.\.venv\Scripts\python.exe .\scripts\generate_openalex_report.py
.\.venv\Scripts\python.exe .\scripts\generate_author_report.py
```

生成的最新报告会保存在 `reports/` 目录，数据文件位于 `data/` 目录。

---

## 📊 核心数据（当前版本）

| 指标                     | 数值 |
| ------------------------ | ---- |
| OpenAlex 返回引用总数    | 162  |
| 剔除自引后的有效记录     | 98   |
| 覆盖作者单位数量         | 67   |
| 涉及独立作者数量         | 374  |
| 报告生成时间             | 2025-10-24 |

详见：  
- `reports/openalex_citation_report.html`  
- `reports/openalex_authors_report.html`

---

## 📚 工作流与扩展

- `citation_workflow.md`：一步步讲解如何采集数据、生成报告及注意事项，并提供 HTML 模板示例。  
- `reports/data_collection_log.md`：记录 Google Scholar 爬虫失败 → OpenAlex 方案成功的过程。  
- 需要替换目标论文时，可修改 `scripts/openalex_citations.py` 中的 `TARGET_DOI` 或使用命令参数扩展。

---

## 🔄 备选方案（简单提及）

| 数据源            | 适用场景                     | 注意事项 |
| ----------------- | ---------------------------- | -------- |
| Google Scholar + Playwright | 需要原版界面或特定字段       | 易触发验证码，法律风险需自行评估 |
| Crossref          | 关注出版方/期刊信息           | 引用覆盖度有限 |
| Semantic Scholar  | 需要引用上下文或 NLP 数据     | 需 API Key，机构字段不完整 |

---

## 🤝 贡献

欢迎提交 Issue / PR，或直接复用脚本到你的项目中。若有改进建议（例如增加 CLI 参数、自动差异对比、定期任务等），也欢迎讨论。

---

## 📄 许可

本仓库未额外声明许可证，默认遵循 GitHub Terms of Service。若你在商业项目中使用，请自行遵守相关 API 使用条款与数据来源协议。
