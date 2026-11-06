#!/usr/bin/env python3
"""Due-diligence MCP orchestration: tool plan + multi-source collection + normalization.

Selects ~20 high-value tools across 5 MCP servers, tuned for investment / M&A /
partnership due-diligence:

  enterprise  : base_info / holders / investments / key persons
  risk        : score / litigation / hearings / penalties / anomalies /
                consumption-restrictions / chattel-mortgage
  operation   : business-scale / financing / company-trends / rankings
  patent      : patent_stats (innovation reserve)
  recruitment : trend / employer-profile (expansion vitality)

Two collection modes:
  * live  — connect to the 5 MCP servers via MultiMcpClient (richest data)
  * cache — read pre-existing atomic report JSONs (reports_探迹/) for dry-run

Both normalize into the SAME unified structure consumed by cross_analysis.
"""

from __future__ import annotations

import asyncio
import copy
import json
import pathlib
from typing import Any, Dict, List, Mapping, Optional

from common import collect_detail_pages
from multi_mcp_client import MultiMcpClient, MultiMcpError

# Live detail interfaces traversed against their upstream total. Only tools
# whose input schema accepts pageIndex/pageSize AND that return a detail
# resultList+total are listed here; stats/summary, profile, fuzzy-resolution
# and single-shot interfaces stay one call.
#   key (from build_mcp_calls) -> safe interface label
PAGED_DETAIL_TOOLS: Dict[str, str] = {
    "risk_hearings": "开庭公告明细",
    "risk_restrictions": "限制高消费明细",
    "op_rankings": "企业上榜榜单明细",
}

# Detail-list interfaces that return resultList+total but whose tool input
# schema accepts only ``keyword`` (no pageIndex/pageSize). They stay a single
# call; when upstream total exceeds the rows returned we disclose the gap so
# consumers know the collection cannot be completed.
SCHEMA_LIMITED_DETAIL: Dict[str, str] = {
    "ent_invest": "对外投资明细",
    "ent_person": "主要人员明细",
}

# Default paid-detail budget: one page per detail interface. The page is used
# both as the data page and as upstream-total discovery (never refetched), and
# its total/remaining counts are disclosed via attach_pagination. Full
# traversal requires an explicit positive max_pages budget from the caller.
DEFAULT_DETAIL_MAX_PAGES = 1


def _canonical_request_key(domain: str, tool: str, arguments: Mapping[str, Any]) -> str:
    """Canonical identity for a paid request so identical calls are never repaid."""
    return json.dumps(
        [domain, tool, dict(arguments)], sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )

# --------------------------------------------------------------------------- #
# Generic extractors
# --------------------------------------------------------------------------- #


def _is_api_error(value: Any) -> bool:
    """Return True for protocol/tool/upstream failures, never for empty data."""
    markers = (
        "接口调用失败",
        "查询失败",
        "状态码：4",
        "状态码：5",
        "error executing tool",
        "unknown tool",
        "validation error",
        "signature",
        "credential",
        "unauthorized",
        "forbidden",
    )
    if value is None:
        return False
    if isinstance(value, str):
        return any(m in value.lower() for m in markers)
    if isinstance(value, dict):
        if (
            value.get("_error")
            or value.get("isError") is True
            or value.get("is_error") is True
        ):
            return True
        code = value.get("code")
        if code not in (None, 0, "0", 200, "200"):
            return True
        return any(_is_api_error(v) for v in value.values())
    if isinstance(value, list):
        return any(_is_api_error(v) for v in value)
    return False


def _first_list(value: Any) -> List[Any]:
    if _is_api_error(value):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in (
            "resultList",
            "list",
            "items",
            "data",
            "holderList",
            "stockHolderList",
            "fpFinancingList",
            "tpQualificationList",
            "punishmentList",
            "anomalyList",
            "tmTypeList",
            "tmStatusList",
            "winbidStatList",
            "winbidAreaStat",
            "tenderStatList",
            "sentimentLabelList",
        ):
            if isinstance(value.get(key), list):
                return value[key]
    return []


def _tool_errors(raw: Mapping[str, Any]) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    for key, value in raw.items():
        if str(key).startswith("_"):
            continue
        if _is_api_error(value):
            errors[str(key)] = "工具调用失败"
    return errors


