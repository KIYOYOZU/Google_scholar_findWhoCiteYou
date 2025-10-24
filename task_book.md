# 项目任务书

## 项目背景
针对 Peter C Ma 等人在 2021 年发表的论文 “An entropy-stable hybrid scheme for simulations of transcritical real-fluid flows”，需要统计除原作者（Peter C Ma、Yu Lv、Matthias Ihme）之外引用该论文的作者及其所在单位，用于后续研究合作分析。

## 项目目标
1. 从 Google Scholar 引用页面获取全部 221 篇引用记录。
2. 抽取每篇引用文献的第一作者及其单位（若有多个单位需全部保留）。
3. 汇总形成结构化数据表（CSV + Markdown），包含字段：序号、引用文献标题、第一作者、作者单位、发表年份、来源链接。
4. 输出统计概览（引用数量、单位覆盖情况等）。

## 约束与注意事项
- 必须排除原论文三位作者的自引。
- Google Scholar 结果存在分页与动态加载，需使用可编程方式（如 Playwright、Requests + 适当头部）稳定抓取。
- 尊重网站使用条款，控制抓取频率，避免过高并发。
- 对缺失单位信息的记录需标注 “信息缺失”，并在总结中说明处理策略。

## 数据来源与工具
- 数据来源：Google Scholar 引用页面（https://scholar.google.com/scholar?oi=bibs&hl=zh-CN&cites=4750462768145396511&as_sdt=5）。
- 解析工具：Python 3.11、Playwright（优先）、BeautifulSoup / pandas 视情况使用。
- 记录与输出：CSV 文件、Markdown 报告。

## 交付成果
1. `data/citations.csv`
2. `reports/citations_summary.md`
3. 终端输出的关键统计结果摘要。

## 工作分解结构 (WBS)
1. 环境准备：创建虚拟环境，安装 Playwright 与所需依赖。
2. 抓取实现：编写脚本分页抓取引用数据。
3. 数据清洗：解析作者、单位信息，过滤原作者。
4. 数据汇总：生成 CSV 和 Markdown 报告。
5. 验证与交付：抽样核对记录准确性，整理最终输出。

## 时间计划（估算）
- T0 + 0.5h：环境配置与测试。
- T0 + 2h：完成抓取与调试。
- T0 + 1h：数据清洗与导出。
- T0 + 0.5h：验证与总结。

## 风险与应对
- 访问受限：准备备用抓取策略（代理 / 调整间隔）。
- 数据缺失：记录缺失条目并在总结中说明。
- 页面结构变化：脚本中增加容错与选择器校验。
