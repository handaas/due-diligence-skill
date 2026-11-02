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
import json
import sys
from typing import Any, Dict, List, Mapping, Optional

import mcp_orchestration as orch
import cross_analysis as xa
from cross_analysis import (
    _pick,
    _i,
    _base,
    _risk,
    _operation,
    _patent,
    _recruitment,
    _investments,
)

REPORT_TYPE = "due_diligence_direct"
BANNER = "企业尽调评估报告"

# --------------------------------------------------------------------------- #
# Per-domain detail extractors
# --------------------------------------------------------------------------- #
_BASE_FIELDS = [
    ("企业名称", ("企业名称", "name", "名称")),
    (
        "统一社会信用代码",
        ("统一社会信用代码", "socialCreditCode", "scCode", "信用代码"),
    ),
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
    ("行政处罚", "penalties"),
    ("经营异常", "anomalies"),
    ("限制高消费", "restrictions"),
    ("开庭公告", "court_hearings"),
    ("动产抵押", "mortgages"),
    ("严重违法", "serious_violations"),
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
    seen = set()
    for h in _risk(data).get("court_hearings") or []:
        if not isinstance(h, dict):
            continue
        raw_key = json.dumps(h, ensure_ascii=False, sort_keys=True, default=str)
        if raw_key in seen:
            continue
        seen.add(raw_key)
        case_no = _pick(h, "caseNo", "caseNumber", "caCaseNo", "案号")
        hearing_date = _pick(
            h,
            "hearingDate",
            "courtTime",
            "startDate",
            "publishDate",
            "noticeDate",
            "开庭日期",
            "发布日期",
        )
        rows.append(
            {
                "案号": str(case_no or "-"),
                "案由": str(_pick(h, "case_reason", "caseReason", "案由") or "-"),
                "法院": str(_pick(h, "publishUnit", "court", "法院") or "-"),
                "相关主体": str(
                    _pick(
                        h,
                        "enterpriseName",
                        "partyName",
                        "relatedEntity",
                        "当事人",
                        "相关主体",
                    )
                    or "-"
                ),
                "开庭/发布日期": str(hearing_date or "-"),
                "公告类型": str(_pick(h, "caseType", "公告类型") or "开庭公告"),
                "去重键状态": (
                    "案号+日期可用"
                    if case_no and hearing_date
                    else "缺少案号或日期，无法逐案去重"
                ),
            }
        )
        if len(rows) >= 20:
            break
    return rows


def _hearing_note(data: Mapping[str, Any], rows: List[Dict[str, Any]]) -> str:
    reported = _risk(data).get("court_hearings_total")
    raw_records = [
        item
        for item in (_risk(data).get("court_hearings") or [])
        if isinstance(item, dict)
    ]
    unique_raw = {
        json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        for item in raw_records
    }
    reconciliation = ""
    reported_count = _i(reported)
    if reported_count is not None and reported_count != len(unique_raw):
        reconciliation = (
            f"；上游统计 {reported} 条与明细唯一原始记录 {len(unique_raw)} 条不一致，"
            "当前未能对账，不推断差异原因"
        )
    return (
        f"上游统计 {reported if reported is not None else '未知'} 条；当前展示 {len(rows)} 条"
        "完整原始记录去重结果（不等同事件级去重）"
        f"{reconciliation}；缺少案号或日期的记录无法逐案去重"
    )


def _restriction_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Consumption restriction (限高) detail records."""
    rows = []
    for r in (_risk(data).get("restrictions") or [])[:20]:
        if not isinstance(r, dict):
            continue
        applicant = r.get("efLimitedApplicant")
        if isinstance(applicant, list):
            applicant = "、".join(str(a) for a in applicant)
        rows.append(
            {
                "案号": str(_pick(r, "efCaseNumber", "caseNo", "案号") or "-"),
                "执行法院": str(
                    _pick(r, "efExecutiveCourt", "court", "执行法院") or "-"
                ),
                "申请执行人": str(
                    applicant or _pick(r, "applicant", "申请执行人") or "-"
                ),
                "被限制人": str(_pick(r, "efLimitedPersonName", "被限制人") or "-"),
                "发布日期": str(
                    _pick(
                        r, "efLimitedPersonCasePublishTime", "publishDate", "发布日期"
                    )
                    or "-"
                ),
            }
        )
    return rows


def _anomaly_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Business anomaly (经营异常) detail records."""
    rows = []
    for a in (_risk(data).get("anomalies") or [])[:20]:
        if not isinstance(a, dict):
            continue
        rows.append(
            {
                "列入原因": str(_pick(a, "createReason", "reason", "列入原因") or "-"),
                "决定机关": str(
                    _pick(a, "createAuthority", "department", "决定机关") or "-"
                ),
                "列入日期": str(_pick(a, "createDate", "inDate", "列入日期") or "-"),
                "移出日期": str(
                    _pick(a, "removeDate", "outDate", "移出日期") or "未移出"
                ),
                "状态": "已移出" if (_pick(a, "removeDate", "outDate")) else "在列",
            }
        )
    return rows


def _penalty_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Administrative penalty (行政处罚) detail records."""
    rows = []
    for p in (_risk(data).get("penalties") or [])[:20]:
        if not isinstance(p, dict):
            continue
        if p.get("text") and len(p) <= 2:
            continue
        rows.append(
            {
                "处罚类型": str(_pick(p, "punishType", "处罚类型") or "-"),
                "处罚内容": str(
                    _pick(p, "punishContent", "penaltyContent", "处罚内容") or "-"
                ),
                "决定机关": str(
                    _pick(p, "punishAuthority", "department", "决定机关") or "-"
                ),
                "决定日期": str(
                    _pick(p, "punishDecisionDate", "penaltyDate", "决定日期") or "-"
                ),
                "文号": str(_pick(p, "punishId", "penaltyNo", "文号") or "-"),
            }
        )
    return rows


def _mortgage_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Chattel mortgage (动产抵押) detail records."""
    rows = []
    for m in (_risk(data).get("mortgages") or [])[:20]:
        if not isinstance(m, dict):
            continue
        if m.get("text") and len(m) <= 2:
            continue
        rows.append(
            {
                "登记编号": str(_pick(m, "mortgageRegNum", "登记编号") or "-"),
                "抵押权人": str(_pick(m, "mortgagee", "抵押权人") or "-"),
                "金额": str(_pick(m, "pledgeAmount", "金额") or "-"),
                "状态": str(_pick(m, "status", "状态") or "-"),
                "登记日期": str(_pick(m, "regDate", "登记日期") or "-"),
            }
        )
    return rows


def _operation_kv(data: Mapping[str, Any]) -> Dict[str, str]:
    op = _operation(data)
    scale = op.get("scale") or {}
    out: Dict[str, str] = {}
    for label, keys in [
        ("人员规模", ("staff", "人员规模", "enterpriseScale")),
        ("年营业额", ("turnover", "年营业额", "annualTurnover")),
    ]:
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
    for label, key in [
        ("专利总数", "total"),
        ("发明申请", "invention_app"),
        ("发明授权", "invention_lic"),
        ("实用新型", "utility"),
        ("外观设计", "design"),
    ]:
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
def build_direct_payload(
    enterprise: str, keyword_type: str, *, dry_run: bool, skills_root: str,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    # 1. Collect multi-source data (live MCP or cached reports)
    data = orch.collect_direct(
        enterprise, keyword_type, dry_run=dry_run, skills_root=skills_root,
        detail_max_pages=max_pages,
    )
    meta = data.get("_meta") or {}
    resolved = meta.get("resolved") or {}
    canon = resolved.get("enterprise") or enterprise
    errors = meta.get("errors") or {}
    source_mode = "live_mcp" if meta.get("source") == "live" else "cached_reports"
    identity_base = _base(data)
    identity_name = str(_pick(identity_base, "企业名称", "name", "名称") or "").strip()
    identity_code = str(
        _pick(identity_base, "统一社会信用代码", "socialCreditCode", "信用代码") or ""
    ).strip()
    subject_confirmed = (
        identity_name not in ("", "-")
        and identity_code not in ("", "-")
        and identity_name == canon
    )
    subject_reason = (
        "工商基础信息中的企业名称和统一社会信用代码已返回"
        if subject_confirmed
        else "工商基础信息未返回可核验企业名称及统一社会信用代码"
    )

    if errors:
        for k, msg in list(errors.items())[:5]:
            print(f"⚠️  工具调用失败 [{k}]: {msg[:120]}", file=sys.stderr)

    # 2. Cross-domain analysis
    cross = xa.analyze(data)
    verdict = dict(cross["verdict"])
    scores: Dict[str, Any] = {"items": [], "average": None}
    factual_metric_labels = {
        "上游风险评分",
        "对外投资",
        "专利储备",
        "在招岗位",
        "注册资本",
        "股东数量",
        "成立年限",
        "限制高消费",
        "开庭公告",
        "行政处罚",
        "经营异常",
        "融资轮次",
        "上榜记录",
    }
    cross["metrics"] = [
        dict(item)
        for item in cross["metrics"]
        if item.get("label") in factual_metric_labels
    ]
    cross["section_specs"] = [
        spec for spec in cross["section_specs"] if spec.get("key") != "dd_specialty"
    ]
    cross["section_data"].pop("dd_specialty", None)
    cross["insights"] = [
        item
        for item in cross["insights"]
        if "评分" not in str(item) and "观察值" not in str(item)
    ]
    verdict["specialty_average"] = None
    judicial_exposure = bool(
        (_i(_risk(data).get("court_hearings_total")) or 0)
        or (_i(_risk(data).get("restrictions_total")) or 0)
    )
    risk_level_display = (
        "上游原等级与司法记录冲突待核验"
        if judicial_exposure
        else (_risk(data).get("level") or "-")
    )
    verdict["key_concerns"] = [
        concern
        for concern in verdict.get("key_concerns", [])
        if concern != "资本充实性薄弱"
    ]
    if not subject_confirmed:
        verdict.update(
            level="主体未确认",
            recommendation="仅作具名检索线索",
            summary="工商名称与统一社会信用代码未同时确认；返回内容不得归属于目标主体，不作风险或尽调评级。",
            blockers=[],
            key_concerns=["主体身份未确认"],
        )
    elif verdict.get("blockers"):
        verdict.update(
            level="不予综合评级",
            recommendation="人工司法核验",
            summary=f"发现需人工核验的司法或合规线索：{'、'.join(verdict['blockers'])}；不生成自定义综合或专项评分。",
        )
    else:
        verdict.update(
            level="事实观察（不评分）",
            recommendation="逐项人工核验",
            summary="报告仅整理公开事实和上游原始口径；缺少经验证模型与同行分母，不生成自定义综合或专项评分。",
        )
    risk_errors = any(str(key).startswith("risk_") for key in errors)
    evidence_gate = (
        subject_confirmed and xa._risk_evidence_known(data) and not risk_errors
    )
    if not evidence_gate:
        cross["insights"] = (
            []
            if not subject_confirmed
            else [
                item
                for item in cross["insights"]
                if not any(
                    word in str(item.get("feature") or "")
                    for word in ("风险", "司法", "诉讼")
                )
            ]
        )

    # 3. Build core_analysis sections + data
    sections: List[Dict[str, Any]] = []
    core: Dict[str, Any] = {}
    attempted_sections = 0

    def _effective(value: Any) -> bool:
        if value in (None, "", "-", [], {}):
            return False
        if isinstance(value, dict):
            return any(_effective(v) for v in value.values())
        if isinstance(value, list):
            return any(_effective(v) for v in value)
        return True

    def _add(spec: Dict[str, Any], body: Any) -> None:
        nonlocal attempted_sections
        attempted_sections += 1
        key = spec["key"]
        # radar carries its data in the chart spec (indicators/series), not the body
        if spec.get("kind") == "radar":
            sections.append(spec)
            if body:
                core[key] = body
            return
        if _effective(body):
            sections.append(spec)
            core[key] = body

    # business base
    base_kv = _base_kv(data)
    _add(
        {
            "key": "dd_base",
            "title": "工商基础信息",
            "kind": "kv",
            "note": "工商登记 + 简介 + 经营范围",
        },
        base_kv,
    )

    # cross-analysis sections (shareholders, investments, litigation, specialty matrix)
    for spec in cross["section_specs"]:
        _add(spec, cross["section_data"].get(spec["key"]))

    # risk gauge + risk dimension counts — paired to avoid whitespace
    risk_score = _i(_risk(data).get("score"))
    if risk_score is not None:
        _add(
            {
                "key": "dd_risk_gauge",
                "title": "综合风险评分",
                "kind": "gauge",
                "chart": {"value_key": "风险评分", "level_key": "风险等级", "max": 100},
                "note": "上游风险评分原始口径；若与司法事件数量冲突，不作为低风险背书",
                "pair_with": "dd_risk_dims",
            },
            {"风险评分": risk_score, "风险等级": risk_level_display},
        )
    risk_rows = _risk_dim_rows(data)
    _add(
        {
            "key": "dd_risk_dims",
            "title": "风险维度统计",
            "kind": "table",
            "note": "各风险维度记录数（尽调合规核查）",
            "columns": [("风险维度", "风险维度"), ("记录数", "记录数")],
        },
        risk_rows,
    )

    # --- 风险案件明细（尽调核心：展开具体案件，而非只给数字）---
    hearing_rows = _hearing_rows(data)
    _add(
        {
            "key": "dd_hearings",
            "title": "开庭公告明细",
            "kind": "table",
            "note": _hearing_note(data, hearing_rows),
            "columns": [
                ("案号", "案号"),
                ("案由", "案由"),
                ("法院", "法院"),
                ("相关主体", "相关主体"),
                ("开庭/发布日期", "开庭/发布日期"),
                ("公告类型", "公告类型"),
                ("去重键状态", "去重键状态"),
            ],
        },
        hearing_rows,
    )

    restriction_rows = _restriction_rows(data)
    _add(
        {
            "key": "dd_restrictions",
            "title": "限制高消费明细",
            "kind": "table",
            "note": "限制高消费是尽调重大风险信号，需核查执行标的与履行情况",
            "columns": [
                ("案号", "案号"),
                ("执行法院", "执行法院"),
                ("申请执行人", "申请执行人"),
                ("被限制人", "被限制人"),
                ("发布日期", "发布日期"),
            ],
        },
        restriction_rows,
    )

    anomaly_rows = _anomaly_rows(data)
    _add(
        {
            "key": "dd_anomalies",
            "title": "经营异常明细",
            "kind": "table",
            "note": "经营异常名录记录（如通过住所无法联系），核查是否已移出",
            "columns": [
                ("列入原因", "列入原因"),
                ("决定机关", "决定机关"),
                ("列入日期", "列入日期"),
                ("移出日期", "移出日期"),
                ("状态", "状态"),
            ],
        },
        anomaly_rows,
    )

    penalty_rows = _penalty_rows(data)
    _add(
        {
            "key": "dd_penalties",
            "title": "行政处罚明细",
            "kind": "table",
            "note": "行政处罚记录，核查违法事实与处罚影响",
            "columns": [
                ("处罚类型", "处罚类型"),
                ("处罚内容", "处罚内容"),
                ("决定机关", "决定机关"),
                ("决定日期", "决定日期"),
                ("文号", "文号"),
            ],
        },
        penalty_rows,
    )

    mortgage_rows = _mortgage_rows(data)
    _add(
        {
            "key": "dd_mortgages",
            "title": "动产抵押明细",
            "kind": "table",
            "note": "动产抵押反映资产质押状况",
            "columns": [
                ("登记编号", "登记编号"),
                ("抵押权人", "抵押权人"),
                ("金额", "金额"),
                ("状态", "状态"),
                ("登记日期", "登记日期"),
            ],
        },
        mortgage_rows,
    )

    # operation
    op_kv = _operation_kv(data)
    _add(
        {
            "key": "dd_operation",
            "title": "经营规模与资本运作",
            "kind": "kv",
            "note": "人员规模 / 营业额 / 融资 / 上榜记录",
        },
        op_kv,
    )

    # patent
    pat_kv = _patent_kv(data)
    _add(
        {
            "key": "dd_patent",
            "title": "专利公开统计",
            "kind": "kv",
            "note": "专利公开字段事实统计；未核验申请人归属、有效性、质量、研发投入或同行分母，不推断技术壁垒与研发深度",
        },
        pat_kv,
    )

    # recruitment
    rec_kv = _recruitment_kv(data)
    _add(
        {
            "key": "dd_recruitment",
            "title": "招聘公开统计",
            "kind": "kv",
            "note": "招聘平台公开字段事实统计；“当前/近三月”为上游窗口标签，未返回精确观察起止日期，不能单独证明经营动能、扩张结果或履约能力",
        },
        rec_kv,
    )

    # 4. Metrics
    metrics: List[Dict[str, Any]] = list(cross["metrics"])
    for item in metrics:
        if item.get("label") == "上游风险评分":
            item["hint"] = "上游原始口径；若与司法事件数量冲突，不作为低风险背书"
            if judicial_exposure:
                item.pop("delta", None)
        elif item.get("label") == "专利储备":
            item["hint"] = "专利公开数量；归属、有效性和质量待核验"
        elif item.get("label") == "在招岗位":
            item["hint"] = "招聘平台公开数量；不代表经营动能或扩张结果"

    # 5. Insights (cross-domain first, then can supplement)
    insights: List[Dict[str, Any]] = list(cross["insights"])

    # 6. Representative records (key cross-domain facts for the "Records" section)
    rep_records: List[Dict[str, str]] = []
    invests = _investments(data)
    inv_total = _risk(data).get("investments_total") or len(invests)
    cancelled = [
        i
        for i in invests
        if "注销" in str(_pick(i, "operStatus", "经营状态", "状态") or "")
    ]
    if inv_total:
        rep_records.append(
            {
                "维度": "对外投资",
                "关键记录": f"{inv_total} 家关联企业"
                + (f"（其中 {len(cancelled)} 家已注销）" if cancelled else ""),
            }
        )
    ls = xa._litigation_summary(data)
    if ls["executed"]:
        rep_records.append(
            {"维度": "执行风险", "关键记录": f"被执行记录 {ls['executed']} 条"}
        )
    risk_score = _i(_risk(data).get("score"))
    if risk_score is not None:
        rep_records.append(
            {
                "维度": "风险评级",
                "关键记录": f"上游风险评分 {risk_score}（{risk_level_display}）",
            }
        )
    patent_total = _i(_patent(data).get("total"))
    if patent_total is not None:
        rep_records.append({"维度": "创新储备", "关键记录": f"专利 {patent_total} 件"})
    fin_n = _i(_operation(data).get("financing_count"))
    if fin_n:
        rep_records.append({"维度": "资本运作", "关键记录": f"已完成 {fin_n} 轮融资"})
    hearing_total = _risk(data).get("court_hearings_total")
    if hearing_total:
        rep_records.append(
            {"维度": "诉讼记录", "关键记录": f"开庭公告 {hearing_total} 条"}
        )
    if not rep_records:
        rep_records.append({"维度": "数据状态", "关键记录": "多维数据覆盖，详见各章节"})

    # 7. Abstract & summary — 数据驱动，不重复 verdict.summary
    n_sources = sum(
        1
        for d in (
            data.get("enterprise"),
            data.get("risk"),
            data.get("operation"),
            data.get("patent"),
            data.get("recruitment"),
        )
        if _effective(d)
    )
    risk_score = _i(_risk(data).get("score"))
    risk_level = risk_level_display
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
        data_facts.append(
            f"上游风险评分 {risk_score}（{risk_level}；不作为低风险背书）"
        )
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
    if verdict["blockers"]:
        abstract_parts.append(f"阻断项：{'、'.join(verdict['blockers'])}。")
    if verdict["key_concerns"]:
        abstract_parts.append(f"关注点：{'、'.join(verdict['key_concerns'][:3])}。")
    abstract = "".join(abstract_parts)

    if not subject_confirmed:
        sections = []
        core = {}
        metrics = []
        insights = []
        rep_records = [
            {
                "维度": "检索状态",
                "关键记录": "仅形成具名检索线索；工商名称与统一社会信用代码未同时确认，所有返回记录归属待核验",
            }
        ]
        abstract = (
            f"本报告仅记录对关键词「{enterprise}」的具名检索线索。"
            "工商名称与统一社会信用代码未同时确认，返回的风险、投资、专利、经营及招聘记录不得归属于目标主体；不作风险、低风险或尽调评级。"
        )

    # Keep evidence-bound narrative deterministic.  An unconstrained optional
    # rewrite can turn sparse public counts into unsupported strength claims.

    # Upstream risk scores may remain as explicitly sourced factual metrics,
    # but must never be promoted into this report's own gauge or "综合" chart.
    gauge_keys = {
        str(section.get("key") or "")
        for section in sections
        if section.get("kind") == "gauge"
    }
    if gauge_keys:
        sections = [section for section in sections if section.get("kind") != "gauge"]
        for key in gauge_keys:
            core.pop(key, None)
        attempted_sections = max(0, attempted_sections - len(gauge_keys))

    # quality report
    populated = sum(
        1
        for s in sections
        if s.get("kind") == "radar" or _effective(core.get(s["key"]))
    )
    quality = {
        "total_sections": attempted_sections,
        "populated_sections": populated,
        "empty_sections": attempted_sections - populated,
        "coverage_pct": round(populated / max(1, attempted_sections) * 100),
        "data_sources": n_sources,
        "cross_insights": len(insights),
    }

    report = {
        "report_type": REPORT_TYPE,
        "title": f"{canon} 尽调评估报告",
        "banner": BANNER,
        "subject": {
            "enterprise": canon,
            "match_raw": enterprise,
            "resolved": subject_confirmed,
            "resolve_reason": subject_reason,
        },
        "abstract": abstract,
        "summary": abstract,
        "executive_summary": [verdict["summary"]]
        + [i["interpretation"] for i in insights[:4]],
        "verdict": verdict,
        "specialty_scores": scores,
        "metrics": metrics,
        "caliber": {
            "match_target": canon,
            "match_type": "企业尽调评估（直接聚合 5 个 MCP：工商/风险/经营/创新/招聘）",
            "data_scope": f"覆盖 {n_sources}/5 大数据源，{len(sections)} 个明细章节，{len(insights)} 条跨维度洞察",
            "products": [
                "企业大数据",
                "企业风险洞察",
                "企业经营分析",
                "专利大数据",
                "招聘大数据",
            ],
            "limit": "未确认主体时所有返回仅为具名检索线索；已确认主体时也仅整理公开事实，不生成自定义评分；专利申请人/权利人与工商主体关系、有效性及质量需逐项核验，并结合财务审计、司法核验与实地尽调。",
        },
        "core_analysis": {**core, "sections": sections},
        "representative_records": rep_records,
        "insights": insights,
        "data_source": {
            "mcp_server": "5 MCP（工商/风险/经营/创新/招聘）",
            "mcp_servers": [
                "enterprise-mcp-server",
                "enterprise-risk-mcp-server",
                "enterprise-operation-mcp-server",
                "patent-mcp-server",
                "recruitment-mcp-server",
            ],
            "mode": source_mode,
            "dry_run": dry_run,
            "generated_at": dt.datetime.now()
            .astimezone()
            .isoformat(timespec="seconds"),
            "quality_report": quality,
            "tool_errors": list(errors.keys()) if errors else [],
        },
    }
    if meta.get("source") == "live":
        from common import attach_pagination

        report = attach_pagination(report, meta.get("pagination_payloads") or {})
        call_usage = meta.get("call_usage")
        if isinstance(call_usage, dict) and call_usage:
            report["data_source"]["call_usage"] = call_usage
        if max_pages is None:
            budget_note = (
                "明细接口默认按单页预算采集（每接口仅请求第 1 页，该页同时用于分析与上游 total 发现，不重复计费）；"
                "如需更多明细页，请先规划所需结论与数据维度，再用 --max-pages N 明确页数预算；"
                "若预算不足以支撑关键结论，必须说明证据缺口与预计所需额外页数，不得悄悄降级结论或扩大计费范围。"
            )
            report["abstract"] += budget_note
            report["summary"] += budget_note
            report["caliber"]["limit"] += budget_note
        for note in (meta.get("schema_limited") or {}).values():
            report["abstract"] += note
            report["summary"] += note
            report["caliber"]["limit"] += note
    return report