def _safe_total(value: Any) -> Optional[int]:
    if isinstance(value, dict):
        if _is_api_error(value):
            return None
        t = value.get("total")
        try:
            return int(t) if t is not None else None
        except (TypeError, ValueError):
            return None
    return None


def _text(value: Any, limit: int = 0) -> str:
    if value is None:
        return ""
    t = (
        json.dumps(value, ensure_ascii=False)
        if isinstance(value, (dict, list))
        else str(value)
    )
    t = " ".join(t.split())
    return (t[: limit - 1].rstrip() + "…") if (limit and len(t) > limit) else t


def _int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> Optional[float]:
    try:
        return float(str(value).replace(",", "").replace("万", "").replace("亿", ""))
    except (TypeError, ValueError):
        return None


def _amount(value: Any) -> str:
    """Parse a HandaaS amount field into readable text.

    Accepts: {"coinType":"人民币","value":2e9} | 20000 | "100万" | "人民币 100万"
    """
    if value in (None, "", "-"):
        return "-"
    if isinstance(value, dict):
        val = value.get("value")
        coin = value.get("coinType") or value.get("currency") or ""
        if val is None:
            return "-"
        try:
            fv = float(val)
        except (TypeError, ValueError):
            return f"{coin} {val}".strip()
        if fv >= 1e8:
            return f"{coin} {fv / 1e8:.2f}亿".strip()
        if fv >= 1e4:
            return f"{coin} {fv / 1e4:.0f}万".strip()
        return f"{coin} {fv:.0f}".strip()
    return str(value)


def _industry_text(value: Any) -> str:
    """Flatten a nested industry dict into '一级/二级/三级' text."""
    if not isinstance(value, dict):
        return str(value) if value else "-"
    parts = []
    for k in ("firstIndustry", "secondIndustry", "thirdIndustry", "fourthIndustry"):
        v = value.get(k)
        if v and str(v) not in parts:
            parts.append(str(v))
    return " / ".join(parts) if parts else "-"


def _amount_num(value: Any) -> Optional[float]:
    """Extract the numeric value from a HandaaS amount field."""
    if isinstance(value, dict):
        return _float(value.get("value"))
    return _float(value)


def _kv_addr(value: Any) -> str:
    """Extract address string from a nested addressValue dict."""
    if isinstance(value, dict):
        return str(value.get("value") or value.get("address") or "-")
    return str(value) if value else ""


# --------------------------------------------------------------------------- #
# Live collection: MCP tool plan
# --------------------------------------------------------------------------- #
def build_mcp_calls(
    enterprise: str, keyword_type: str
) -> List[tuple[str, str, str, Dict[str, Any]]]:
    """Return [(key, domain, tool, args), ...] for all due-diligence tools."""
    ent_kw: Dict[str, Any] = {"keyword": enterprise}
    mk_kw: Dict[str, Any] = {"matchKeyword": enterprise, "keywordType": keyword_type}
    return [
        # --- enterprise (工商) ---
        ("ent_base", "enterprise", "enterprise_get_enterprise_base_info", ent_kw),
        ("ent_holder", "enterprise", "enterprise_get_enterprise_holder_info", ent_kw),
        ("ent_invest", "enterprise", "enterprise_get_enterprise_invest_info", ent_kw),
        (
            "ent_person",
            "enterprise",
            "enterprise_get_enterprise_main_person_info",
            ent_kw,
        ),
        # --- risk (风险) ---
        ("risk_score", "risk", "enterprise_risk_insight_score", mk_kw),
        ("risk_litigation", "risk", "risk_insight_litigation_risk_profile", mk_kw),
        (
            "risk_hearings",
            "risk",
            "risk_insight_court_hearings",
            {**mk_kw, "pageSize": 50},
        ),
        ("risk_penalties", "risk", "risk_insight_penalties", mk_kw),
        ("risk_anomalies", "risk", "risk_insight_business_anomalies", mk_kw),
        (
            "risk_restrictions",
            "risk",
            "risk_insight_consumption_restrictions",
            {**mk_kw, "pageSize": 50},
        ),
        ("risk_mortgage", "risk", "risk_insight_chattel_mortgage", mk_kw),
        # --- operation (经营) ---
        ("op_scale", "operation", "operation_insight_business_scale", mk_kw),
        ("op_financing", "operation", "operation_insight_financing_info", mk_kw),
        ("op_trends", "operation", "operation_insight_company_trends", mk_kw),
        (
            "op_rankings",
            "operation",
            "operation_insight_enterprise_rankings",
            {**mk_kw, "pageSize": 10},
        ),
        # --- patent (创新) ---
        ("patent_stats", "patent", "patent_bigdata_patent_stats", mk_kw),
        # --- recruitment (招聘/扩张活跃度) ---
        ("rec_profile", "recruitment", "recruitment_employer_profile", mk_kw),
    ]


