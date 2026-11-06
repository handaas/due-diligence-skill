---
name: due-diligence-report
description: Use for generating a 企业尽调评估报告 (尽调报告, 尽职调查, 投资评估, 并购评估, 合作前评估, 风险评估). Directly connects to 5 MCP servers, confirms the subject, and produces an evidence-bound factual report without unvalidated custom scores.
---

# 企业尽调评估报告

## 定位

投资 / 并购 / 合作前的风险事实核查 skill。**直接连接 5 个 MCP server**（工商 / 风险 / 经营 / 创新 / 招聘），确认主体后整理跨域公开事实、司法核验项和数据缺口。

### 执行路径边界

- 默认 direct-mcp 路径仅发布可追溯事实和上游原始评分口径；不发布未经验证的自定义综合分、专项分或由数量直接推导的强弱结论。
- `--reports-dir`、`--skills-dir`、`--no-direct-mcp` 会进入兼容保留的旧 `fusion_engine` 路径。该路径可能包含历史自定义评分，未完成本轮证据门禁验证，**不得用于准入、投资或低风险决策**。
- 两条路径不可混同；本说明中的主体确认、去自定义评分和司法冲突门禁仅保证默认 direct-mcp 最终出口。

## 查询成本与分页纪律（必读）

1. **每次调用、每一页都计费。** 想算总页数/总数不是拉全量的授权；没有明确预算时绝不自动翻到 total。
2. **先规划后调用。** 动手前先明确：报告需要哪些结论、每个结论需要哪些数据维度、要调哪些工具和参数、每接口必要页数、最大调用预算。总数未知时，第一页明细既是数据也是 total 发现，**同一页绝不付第二次费**。
3. **优先统计/画像/聚合接口。** 能由统计口径回答的不用明细接口；只取结论、图表、代表性记录或明确"全量/计数"需求所需的明细。只有用户真要求综合报告才跑全管线，绝不"因为工具存在就全调"。
4. **用 schema 允许且合理的大 pageSize，够了就停。** 在明确预算内取到所需证据/样本即停止；追加调用必须来自"缺结论"，而不是"想填满所有章节"。不得用样本分布冒充全量结论来省调用。
5. **同一任务内复用相同请求。** 相同 tool+参数只调一次（含第一页规划数据，一律复用）；渲染只用已落盘 JSON，不重跑 compose/MCP；不自动重试、不重复取统计/明细、不并行取相同数据。补充查询必须先列出具体缺口并复用已有记录。
6. **total_pages/remaining_pages 是按请求 pageSize 的估算。** 预算内短页但上游仍有剩余记录时继续翻页；只有稳定有效的 total 与实际扫描条数相等才算"完整"。错误、提前空页、重复页、total 漂移/缺失、超量都算"不完整"。预算或样本截停是部分采集，**绝不宣称全量**。禁止无关工具/维度调用。

预算不足以支撑关键结论时：先在报告中说明证据缺口与预计需要的额外页数，再请求扩大授权；不得悄悄降级结论，也不得擅自扩大计费范围。

### 分页实现口径

- `compose_fusion_report.py` 新增 `--max-pages N`（正整数，默认 1 页）；每接口的分页明细页数预算，非法值在任何真实调用前被拒绝。
- 直连模式下，分页明细接口（`risk_insight_court_hearings` 每页 ≤50、`risk_insight_consumption_restrictions` 每页 ≤50、`operation_insight_enterprise_rankings` 每页 ≤10）走统一的 total 驱动采集：第 1 页同时用于分析与上游 total 发现，不重复计费；后续页仅在预算内按 total 规划翻页。
- 报告 `data_source.pagination` 与 `data_source.call_usage` 会披露每接口的上游 total、预计页数、实际请求页数、取得/未纳入条数与停止原因；`abstract`/`summary`/`caliber.limit` 同步可见。
- 模糊查询主体确认（`enterprise_get_keyword_search`）不做分页；统计/画像接口（`risk_insight_litigation_risk_profile`、`risk_insight_penalties`、`risk_insight_business_anomalies`、`risk_insight_chattel_mortgage`、`patent_bigdata_patent_stats`、`operation_insight_financing_info`、`operation_insight_business_scale`、`operation_insight_company_trends`、`recruitment_employer_profile`（趋势与画像同属一个上游统计产品，仅调用一次）等）单次调用不翻页；`enterprise_get_enterprise_invest_info` 与 `enterprise_get_enterprise_main_person_info` 返回 resultList+total 但工具参数不含分页，保持单次调用并在报告中披露 total 与未纳入条数。

