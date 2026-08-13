#!/usr/bin/env python3
"""Direct multi-MCP composition for the due-diligence report.

Connects to 5 MCP servers (or reads cached reports for dry-run), runs
cross-domain analysis, and assembles a rich report payload that no single
atomic skill can produce — including cross-dimensional insights, a specialty
score matrix, and a structured verdict.

Output payload follows the unified JSON skeleton so render_report.py renders it
unchanged.
"""
from __future__ import annotations

import datetime as dt
import sys
from typing import Any, Dict, List, Mapping, Optional

import mcp_orchestration as orch
import cross_analysis as xa
from cross_analysis import _pick, _i, _base, _risk, _operation, _patent, _recruitment, _holders, _investments

REPORT_TYPE = "due_diligence_direct"
BANNER = "企业尽调评估报告"

# --------------------------------------------------------------------------- #
# Per-domain detail extractors
# --------------------------------------------------------------------------- #
_BASE_FIELDS = [
    ("企业名称", ("企业名称", "name", "名称")),
    ("统一社会信用代码", ("统一社会信用代码", "socialCreditCode", "scCode", "信用代码")),
    ("法定代表人", ("法定代表人", "legalRepresentative", "法人代表")),
    ("企业类型", ("企业类型", "enterpriseType")),
    ("行业", ("行业", "industry", "industryName")),
    ("注册资本", ("注册资本", "regCapital", "regCapitalValue")),
    ("实缴资本", ("实缴资本", "realCapital", "paidInCapital")),
    ("成立日期", ("成立日期", "foundTime", "成立时间")),
    ("经营状态", ("经营状态", "operStatus")),
    ("注册地址", ("注册地址", "address", "addressValue")),
    ("经营范围", ("经营范围", "businessScope")),
]


def _base_kv(data: Mapping[str, Any]) -> Dict[str, str]:
    base = _base(data)
    out: Dict[str, str] = {}
    for label, keys in _BASE_FIELDS:
        v = _pick(base, *keys)
        if v not in (None, "", "-"):
            out[label] = str(v)
    # also surface paid-in rate if present in the cached-report base
    rate = _pick(base, "资本实缴率", "实缴率")
    if rate:
        out["资本实缴率"] = str(rate)
    return out


_RISK_DIMS = [
    ("行政处罚", "penalties"), ("经营异常", "anomalies"), ("限制高消费", "restrictions"),
    ("开庭公告", "court_hearings"), ("动产抵押", "mortgages"), ("严重违法", "serious_violations"),
    ("知识产权出质", "ip_pledge"),
]


def _risk_dim_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    risk = _risk(data)
    rows = []
    for label, key in _RISK_DIMS:
        val = risk.get(key)
        if val:
            # 优先用 MCP total，回退到 list 长度
            total_key = key + "_total"
            count = risk.get(total_key) or len(val) if isinstance(val, list) else 1
            rows.append({"风险维度": label, "记录数": str(count)})
    return rows


def _hearing_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Court hearing detail records."""
    rows = []
    for h in (_risk(data).get("court_hearings") or [])[:20]:
        if not isinstance(h, dict):
            continue
        rows.append({
            "案由": str(_pick(h, "case_reason", "caseReason", "案由") or "-"),
            "法院": str(_pick(h, "publishUnit", "court", "法院") or "-"),
            "公告类型": str(_pick(h, "caseType", "公告类型") or "开庭公告"),
        })
    return rows


def _restriction_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Consumption restriction (限高) detail records."""
    rows = []
    for r in (_risk(data).get("restrictions") or [])[:20]:
        if not isinstance(r, dict):
            continue
        applicant = r.get("efLimitedApplicant")
        if isinstance(applicant, list):
            applicant = "、".join(str(a) for a in applicant)
        rows.append({
            "案号": str(_pick(r, "efCaseNumber", "caseNo", "案号") or "-"),
            "执行法院": str(_pick(r, "efExecutiveCourt", "court", "执行法院") or "-"),
            "申请执行人": str(applicant or _pick(r, "applicant", "申请执行人") or "-"),
            "被限制人": str(_pick(r, "efLimitedPersonName", "被限制人") or "-"),
            "发布日期": str(_pick(r, "efLimitedPersonCasePublishTime", "publishDate", "发布日期") or "-"),
        })
    return rows


