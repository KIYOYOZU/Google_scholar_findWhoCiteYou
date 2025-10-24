# Project File Index

> 仓库：`Google_scholar_findWhoCiteYou`  
> 更新日期：2025-10-24  
> 说明：列出项目关键目录与文件，帮助快速定位脚本、数据与文档。虚拟环境 `.venv/` 体积较大，仅在“本地环境”小节简要说明。

---

## 1. 顶层目录概览

| 路径 | 描述 |
| --- | --- |
| `.claude/` | 旧版 Claude 代理配置与提示词（未在当前流程中使用，可忽略）。 |
| `.venv/` | Python 3.13 本地虚拟环境，包含运行依赖。 |
| `data/` | 所有采集与清洗后的结构化数据（JSON / CSV）。 |
| `reports/` | 统计报告、日志与说明文档。 |
| `scripts/` | Python 脚本：采集、统计与报告生成。 |
| `AGENT.md` | 早期代理说明（历史文件）。 |
| `README.md` | 项目介绍、快速开始、指标概览。 |
| `FILE_INDEX.md` | 本文件，项目索引。 |
| `citation_workflow.md` | 工作流指南与 HTML 模板示例。 |
| `html_to_pdf_conversion_report.md` | 历史 HTML→PDF 转换报告。 |
| `task_book.md` | 任务说明/需求记录。 |
| `todo.md` | 已完成与待办事项追踪。 |

---

## 2. `scripts/` 目录

| 文件 | 说明 |
| --- | --- |
| `openalex_citations.py` | 主采集脚本。通过 OpenAlex API 拉取引用、过滤自引并生成 JSON/CSV/Markdown。 |
| `generate_openalex_report.py` | 读取 `data/citations.csv`，输出总体统计 HTML 报告。 |
| `generate_author_report.py` | 解析作者-单位映射，生成作者明细 HTML 报告。 |
| `collect_citations.py` | 旧版 Google Scholar + Playwright 采集脚本（易触发验证码，保留作为备选）。 |
| `__pycache__/` | Python 编译缓存，可忽略。 |

---

## 3. `data/` 目录

| 文件 | 说明 |
| --- | --- |
| `citations_raw.json` | OpenAlex 原始响应（162 条引用记录）。 |
| `citations.csv` | 清洗后数据（98 条，剔除自引、结构化字段）。 |
| `crossref_cache.json` | 旧流程缓存的 Crossref 查询结果（历史遗留，仅支持参考）。 |

---

## 4. `reports/` 目录

| 文件/子目录 | 说明 |
| --- | --- |
| `openalex_citation_report.html` | 总体统计报告（指标网格、年度分布、Top10、98 篇引用条目）。 |
| `openalex_authors_report.html` | 作者明细报告（374 位作者，含单位与文章列表）。 |
| `data_collection_log.md` | 数据采集日志：记录 Google Scholar 失败与 OpenAlex 成功流程。 |
| `final_summary.md` | 对外说明/总结文档。 |
| `citation_workflow.md` |（根目录备份）完整工作流指南。 |
| `convert_to_pdf.py` / `convert_to_pdf_v2.py` | 历史 HTML→PDF 转换脚本（当前未使用）。 |
| `html_to_pdf_conversion_report.md` | 配套转换说明。 |

---

## 5. 其他文档

| 文件 | 说明 |
| --- | --- |
| `README.md` | 最新项目 README，覆盖特性、目录结构、使用流程、关键指标。 |
| `task_book.md` | 任务来源/背景描述。 |
| `todo.md` | 项目任务列表（全部勾选）。 |
| `AGENT.md` | 早期多代理协作说明。 |
| `.claude/` 系列 | Claude Prompt/设定（历史遗留，可忽略）。 |

---

## 6. 本地环境说明

- `.venv/` 为本地虚拟环境，包含 `pandas`、`requests`、`playwright` 等依赖。  
- 仓库推送到 GitHub 时建议忽略 `.venv/`（可在 `.gitignore` 中配置），以减小体积并避免平台差异。  
- 若需要复现环境，可按 `README.md` 中的“快速开始”重新创建虚拟环境。

---

若后续新增脚本或报告，请同步更新本索引，保持文档与代码结构一致。*** End Patch```}ġġ
