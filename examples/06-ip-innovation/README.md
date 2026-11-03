# 知识产权导向尽调

- 用户需求：对华为技术有限公司开展创新资产尽调，结合专利储备、经营规模和风险记录判断技术资产基础。
- 决策用途：支持技术合作与知识产权核查。
- 本轮结果：**本轮检查通过**
- 实际工具调用：18；失败 0
- 章节覆盖率：69%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 专利统计含清晰口径
- 创新结论同时考虑专利与经营证据
- 风险数据不足时不输出绝对安全结论
- 企业与专利申请主体差异有局限提示

## 本轮自动检查发现


## 使用局限

- 专利数量不代表权利稳定性
- 需另行开展专利法律状态和权属核验

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 due-diligence-skill/scripts/compose_fusion_report.py --enterprise '华为技术有限公司' --keyword-type name --output due-diligence-skill/output/06-ip-innovation/report.json --report-output due-diligence-skill/output/06-ip-innovation/report.html
```

## 逐场景业务复核

当前冻结产物逐项满足场景契约；结论仅限本轮公开数据和报告口径。

- **pass** 专利统计含清晰口径：专利133237及申请59570、授权66820、实用新型3440、外观设计3407分项清楚；明确未核验申请人归属、有效性、质量、研发投入和同行分母。 当前第六轮result.started_at=2026-10-26T18:54:42+08:00，invocation_id=1793012082069968000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=13；subject.enterprise=华为技术有限公司，resolved=True；metrics[上游风险评分=99；对外投资=54；专利储备=133237；在招岗位=6258；注册资本=人民币 411.41亿；股东数量=1；成立年限=39 年；开庭公告=4401；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=4；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=empty；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(10/18)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_main_person_info=data(32/32)；enterprise:enterprise_get_enterprise_invest_info=data(50/54)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/4401)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=empty]
- **pass** 创新结论同时考虑专利与经营证据：洞察同时引用专利133237、经营规模字段和上榜记录，且只称并存事实，不推断研发强弱或技术竞争力。 当前第六轮result.started_at=2026-10-26T18:54:42+08:00，invocation_id=1793012082069968000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=13；subject.enterprise=华为技术有限公司，resolved=True；metrics[上游风险评分=99；对外投资=54；专利储备=133237；在招岗位=6258；注册资本=人民币 411.41亿；股东数量=1；成立年限=39 年；开庭公告=4401；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=4；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=empty；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(10/18)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_main_person_info=data(32/32)；enterprise:enterprise_get_enterprise_invest_info=data(50/54)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/4401)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=empty]
- **pass** 风险数据不足时不输出绝对安全结论：开庭4401触发人工司法核验和不予评级；上游99分明确与司法记录存在口径冲突，未形成绝对安全或低风险背书。 当前第六轮result.started_at=2026-10-26T18:54:42+08:00，invocation_id=1793012082069968000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=13；subject.enterprise=华为技术有限公司，resolved=True；metrics[上游风险评分=99；对外投资=54；专利储备=133237；在招岗位=6258；注册资本=人民币 411.41亿；股东数量=1；成立年限=39 年；开庭公告=4401；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=4；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=empty；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(10/18)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_main_person_info=data(32/32)；enterprise:enterprise_get_enterprise_invest_info=data(50/54)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/4401)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=empty]
- **pass** 企业与专利申请主体差异有局限提示：caliber与专利章节均要求逐项核验专利申请人/权利人与工商主体的关系。 当前第六轮result.started_at=2026-10-26T18:54:42+08:00，invocation_id=1793012082069968000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=13；subject.enterprise=华为技术有限公司，resolved=True；metrics[上游风险评分=99；对外投资=54；专利储备=133237；在招岗位=6258；注册资本=人民币 411.41亿；股东数量=1；成立年限=39 年；开庭公告=4401；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=4；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=empty；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(10/18)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_main_person_info=data(32/32)；enterprise:enterprise_get_enterprise_invest_info=data(50/54)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/4401)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=empty]

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)