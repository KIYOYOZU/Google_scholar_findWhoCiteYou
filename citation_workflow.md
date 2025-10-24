# OpenAlex 引用统计工作流指南（含 HTML 报告示范）

> 适用：当你需要对某篇论文的引用情况进行全面统计、输出结构化数据及成套报告时，照此流程执行即可。本文以 “An entropy-stable hybrid scheme for simulations of transcritical real-fluid flows” 为例总结实践经验、标准做法、备选方案与踩坑记录。

---

## 1. 目标与交付物
- **目标**：拿到目标论文的完整引用列表 → 过滤自引 → 输出可复现的数据集与可读性报告。
- **主输出**  
  1. `data/citations_raw.json`（OpenAlex 原始响应）  
  2. `data/citations.csv`（整理后的结构化数据）  
  3. `reports/openalex_citation_report.html`（总体统计报告）  
  4. `reports/openalex_authors_report.html`（作者-文章明细）  
  5. `reports/data_collection_log.md` / `reports/final_summary.md`（日志与总结，可选）

---

## 2. 标准工作流（推荐路径）

### Step 0：目录 & 依赖初始化
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install pandas requests beautifulsoup4 lxml playwright
mkdir scripts data reports
```
> Playwright 用作兜底，主流程依赖 `requests + pandas` 即可。

### Step 1：确定数据主键与来源
1. 优先使用 **OpenAlex**（免费、稳定、字段丰富）。  
2. 使用 DOI 直接命中：`https://api.openalex.org/works/https://doi.org/<target-doi>`  
   - 对本文例子返回 `id = https://openalex.org/W2602295025`。  
3. 如果 DOI 不确定，再 fallback 到 `?search=<title keywords>`。

### Step 2：设计采集脚本 `scripts/openalex_citations.py`

> 脚本结构建议：

| 函数 | 作用 |
| --- | --- |
| `fetch_target_work(session)` | 验证 DOI、获取 OpenAlex Work 信息 |
| `fetch_citing_works(session, work_id)` | `filter=cites:{id}`，带游标循环直到抓完；`per-page=200` |
| `filter_self_citations(records)` | 维护原作者名单（小写、去符号），命中即剔除 |
| `record_to_output_row(index, record)` | 生成 CSV 行（标题、作者、作者-机构映射、年、DOI、链接、备注） |
| `build_markdown_summary(df, total, filtered)` | 输出统计摘要 |

关键实现要点：
- **请求头**：设置 `User-Agent`，并添加邮箱方便被允许。  
- **容错**：捕获 `requests.HTTPError` / `RequestException`，必要时重试；分页时 `time.sleep(0.2~0.5s)`。  
- **结果去重**：用 `record["id"]` 或 `doi` 去重，避免分页重复。  
- **输出编码**：CSV 使用 `utf-8-sig`，JSON 设置 `ensure_ascii=False`。

运行命令：
```powershell
.\.venv\Scripts\python.exe .\scripts\openalex_citations.py --force-refresh
```
执行完成后检查：
```powershell
python - <<'PY'
import pandas as pd
df = pd.read_csv("data/citations.csv", encoding="utf-8-sig")
print(len(df), df.columns.tolist())
PY
```

### Step 3：生成两份 HTML 报告

#### 3.1 总体统计报告 `scripts/generate_openalex_report.py`
1. 读取 `citations.csv` + `citations_raw.json`。  
2. 统计需要呈现的数字：
   - OpenAlex 返回总数 / 过滤后数量  
   - 覆盖机构数、缺失机构数  
   - 年度分布、机构 Top10、作者 Top10  
3. 组织 HTML：参考示例样式（见下文 “HTML 报告格式示范”）。  
4. 输出 `reports/openalex_citation_report.html`。

运行：
```powershell
.\.venv\Scripts\python.exe .\scripts\generate_openalex_report.py
```

#### 3.2 作者明细报告 `scripts/generate_author_report.py`
1. 读取 `citations.csv` 的 `authors` 字段与 `作者-单位映射` 字段。  
2. 将 “姓名 (单位1; 单位2)” 解析为 `dict[作者 -> {单位集}]`。  
3. 汇总每位作者参与的文章（标题、年份），按文章数倒序。  
4. 生成 `reports/openalex_authors_report.html`。

运行：
```powershell
.\.venv\Scripts\python.exe .\scripts\generate_author_report.py
```

### Step 4：记录过程 & 输出总结
- 实时把尝试命令、异常和解决方案写入 `reports/data_collection_log.md`。  
- 任务完成后在 `reports/final_summary.md` 写明：
  - 目标、数据源、过滤逻辑  
  - 核心统计结论  
  - 下一步建议
- 更新项目 `todo.md`，确保所有步骤留痕。

---

## 3. HTML 报告格式示范

以下示例节选自最终脚本，可用于复用或快速起稿：

### 3.1 总体报告核心结构