_ENTERPRISE_SUFFIXES = (
    "公司",
    "集团",
    "有限",
    "院",
    "厂",
    "中心",
    "事务所",
    "合作社",
    "合伙",
)


def is_full_name(raw: str) -> bool:
    return any(s in (raw or "") for s in _ENTERPRISE_SUFFIXES)


async def resolve_enterprise(client: MultiMcpClient, keyword: str, *, call: Any = None) -> Dict[str, Any]:
    """Resolve a keyword to a canonical enterprise name via enterprise MCP fuzzy search."""
    keyword = (keyword or "").strip()
    if not keyword:
        return {"keyword": "", "enterprise": "", "resolved": False}
    if is_full_name(keyword):
        return {
            "keyword": keyword,
            "enterprise": keyword,
            "resolved": True,
            "reason": "视为企业全称",
        }
    fuzzy = await (call or client.call)(
        "enterprise",
        "enterprise_get_keyword_search",
        {"matchKeyword": keyword, "pageSize": 5},
    )
    candidates = [
        str(rec.get("name") or "").strip()
        for rec in _first_list(fuzzy)
        if isinstance(rec, dict) and str(rec.get("name") or "").strip()
    ]
    exact = next((name for name in candidates if name == keyword), None)
    if exact:
        return {
            "keyword": keyword,
            "enterprise": exact,
            "resolved": True,
            "reason": "精确名称命中",
        }
    if len(candidates) == 1:
        return {
            "keyword": keyword,
            "enterprise": candidates[0],
            "resolved": True,
            "reason": "唯一候选补全",
        }
    reason = (
        "模糊查询存在多个候选，未自动确认主体"
        if candidates
        else "模糊查询未命中，停止后续查询"
    )
    return {
        "keyword": keyword,
        "enterprise": keyword,
        "resolved": False,
        "reason": reason,
        "candidates": candidates,
    }


