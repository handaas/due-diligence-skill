# 制造企业产研能力尽调

- 用户需求：对比亚迪股份有限公司做制造与研发能力尽调，观察经营规模、专利和招聘趋势是否匹配。
- 决策用途：验证规模扩张与研发人才信号的一致性。
- 本轮结果：**本轮检查通过**
- 实际工具调用：18；失败 0
- 章节覆盖率：69%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 专利统计与经营规模分别有数据依据
- 招聘趋势不被直接等同于产能
- 跨域洞察说明证据链
- 趋势缺年不补零

## 本轮自动检查发现


## 使用局限

- 招聘活跃度不是实际产量证明
- 专利数量不能单独代表技术质量

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 due-diligence-skill/scripts/compose_fusion_report.py --enterprise '比亚迪股份有限公司' --keyword-type name --output due-diligence-skill/output/04-manufacturing-scale/report.json --report-output due-diligence-skill/output/04-manufacturing-scale/report.html
```

## 逐场景业务复核

当前冻结产物逐项满足场景契约；结论仅限本轮公开数据和报告口径。

- **pass** 专利统计与经营规模分别有数据依据：dd_patent独立列专利46035及类型分项；dd_operation独立列人员10000人以上、营业额10亿以上、融资7，相关来源调用均为data。 当前第六轮result.started_at=2026-10-26T18:54:39+08:00，invocation_id=1793012079484009000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=14；subject.enterprise=比亚迪股份有限公司，resolved=True；metrics[上游风险评分=100；对外投资=109；专利储备=46035；在招岗位=126960；注册资本=人民币 91.17亿；股东数量=2；成立年限=31 年；开庭公告=298；融资轮次=7；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_enterprise_rankings=data(10/76)；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/109)；enterprise:enterprise_get_enterprise_main_person_info=data(6/6)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/298)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=empty]
- **pass** 招聘趋势不被直接等同于产能：招聘当前/近三月125052仅作平台公开字段，章节明确不能证明经营动能、扩张结果或履约能力，未直接等同产能。 当前第六轮result.started_at=2026-10-26T18:54:39+08:00，invocation_id=1793012079484009000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=14；subject.enterprise=比亚迪股份有限公司，resolved=True；metrics[上游风险评分=100；对外投资=109；专利储备=46035；在招岗位=126960；注册资本=人民币 91.17亿；股东数量=2；成立年限=31 年；开庭公告=298；融资轮次=7；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_enterprise_rankings=data(10/76)；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/109)；enterprise:enterprise_get_enterprise_main_person_info=data(6/6)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/298)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=empty]
- **pass** 跨域洞察说明证据链：洞察明确列专利46035+融资7+经营规模，以及经营趋势+招聘125052+开庭298，并将并存事实与解释分开。 当前第六轮result.started_at=2026-10-26T18:54:39+08:00，invocation_id=1793012079484009000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=14；subject.enterprise=比亚迪股份有限公司，resolved=True；metrics[上游风险评分=100；对外投资=109；专利储备=46035；在招岗位=126960；注册资本=人民币 91.17亿；股东数量=2；成立年限=31 年；开庭公告=298；融资轮次=7；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_enterprise_rankings=data(10/76)；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/109)；enterprise:enterprise_get_enterprise_main_person_info=data(6/6)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/298)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=empty]
- **pass** 趋势缺年不补零：报告未生成年度趋势序列；招聘仅使用上游“当前/近三月”标签并披露精确观察日期未返回，没有把缺失年份补零。 当前第六轮result.started_at=2026-10-26T18:54:39+08:00，invocation_id=1793012079484009000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=14；subject.enterprise=比亚迪股份有限公司，resolved=True；metrics[上游风险评分=100；对外投资=109；专利储备=46035；在招岗位=126960；注册资本=人民币 91.17亿；股东数量=2；成立年限=31 年；开庭公告=298；融资轮次=7；上榜记录=10]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_employer_profile=data；recruitment:recruitment_trend=data；operation:operation_insight_business_scale=data；operation:operation_insight_enterprise_rankings=data(10/76)；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/109)；enterprise:enterprise_get_enterprise_main_person_info=data(6/6)；risk:enterprise_risk_insight_score=data；risk:risk_insight_litigation_risk_profile=data；risk:risk_insight_court_hearings=data(20/298)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_consumption_restrictions=empty；risk:risk_insight_chattel_mortgage=empty]

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)