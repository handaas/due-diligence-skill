# 高增长招聘信号尽调

- 用户需求：评估小米科技有限责任公司的经营和招聘变化，检查快速扩张是否伴随风险或融资压力。
- 决策用途：支持成长企业持续经营判断。
- 本轮结果：**本轮检查通过**
- 实际工具调用：18；失败 0
- 章节覆盖率：69%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 招聘与经营趋势时间口径清楚
- 融资和风险事实不建立无依据因果
- 主体名称与输入一致
- 结论区分事实和解释

## 本轮自动检查发现


## 使用局限

- 公开招聘可能包含储备岗位
- 融资记录不等于当前现金流

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 due-diligence-skill/scripts/compose_fusion_report.py --enterprise '小米科技有限责任公司' --keyword-type name --output due-diligence-skill/output/05-growth-hiring/report.json --report-output due-diligence-skill/output/05-growth-hiring/report.html
```

## 逐场景业务复核

当前冻结产物逐项满足场景契约；结论仅限本轮公开数据和报告口径。

- **pass** 招聘与经营趋势时间口径清楚：招聘使用“当前/近三月”上游窗口并披露无精确起止日期；经营仅列当前规模及趋势命中数，没有伪造统一年度序列。 当前第六轮result.started_at=2026-10-26T18:54:39+08:00，invocation_id=1793012079932129000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=14；subject.enterprise=小米科技有限责任公司，resolved=True；metrics[上游风险评分=100；对外投资=53；专利储备=9436；在招岗位=3726；注册资本=人民币 14.77亿；股东数量=2；成立年限=16 年；开庭公告=10195；融资轮次=7；上榜记录=9]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_trend=data；recruitment:recruitment_employer_profile=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(9/9)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/53)；enterprise:enterprise_get_enterprise_main_person_info=data(5/5)；risk:risk_insight_litigation_risk_profile=data；risk:enterprise_risk_insight_score=data；risk:risk_insight_court_hearings=data(20/10195)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_chattel_mortgage=empty；risk:risk_insight_consumption_restrictions=empty]
- **pass** 融资和风险事实不建立无依据因果：洞察将融资7、经营规模与专利列为并存事实；扩张线索与开庭10193并列后仅触发核验，不声称融资导致风险。 当前第六轮result.started_at=2026-10-26T18:54:39+08:00，invocation_id=1793012079932129000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=14；subject.enterprise=小米科技有限责任公司，resolved=True；metrics[上游风险评分=100；对外投资=53；专利储备=9436；在招岗位=3726；注册资本=人民币 14.77亿；股东数量=2；成立年限=16 年；开庭公告=10195；融资轮次=7；上榜记录=9]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_trend=data；recruitment:recruitment_employer_profile=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(9/9)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/53)；enterprise:enterprise_get_enterprise_main_person_info=data(5/5)；risk:risk_insight_litigation_risk_profile=data；risk:enterprise_risk_insight_score=data；risk:risk_insight_court_hearings=data(20/10195)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_chattel_mortgage=empty；risk:risk_insight_consumption_restrictions=empty]
- **pass** 主体名称与输入一致：subject.enterprise与match_raw均为小米科技有限责任公司，工商统一社会信用代码为91110108551385082Q。 当前第六轮result.started_at=2026-10-26T18:54:39+08:00，invocation_id=1793012079932129000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=14；subject.enterprise=小米科技有限责任公司，resolved=True；metrics[上游风险评分=100；对外投资=53；专利储备=9436；在招岗位=3726；注册资本=人民币 14.77亿；股东数量=2；成立年限=16 年；开庭公告=10195；融资轮次=7；上榜记录=9]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_trend=data；recruitment:recruitment_employer_profile=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(9/9)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/53)；enterprise:enterprise_get_enterprise_main_person_info=data(5/5)；risk:risk_insight_litigation_risk_profile=data；risk:enterprise_risk_insight_score=data；risk:risk_insight_court_hearings=data(20/10195)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_chattel_mortgage=empty；risk:risk_insight_consumption_restrictions=empty]
- **pass** 结论区分事实和解释：洞察分别使用evidence与interpretation；专利、融资、经营仅为事实，解释明确不能判定研发强弱或稳健扩张。 当前第六轮result.started_at=2026-10-26T18:54:39+08:00，invocation_id=1793012079932129000；calls=18；JSON/HTML/MD、calls.json与result.json已逐文件核读。；本轮当前产物：technical=passed，successful_data_calls=14；subject.enterprise=小米科技有限责任公司，resolved=True；metrics[上游风险评分=100；对外投资=53；专利储备=9436；在招岗位=3726；注册资本=人民币 14.77亿；股东数量=2；成立年限=16 年；开庭公告=10195；融资轮次=7；上榜记录=9]；quality={'total_sections': 13, 'populated_sections': 9, 'empty_sections': 4, 'coverage_pct': 69, 'data_sources': 5, 'cross_insights': 4}；非空章节=['工商基础信息', '股东出资结构', '对外投资清单（关联方敞口）', '诉讼风险结构', '风险维度统计', '开庭公告明细', '经营规模与资本运作', '专利公开统计', '招聘公开统计']；代表记录=5；calls[patent:patent_bigdata_patent_stats=data；recruitment:recruitment_trend=data；recruitment:recruitment_employer_profile=data；operation:operation_insight_business_scale=data；operation:operation_insight_financing_info=data；operation:operation_insight_company_trends=data；operation:operation_insight_enterprise_rankings=data(9/9)；enterprise:enterprise_get_enterprise_base_info=data；enterprise:enterprise_get_enterprise_holder_info=data；enterprise:enterprise_get_enterprise_invest_info=data(50/53)；enterprise:enterprise_get_enterprise_main_person_info=data(5/5)；risk:risk_insight_litigation_risk_profile=data；risk:enterprise_risk_insight_score=data；risk:risk_insight_court_hearings=data(20/10195)；risk:risk_insight_penalties=empty；risk:risk_insight_business_anomalies=empty；risk:risk_insight_chattel_mortgage=empty；risk:risk_insight_consumption_restrictions=empty]

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)