## 与原子 skill 的区别

原子 skill（enterprise-report / enterprise-risk-report 等）各自只连一个 MCP、产出单维度报告。本 skill 直连 5 个 MCP 拿原始数据，做交叉分析：

- **关联方风险传染** — 股东 / 对外投资广度 × 诉讼 / 被执行风险
- **资本与风险公开字段** — 并列呈现实缴率与风险记录，不代替财务审计
- **专利与经营公开字段** — 并列呈现专利、规模和融资事实，不判定企业类型或研发强弱
- **招聘 / 融资与司法记录** — 分别呈现活动数量和司法暴露，不评价扩张质量
- **诉讼结构** — 展示原被告、开庭和执行公开字段及其可追溯性缺口

## 用户契约

1. 不要向用户索要 product_id、MCP 工具名、内部参数；只接受企业名称 / 统一信用代码 / 注册号。
2. 接受自然目标，自动补全企业全称、直连多 MCP、交叉分析。
3. 默认直连多 MCP；`--dry-run` 读缓存报告做交叉分析骨架；`--reports-dir` 走旧融合引擎。
4. 同时产出 facts-only HTML、Markdown、JSON；默认路径不生成雷达图或评分仪表盘。
5. 绝不打印密钥 / 签名 / token；默认 dry-run，真实查询需 MCP 配置完整。
6. 数据不足的维度如实标注，不臆造；空明细章节在 HTML/Markdown 及目录中整体跳过。

## 直连的 5 个 MCP

| MCP server | 工具 | 数据用途 |
| --- | --- | --- |
| enterprise-mcp-server | base_info / holders / invest / main_person | 工商基础、股权、关联方 |
| enterprise-risk-mcp-server | score / litigation / hearings / penalties / anomalies / restrictions / mortgage | 风险全景、诉讼结构 |
| enterprise-operation-mcp-server | business_scale / financing / trends / rankings | 经营规模、资本运作、扩张信号 |
| patent-mcp-server | patent_stats | 创新储备 |
| recruitment-mcp-server | employer_profile | 招聘活跃度（趋势+福利画像，同一上游统计产品，单次调用） |

## 交叉分析产出

| 产出 | 说明 |
| --- | --- |
| 事实指标 | 工商、司法、投资、专利、经营和招聘的可追溯公开字段 |
| 尽调边界 | 主体确认状态、人工司法核验项、数据缺口；不生成自定义评级 |
| 跨维度洞察 | 5 类交叉分析（关联方风险 / 资本信用 / 创新匹配 / 扩张张力 / 诉讼结构） |
| 明细章节 | 按实际有效数据动态生成；可能包括工商、股东、投资、司法、经营、专利与招聘，空章节跳过 |

## Golden path

1. 解析企业关键词 → 模糊补全全称（enterprise MCP fuzzy search）。
2. 直连 5 个 MCP，并发调用 ~20 个工具，获取多源原始数据。
3. 归一化为统一结构，运行跨维度交叉分析。
4. 应用主体确认、司法冲突和事实白名单门禁，生成关联洞察。
5. 渲染事实指标、上游原始口径和交叉明细表。
6. 返回 JSON / HTML / MD 路径。

## 内容整理与语义审校（生成前必读）

按“原始值 → 规范标签/分类 → 证据位置”逐项核对，尽调结论必须可回溯到字段：

