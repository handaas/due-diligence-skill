# due-diligence-skill：已验收示例

本目录只展示 **4 个完全通过的真实正向场景**（最低要求4例）。

每例均为真实、非空、非缓存调用；技术检查、独立业务检查和离线浏览器检查全部通过。报告保持原实测字节，不把空数据、报错处理或仅生成页面计作通过。

| 场景 | 真实使用需求 | 报告 |
|---|---|---|
| [投资前综合尽调](01-investment-review/README.md) | 对宁德时代新能源科技股份有限公司做投资前尽调，重点核验股权、经营、风险、知识产权和招聘信号。 | [HTML](01-investment-review/report.html) / [MD](01-investment-review/report.md) / [JSON](01-investment-review/report.json) |
| [制造企业产研能力尽调](04-manufacturing-scale/README.md) | 对比亚迪股份有限公司做制造与研发能力尽调，观察经营规模、专利和招聘趋势是否匹配。 | [HTML](04-manufacturing-scale/report.html) / [MD](04-manufacturing-scale/report.md) / [JSON](04-manufacturing-scale/report.json) |
| [高增长招聘信号尽调](05-growth-hiring/README.md) | 评估小米科技有限责任公司的经营和招聘变化，检查快速扩张是否伴随风险或融资压力。 | [HTML](05-growth-hiring/report.html) / [MD](05-growth-hiring/report.md) / [JSON](05-growth-hiring/report.json) |
| [知识产权导向尽调](06-ip-innovation/README.md) | 对华为技术有限公司开展创新资产尽调，结合专利储备、经营规模和风险记录判断技术资产基础。 | [HTML](06-ip-innovation/report.html) / [MD](06-ip-innovation/report.md) / [JSON](06-ip-innovation/report.json) |

- [逐例验收结果](results.json) · [业务复核](review.json) · [证据摘要](evidence-index.json)
- [完整测试记录](../test-records/live-replaced-20261027/README.md)仅用于审计，不属于可展示示例。
- 当前数据与结论限于原查询时点及公开样本；覆盖率不代表准确率或低风险。