async def _collect_live(
    enterprise: str, keyword_type: str, *, detail_max_pages: Optional[int] = None
) -> Dict[str, Any]:
    """Connect to 5 MCP servers, resolve name, fan out all tool calls with
    bounded total-driven pagination for detail-list interfaces.

    *detail_max_pages* is a paid-call budget per detail interface; the first
    page doubles as total discovery and is never refetched. Default is the
    module-level DEFAULT_DETAIL_MAX_PAGES (one page); full traversal requires
    an explicit positive budget from the caller.
    """
    budget = detail_max_pages if detail_max_pages is not None else DEFAULT_DETAIL_MAX_PAGES
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise ValueError("detail_max_pages 必须为正整数或 None（默认单页预算）")
    loop = asyncio.get_running_loop()
    async with MultiMcpClient() as client:

        # Client-scoped request reuse: identical domain+tool+params within this
        # task share ONE in-flight awaitable (failures included) and are never
        # repaid. Lives and dies with this client/task; no persistent cache.
        inflight: Dict[str, asyncio.Future] = {}
        executed = 0
        reused = 0

        async def _call_once(domain: str, tool: str, arguments: Dict[str, Any]) -> Any:
            nonlocal executed, reused
            key = _canonical_request_key(domain, tool, arguments)
            existing = inflight.get(key)
            if existing is not None:
                reused += 1
                return copy.deepcopy(await asyncio.shield(existing))
            task = asyncio.ensure_future(client.call(domain, tool, arguments))
            inflight[key] = task
            executed += 1
            return copy.deepcopy(await task)
        if keyword_type == "name":
            resolved = await resolve_enterprise(client, enterprise, call=_call_once)
        else:
            resolved = {"keyword": enterprise, "enterprise": enterprise,
                        "resolved": bool(enterprise.strip()), "reason": "使用显式企业标识"}
        if not resolved.get("resolved"):
            candidates = "；".join(resolved.get("candidates") or [])
            detail = f"候选企业：{candidates}。" if candidates else "请核对企业查询工具状态与输入。"
            raise ValueError("企业主体未唯一确认，已停止后续付费查询；请确认企业全称或明确企业标识。" + detail)
        canon = resolved["enterprise"] or enterprise
        calls = build_mcp_calls(canon, keyword_type)
        paged = [c for c in calls if c[0] in PAGED_DETAIL_TOOLS]
        plain = [c for c in calls if c[0] not in PAGED_DETAIL_TOOLS]

        needed: List[str] = []
        for _k, domain, _t, _a in plain:
            if domain not in needed:
                needed.append(domain)
        await client.warmup(needed)

        async def _one(key: str, domain: str, tool: str, args: Dict[str, Any]) -> tuple[str, Any]:
            return key, await _call_once(domain, tool, args)

        raw: Dict[str, Any] = {}
        tasks = [asyncio.ensure_future(_one(k, d, t, a)) for k, d, t, a in plain]
        for coro in asyncio.as_completed(tasks):
            try:
                key, value = await coro
                raw[key] = value
            except Exception as exc:  # last-resort isolation, mirrors call_many
                raw[f"_task_error_{len(raw)}"] = {"_error": str(exc)}

        pagination_payloads: Dict[str, Any] = {}
        for key, domain, tool, args in paged:
            label = PAGED_DETAIL_TOOLS[key]

            def _sync_call(_tool: str, _arguments: Dict[str, Any]) -> Any:
                future = asyncio.run_coroutine_threadsafe(
                    _call_once(domain, _tool, _arguments), loop
                )
                return future.result()

            collected = await asyncio.to_thread(
                collect_detail_pages,
                _sync_call, tool, args,
                get_rows=_first_list, get_total=_safe_total, is_error=_is_api_error,
                max_pages=budget,
            )
            raw[key] = collected
            pagination_payloads[label] = collected
        schema_limited: Dict[str, str] = {}
        for key, label in SCHEMA_LIMITED_DETAIL.items():
            payload = raw.get(key)
            total = _safe_total(payload)
            rows = _first_list(payload)
            if total is not None and total > len(rows):
                schema_limited[label] = (
                    f"{label}工具参数不含分页（仅 keyword），上游 total={total}、"
                    f"实际取得 {len(rows)} 条，其余 {total - len(rows)} 条无法遍历，采集不完整。"
                )
    raw["_resolved"] = resolved
    if pagination_payloads:
        raw["_pagination_payloads"] = pagination_payloads
    if schema_limited:
        raw["_schema_limited"] = schema_limited
    raw["_detail_max_pages"] = detail_max_pages
    raw["_call_usage"] = {
        "executed_requests": executed,
        "reused_requests": reused,
        "scope": "current_task_client_lifecycle",
    }
    return normalize_mcp(raw)


# --------------------------------------------------------------------------- #
# Cache collection: read pre-existing atomic report JSONs (dry-run)
# --------------------------------------------------------------------------- #
def _metric_value(report: Mapping[str, Any], label: str) -> Optional[str]:
    for m in report.get("metrics", []):
        if isinstance(m, dict) and label in str(m.get("label", "")):
            return str(m.get("value", ""))
    return None


def _metric_int(report: Mapping[str, Any], label: str) -> Optional[int]:
    v = _metric_value(report, label)
    return _int(v.replace(",", "").replace("万", "").replace("%", "")) if v else None


def _collect_cache(skills_root: str, enterprise: str) -> Dict[str, Any]:
    """Load atomic report JSONs from reports_探迹/ and normalize."""
    root = pathlib.Path(skills_root)
    reports_dir = root / "reports_探迹"
    if not reports_dir.exists():
        # fall back to each atomic skill's output/ sample
        return normalize_reports({}, enterprise, resolved=False)
    reports: Dict[str, Any] = {}
    for p in sorted(reports_dir.glob("*.json")):
        try:
            reports[p.stem] = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return normalize_reports(reports, enterprise)


