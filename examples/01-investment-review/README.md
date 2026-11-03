# 投资前综合尽调

- 用户需求：对宁德时代新能源科技股份有限公司做投资前尽调，重点核验股权、经营、风险、知识产权和招聘信号。
- 决策用途：为投资立项提供跨域事实底稿。
- 本轮结果：**本轮检查通过**
- 实际工具调用：18；失败 0
- 章节覆盖率：69%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 主体工商信息可追溯
- 风险、经营、专利和招聘维度分别标注数据覆盖
- 跨维度结论引用至少两个独立证据
- 缺失维度不参与肯定性结论

## 本轮自动检查发现


## 使用局限

- 报告不替代法律、财务和现场尽调
- 评分取决于已返回维度的覆盖质量

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 due-diligence-skill/scripts/compose_fusion_report.py --enterprise '宁德时代新能源科技股份有限公司' --keyword-type name --output due-diligence-skill/output/01-investment-review/report.json --report-output due-diligence-skill/output/01-investment-review/report.html
```

## 逐场景业务复核

当前冻结产物逐项满足场景契约；结论仅限本轮公开数据和报告口径。

- **pass** 主体工商信息可追溯：工商基础信息明确企业名称、统一社会信用代码91350900587527783P、法定代表人及注册地址；subject.resolved=true，工商基础调用为data。 当前第六轮result.started_at=2026-10-26T18:54:37+08:00，invocation_id=1793012077387900000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=15；subject.enterprise=宁德时代新能源科技股份有限公司，resolved=True；metrics[上游风险评分=100；对外投资=159；专利储备=26876；在招岗位=8606；注册资本=人民币 45.64亿；股东数量=5；成立年限=15 年；开庭公告=229；融资轮次=22；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(10/34)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/159)；enterprise:enterprise_get_enterprise_main_person_info=data(15/15)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/229)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=data]
- **pass** 风险、经营、专利和招聘维度分别标注数据覆盖：风险列开庭229；经营列规模、融资22及上榜10；专利分型合计26876；招聘列当前/近三月8737并披露窗口无精确日期；quality_report为9/13、覆盖69%、5个数据源。 当前第六轮result.started_at=2026-10-26T18:54:37+08:00，invocation_id=1793012077387900000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=15；subject.enterprise=宁德时代新能源科技股份有限公司，resolved=True；metrics[上游风险评分=100；对外投资=159；专利储备=26876；在招岗位=8606；注册资本=人民币 45.64亿；股东数量=5；成立年限=15 年；开庭公告=229；融资轮次=22；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(10/34)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/159)；enterprise:enterprise_get_enterprise_main_person_info=data(15/15)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/229)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=data]
- **pass** 跨维度结论引用至少两个独立证据：四条洞察分别组合投资159+开庭229、专利26876+融资22+经营规模、趋势13项+招聘8737+开庭229、开庭+限高；投资洞察准确写明总量159家而当前展示15家。 当前第六轮result.started_at=2026-10-26T18:54:37+08:00，invocation_id=1793012077387900000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=15；subject.enterprise=宁德时代新能源科技股份有限公司，resolved=True；metrics[上游风险评分=100；对外投资=159；专利储备=26876；在招岗位=8606；注册资本=人民币 45.64亿；股东数量=5；成立年限=15 年；开庭公告=229；融资轮次=22；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(10/34)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/159)；enterprise:enterprise_get_enterprise_main_person_info=data(15/15)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/229)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=data]
- **pass** 缺失维度不参与肯定性结论：专利和招聘章节明确不推断壁垒、研发强弱或经营动能；开庭229触发不予综合评级，上游100分仅作上游事实并披露与司法门禁冲突。 当前第六轮result.started_at=2026-10-26T18:54:37+08:00，invocation_id=1793012077387900000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=15；subject.enterprise=宁德时代新能源科技股份有限公司，resolved=True；metrics[上游风险评分=100；对外投资=159；专利储备=26876；在招岗位=8606；注册资本=人民币 45.64亿；股东数量=5；成立年限=15 年；开庭公告=229；融资轮次=22；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(10/34)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/159)；enterprise:enterprise_get_enterprise_main_person_info=data(15/15)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/229)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=data]

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)
[页面截图](browser.png)