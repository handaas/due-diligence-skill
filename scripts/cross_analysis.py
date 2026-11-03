#!/usr/bin/env python3
"""Cross-domain analysis engine for due-diligence reports.

Consumes the unified NormalizedData from mcp_orchestration and produces
cross-dimensional insights that NO single atomic skill can generate on its own:

  1. 资本充实性     — 实缴率 × 信用风险等级
  2. 风险传导敞口   — 对外投资广度 × 股权集中度 × 自身风险评分 / 诉讼结构
  3. 创新经营匹配   — 专利储备 × 经营规模 × 融资轮次 → 企业类型判定
  4. 扩张风险张力   — 招聘/融资/异地中标扩张信号 × 诉讼/合规风险趋势
  5. 尽调专项评分   — 资本充实性 / 风险隔离度 / 合规健康度 / 经营稳健性
  6. 尽调结论       — 综合判定 + 关键关注点

All evidence is grounded in actual data; missing dimensions are skipped (never
fabricated).
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Optional


# --------------------------------------------------------------------------- #
# Tolerant field extraction (handles both live MCP and cached report shapes)
# --------------------------------------------------------------------------- #
def source_ratio_percent(value: Any) -> Optional[Decimal]:
    """Return a percentage as Decimal without rounding; None when unavailable.

    Accepts a 0-1 fraction, an already-percent number, a '12.3456%' string,
    or a dict. Zero is a real value; only missing/invalid input returns None.
    """
    if isinstance(value, dict):
        value = value.get("value", value.get("ratio", value.get("percent")))
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text or text in {"-", "—"}:
        return None
    if "%" in text:
        text = text.replace("%", "").strip()
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if number != 0 and abs(number) <= 1:
        number *= 100
    return number


def format_source_ratio(value: Any) -> str:
    """Render an upstream ratio without rounding, zero-padding, or unit guessing.

    A percent string such as '12.3400%' is returned verbatim. Numeric 0-1
    fractions keep their original significant digits (0.123456 -> 12.3456%).
    Zero renders as '0%'; missing or invalid values render as '-'.
    """
    if isinstance(value, dict):
        value = value.get("value", value.get("ratio", value.get("percent")))
    if value is None:
        return "-"
    text = str(value).strip()
    if not text or text in {"-", "—"}:
        return "-"
    if "%" in text:
        return text
    number = source_ratio_percent(value)
    if number is None:
        return text
    return f"{format(number.normalize(), 'f')}%"


def _pick(d: Any, *keys: str) -> Any:
    if not isinstance(d, dict):
        return None
    for k in keys:
        v = d.get(k)
        if v not in (None, "", "-", []):
            return v
    return None


def _f(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(
            str(value)
            .replace(",", "")
            .replace("万", "")
            .replace("%", "")
            .replace("亿", "")
        )
    except (TypeError, ValueError):
        return None


def _i(value: Any) -> Optional[int]:
    f = _f(value)
    return int(f) if f is not None else None


def _ratio_pct(value: Any) -> Optional[float]:
    """Parse '67%' / '0.67' / 67 into a 0-100 percentage."""
    if value is None:
        return None
    s = str(value).strip()
    if "%" in s:
        try:
            return float(s.replace("%", "").strip())
        except ValueError:
            return None
    f = _f(value)
    if f is None:
        return None
    return f * 100 if f <= 1 else f


# --------------------------------------------------------------------------- #
# Data accessors
# --------------------------------------------------------------------------- #
def _holders(data: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return list(data.get("enterprise", {}).get("holders") or [])


def _investments(data: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return list(data.get("enterprise", {}).get("investments") or [])


def _base(data: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(data.get("enterprise", {}).get("base") or {})


def _risk(data: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(data.get("risk") or {})


def _litigation(data: Mapping[str, Any]) -> Dict[str, Any]:
    lit = _risk(data).get("litigation") or {}
    return lit if isinstance(lit, dict) else {}


def _litigation_summary(data: Mapping[str, Any]) -> Dict[str, Any]:
    risk = _risk(data)
    lit = _litigation(data)
    hearings = _i(risk.get("court_hearings_total"))
    executed = _i(risk.get("restrictions_total"))
    case_count = _i(lit.get("case_count") or lit.get("caseCount"))
    defendant = _i(lit.get("as_defendant") or lit.get("asDefendant"))
    plaintiff = _i(lit.get("as_plaintiff") or lit.get("asPlaintiff"))
    announcements = _i(lit.get("法院公告数"))
    judgments = _i(lit.get("裁判文书数"))
    dishonest = _i(lit.get("失信被执行人数"))
    known = any(
        v is not None and v > 0
        for v in (
            hearings,
            executed,
            case_count,
            defendant,
            plaintiff,
            announcements,
            judgments,
            dishonest,
        )
    ) or bool(risk.get("level"))
    if not known:
        return {
            "case_count": None,
            "as_defendant": None,
            "as_plaintiff": None,
            "hearings": None,
            "announcements": None,
            "judgments": None,
            "executed": None,
            "dishonest": None,
            "has_role_detail": False,
        }
    if case_count is None:
        case_count = hearings
    return {
        "case_count": case_count,
        "as_defendant": defendant,
        "as_plaintiff": plaintiff,
        "hearings": hearings,
        "announcements": announcements,
        "judgments": judgments,
        "executed": executed,
        "dishonest": dishonest,
        "has_role_detail": defendant is not None or plaintiff is not None,
    }


def _operation(data: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(data.get("operation") or {})


def _patent(data: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(data.get("patent") or {})


def _recruitment(data: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(data.get("recruitment") or {})


def _risk_evidence_known(data: Mapping[str, Any]) -> bool:
    """Distinguish an explicitly queried risk result from an empty/failed domain."""
    risk = _risk(data)
    marker = risk.get("_evidence_known")
    if marker is not None:
        return marker is True
    if risk.get("score") is not None or risk.get("level") not in (None, "", "-"):
        return True
    return any(
        risk.get(key) is not None
        for key in (
            "court_hearings_total",
            "restrictions_total",
            "penalties_total",
            "anomalies_total",
        )
    )


# --------------------------------------------------------------------------- #
# Specialty scores (each 0-100, or None if data unavailable)
# --------------------------------------------------------------------------- #
def score_capital_adequacy(data: Mapping[str, Any]) -> Optional[float]:
    """资本充实性: 实缴率 driven, penalized by credit risk."""
    base = _base(data)
    paid_rate = _ratio_pct(_pick(base, "资本实缴率", "实缴率", "paidRate", "paidRatio"))
    if paid_rate is None:
        reg = _f(_pick(base, "注册资本", "regCapital", "regCapitalValue"))
        paid = _f(_pick(base, "实缴资本", "realCapital", "paidInCapital"))
        if reg and paid is not None and reg > 0:
            paid_rate = paid / reg * 100
    if paid_rate is None:
        return None
    if paid_rate >= 80:
        s = 90 + min(10, (paid_rate - 80) * 0.5)
    elif paid_rate >= 50:
        s = 65 + (paid_rate - 50) * 0.8
    elif paid_rate >= 20:
        s = 35 + (paid_rate - 20) * 1.0
    else:
        s = paid_rate * 1.5
    # 实缴数据为估算时降权（置信度折扣）
    if (
        _pick(base, "资本实缴率", "实缴率") is None
        and _pick(base, "实缴资本", "realCapital", "paidInCapital") is None
    ):
        s = min(s, 60)  # 估算值封顶 60 分
    credit = str(_risk(data).get("credit_level") or "").strip()
    if credit and ("高" in credit or "严重" in credit):
        s -= 20
    elif credit and ("中" in credit):
        s -= 8
    return round(max(0, min(100, s)), 1)


def score_risk_isolation(data: Mapping[str, Any]) -> Optional[float]:
    if not _risk_evidence_known(data):
        return None
    risk = _risk(data)
    inv_total = _i(risk.get("investments_total"))
    hearings = _i(risk.get("court_hearings_total"))
    restrictions = _i(risk.get("restrictions_total"))
    if all(v is None for v in (inv_total, hearings, restrictions)):
        return None
    exposure = (
        min(35, (inv_total or 0) / 5)
        + min(45, (hearings or 0) / 10)
        + min(60, (restrictions or 0) * 12)
    )
    return round(max(0, 100 - exposure), 1)


def score_compliance_health(data: Mapping[str, Any]) -> Optional[float]:
    if not _risk_evidence_known(data):
        return None
    risk = _risk(data)
    hearings = _i(risk.get("court_hearings_total"))
    restrictions = _i(risk.get("restrictions_total"))
    penalties = _i(risk.get("penalties_total"))
    anomalies = _i(risk.get("anomalies_total"))
    if all(v is None for v in (hearings, restrictions, penalties, anomalies)):
        return None
    exposure = (
        min(60, (hearings or 0) / 5)
        + min(50, (restrictions or 0) * 10)
        + min(30, (penalties or 0) * 10)
        + min(20, (anomalies or 0) * 5)
    )
    return round(max(0, 100 - exposure), 1)


def score_operation_stability(data: Mapping[str, Any]) -> Optional[float]:
    """经营公开线索: 规模 + 融资 + 招聘 + 趋势，不混入方向未知的上游风险分."""
    op = _operation(data)
    rec = _recruitment(data)
    scale = op.get("scale") or {}
    has_scale = bool(
        _pick(scale, "staff", "人员规模", "enterpriseScale")
        or _pick(scale, "turnover", "年营业额", "annualTurnover")
    )
    fin_n = _i(op.get("financing_count")) or 0
    cur_hire = _i(rec.get("current")) or 0
    trends = op.get("trends") or {}
    expand_signals = sum(
        1 for k, v in trends.items() if str(k).startswith("is") and str(v) == "1"
    )
    if not (has_scale or fin_n or cur_hire or expand_signals):
        return None
    s = 0.0
    s += 25 if has_scale else 0
    s += min(20, fin_n * 7)
    s += min(20, 8 if cur_hire > 0 else 0) + min(12, cur_hire / 10 if cur_hire else 0)
    s += min(10, expand_signals * 3)
    return round(max(0, min(100, s)), 1)


def specialty_scores(data: Mapping[str, Any]) -> Dict[str, Any]:
    items = [
        ("capital_adequacy", "资本充实性", score_capital_adequacy(data)),
        ("risk_isolation", "风险隔离度", score_risk_isolation(data)),
        ("compliance_health", "合规健康度", score_compliance_health(data)),
        ("operation_stability", "经营公开线索", score_operation_stability(data)),
    ]
    valid = [(key, label, value) for key, label, value in items if value is not None]
    meta = data.get("_meta") or {}
    resolved_meta = meta.get("resolved") or {}
    canon = str(resolved_meta.get("enterprise") or "").strip()
    base = _base(data)
    base_name = str(_pick(base, "企业名称", "name", "名称") or "").strip()
    code = str(
        _pick(base, "统一社会信用代码", "socialCreditCode", "信用代码") or ""
    ).strip()
    subject_ok = (
        base_name not in ("", "-")
        and code not in ("", "-")
        and (not canon or base_name == canon)
    )
    risk = _risk(data)
    hearings = _i(risk.get("court_hearings_total"))
    restrictions = _i(risk.get("restrictions_total"))
    level = str(risk.get("level") or "")
    risk_known = (hearings is not None or restrictions is not None) and bool(
        level or (hearings or 0) > 0 or (restrictions or 0) > 0
    )
    judicial_clear = (
        hearings is not None and hearings < 100 and (restrictions or 0) == 0
    )
    supply_ok = True
    eligible = (
        subject_ok
        and not meta.get("errors")
        and risk_known
        and judicial_clear
        and supply_ok
        and len(valid) >= 3
    )
    avg = (
        round(sum(value for _, _, value in valid) / len(valid), 1) if eligible else None
    )
    return {
        "items": items,
        "valid": valid,
        "average": avg,
        "rating_eligible": eligible,
        "minimum_domains": 3,
        "gate_reason": None if eligible else "主体、关键域或司法风险门禁未满足",
    }


def insight_capital_risk(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    score = score_capital_adequacy(data)
    if score is None:
        return None
    base = _base(data)
    rate = _ratio_pct(_pick(base, "资本实缴率", "实缴率"))
    if rate is None:
        reg = _f(_pick(base, "注册资本", "regCapital", "regCapitalValue"))
        paid = _f(_pick(base, "实缴资本", "realCapital", "paidInCapital"))
        rate = paid / reg * 100 if reg and paid is not None and reg > 0 else None
    credit = _risk(data).get("credit_level") or "-"
    level = "充足" if score >= 70 else ("一般" if score >= 40 else "薄弱")
    rate_text = f"{rate:.0f}%" if rate is not None else "未知"
    evidence = f"资本充实性观察值 {score}（{level}），实缴率约 {rate_text}，信用风险等级「{credit}」。"
    if score < 40:
        interp = "实缴资本远低于注册资本，叠加信用风险，存在资本充实性瑕疵。建议核查股东实缴到位情况与出资期限，评估补缴能力。"
    elif score < 70:
        interp = "实缴资本部分到位，资本充实性中等。建议关注认缴出资期限是否临近、是否有抽逃出资迹象。"
    else:
        interp = "工商实缴比例较高；该公开字段不等于现金流、偿债能力或股东未来履约能力，仍需财务审计。"
    return {
        "feature": "资本充实性与信用风险",
        "evidence": evidence,
        "interpretation": interp,
    }


def insight_risk_contagion(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    if not _risk_evidence_known(data):
        return None
    risk = _risk(data)
    inv_total = _i(risk.get("investments_total"))
    shown = len(_investment_rows(data))
    ls = _litigation_summary(data)
    hearings = ls["hearings"]
    restrictions = ls["executed"]
    if inv_total is None and hearings is None and restrictions is None:
        return None
    parts = []
    if inv_total is not None:
        parts.append(f"对外投资总量 {inv_total} 家（当前报告展示 {shown} 家）")
    if hearings is not None:
        parts.append(f"开庭公告 {hearings} 条")
    if restrictions is not None:
        parts.append(f"限制高消费 {restrictions} 条")
    severe = (hearings or 0) >= 100 or (restrictions or 0) > 0
    interpretation = (
        "司法暴露达到人工核验门禁，不予综合评级；需按案由、时间、标的金额和主体相关性复核。"
        if severe
        else "关联投资与司法记录仅反映暴露面，不能据展示样本推断全部关联方受牵连。"
    )
    return {
        "feature": "关联投资与司法暴露",
        "evidence": "，".join(parts) + "。",
        "interpretation": interpretation,
    }


def insight_innovation_operation(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    patent = _patent(data)
    total = _i(patent.get("total"))
    inv_app = _i(patent.get("invention_app"))
    inv_lic = _i(patent.get("invention_lic"))
    op = _operation(data)
    fin_n = _i(op.get("financing_count")) or 0
    scale = op.get("scale") or {}
    has_scale = bool(
        _pick(scale, "staff", "人员规模", "enterpriseScale")
        or _pick(scale, "turnover", "年营业额", "annualTurnover")
    )
    if total is None and fin_n == 0 and not has_scale:
        return None
    patent_parts = []
    if total is not None:
        patent_parts.append(f"专利统计 {total} 件")
    if total and (inv_app is not None or inv_lic is not None):
        inv_share = ((inv_app or 0) + (inv_lic or 0)) / total * 100
        patent_parts.append(f"发明申请/授权数量占比约 {inv_share:.0f}%")
    fin_clause = f"已完成 {fin_n} 轮融资、" if fin_n else ""
    scale_clause = "经营规模字段已返回、" if has_scale else ""
    evidence = (
        "、".join(patent_parts)
        + ("；" if patent_parts else "")
        + fin_clause
        + scale_clause
    )
    evidence = evidence.rstrip("、；") + "。"
    interp = "专利数量、类型占比、融资和经营规模仅为并存事实；缺少权属、有效性、研发投入、收入转化和同行分母，不能判定企业类型、研发强弱或技术竞争力；需逐项核验。"
    return {
        "feature": "专利、融资与经营公开事实",
        "evidence": evidence,
        "interpretation": interp,
    }


def insight_expansion_risk(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    op = _operation(data)
    rec = _recruitment(data)
    trends = op.get("trends") or {}
    current = _i(rec.get("current"))
    active = (
        [k for k, v in trends.items() if str(k).startswith("is") and str(v) == "1"]
        if isinstance(trends, dict)
        else []
    )
    risk_known = _risk_evidence_known(data)
    hearings = _i(_risk(data).get("court_hearings_total")) if risk_known else None
    restrictions = _i(_risk(data).get("restrictions_total")) if risk_known else None
    if not active and current is None and hearings is None and restrictions is None:
        return None
    evidence = f"经营趋势命中 {len(active)} 项；当前招聘 {current if current is not None else '未知'}；开庭 {hearings if hearings is not None else '未知'}；限高 {restrictions if restrictions is not None else '未知'}。"
    if (hearings or 0) >= 100 or (restrictions or 0) > 0:
        interp = "存在扩张活动线索，但司法暴露触发人工核验门禁，不能解释为稳健扩张或风险可控。"
    else:
        interp = "经营与招聘仅为公开活动线索；缺少现金流、负债和统一观察窗口，不能评价扩张稳健性。"
    return {
        "feature": "扩张活动与司法暴露",
        "evidence": evidence,
        "interpretation": interp,
    }


def insight_litigation_structure(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    if not _risk_evidence_known(data):
        return None
    s = _litigation_summary(data)
    hearings = s["hearings"]
    restrictions = s["executed"]
    if hearings is None and restrictions is None:
        return None
    parts = []
    if hearings is not None:
        parts.append(f"开庭公告 {hearings} 条")
    if restrictions is not None:
        parts.append(f"限制高消费 {restrictions} 条")
    if (hearings or 0) >= 100 or (restrictions or 0) > 0:
        interp = "司法暴露触发人工核验门禁；展示数量不代表案件去重后数量，需核验日期、案号、案由、标的和主体关联。"
    else:
        interp = "仅列示司法公开记录，不因数量较少直接认定低风险或风险可控。"
    return {
        "feature": "司法记录核验",
        "evidence": "、".join(parts) + "。",
        "interpretation": interp,
    }


def _holder_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for h in _holders(data)[:15]:
        ratio = _pick(h, "持股比例", "ratio", "占比")
        sub = _pick(h, "认缴金额", "subscriptionDetail", "认缴", "认缴/实缴")
        if isinstance(sub, dict):
            sub = sub.get("amount") or sub.get("value")
        paid = _pick(h, "实缴金额", "payAmount", "实缴", "paidAmount", "认缴/实缴")
        rows.append(
            {
                "股东名称": str(
                    _pick(h, "股东名称", "name", "名称", "holderName") or "-"
                ),
                "持股比例": format_source_ratio(ratio),
                "认缴金额": _amount_text(sub),
                "实缴金额": _amount_text(paid),
                "股东类型": str(
                    _pick(h, "股东类型", "holderType", "entityType") or "-"
                ),
            }
        )
    return rows


def _amount_text(value: Any) -> str:
    """Readable amount for holder/investment tables (handles JSON amount dicts)."""
    if value in (None, "", "-"):
        return "-"
    if isinstance(value, dict):
        val = value.get("value") or value.get("amount")
        coin = value.get("coinType") or ""
        if val is None:
            return "-"
        try:
            fv = float(val)
            if fv >= 1e8:
                return f"{coin} {fv / 1e8:.2f}亿".strip()
            if fv >= 1e4:
                return f"{coin} {fv / 1e4:.0f}万".strip()
            return f"{coin} {fv:.0f}".strip()
        except (TypeError, ValueError):
            return f"{coin} {val}".strip()
    # bare number string
    try:
        fv = float(str(value).replace(",", ""))
        if fv >= 1e8:
            return f"人民币 {fv / 1e8:.2f}亿"
        if fv >= 1e4:
            return f"人民币 {fv / 1e4:.0f}万"
        return f"人民币 {fv:.0f}"
    except (TypeError, ValueError):
        return str(value)


def _clean_amount(value: Any) -> str:
    """Parse a possibly-JSON amount field (e.g. {"coinType":"人民币","value":1e7}) into readable text."""
    if not value or value == "-":
        return "-"
    s = str(value).strip()
    if s.startswith("{"):
        try:
            d = json.loads(s)
            val = d.get("value")
            coin = d.get("coinType") or d.get("currency") or ""
            if val is not None:
                try:
                    fv = float(val)
                    return (
                        f"{coin} {fv / 10000:.0f}万".strip()
                        if fv >= 10000
                        else f"{coin} {fv:.0f}".strip()
                    )
                except (TypeError, ValueError):
                    return f"{coin} {val}".strip()
        except Exception:
            pass
    return s


def _investment_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for inv in _investments(data)[:15]:
        iratio = _pick(inv, "ratio", "持股比例", "占股比例", "投资比例")
        rows.append(
            {
                "被投资企业": str(
                    _pick(inv, "name", "企业名称", "对外投资企业", "被投资企业") or "-"
                ),
                "持股比例": format_source_ratio(iratio),
                "经营状态": str(_pick(inv, "operStatus", "经营状态", "状态") or "-"),
                "成立日期": str(_pick(inv, "foundTime", "成立日期", "成立时间") or "-"),
                "注册资本": _amount_text(
                    _pick(
                        inv, "subscriptionAmount", "投资金额", "regCapital", "注册资本"
                    )
                ),
            }
        )
    return rows


def _litigation_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    s = _litigation_summary(data)
    rows = []
    if s["case_count"] is not None:
        rows.append({"诉讼维度": "案件/公告总数", "数值": str(s["case_count"])})
    for label, v in [
        ("作为被告", s["as_defendant"]),
        ("作为原告", s["as_plaintiff"]),
        ("开庭公告", s["hearings"]),
        ("法院公告", s["announcements"]),
        ("裁判文书", s["judgments"]),
        ("被执行人", s["executed"]),
        ("失信被执行", s["dishonest"]),
    ]:
        if v is not None:
            rows.append({"诉讼维度": label, "数值": str(v)})
    return rows


def _specialty_score_rows(scores: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for _key, label, v in scores.get("items", []):
        if v is not None:
            grade = (
                "优" if v >= 75 else ("良" if v >= 55 else ("中" if v >= 35 else "弱"))
            )
            rows.append({"评估维度": label, "评分": str(v), "等级": grade})
    return rows


# --------------------------------------------------------------------------- #
# Verdict
# --------------------------------------------------------------------------- #
def build_verdict(data: Mapping[str, Any], scores: Mapping[str, Any]) -> Dict[str, Any]:
    risk = _risk(data)
    concerns: List[str] = []
    blockers: List[str] = []

    n_vio = len(risk.get("serious_violations") or [])
    n_res = risk.get("restrictions_total") or len(risk.get("restrictions") or [])
    n_pen = risk.get("penalties_total") or len(risk.get("penalties") or [])
    n_ano = risk.get("anomalies_total") or len(risk.get("anomalies") or [])
    risk_level_text = str(risk.get("level") or "")

    if n_vio:
        blockers.append(f"严重违法记录 {n_vio} 条")
    if n_res:
        blockers.append(f"限制高消费记录 {n_res} 条")
    if n_pen >= 3:
        concerns.append(f"行政处罚 {n_pen} 条")
    if n_ano:
        concerns.append(f"经营异常 {n_ano} 条")
    hearings = _i(risk.get("court_hearings_total"))
    if hearings is not None and hearings >= 100:
        blockers.append(f"开庭公告 {hearings} 条，需人工司法核验")
    elif hearings:
        concerns.append(f"开庭公告 {hearings} 条")
    # 风险判断：优先采信风险等级文本，回退到数值
    if risk_level_text:
        if "高" in risk_level_text or "严重" in risk_level_text:
            blockers.append(f"风险等级「{risk_level_text}」")
        elif "中" in risk_level_text:
            concerns.append(f"风险等级「{risk_level_text}」")

    capital = score_capital_adequacy(data)
    if capital is not None and capital < 40:
        concerns.append("资本充实性薄弱")

    avg = scores.get("average")
    if avg is None:
        level = "不予综合评级" if blockers else "数据不足"
        recommendation = "人工司法核验" if blockers else "需补充数据"
        evidence_note = (
            "、".join((blockers + concerns)[:4]) or "主体确认、关键域或工具调用证据不足"
        )
        summary = f"评级门禁未满足，不予综合评级。需核验：{evidence_note}。"
    elif blockers:
        level = "不建议合作"
        recommendation = "不建议合作" if len(blockers) >= 2 else "需深入调查"
        summary = f"发现 {len(blockers)} 项重大风险阻断项（{'、'.join(blockers)}），建议审慎决策或补充尽调。"
    elif avg is not None and avg >= 72 and not concerns:
        level = "建议通过"
        recommendation = "建议通过"
        summary = f"尽调专项评分均值 {avg}，各维度表现稳健，未见重大风险信号。"
    elif avg is not None and avg >= 50:
        level = "附条件通过"
        recommendation = "附条件通过"
        summary = f"尽调专项评分均值 {avg}，存在 {len(concerns)} 项需关注事项（{'、'.join(concerns[:3])}），建议设置风险缓释条款。"
    elif avg is not None:
        level = "需深入调查"
        recommendation = "需深入调查"
        summary = f"尽调专项评分均值 {avg} 偏低，建议补充财务、法务、业务多维深度调查。"
    else:
        level = "数据不足"
        recommendation = "需补充数据"
        summary = "多维数据覆盖不足，无法形成充分尽调结论，建议补充更多维度数据。"

    return {
        "recommendation": recommendation,
        "level": level,
        "summary": summary,
        "blockers": blockers,
        "key_concerns": concerns[:6],
        "specialty_average": avg,
    }


# --------------------------------------------------------------------------- #
# Main entry
# --------------------------------------------------------------------------- #
def analyze(data: Mapping[str, Any]) -> Dict[str, Any]:
    """Run full cross-domain analysis, returning all artifacts for the report."""
    scores = specialty_scores(data)
    insight_fns = [
        insight_capital_risk,
        insight_risk_contagion,
        insight_innovation_operation,
        insight_expansion_risk,
        insight_litigation_structure,
    ]
    cross_insights: List[Dict[str, Any]] = []
    for fn in insight_fns:
        ins = fn(data)
        if ins:
            cross_insights.append(ins)

    verdict = build_verdict(data, scores)
    base = _base(data)

    # Cross metrics (top-level indicator cards)
    metrics: List[Dict[str, Any]] = []
    risk_score = _i(_risk(data).get("score"))
    if risk_score is not None:
        metrics.append(
            {
                "label": "上游风险评分",
                "value": str(risk_score),
                "hint": "上游评分；方向以同次返回等级为准",
                "delta": _risk(data).get("level") or "",
            }
        )
    inv_n = _risk(data).get("investments_total") or len(_investments(data))
    if inv_n:
        metrics.append(
            {
                "label": "对外投资",
                "value": str(inv_n),
                "hint": "关联方数量（风险传导面）",
            }
        )
    if scores.get("average") is not None:
        metrics.append(
            {
                "label": "尽调综合评分",
                "value": str(scores["average"]),
                "hint": f"{len(scores['valid'])} 项有效专项观察均值",
                "delta": verdict["level"],
            }
        )
    patent_total = _i(_patent(data).get("total"))
    if patent_total is not None:
        metrics.append(
            {
                "label": "专利储备",
                "value": str(patent_total),
                "hint": "创新实力基础指标",
            }
        )
    cur_hire = _i(_recruitment(data).get("current"))
    if cur_hire is not None:
        metrics.append(
            {"label": "在招岗位", "value": str(cur_hire), "hint": "扩张活跃度信号"}
        )
    reg = _pick(base, "注册资本", "regCapital", "regCapitalValue")
    if reg:
        metrics.append(
            {"label": "注册资本", "value": str(reg), "hint": "工商登记注册资本"}
        )
    holder_n = len(_holders(data))
    if holder_n:
        metrics.append(
            {"label": "股东数量", "value": str(holder_n), "hint": "工商公示股东数"}
        )
    found_year = _pick(base, "成立日期", "foundTime", "成立时间")
    if found_year and str(found_year)[:4].isdigit():
        import datetime as _dt

        age = _dt.datetime.now().year - int(str(found_year)[:4])
        if age >= 0:
            metrics.append(
                {
                    "label": "成立年限",
                    "value": f"{age} 年",
                    "hint": f"成立于 {str(found_year)[:4]} 年",
                }
            )
    # 风险计数指标（尽调核心信号）— 优先用 MCP total
    risk = _risk(data)
    res_n = risk.get("restrictions_total") or len(risk.get("restrictions") or [])
    if res_n:
        metrics.append(
            {
                "label": "限制高消费",
                "value": str(res_n),
                "hint": "被执行限高记录数",
                "delta": "▼" if res_n >= 5 else "",
            }
        )
    hearing_n = risk.get("court_hearings_total")
    if hearing_n:
        metrics.append(
            {"label": "开庭公告", "value": str(hearing_n), "hint": "诉讼开庭记录总数"}
        )
    pen_n = risk.get("penalties_total") or len(risk.get("penalties") or [])
    if pen_n:
        metrics.append(
            {"label": "行政处罚", "value": str(pen_n), "hint": "行政处罚记录数"}
        )
    ano_n = risk.get("anomalies_total") or len(risk.get("anomalies") or [])
    if ano_n:
        metrics.append(
            {"label": "经营异常", "value": str(ano_n), "hint": "经营异常名录记录"}
        )
    fin_n = _i(_operation(data).get("financing_count"))
    if fin_n:
        metrics.append(
            {"label": "融资轮次", "value": str(fin_n), "hint": "历史融资轮次"}
        )
    rank_n = len(_operation(data).get("rankings") or [])
    if rank_n:
        metrics.append(
            {"label": "上榜记录", "value": str(rank_n), "hint": "企业上榜次数"}
        )
    for _key, label, v in scores["valid"]:
        metrics.append({"label": label, "value": str(v), "hint": "尽调专项评分"})

    # Detail sections
    section_specs: List[Dict[str, Any]] = []
    section_data: Dict[str, Any] = {}

    holder_rows = _holder_rows(data)
    if holder_rows:
        section_specs.append(
            {
                "key": "dd_holders",
                "title": "股东出资结构",
                "kind": "table",
                "note": "股东持股比例与实缴情况（资本充实性核查基础）",
                "columns": [
                    ("股东名称", "股东名称"),
                    ("持股比例", "持股比例"),
                    ("认缴金额", "认缴金额"),
                    ("实缴金额", "实缴金额"),
                    ("股东类型", "股东类型"),
                ],
            }
        )
        section_data["dd_holders"] = holder_rows

    invest_rows = _investment_rows(data)
    if invest_rows:
        inv_total = _risk(data).get("investments_total") or len(_investments(data))
        section_specs.append(
            {
                "key": "dd_investments",
                "title": "对外投资清单（关联方敞口）",
                "kind": "table",
                "note": f"报告总量 {inv_total} 家，当前列表展示 {min(len(_investments(data)), 15)} 家；仅表示关联暴露面，未核验关联方风险传导",
                "columns": [
                    ("被投资企业", "被投资企业"),
                    ("持股比例", "持股比例"),
                    ("经营状态", "经营状态"),
                    ("成立日期", "成立日期"),
                    ("注册资本", "注册资本"),
                ],
            }
        )
        section_data["dd_investments"] = invest_rows

    lit_rows = _litigation_rows(data)
    if len(lit_rows) > 1:
        section_specs.append(
            {
                "key": "dd_litigation",
                "title": "诉讼风险结构",
                "kind": "table",
                "note": "按上游汇总字段列示事件类型及执行状态计数；不是事件级明细或去重结果，当事人角色仅在上游明确返回原告/被告计数时可见，否则未知",
                "columns": [("诉讼维度", "诉讼维度"), ("数值", "数值")],
            }
        )
        section_data["dd_litigation"] = lit_rows

    score_rows = _specialty_score_rows(scores)
    if score_rows:
        section_specs.append(
            {
                "key": "dd_specialty",
                "title": "尽调专项评分矩阵",
                "kind": "table",
                "note": "跨维度交叉评分（资本充实性 / 风险隔离度 / 合规健康度 / 经营稳健性）",
                "columns": [
                    ("评估维度", "评估维度"),
                    ("评分", "评分"),
                    ("等级", "等级"),
                ],
            }
        )
        section_data["dd_specialty"] = score_rows

    return {
        "metrics": metrics,
        "insights": cross_insights,
        "specialty_scores": {
            "items": [
                {"key": key, "label": label, "score": value}
                for key, label, value in scores["items"]
            ],
            "average": scores["average"],
        },
        "verdict": verdict,
        "section_specs": section_specs,
        "section_data": section_data,
    }