def _anomaly_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Business anomaly (经营异常) detail records."""
    rows = []
    for a in (_risk(data).get("anomalies") or [])[:20]:
        if not isinstance(a, dict):
            continue
        rows.append({
            "列入原因": str(_pick(a, "createReason", "reason", "列入原因") or "-"),
            "决定机关": str(_pick(a, "createAuthority", "department", "决定机关") or "-"),
            "列入日期": str(_pick(a, "createDate", "inDate", "列入日期") or "-"),
            "移出日期": str(_pick(a, "removeDate", "outDate", "移出日期") or "未移出"),
            "状态": "已移出" if (_pick(a, "removeDate", "outDate")) else "在列",
        })
    return rows


def _penalty_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Administrative penalty (行政处罚) detail records."""
    rows = []
    for p in (_risk(data).get("penalties") or [])[:20]:
        if not isinstance(p, dict):
            continue
        if p.get("text") and len(p) <= 2:
            continue
        rows.append({
            "处罚类型": str(_pick(p, "punishType", "处罚类型") or "-"),
            "处罚内容": str(_pick(p, "punishContent", "penaltyContent", "处罚内容") or "-"),
            "决定机关": str(_pick(p, "punishAuthority", "department", "决定机关") or "-"),
            "决定日期": str(_pick(p, "punishDecisionDate", "penaltyDate", "决定日期") or "-"),
            "文号": str(_pick(p, "punishId", "penaltyNo", "文号") or "-"),
        })
    return rows