# --------------------------------------------------------------------------- #
# Normalization — both modes produce THIS structure
# --------------------------------------------------------------------------- #
def normalize_mcp(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize live MCP results into the unified cross-analysis structure."""
    resolved = raw.get("_resolved") or {}
    errors = _tool_errors(raw)

    # --- enterprise ---
    base_raw = raw.get("ent_base") or {}
    bi = base_raw.get("base_info") if isinstance(base_raw, dict) else {}
    if not isinstance(bi, dict):
        bi = {}
    base = {
        "企业名称": bi.get("name") or "-",
        "统一社会信用代码": bi.get("socialCreditCode") or bi.get("orgCode") or "-",
        "法定代表人": bi.get("legalRepresentative") or "-",
        "企业类型": bi.get("enterpriseType") or "-",
        "行业": _industry_text(bi.get("industry")),
        "注册资本": _amount(bi.get("regCapital")),
        "实缴资本": _amount(bi.get("realCapital") or bi.get("payAmountCount")),
        "成立日期": str(bi.get("foundTime") or "-"),
        "经营状态": bi.get("operStatus") or "-",
        "注册地址": bi.get("address") or _kv_addr(bi.get("addressValue")) or "-",
        "经营范围": _text(bi.get("business") or bi.get("businessScope"), limit=400)
        or "-",
    }
    # 实缴率：若实缴与注册资本都可量化则计算
    reg_v = _amount_num(bi.get("regCapital"))
    paid_v = _amount_num(bi.get("realCapital") or bi.get("payAmountCount"))
    if reg_v and paid_v is not None and reg_v > 0:
        base["资本实缴率"] = f"{paid_v / reg_v * 100:.1f}%"
    holders = _first_list(raw.get("ent_holder"))
    investments = _first_list(raw.get("ent_invest"))
    investments_total = _safe_total(raw.get("ent_invest")) or len(investments)
    persons = _first_list(raw.get("ent_person"))

    # --- risk ---
    rs = raw.get("risk_score") or {}
    rl = raw.get("risk_litigation") or {}
    rl = rl if isinstance(rl, dict) else {}
    # litigation: live MCP returns caKaitingList/caLiAnList etc. + summary fields
    hearings_list = _first_list(raw.get("risk_hearings"))
    hearings_total = _safe_total(raw.get("risk_hearings")) or len(hearings_list)
    # penalties: MCP wraps records in {punishmentCount, punishmentList:[...]}
    penalties_raw = raw.get("risk_penalties") or {}
    if isinstance(penalties_raw, dict) and isinstance(
        penalties_raw.get("punishmentList"), list
    ):
        penalties_count = _int(penalties_raw.get("punishmentCount"))
        penalties_list = [
            r
            for r in penalties_raw["punishmentList"]
            if isinstance(r, dict) and r.get("text") != "查询数据为空"
        ]
        penalties_total = penalties_count or len(penalties_list)
    else:
        penalties_list = [
            r
            for r in _first_list(penalties_raw)
            if isinstance(r, dict) and r.get("text") != "查询数据为空"
        ]
        penalties_total = _safe_total(penalties_raw) or len(penalties_list)
    # anomalies: MCP may nest {anomalyList:[...], anomalyCount} OR return {text:"查询数据为空"}
    anomalies_raw_raw = raw.get("risk_anomalies") or {}
    if (
        isinstance(anomalies_raw_raw, dict)
        and anomalies_raw_raw.get("text") == "查询数据为空"
    ):
        anomalies_list = []
    elif isinstance(anomalies_raw_raw, dict) and isinstance(
        anomalies_raw_raw.get("anomalyList"), list
    ):
        anomalies_list = [
            a for a in anomalies_raw_raw["anomalyList"] if isinstance(a, dict)
        ]
    else:
        anomalies_list = [
            a
            for a in _first_list(anomalies_raw_raw)
            if isinstance(a, dict) and a.get("text") != "查询数据为空"
        ]
    # restrictions: filter "查询数据为空"
    restrictions_raw = raw.get("risk_restrictions") or {}
    if (
        isinstance(restrictions_raw, dict)
        and restrictions_raw.get("text") == "查询数据为空"
    ):
        restrictions_list = []
        restrictions_total = 0
    else:
        restrictions_list = [
            r
            for r in _first_list(restrictions_raw)
            if isinstance(r, dict) and r.get("text") != "查询数据为空"
        ]
        restrictions_total = _safe_total(restrictions_raw) or len(restrictions_list)
    # mortgages: filter "查询数据为空"
    mortgages_raw = raw.get("risk_mortgage") or {}
    if isinstance(mortgages_raw, dict) and mortgages_raw.get("text") == "查询数据为空":
        mortgages_list = []
        mortgages_total = 0
    else:
        mortgages_list = [
            r
            for r in _first_list(mortgages_raw)
            if isinstance(r, dict) and r.get("text") != "查询数据为空"
        ]
        mortgages_total = _safe_total(mortgages_raw) or len(mortgages_list)
    # litigation summary: keep the upstream category totals distinct.
    # caTotal=法院公告, caLianTotal=立案公告, caKaitingTotal=开庭公告,
    # jdTotal=裁判文书, enforcementTotal=被执行人, edTotal=失信被执行人,
    # limitedTotal=限制高消费. Never relabel 开庭公告 as 案件/公告总数.
    hearings_n = hearings_total
    ca_total = _int(rl.get("caTotal"))
    filing_total = _int(rl.get("caLianTotal"))
    judgments_total = _int(rl.get("jdTotal"))
    enforcement_total = _int(rl.get("enforcementTotal"))
    dishonest_total = _int(rl.get("edTotal"))
    limited_total = _int(rl.get("limitedTotal"))
    litigation = {
        "case_count": ca_total,
        "as_defendant": _int(rl.get("asDefendantCount")),
        "as_plaintiff": _int(rl.get("asPlaintiffCount")),
        "recent_count": _int(rl.get("recentCaseCount")),
        "total_amount": _float(rl.get("totalAmount")),
        "announcements_total": ca_total,
        "filing_total": filing_total,
        "hearings_count": hearings_n if hearings_n is not None else _int(rl.get("caKaitingTotal")),
        "judgments_total": judgments_total,
        "enforcement_total": enforcement_total,
        "dishonest_total": dishonest_total,
        "restricted_total": limited_total,
        "开庭公告数": hearings_n,
        "被执行人记录数": enforcement_total,
        "失信被执行人数": dishonest_total,
    }
    if limited_total is not None:
        restrictions_total = limited_total
    risk = {
        "_evidence_known": any(
            (
                (
                    isinstance(rs, dict)
                    and any(
                        rs.get(key) is not None
                        for key in (
                            "risk_score",
                            "riskScore",
                            "risk_level",
                            "riskLevel",
                        )
                    )
                ),
                _safe_total(raw.get("risk_hearings")) is not None,
                bool(hearings_list),
                _int(penalties_raw.get("punishmentCount")) is not None
                if isinstance(penalties_raw, dict)
                else False,
                bool(penalties_list),
                _int(anomalies_raw_raw.get("anomalyCount")) is not None
                if isinstance(anomalies_raw_raw, dict)
                else False,
                bool(anomalies_list),
                _safe_total(restrictions_raw) is not None,
                bool(restrictions_list),
            )
        ),
        "score": _int(rs["risk_score"])
        if isinstance(rs, dict) and rs.get("risk_score") is not None
        else (_int(rs.get("riskScore")) if isinstance(rs, dict) else None),
        "level": (
            rs["risk_level"]
            if isinstance(rs, dict) and rs.get("risk_level")
            else (rs.get("riskLevel") if isinstance(rs, dict) else None)
        ),
        "credit_level": None,
        "oper_level": None,
        "litigation_level": None,
        "litigation": litigation,
        "court_hearings": hearings_list,
        "court_hearings_total": hearings_total,
        "penalties": penalties_list,
        "penalties_total": penalties_total,
        "anomalies": anomalies_list,
        "anomalies_total": len(anomalies_list),
        "restrictions": restrictions_list,
        "restrictions_total": restrictions_total,
        "mortgages": mortgages_list,
        "mortgages_total": mortgages_total,
        "investments_total": investments_total,
    }

    # --- operation ---
    os_ = raw.get("op_scale") or {}
    of = raw.get("op_financing") or {}
    ot = raw.get("op_trends") or {}
    operation = {
        "scale": {
            "staff": os_.get("enterpriseScale") if isinstance(os_, dict) else None,
            "turnover": os_.get("annualTurnover") if isinstance(os_, dict) else None,
        },
        "financing_count": _int(of.get("fpFinancingCount"))
        if isinstance(of, dict)
        else None,
        "financing_list": _first_list(of.get("fpFinancingList"))
        if isinstance(of, dict)
        else [],
        "trends": ot if isinstance(ot, dict) else {},
        "rankings": _first_list(raw.get("op_rankings")),
    }

    # --- patent ---
    ps = raw.get("patent_stats") or {}
    ps = ps if isinstance(ps, dict) else {}
    type_stat = (
        ps.get("patentTypeStat") if isinstance(ps.get("patentTypeStat"), dict) else {}
    )
    invention_app = _int(
        ps.get("inventionAppPatentCount") or type_stat.get("inventionAppPatentCount")
    )
    invention_lic = _int(
        ps.get("inventionLicPatentCount") or type_stat.get("inventionLicPatentCount")
    )
    utility = _int(
        ps.get("utilityModelPatentCount") or type_stat.get("utilityModelPatentCount")
    )
    design = _int(
        ps.get("appearanceDesignPatentCount")
        or type_stat.get("appearanceDesignPatentCount")
    )
    known_types = [
        value
        for value in (invention_app, invention_lic, utility, design)
        if value is not None
    ]
    patent = {
        "total": _int(ps.get("patentCount"))
        if ps.get("patentCount") is not None
        else (sum(known_types) if known_types else None),
        "invention_app": invention_app,
        "invention_lic": invention_lic,
        "utility": utility,
        "design": design,
        "apply_trend": _first_list(ps.get("patentTypeAppTimeStat")),
        "publish_trend": _first_list(ps.get("patentTypePubTimeStat")),
        "legal_status": _first_list(ps.get("patentDivAppLegalStat")),
    }

    # --- recruitment ---
    rp = raw.get("rec_profile") or {}
    recruitment = {
        "current": _int(rp.get("recruitingCurrentCount"))
        if isinstance(rp, dict)
        else None,
        "last_3m": _int(rp.get("recruitingLastThreeMonthCount"))
        if isinstance(rp, dict)
        else None,
        "avg_salary": rp.get("recruitingAvgWorkingSalary")
        if isinstance(rp, dict)
        else None,
        "welfare": _first_list(rp.get("recruitingWelfareList") or rp.get("welfareList"))
        if isinstance(rp, dict)
        else [],
    }

    return _wrap(
        resolved,
        errors,
        "live",
        enterprise=resolved.get("enterprise", ""),
        base=base,
        holders=holders,
        investments=investments,
        persons=persons,
        risk=risk,
        operation=operation,
        patent=patent,
        recruitment=recruitment,
        pagination_payloads=raw.get("_pagination_payloads") or {},
        schema_limited=raw.get("_schema_limited") or {},
        detail_max_pages=raw.get("_detail_max_pages"),
        call_usage=raw.get("_call_usage") or {},
    )


def normalize_reports(
    reports: Mapping[str, Any], enterprise: str, *, resolved: bool = True
) -> Dict[str, Any]:
    """Normalize cached atomic report JSONs into the unified structure (dry-run)."""
    er = reports.get("enterprise-report", {}) if isinstance(reports, dict) else {}
    rr = reports.get("enterprise-risk-report", {}) if isinstance(reports, dict) else {}
    opr = (
        reports.get("enterprise-operation-report", {})
        if isinstance(reports, dict)
        else {}
    )
    pr = reports.get("patent-report", {}) if isinstance(reports, dict) else {}
    recr = reports.get("recruitment-report", {}) if isinstance(reports, dict) else {}

    def _ca(report: Mapping[str, Any]) -> Mapping[str, Any]:
        return report.get("core_analysis", {}) if isinstance(report, dict) else {}

    # enterprise
    ec = _ca(er)
    base = (
        _kv_to_dict(ec.get("enterprise_base"))
        if isinstance(ec.get("enterprise_base"), list)
        else (ec.get("enterprise_base") or {})
    )
    # 补充 metrics 里的资本充实性字段（enterprise_base KV 可能不含实缴率）
    for mlabel, bkey in [
        ("资本实缴率", "资本实缴率"),
        ("注册资本", "注册资本"),
        ("实缴资本", "实缴资本"),
    ]:
        mv = _metric_value(er, mlabel)
        if mv and not base.get(bkey):
            base[bkey] = mv
    holders = ec.get("holders") or []
    investments = ec.get("investments") or []
    persons = ec.get("key_persons") or []

    # risk
    rc = _ca(rr)
    risk = {
        "score": _metric_int(rr, "风险评分"),
        "level": _metric_value(rr, "风险等级"),
        "credit_level": None,
        "oper_level": None,
        "litigation_level": None,
        "litigation": _kv_to_dict(rc.get("litigation_overview")),
        "court_hearings": rc.get("court_hearings") or [],
        "penalties": rc.get("penalties") or [],
        "anomalies": rc.get("business_anomalies") or [],
        "restrictions": rc.get("consumption_restrictions") or [],
        "mortgages": rc.get("chattel_mortgage") or [],
    }

    # operation
    opc = _ca(opr)
    operation = {
        "scale": _kv_to_dict(opc.get("business_scale")),
        "financing_count": _metric_int(opr, "融资次数"),
        "financing_list": opc.get("financing_info") or [],
        "trends": _kv_to_dict(opc.get("company_trends")),
        "rankings": opc.get("enterprise_rankings") or [],
    }

    # patent
    patent = {
        "total": _metric_int(pr, "专利总数"),
        "invention_app": _metric_int(pr, "发明申请"),
        "invention_lic": _metric_int(pr, "发明授权"),
        "utility": None,
        "design": _metric_int(pr, "外观设计"),
        "apply_trend": _ca(pr).get("apply_trend") or [],
    }

    # recruitment
    recc = _ca(recr)
    recruitment = {
        "current": _metric_int(recr, "当前招聘人数"),
        "last_3m": _metric_int(recr, "近三月招聘人数"),
        "avg_salary": _metric_value(recr, "平均薪酬"),
        "welfare": recc.get("benefit_tags") or [],
    }

    resolved_meta = {
        "keyword": enterprise,
        "enterprise": enterprise,
        "resolved": resolved,
        "reason": "缓存报告（dry-run）" if not resolved else "已有报告",
    }
    return _wrap(
        resolved_meta,
        {},
        "cache",
        enterprise=enterprise,
        base=base,
        holders=holders,
        investments=investments,
        persons=persons,
        risk=risk,
        operation=operation,
        patent=patent,
        recruitment=recruitment,
    )


def _kv_to_dict(value: Any) -> Dict[str, Any]:
    """Convert a [{字段/名称, 内容/值}] KV list (report style) to a plain dict."""
    out: Dict[str, Any] = {}
    if isinstance(value, list):
        for row in value:
            if isinstance(row, dict):
                k = (
                    row.get("字段")
                    or row.get("名称")
                    or row.get("指标")
                    or row.get("维度")
                    or ""
                )
                v = (
                    row.get("内容")
                    or row.get("值")
                    or row.get("数量")
                    or row.get("占比")
                    or row.get("值/说明")
                    or ""
                )
                if k:
                    out[str(k)] = v
    elif isinstance(value, dict):
        out = dict(value)
    return out


def _wrap(
    resolved: Mapping[str, Any], errors: Mapping[str, Any], source: str, **domain: Any
) -> Dict[str, Any]:
    enterprise = domain.pop("enterprise", resolved.get("enterprise", ""))
    pagination_payloads = domain.pop("pagination_payloads", {})
    schema_limited = domain.pop("schema_limited", {})
    detail_max_pages = domain.pop("detail_max_pages", None)
    call_usage = domain.pop("call_usage", {})
    return {
        "_meta": {
            "enterprise": enterprise,
            "resolved": dict(resolved),
            "source": source,  # "live" | "cache"
            "errors": dict(errors),
            "pagination_payloads": dict(pagination_payloads),
            "schema_limited": dict(schema_limited),
            "detail_max_pages": detail_max_pages,
            "call_usage": dict(call_usage),
        },
        "enterprise": {
            "base": domain.get("base", {}),
            "holders": domain.get("holders", []),
            "investments": domain.get("investments", []),
            "persons": domain.get("persons", []),
        },
        "risk": domain.get("risk", {}),
        "operation": domain.get("operation", {}),
        "patent": domain.get("patent", {}),
        "recruitment": domain.get("recruitment", {}),
    }


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def collect_direct(
    enterprise: str, keyword_type: str, *, dry_run: bool, skills_root: str,
    detail_max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Collect multi-source data: live MCP (default) or cached reports (dry-run).

    *detail_max_pages* bounds the paid detail pages per paginated interface in
    live mode (default: one page, DEFAULT_DETAIL_MAX_PAGES); non-positive
    values are rejected before any real call.
    """
    if dry_run:
        return _collect_cache(skills_root, enterprise)
    try:
        return asyncio.run(_collect_live(enterprise, keyword_type, detail_max_pages=detail_max_pages))
    except MultiMcpError as exc:
        # No MCP connection available — gracefully degrade to cached reports.
        print(
            f"⚠️  MCP 连接不可用 ({exc})，回退到缓存报告模式",
            file=__import__("sys").stderr,
        )
        return _collect_cache(skills_root, enterprise)