```html
<!-- 摘要与指标 -->
<div class="summary-box">
  <p>本报告基于 OpenAlex 数据源，对论文 <strong>...</strong> 的引用情况进行了统计。</p>
  <p>引用数据更新日期：2025-10-24 13:03:34。</p>
</div>

<div class="stat-grid">
  <div class="stat-item">
    <div class="stat-label">OpenAlex 返回引用总数</div>
    <div class="stat-value">162</div>
  </div>
  <!-- 其余指标 -->
</div>

<!-- 年度分布 -->
<h2>年度引用分布</h2>
<table>
  <thead>
    <tr><th>年份</th><th>引用篇数</th></tr>
  </thead>
  <tbody>
    <tr><td>2017</td><td>3</td></tr>
    <!-- ... -->
  </tbody>
</table>

<!-- 作者单位 Top 10 -->
<h2>作者单位 Top 10</h2>
<table>
  <thead>
    <tr><th>排名</th><th>单位</th><th>出现次数</th></tr>
  </thead>
  <tbody>
    <tr><td>1</td><td>Georgia Institute of Technology</td><td>9</td></tr>
    <!-- ... -->
  </tbody>
</table>

<!-- 单篇条目示例 -->
<div class="article-item">
  <div class="article-title">1. An efficient lattice Boltzmann method ...</div>
  <div class="article-meta"><strong>作者：</strong> Shaolong Guo; Yongliang Feng; ...</div>
  <div class="article-meta">
    <strong>作者-单位：</strong>
    Shaolong Guo (Laboratoire de Mécanique, Modélisation & Procédés Propres) | ...
  </div>
  <div class="article-meta"><strong>发表年份：</strong> 2020</div>
  <div class="article-meta"><strong>期刊/会议：</strong> 信息缺失</div>
  <div class="article-meta"><strong>DOI：</strong> 10.1016/j.jcp.2020.109570</div>
  <a class="article-link" href="https://doi.org/10.1016/j.jcp.2020.109570" target="_blank">访问原文</a>
</div>
```

### 3.2 作者报告结构

```html
<div class="author-block">
  <h3>1. Jean-Pierre Hickey</h3>
  <p><strong>作者单位：</strong> University of Waterloo; Purdue University West Lafayette</p>
  <table>
    <thead>
      <tr><th>#</th><th>文章题目</th><th>年份</th></tr>
    </thead>
    <tbody>
      <tr><td>1</td><td>Pseudophase change effects in turbulent channel flow ...</td><td>2019</td></tr>
      <tr><td>2</td><td>Direct Numerical Simulation of Wall-Bounded Turbulence ...</td><td>2023</td></tr>
    </tbody>
  </table>
</div>
```

> 样式（CSS）可直接复用 `generate_openalex_report.py` / `generate_author_report.py` 中的内联 `<style>`，或抽成单独 `.css` 文件。

---

## 4. 备选方案（简要）

| 方案 | 使用方式 | 适用场景 | 注意事项 |
| --- | --- | --- | --- |
| **Google Scholar + Playwright** | 模拟浏览器翻页抓取 | 无法使用 OpenAlex；需要原版界面 | 易触发验证码；需手动应对验证；结构易变 |
| **Crossref** | `https://api.crossref.org/works?filter=relation.type:is-referenced-by,relation.object:<DOI>` | 关注出版方、期刊信息 | 覆盖度有限；字段稀疏 |
| **Semantic Scholar** | `/paper/{id}/citations` | 需要科研指标/NLP 数据 | 需 API Key；机构信息缺失较多 |
| **商业数据库（Scopus/Dimensions）** | 官方导出或 API | 企业/高校有订阅时 | 授权/费用限制；注意使用协议 |

---

## 5. 踩坑与经验

1. **Google Scholar 验证码**  
   - 现象：`tmp_2024.html` 仅含 captcha，`div.gs_r` 为 0。  
   - 结果：后续统计报错 `KeyError: '作者单位（汇总）'`。  
   - 处理：检测到 captcha 即退出；改用 OpenAlex。

2. **中文列名编码问题**  
   - 解决：CSV 写入 `encoding="utf-8-sig"`，避免在 Windows 上显示乱码。

3. **作者单位缺失**  
   - OpenAlex 某些记录缺少 `institutions`；统一填“信息缺失”，统计缺失数量。

4. **多数据源对比差异大**  
   - 与 Google Scholar 结果不一致是常态：数据源、过滤、机构定义不同。  
   - 应在报告中明确“数据来源=OpenAlex + 自引过滤规则”。

5. **样式与结构审美**  
   - 若用户已有参考模板（如 `citation_analysis_report.html`），优先对齐布局、颜色、组件命名，减少沟通成本。

---

## 6. 复用与扩展建议

- 将两个生成脚本参数化（`--doi`、`--output-dir`），即可用于其他论文。  
- 编写 `Makefile` 或 `invoke` 脚本，固化常用命令：
  ```makefile
  refresh-data:
  	.\.venv\Scripts\python.exe scripts/openalex_citations.py --force-refresh

  report:
  	.\.venv\Scripts\python.exe scripts/generate_openalex_report.py
  	.\.venv\Scripts\python.exe scripts/generate_author_report.py
  ```
- 纳入 CI：定期调用 `refresh-data` 并比较 `citations.csv` 差异以监控新增引用。  
- 若需导出 PDF，可在 HTML 基础上使用 `weasyprint` 或浏览器打印。

---

**最新更新时间**：2025-10-24  
**整理人**：Codex 任务记录员