def _mortgage_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Chattel mortgage (动产抵押) detail records."""
    rows = []
    for m in (_risk(data).get("mortgages") or [])[:20]:
        if not isinstance(m, dict):
            continue
        if m.get("text") and len(m) <= 2:
            continue
        rows.append({
            "登记编号": str(_pick(m, "mortgageRegNum", "登记编号") or "-"),
            "抵押权人": str(_pick(m, "mortgagee", "抵押权人") or "-"),
            "金额": str(_pick(m, "pledgeAmount", "金额") or "-"),
            "状态": str(_pick(m, "status", "状态") or "-"),
            "登记日期": str(_pick(m, "regDate", "登记日期") or "-"),
        })
    return rows


def _operation_kv(data: Mapping[str, Any]) -> Dict[str, str]:
    op = _operation(data)
    scale = op.get("scale") or {}
    out: Dict[str, str] = {}
    for label, keys in [("人员规模", ("staff", "人员规模", "enterpriseScale")), ("年营业额", ("turnover", "年营业额", "annualTurnover"))]:
        v = _pick(scale, *keys)
        if v not in (None, "", "-"):
            out[label] = str(v)
    fin_n = _i(op.get("financing_count"))
    if fin_n is not None:
        out["融资轮次"] = str(fin_n)
    rankings = op.get("rankings") or []
    if rankings:
        out["上榜记录"] = str(len(rankings))
    return out


def _patent_kv(data: Mapping[str, Any]) -> Dict[str, str]:
    pat = _patent(data)
    out: Dict[str, str] = {}
    for label, key in [("专利总数", "total"), ("发明申请", "invention_app"), ("发明授权", "invention_lic"), ("实用新型", "utility"), ("外观设计", "design")]:
        v = _i(pat.get(key))
        if v is not None:
            out[label] = str(v)
    return out


def _recruitment_kv(data: Mapping[str, Any]) -> Dict[str, str]:
    rec = _recruitment(data)
    out: Dict[str, str] = {}
    for label, key in [("当前在招", "current"), ("近三月招聘", "last_3m")]:
        v = _i(rec.get(key))
        if v is not None:
            out[label] = str(v)
    sal = rec.get("avg_salary")
    if sal not in (None, "", "-"):
        try:
            out["平均薪酬"] = f"{float(str(sal).replace(',', '')):.0f} 元/月"
        except (TypeError, ValueError):
            out["平均薪酬"] = str(sal)
    welfare = rec.get("welfare") or []
    if welfare:
        out["福利项数"] = str(len(welfare))
    return out


# --------------------------------------------------------------------------- #
# Payload assembly
# --------------------------------------------------------------------------- #
def build_direct_payload(enterprise: str, keyword_type: str, *, dry_run: bool, skills_root: str) -> Dict[str, Any]:
    # 1. Collect multi-source data (live MCP or cached reports)
    data = orch.collect_direct(enterprise, keyword_type, dry_run=dry_run, skills_root=skills_root)
    meta = data.get("_meta") or {}
    resolved = meta.get("resolved") or {}
    canon = resolved.get("enterprise") or enterprise
    errors = meta.get("errors") or {}
    source_mode = "live_mcp" if meta.get("source") == "live" else "cached_reports"

    if errors:
        for k, msg in list(errors.items())[:5]:
            print(f"⚠️  工具调用失败 [{k}]: {msg[:120]}", file=sys.stderr)

    # 2. Cross-domain analysis
    cross = xa.analyze(data)
    verdict = cross["verdict"]
    scores = cross["specialty_scores"]

    # 3. Build core_analysis sections + data
    sections: List[Dict[str, Any]] = []
    core: Dict[str, Any] = {}

    def _add(spec: Dict[str, Any], body: Any) -> None:
        key = spec["key"]
        # radar carries its data in the chart spec (indicators/series), not the body
        if spec.get("kind") == "radar":
            sections.append(spec)
            if body:
                core[key] = body
            return
        if body not in (None, "", [], {}):
            sections.append(spec)
            core[key] = body

    # verdict gauge — paired with radar to avoid whitespace
    if scores.get("average") is not None:
        _add({"key": "dd_verdict_gauge", "title": "尽调综合评分", "kind": "gauge",
              "chart": {"value_key": "尽调综合评分", "level_key": "尽调结论", "max": 100},
              "note": f"尽调结论：{verdict['recommendation']}",
              "pair_with": "dd_radar"},
             {"尽调综合评分": scores["average"], "尽调结论": verdict["level"]})

    # specialty radar — paired with the verdict gauge above
    valid_scores = [(s["label"], s["score"]) for s in scores["items"] if s["score"] is not None]
    if len(valid_scores) >= 3:
        dim_names = " / ".join(l for l, _ in valid_scores)
        _add({"key": "dd_radar", "title": "尽调专项评分雷达", "kind": "radar",
              "chart": {"indicators": [{"name": l, "max": 100} for l, _ in valid_scores],
                        "series": [{"name": "专项评分", "value": [v for _, v in valid_scores]}]},
              "note": f"跨维度交叉评分（{len(valid_scores)} 维）：{dim_names}"},
             {})

    # business base
    base_kv = _base_kv(data)
    _add({"key": "dd_base", "title": "工商基础信息", "kind": "kv", "note": "工商登记 + 简介 + 经营范围"}, base_kv)

    # cross-analysis sections (shareholders, investments, litigation, specialty matrix)
    for spec in cross["section_specs"]:
        _add(spec, cross["section_data"].get(spec["key"]))

    # risk gauge + risk dimension counts — paired to avoid whitespace
    risk_score = _i(_risk(data).get("score"))
    if risk_score is not None:
        _add({"key": "dd_risk_gauge", "title": "综合风险评分", "kind": "gauge",
              "chart": {"value_key": "风险评分", "level_key": "风险等级", "max": 100},
              "note": "风险洞察综合评分（越低越好）",
              "pair_with": "dd_risk_dims"},
             {"风险评分": risk_score, "风险等级": _risk(data).get("level") or "-"})
    risk_rows = _risk_dim_rows(data)
    _add({"key": "dd_risk_dims", "title": "风险维度统计", "kind": "table",
          "note": "各风险维度记录数（尽调合规核查）",
          "columns": [("风险维度", "风险维度"), ("记录数", "记录数")]}, risk_rows)

    # --- 风险案件明细（尽调核心：展开具体案件，而非只给数字）---
    hearing_rows = _hearing_rows(data)
    _add({"key": "dd_hearings", "title": "开庭公告明细", "kind": "table",
          "note": f"共 {len(_risk(data).get('court_hearings') or [])} 条开庭公告（展示前 20 条），案由分布反映诉讼焦点",
          "columns": [("案由", "案由"), ("法院", "法院"), ("公告类型", "公告类型")]}, hearing_rows)

    restriction_rows = _restriction_rows(data)
    _add({"key": "dd_restrictions", "title": "限制高消费明细", "kind": "table",
          "note": "限制高消费是尽调重大风险信号，需核查执行标的与履行情况",
          "columns": [("案号", "案号"), ("执行法院", "执行法院"), ("申请执行人", "申请执行人"), ("被限制人", "被限制人"), ("发布日期", "发布日期")]}, restriction_rows)

    anomaly_rows = _anomaly_rows(data)
    _add({"key": "dd_anomalies", "title": "经营异常明细", "kind": "table",
          "note": "经营异常名录记录（如通过住所无法联系），核查是否已移出",
          "columns": [("列入原因", "列入原因"), ("决定机关", "决定机关"), ("列入日期", "列入日期"), ("移出日期", "移出日期"), ("状态", "状态")]}, anomaly_rows)

    penalty_rows = _penalty_rows(data)
    _add({"key": "dd_penalties", "title": "行政处罚明细", "kind": "table",
          "note": "行政处罚记录，核查违法事实与处罚影响",
          "columns": [("处罚类型", "处罚类型"), ("处罚内容", "处罚内容"), ("决定机关", "决定机关"), ("决定日期", "决定日期"), ("文号", "文号")]}, penalty_rows)

    mortgage_rows = _mortgage_rows(data)
    _add({"key": "dd_mortgages", "title": "动产抵押明细", "kind": "table",
          "note": "动产抵押反映资产质押状况",
          "columns": [("登记编号", "登记编号"), ("抵押权人", "抵押权人"), ("金额", "金额"), ("状态", "状态"), ("登记日期", "登记日期")]}, mortgage_rows)

    # operation
    op_kv = _operation_kv(data)
    _add({"key": "dd_operation", "title": "经营规模与资本运作", "kind": "kv",
          "note": "人员规模 / 营业额 / 融资 / 上榜记录"}, op_kv)

    # patent
    pat_kv = _patent_kv(data)
    _add({"key": "dd_patent", "title": "创新储备", "kind": "kv",
          "note": "专利储备反映技术壁垒与研发深度"}, pat_kv)

    # recruitment
    rec_kv = _recruitment_kv(data)
    _add({"key": "dd_recruitment", "title": "招聘与扩张活跃度", "kind": "kv",
          "note": "招聘活跃度反映企业经营动能"}, rec_kv)

    # 4. Metrics
    metrics: List[Dict[str, Any]] = list(cross["metrics"])

    # 5. Insights (cross-domain first, then can supplement)
    insights: List[Dict[str, Any]] = list(cross["insights"])

    # 6. Representative records (key cross-domain facts for the "Records" section)
    rep_records: List[Dict[str, str]] = []
    invests = _investments(data)
    inv_total = _risk(data).get("investments_total") or len(invests)
    cancelled = [i for i in invests if "注销" in str(_pick(i, "operStatus", "经营状态", "状态") or "")]
    if inv_total:
        rep_records.append({"维度": "对外投资", "关键记录": f"{inv_total} 家关联企业" + (f"（其中 {len(cancelled)} 家已注销）" if cancelled else "")})
    ls = xa._litigation_summary(data)
    if ls["executed"]:
        rep_records.append({"维度": "执行风险", "关键记录": f"被执行记录 {ls['executed']} 条"})
    risk_score = _i(_risk(data).get("score"))
    if risk_score is not None:
        rep_records.append({"维度": "风险评级", "关键记录": f"风险评分 {risk_score}（{_risk(data).get('level') or '-'}）"})
    patent_total = _i(_patent(data).get("total"))
    if patent_total is not None:
        rep_records.append({"维度": "创新储备", "关键记录": f"专利 {patent_total} 件"})
    fin_n = _i(_operation(data).get("financing_count"))
    if fin_n:
        rep_records.append({"维度": "资本运作", "关键记录": f"已完成 {fin_n} 轮融资"})
    hearing_total = _risk(data).get("court_hearings_total")
    if hearing_total:
        rep_records.append({"维度": "诉讼记录", "关键记录": f"开庭公告 {hearing_total} 条"})
    if not rep_records:
        rep_records.append({"维度": "数据状态", "关键记录": "多维数据覆盖，详见各章节"})

    # 7. Abstract & summary — 数据驱动，不重复 verdict.summary
    n_sources = sum(1 for d in (data.get("enterprise"), data.get("risk"), data.get("operation"), data.get("patent"), data.get("recruitment")) if d)
    risk_score = _i(_risk(data).get("score"))
    risk_level = _risk(data).get("level") or "-"
    inv_total = _risk(data).get("investments_total") or len(_investments(data))
    ls = xa._litigation_summary(data)
    hearing_total = _risk(data).get("court_hearings_total") or 0
    restriction_total = _risk(data).get("restrictions_total") or 0
    patent_total = _i(_patent(data).get("total"))
    abstract_parts = [
        f"本报告以「{canon}」为尽调对象，直接聚合工商、风险、经营、创新、招聘 {n_sources} 大数据源，",
    ]
    # 核心数据概览（与正文表格数据一致）
    data_facts = []
    if risk_score is not None:
        data_facts.append(f"风险评分 {risk_score}（{risk_level}）")
    if inv_total:
        data_facts.append(f"对外投资 {inv_total} 家")
    if hearing_total:
        data_facts.append(f"开庭公告 {hearing_total} 条")
    if restriction_total:
        data_facts.append(f"限制高消费 {restriction_total} 条")
    if patent_total is not None:
        data_facts.append(f"专利 {patent_total} 件")
    if data_facts:
        abstract_parts.append(f"核心数据：{'; '.join(data_facts[:5])}。")
    # 尽调结论
    if scores.get("average") is not None:
        abstract_parts.append(f"尽调综合评分 {scores['average']}，结论：{verdict['recommendation']}。")
    if verdict["blockers"]:
        abstract_parts.append(f"阻断项：{'、'.join(verdict['blockers'])}。")
    if verdict["key_concerns"]:
        abstract_parts.append(f"关注点：{'、'.join(verdict['key_concerns'][:3])}。")
    abstract = "".join(abstract_parts)

    # 7b. LLM-powered narrative (abstract + insights) — falls back to template
    try:
        import llm_analysis as llm
        llm_abstract = llm.generate_abstract(data, canon, verdict, scores)
        if llm_abstract:
            abstract = llm_abstract
        insights = llm.refine_insights(insights, data, verdict)
    except Exception as exc:
        print(f"⚠️  LLM 分析跳过（使用模板文案）: {exc}", file=sys.stderr)

    # quality report
    populated = sum(1 for s in sections if core.get(s["key"]) not in (None, "", [], {}))
    quality = {
        "total_sections": len(sections),
        "populated_sections": populated,
        "empty_sections": len(sections) - populated,
        "coverage_pct": round(populated / max(1, len(sections)) * 100),
        "data_sources": n_sources,
        "cross_insights": len(insights),
    }

    return {
        "report_type": REPORT_TYPE,
        "title": f"{canon} 尽调评估报告",
        "banner": BANNER,
        "subject": {"enterprise": canon, "match_raw": enterprise, "resolved": resolved.get("resolved", False),
                    "resolve_reason": resolved.get("reason", "")},
        "abstract": abstract,
        "summary": abstract,
        "executive_summary": [verdict["summary"]] + [i["interpretation"] for i in insights[:4]],
        "verdict": verdict,
        "specialty_scores": scores,
        "metrics": metrics,
        "caliber": {
            "match_target": canon,
            "match_type": f"企业尽调评估（直接聚合 5 个 MCP：工商/风险/经营/创新/招聘）",
            "data_scope": f"覆盖 {n_sources}/5 大数据源，{len(sections)} 个明细章节，{len(insights)} 条跨维度洞察",
            "products": ["企业大数据", "企业风险洞察", "企业经营分析", "专利大数据", "招聘大数据"],
            "limit": "尽调结论基于多维公开数据交叉分析；建议结合财务审计与实地尽调综合决策。",
        },
        "core_analysis": {**core, "sections": sections},
        "representative_records": rep_records,
        "insights": insights,
        "data_source": {
            "mcp_server": "5 MCP（工商/风险/经营/创新/招聘）",
            "mcp_servers": ["enterprise-mcp-server", "enterprise-risk-mcp-server", "enterprise-operation-mcp-server",
                            "patent-mcp-server", "recruitment-mcp-server"],
            "mode": source_mode,
            "dry_run": dry_run,
            "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "quality_report": quality,
            "tool_errors": list(errors.keys()) if errors else [],
        },
    }
