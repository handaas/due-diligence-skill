---
name: due-diligence-report
description: Use for generating a 企业尽调评估报告 (尽调报告, 尽职调查, 投资评估, 并购评估, 合作前评估, 风险评估). Directly connects to 5 MCP servers (enterprise / risk / operation / patent / recruitment), pulls raw data, and runs cross-domain analysis — affiliated-party risk contagion, capital-adequacy × credit risk, innovation-operation fit, litigation structure — producing a scored verdict report. Trigger when users ask for "尽调报告", "尽职调查", "投资评估", "并购评估", "合作前评估", "风险评估", "尽调". Infer the enterprise name, connect MCPs, cross-analyze, and produce a radar + gauge + verdict report.
---

# 企业尽调评估报告

## 定位

投资 / 并购 / 合作前的风险评估 skill。**直接连接 5 个 MCP server**（工商 / 风险 / 经营 / 创新 / 招聘），获取多源原始数据，运行**跨维度交叉分析**——产出单维度原子 skill 无法生成的关联洞察、专项评分矩阵与结构化尽调结论。

## 与原子 skill 的区别

原子 skill（enterprise-report / enterprise-risk-report 等）各自只连一个 MCP、产出单维度报告。本 skill 直连 5 个 MCP 拿原始数据，做交叉分析：

- **关联方风险传染** — 股东 / 对外投资广度 × 诉讼 / 被执行风险
- **资本充实性 × 信用风险** — 实缴率 × 信用风险等级
- **创新经营匹配度** — 专利储备 × 经营规模 × 融资 → 企业类型判定
- **扩张张力 × 风险** — 招聘 / 融资 / 异地中标扩张信号 × 诉讼 / 合规趋势
- **诉讼结构** — 原被告身份 / 执行风险研判

## 用户契约

1. 不要向用户索要 product_id、MCP 工具名、内部参数；只接受企业名称 / 统一信用代码 / 注册号。
2. 接受自然目标，自动补全企业全称、直连多 MCP、交叉分析。
3. 默认直连多 MCP；`--dry-run` 读缓存报告做交叉分析骨架；`--reports-dir` 走旧融合引擎。
4. 同时产出 HTML（雷达图 + 评分仪表盘 + 尽调结论 + 交叉明细）、Markdown、JSON。
5. 绝不打印密钥 / 签名 / token；默认 dry-run，真实查询需 MCP 配置完整。
6. 数据不足的维度如实标注，不臆造；尽调结论全部基于数据交叉验证。

## 直连的 5 个 MCP

| MCP server | 工具 | 数据用途 |
| --- | --- | --- |
| enterprise-mcp-server | base_info / holders / invest / main_person | 工商基础、股权、关联方 |
| enterprise-risk-mcp-server | score / litigation / hearings / penalties / anomalies / restrictions / mortgage | 风险全景、诉讼结构 |
| enterprise-operation-mcp-server | business_scale / financing / trends / rankings | 经营规模、资本运作、扩张信号 |
| patent-mcp-server | patent_stats | 创新储备 |
| recruitment-mcp-server | trend / employer_profile | 招聘活跃度 |

## 交叉分析产出

| 产出 | 说明 |
| --- | --- |
| 尽调专项评分 | 资本充实性 / 风险隔离度 / 合规健康度 / 经营稳健性（0-100） |
| 尽调结论 | 建议通过 / 附条件通过 / 需深入调查 / 不建议合作 + 阻断项 + 关注点 |
| 跨维度洞察 | 5 类交叉分析（关联方风险 / 资本信用 / 创新匹配 / 扩张张力 / 诉讼结构） |
| 明细章节 | 工商基础 / 股东出资 / 对外投资 / 风险评分 / 诉讼结构 / 风险维度 / 经营 / 创新 / 招聘 |

## Golden path

1. 解析企业关键词 → 模糊补全全称（enterprise MCP fuzzy search）。
2. 直连 5 个 MCP，并发调用 ~20 个工具，获取多源原始数据。
3. 归一化为统一结构，运行跨维度交叉分析。
4. 计算专项评分矩阵 + 尽调结论 + 关联洞察。
5. 渲染雷达图 + 评分仪表盘 + 交叉明细表 + 结论。
6. 返回 JSON / HTML / MD 路径。

## 脚本速查

```bash
# 默认：直连多 MCP 交叉分析（需 MCP 连接配置）
python scripts/compose_fusion_report.py \
  --enterprise "广州探迹科技有限公司" \
  --output output/尽调.json \
  --report-output output/尽调.html

# dry-run：读缓存报告做交叉分析（不调真实 MCP）
python scripts/compose_fusion_report.py \
  --enterprise "广州探迹科技有限公司" \
  --dry-run \
  --output output/尽调.json \
  --report-output output/尽调.html

# 旧模式：聚合已有原子报告（fusion_engine）
python scripts/compose_fusion_report.py \
  --enterprise "广州探迹科技有限公司" \
  --reports-dir ../../reports_探迹 \
  --output output/尽调.json \
  --report-output output/尽调.html
```

## 输出字段

- `verdict` — 尽调结论（recommendation / level / blockers / key_concerns / summary）。
- `specialty_scores` — 4 项专项评分（资本充实性 / 风险隔离度 / 合规健康度 / 经营稳健性）+ 均值。
- `metrics` — 指标卡（综合风险 / 对外投资 / 尽调综合评分 / 专利 / 招聘 / 注册资本 + 各专项评分）。
- `insights` — 5 类跨维度交叉洞察。
- `core_analysis.sections` — 10 个明细章节（含雷达图 + 2 个 gauge + 交叉明细表）。
- `data_source` — 连接模式（live_mcp / cached_reports）+ 质量报告。

## MCP 连接

- Remote MCP：设置 `<DOMAIN>_MCP_URL`（如 `ENTERPRISE_MCP_URL`）或统一 `HANDAAS_MCP_URL`。
- 本地 stdio：设置 `HANDAAS_MCP_SERVER_ROOT` 指向 `handaas-mcp-server` 根目录；凭证由各 server 自己的 `.env` / 统一 `.env`（经 `assets/mcp_server_wrapper.py` 注入）提供。


- MCP 返回的嵌套 JSON 字符串（如金额 `{"coinType":"人民币","value":430000000.0}`、地址 `{"city":"杭州市",...}`）必须解析为可读文本（如"4.30 亿 人民币"、"浙江省杭州市"），绝不在报告正文、表格或指标中输出原始 JSON 字符串。
- 报告所有章节标题、指标卡标签必须用中文；`core_analysis.sections` 的 `title` 字段必须中文，不可显示英文 key（如 `holders`、`investments`）。
- 指标值必须可读化：金额格式为"X 亿/万 + 币种"，地址拼接省市区，比率显示百分号。详见 `references/report-output.md` 的「数据格式约束」。

## 按需加载 references

- 报告结构规范：`references/report-output.md`。
- 证据评分模型：`references/evidence-scoring.md`。
- 维度矩阵：`references/dimension-matrix.md`。