1. **诉讼类别不得合并。** 法院公告 `caTotal`、立案公告 `caLianTotal`、开庭公告 `caKaitingTotal`、裁判文书 `jdTotal`、被执行人 `enforcementTotal`、失信被执行人 `edTotal`、限制高消费 `limitedTotal` 分别展示；不得把开庭公告改写成“案件/公告总数”，也不得把限高数写成被执行数。
2. **风险评分不猜方向。** 上游 `risk_score` 与 `risk_level` 原样保留并注明接口未说明阈值/方向；存在司法暴露时只写“需人工核验、不作低风险背书”，不得编造“与司法记录冲突”或反推等级。
3. **专利占比先写分母。** “发明申请/授权数量占比”的分母是专利总数，不能据此判断有效专利或研发强度；权属、有效性、质量和同行分母缺失时保留为缺口。
4. **招聘窗口不重复。** 当前在招与近三月招聘同值时只作一个观察并注明窗口不可区分；不得据此评价经营动能或扩张质量。
5. **主体与时间限定。** 主体未同时确认名称和信用代码时，风险、投资、专利、招聘记录不得归属该主体，也不生成尽调评级；跨年度/跨接口数据不直接相加。
6. **冲突并列。** 上游等级、案件计数、明细条数不一致时并列展示并说明“未能对账”，不推断差异原因，不擅自择一。
7. **不新增事实、不删除风险。** 未查询的司法/合规维度保留为缺口；不得把“未查询/无记录”写成“低风险”；不得用展示样本推断全量。
8. **AI 只做整理，不冒充审校。** 不写“已通过 LLM 审校/已验证”；推断与事实分开，推断注明依据字段。

- **渲染前置检查**：执行会产出含图表 HTML / PDF 的报告命令前，先验证 `node --version` 与本 skill 自带 `assets/vendor/echarts.min.js` 存在；内嵌静态 SVG 的生成需要 Node.js（推荐当前 LTS，无需 npm 包），缺失时报告生成明确报错。查看已生成的 HTML 与 Markdown 输出不需要 Node。

## 脚本速查

```bash
# 默认：直连多 MCP 交叉分析（明细接口按默认 1 页预算采集并披露 total）
python scripts/compose_fusion_report.py \
  --enterprise "广州探迹科技有限公司" \
  --output output/尽调.json \
  --report-output output/尽调.html

# 明确扩大明细页数预算（每页计费，先规划结论与维度再定）
python scripts/compose_fusion_report.py \
  --enterprise "广州探迹科技有限公司" \
  --max-pages 3 \
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
- `specialty_scores` — 默认 direct-mcp 路径固定为空，不发布自定义评分。
- `metrics` — 事实指标卡；上游原始风险分仅是数据源原始字段，不是本报告综合评级，且司法暴露时不展示正向等级。
- `insights` — 5 类跨维度交叉洞察。
- `core_analysis.sections` — 按有效数据动态生成的事实明细；不含 gauge，空时 HTML/Markdown 与目录均不输出“核心分析”。
- `data_source` — 连接模式（live_mcp / cached_reports）+ 质量报告。

## MCP 连接

- Remote MCP：设置 `<DOMAIN>_MCP_URL`（如 `ENTERPRISE_MCP_URL`）或统一 `HANDAAS_MCP_URL`。
- 本地 stdio：设置 `HANDAAS_MCP_SERVER_ROOT` 指向 `handaas-mcp-server` 根目录；凭证由各 server 自己的 `.env` / 统一 `.env`（经 `assets/mcp_server_wrapper.py` 注入）提供。


- MCP 返回的嵌套 JSON 字符串（如金额 `{"coinType":"人民币","value":430000000.0}`、地址 `{"city":"杭州市",...}`）必须解析为可读文本（如"4.30 亿 人民币"、"浙江省杭州市"），绝不在报告正文、表格或指标中输出原始 JSON 字符串。
- 报告所有章节标题、指标卡标签必须用中文；`core_analysis.sections` 的 `title` 字段必须中文，不可显示英文 key（如 `holders`、`investments`）。
- 指标值必须可读化：金额格式为"X 亿/万 + 币种"，地址拼接省市区，比率显示百分号。详见 `references/report-output.md` 的「数据格式约束」。

## 按需加载 references

- 报告结构规范：`references/report-output.md`。
- 历史评分参考（仅用于理解 legacy `fusion_engine`，默认 direct-mcp 不发布其分值）：`references/evidence-scoring.md`。
- 维度矩阵：`references/dimension-matrix.md`。

### 付费主体校验与批次

- 主体模糊查询也是付费请求，计入本任务调用次数并进入同一请求复用范围；存在多个候选或无法确认时立即停止其他维度查询，返回候选名称供选择，不能为不确定主体继续购买数据。显式企业标识不额外做名称模糊查询。
- 可分页标讯、开庭、限高和渠道明细采用接口允许的 50 条批次；企业上榜保持 schema 上限 10 条，减少相同采集范围的分页调用。预算仍为每数据源最多页数，不是全报告总调用次数。
- 招聘画像已包含趋势汇总所需字段，只购买一次同主体统计结果，在本地复用，不再另查招聘趋势工具。
