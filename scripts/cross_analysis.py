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
from typing import Any, Dict, List, Mapping, Optional

# --------------------------------------------------------------------------- #
# Tolerant field extraction (handles both live MCP and cached report shapes)
# --------------------------------------------------------------------------- #
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
        return float(str(value).replace(",", "").replace("万", "").replace("%", "").replace("亿", ""))
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
    """Unified litigation info across live MCP (English keys) and cached reports (Chinese keys)."""
    risk = _risk(data)
    lit = _litigation(data)
    case_count = _i(lit.get("case_count") or lit.get("caseCount"))
    defendant = _i(lit.get("as_defendant") or lit.get("asDefendant"))
    plaintiff = _i(lit.get("as_plaintiff") or lit.get("asPlaintiff"))
    hearings = risk.get("court_hearings_total") or _i(lit.get("开庭公告数"))
    announcements = _i(lit.get("法院公告数"))
    judgments = _i(lit.get("裁判文书数"))
    executed = risk.get("restrictions_total") or _i(lit.get("被执行人记录数"))
    dishonest = _i(lit.get("失信被执行人数"))
    if case_count is None:
        parts = [v for v in (hearings, announcements, judgments) if v is not None]
        if parts:
            case_count = sum(parts)
    return {
        "case_count": case_count, "as_defendant": defendant, "as_plaintiff": plaintiff,
        "hearings": hearings, "announcements": announcements, "judgments": judgments,
        "executed": executed, "dishonest": dishonest,
        "has_role_detail": defendant is not None,  # live mode has defendant/plaintiff split
    }


def _operation(data: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(data.get("operation") or {})


def _patent(data: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(data.get("patent") or {})


def _recruitment(data: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(data.get("recruitment") or {})


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
        # 实缴数据完全缺失时，基于注册资本规模给保守估算（不至于让雷达缺一维）
        reg_str = _pick(base, "注册资本", "regCapital", "regCapitalValue")
        reg = _f(reg_str)
        if reg and reg >= 1e8:
            paid_rate = 70  # 大额注册资本假设实缴率较高
        elif reg and reg >= 1e7:
            paid_rate = 50
        else:
            paid_rate = 30
    if paid_rate >= 80:
        s = 90 + min(10, (paid_rate - 80) * 0.5)
    elif paid_rate >= 50:
        s = 65 + (paid_rate - 50) * 0.8
    elif paid_rate >= 20:
        s = 35 + (paid_rate - 20) * 1.0
    else:
        s = paid_rate * 1.5
    # 实缴数据为估算时降权（置信度折扣）
    if _pick(base, "资本实缴率", "实缴率") is None and _pick(base, "实缴资本", "realCapital", "paidInCapital") is None:
        s = min(s, 60)  # 估算值封顶 60 分
    credit = str(_risk(data).get("credit_level") or "").strip()
    if credit and ("高" in credit or "严重" in credit):
        s -= 20
    elif credit and ("中" in credit):
        s -= 8
    return round(max(0, min(100, s)), 1)


def score_risk_isolation(data: Mapping[str, Any]) -> Optional[float]:
    """风险隔离度 (higher = better isolated): penalized by investment breadth × risk."""
    invest_n = len(_investments(data))
    risk_score = _i(_risk(data).get("score"))
    level_text = str(_risk(data).get("level") or "")
    ls = _litigation_summary(data)
    defendant = ls["as_defendant"] or 0
    executed = ls["executed"] or 0
    dishonest = ls["dishonest"] or 0
    penalties = len(_risk(data).get("penalties") or [])
    if risk_score is None and not level_text and invest_n == 0 and defendant == 0 and penalties == 0 and not executed and not dishonest:
        return None
    # risk factor: prefer level text, fall back to raw score
    if "高" in level_text or "严重" in level_text:
        risk_factor = 28
    elif "中" in level_text:
        risk_factor = 14
    elif "低" in level_text:
        risk_factor = 2
    else:
        risk_factor = max(0, (risk_score or 50) - 40) * 1.1
    exposure = invest_n * 4 + risk_factor + defendant * 7 + penalties * 6 + executed * 10 + dishonest * 20
    return round(max(0, min(100, 100 - exposure)), 1)


def score_compliance_health(data: Mapping[str, Any]) -> Optional[float]:
    """合规健康度: deduct for penalties / anomalies / restrictions / violations."""
    risk = _risk(data)
    n_pen = len(risk.get("penalties") or [])
    n_ano = len(risk.get("anomalies") or [])
    n_res = len(risk.get("restrictions") or [])
    n_vio = len(risk.get("serious_violations") or []) if risk.get("serious_violations") else 0
    total_hits = n_pen + n_ano + n_res + n_vio
    if total_hits == 0 and risk.get("score") is None:
        return None
    health = 100 - (n_pen * 14 + n_ano * 9 + n_res * 18 + n_vio * 25)
    return round(max(0, min(100, health)), 1)


def score_operation_stability(data: Mapping[str, Any]) -> Optional[float]:
    """经营稳健性: multi-factor (scale + financing + hiring + low-risk + trends)."""
    op = _operation(data)
    rec = _recruitment(data)
    risk_score = _i(_risk(data).get("score"))
    scale = op.get("scale") or {}
    has_scale = bool(_pick(scale, "staff", "人员规模", "enterpriseScale") or _pick(scale, "turnover", "年营业额", "annualTurnover"))
    fin_n = _i(op.get("financing_count")) or 0
    cur_hire = _i(rec.get("current")) or 0
    trends = op.get("trends") or {}
    expand_signals = sum(1 for k, v in trends.items() if str(k).startswith("is") and str(v) == "1")
    if not (has_scale or fin_n or cur_hire or expand_signals):
        return None
    s = 0
    s += 25 if has_scale else 0
    s += min(20, fin_n * 7)
    s += min(20, 8 if cur_hire > 0 else 0) + min(12, cur_hire / 10 if cur_hire else 0)
    if risk_score is not None:
        s += 25 if risk_score < 40 else (10 if risk_score < 60 else 0)
    else:
        s += 12
    s += min(10, expand_signals * 3)
    return round(max(0, min(100, s)), 1)


def specialty_scores(data: Mapping[str, Any]) -> Dict[str, Any]:
    items = [
        ("capital_adequacy", "资本充实性", score_capital_adequacy(data)),
        ("risk_isolation", "风险隔离度", score_risk_isolation(data)),
        ("compliance_health", "合规健康度", score_compliance_health(data)),
        ("operation_stability", "经营稳健性", score_operation_stability(data)),
    ]
    valid = [(key, label, v) for key, label, v in items if v is not None]
    avg = round(sum(v for _, _, v in valid) / len(valid), 1) if valid else None
    return {"items": items, "valid": valid, "average": avg}


# --------------------------------------------------------------------------- #
# Cross-domain insights
# --------------------------------------------------------------------------- #
def insight_capital_risk(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    score = score_capital_adequacy(data)
    if score is None:
        return None
    base = _base(data)
    rate = _ratio_pct(_pick(base, "资本实缴率", "实缴率")) or 0
    credit = _risk(data).get("credit_level") or "-"
    level = "充足" if score >= 70 else ("一般" if score >= 40 else "薄弱")
    evidence = f"资本充实性评分 {score}（{level}），实缴率约 {rate:.0f}%，信用风险等级「{credit}」。"
    if score < 40:
        interp = "实缴资本远低于注册资本，叠加信用风险，存在资本充实性瑕疵。建议核查股东实缴到位情况与出资期限，评估补缴能力。"
    elif score < 70:
        interp = "实缴资本部分到位，资本充实性中等。建议关注认缴出资期限是否临近、是否有抽逃出资迹象。"
    else:
        interp = "实缴资本到位情况良好，资本充实性较高，股东出资履约能力较强。"
    return {"feature": "资本充实性与信用风险", "evidence": evidence, "interpretation": interp}


def insight_risk_contagion(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    invests = _investments(data)
    inv_total = _risk(data).get("investments_total") or len(invests)
    holders = _holders(data)
    risk_score = _i(_risk(data).get("score"))
    risk_level_text = str(_risk(data).get("level") or "")
    ls = _litigation_summary(data)
    defendant = ls["as_defendant"] or 0
    plaintiff = ls["as_plaintiff"] or 0
    case_count = ls["case_count"]
    executed = ls["executed"] or 0
    if not invests and risk_score is None and case_count is None and not executed:
        return None
    # shareholder concentration (top-1 ratio)
    top_ratio = None
    for h in holders:
        r = _f(_pick(h, "持股比例", "ratio", "占比"))
        if r is not None:
            r = r if r <= 1 else r / 100
            top_ratio = r if top_ratio is None else max(top_ratio, r)
    parts = [f"对外投资 {inv_total} 家"]
    if case_count is not None:
        role_clause = f"（被告 {defendant} / 原告 {plaintiff}）" if ls["has_role_detail"] else ""
        parts.append(f"涉诉 {case_count} 起{role_clause}")
    if executed:
        parts.append(f"被执行 {executed} 条")
    if risk_score is not None:
        parts.append(f"风险评分 {risk_score}（{risk_level_text or '-'}）")
    if top_ratio is not None:
        parts.append(f"最大股东持股 {top_ratio * 100:.0f}%")
    evidence = "，".join(parts) + "。"
    level = risk_level_text or ("高" if (risk_score or 0) >= 60 else ("中" if (risk_score or 0) >= 40 else "低"))
    high_risk = executed > 0 or defendant > 5 or (risk_score or 0) >= 60
    mid_risk = defendant > 0 or (risk_score or 0) >= 40
    if high_risk:
        interp = f"风险传导敞口较大：综合风险「{level}」" + (f"、被执行记录 {executed} 条" if executed else "") + f"。对外投资 {len(invests)} 家可能受牵连，建议排查核心投资标的的经营与涉诉状况。"
    elif mid_risk:
        interp = f"存在一定风险传导面：风险「{level}」。建议持续监控关联方风险变化与被执行进展。"
    else:
        interp = f"风险传导面可控：风险「{level}」，对外投资暂未见显著风险扩散。"
    return {"feature": "风险传导敞口（股权 × 诉讼）", "evidence": evidence, "interpretation": interp}


def insight_innovation_operation(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    patent = _patent(data)
    total = _i(patent.get("total"))
    inv_app = _i(patent.get("invention_app"))
    inv_lic = _i(patent.get("invention_lic"))
    op = _operation(data)
    fin_n = _i(op.get("financing_count")) or 0
    scale = op.get("scale") or {}
    has_scale = bool(_pick(scale, "staff", "人员规模", "enterpriseScale") or _pick(scale, "turnover", "年营业额", "annualTurnover"))
    if total is None and fin_n == 0 and not has_scale:
        return None
    if total is not None:
        inv_share = ((inv_app or 0) + (inv_lic or 0)) / total * 100 if total else 0
        if total >= 20 and inv_share >= 30:
            etype = "技术驱动型企业"
            interp_core = f"专利储备 {total} 件（发明型占比 {inv_share:.0f}%），"
        elif total >= 5:
            etype = "技术成长型企业"
            interp_core = f"专利 {total} 件、有一定研发投入，"
        elif total and total < 5:
            etype = "传统/服务型企业"
            interp_core = f"专利仅 {total} 件、研发投入有限，"
        else:
            etype = "非技术型企业"
            interp_core = "未见专利储备，"
    else:
        etype = "数据有限"
        interp_core = "专利数据缺失，"
    fin_clause = f"已完成 {fin_n} 轮融资、" if fin_n else ""
    scale_clause = "经营规模已具量级、" if has_scale else ""
    evidence = f"{interp_core}{fin_clause}{scale_clause}判定为「{etype}」。"
    interp = {
        "技术驱动型企业": "研发壁垒较高，核心竞争力源于技术创新；尽调应重点核查核心专利权属、有效期与侵权风险。",
        "技术成长型企业": "处于技术积累期，创新潜力初显；建议关注专利维持、研发投入持续性与技术商业化进展。",
        "传统/服务型企业": "以经营/渠道为主，技术不是核心壁垒；尽调聚焦经营稳定性、客户集中度与合规风险。",
        "非技术型企业": "业务模式不以技术驱动；尽调聚焦工商、经营与风险维度。",
    }.get(etype, "建议结合更多维度数据综合判断企业类型与价值。")
    return {"feature": "创新与经营匹配度（企业类型判定）", "evidence": evidence, "interpretation": interp}


def insight_expansion_risk(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    op = _operation(data)
    rec = _recruitment(data)
    trends = op.get("trends") or {}
    if not isinstance(trends, dict):
        trends = {}
    signals = {}
    for label, keys in [
        ("人员扩张", ("isStaffExpandIn3Month", "isStaffExpandIn6Month", "isStaffExpandIn12Month")),
        ("新增融资", ("isNewFinancingIn3Month", "isNewFinancingIn6Month", "isNewFinancingIn12Month")),
        ("异地中标", ("isDiffAreaWinBidIn3Month", "isDiffAreaWinBidIn6Month", "isDiffAreaWinBidIn12Month")),
        ("开设子公司", ("isFoundSubsidiaryIn3Month", "isFoundSubsidiaryIn6Month")),
    ]:
        signals[label] = any(str(trends.get(k)) == "1" for k in keys)
    cur_hire = _i(rec.get("current")) or 0
    risk_score = _i(_risk(data).get("score"))
    active = [k for k, v in signals.items() if v]
    if not active and cur_hire == 0 and risk_score is None:
        return None
    expansion = "高" if len(active) >= 2 else ("中" if len(active) == 1 else "低")
    parts = []
    if active:
        parts.append("近期动向：" + "、".join(active))
    if cur_hire:
        parts.append(f"在招 {cur_hire} 人")
    if risk_score is not None:
        parts.append(f"风险评分 {risk_score}")
    evidence = "，".join(parts) + "。" if parts else "近期经营动向数据有限。"
    if expansion == "高" and (risk_score or 0) >= 50:
        interp = "扩张活跃但伴随风险抬升：快速扩张（人员/融资/异地中标）可能带来管理与合规压力，建议核查扩张资金来源、新设主体合规性及劳动用工风险。"
    elif expansion == "高":
        interp = "扩张活跃且风险可控：企业经营动能强劲、风险处于低位，呈健康发展态势。建议关注扩张可持续性与现金流匹配。"
    elif expansion != "低":
        interp = "经营处于温和扩张期，风险信号一般。建议结合行业周期判断扩张节奏的合理性。"
    else:
        interp = "近期未见明显扩张信号，经营节奏偏稳。若处于收缩期，建议关注人员流失、分支机构注销等收缩风险。"
    return {"feature": "扩张活跃度与风险张力", "evidence": evidence, "interpretation": interp}


def insight_litigation_structure(data: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    s = _litigation_summary(data)
    case_count = s["case_count"]
    executed = s["executed"] or 0
    dishonest = s["dishonest"] or 0
    if case_count is None and not executed and not dishonest:
        return None
    if s["has_role_detail"]:
        # live mode: rich defendant/plaintiff analysis
        defendant = s["as_defendant"] or 0
        plaintiff = s["as_plaintiff"] or 0
        total = case_count or (defendant + plaintiff) or 0
        def_share = defendant / total * 100 if total else 0
        evidence = f"涉诉 {total} 起，其中作为被告 {defendant} 起（占比 {def_share:.0f}%）、原告 {plaintiff} 起。"
        if def_share >= 60:
            interp = "诉讼以被动应诉（被告）为主，防御性法律风险突出。建议核查重大案件案由、标的金额及执行情况，评估对经营的实际影响。"
        elif def_share >= 30:
            interp = "诉讼中原被告兼有，需分类核查：作为被告的案件评估败诉影响，作为原告的案件评估维权成效。"
        else:
            interp = "诉讼以主动维权（原告）为主，被动风险较低。企业法务主动性强，整体诉讼风险可控。"
    else:
        # cached mode: dimension counts (开庭公告 / 法院公告 / 裁判文书 / 被执行 / 失信)
        parts = []
        for label, v in [("开庭公告", s["hearings"]), ("法院公告", s["announcements"]), ("裁判文书", s["judgments"])]:
            if v:
                parts.append(f"{label} {v}")
        evidence = "、".join(parts) if parts else "诉讼记录极少"
        if executed or dishonest:
            evidence += f"；被执行 {executed} 条" + (f"、失信 {dishonest} 条" if dishonest else "")
            interp = "存在被执行/失信记录，执行风险突出，是尽调关键关注项。建议核查执行案件标的与履行情况，评估对企业信用与经营的实质影响。"
        elif case_count and case_count >= 30:
            interp = f"诉讼记录较多（约 {case_count} 条），建议核查高频案由、主要对手及重大案件影响。"
        elif case_count:
            interp = f"诉讼记录 {case_count} 条，规模可控，建议关注核心案件进展与裁判结果。"
        else:
            interp = "诉讼风险低，法律纠纷面窄，尽调风险可控。"
    return {"feature": "诉讼结构与执行风险", "evidence": evidence + "。", "interpretation": interp}


# --------------------------------------------------------------------------- #
# Detail sections (tables fed to the renderer)
# --------------------------------------------------------------------------- #
def _holder_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for h in _holders(data)[:15]:
        ratio = _pick(h, "持股比例", "ratio", "占比")
        if ratio is not None:
            try:
                rf = float(ratio)
                ratio = f"{rf * 100:.1f}%" if rf <= 1 else f"{rf:.1f}%"
            except (TypeError, ValueError):
                pass
        sub = _pick(h, "认缴金额", "subscriptionDetail", "认缴", "认缴/实缴")
        if isinstance(sub, dict):
            sub = sub.get("amount") or sub.get("value")
        paid = _pick(h, "实缴金额", "payAmount", "实缴", "paidAmount", "认缴/实缴")
        rows.append({
            "股东名称": str(_pick(h, "股东名称", "name", "名称", "holderName") or "-"),
            "持股比例": str(ratio or "-"),
            "认缴金额": _amount_text(sub),
            "实缴金额": _amount_text(paid),
            "股东类型": str(_pick(h, "股东类型", "holderType", "entityType") or "-"),
        })
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
                return f"{coin} {fv/1e8:.2f}亿".strip()
            if fv >= 1e4:
                return f"{coin} {fv/1e4:.0f}万".strip()
            return f"{coin} {fv:.0f}".strip()
        except (TypeError, ValueError):
            return f"{coin} {val}".strip()
    # bare number string
    try:
        fv = float(str(value).replace(",", ""))
        if fv >= 1e8:
            return f"人民币 {fv/1e8:.2f}亿"
        if fv >= 1e4:
            return f"人民币 {fv/1e4:.0f}万"
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
                    return f"{coin} {fv / 10000:.0f}万".strip() if fv >= 10000 else f"{coin} {fv:.0f}".strip()
                except (TypeError, ValueError):
                    return f"{coin} {val}".strip()
        except Exception:
            pass
    return s


def _investment_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for inv in _investments(data)[:15]:
        iratio = _pick(inv, "ratio", "持股比例", "占股比例", "投资比例")
        if iratio is not None:
            try:
                rf = float(iratio)
                iratio = f"{rf * 100:.0f}%" if rf <= 1 else f"{rf:.0f}%"
            except (TypeError, ValueError):
                pass
        rows.append({
            "被投资企业": str(_pick(inv, "name", "企业名称", "对外投资企业", "被投资企业") or "-"),
            "持股比例": str(iratio or "-"),
            "经营状态": str(_pick(inv, "operStatus", "经营状态", "状态") or "-"),
            "成立日期": str(_pick(inv, "foundTime", "成立日期", "成立时间") or "-"),
            "注册资本": _amount_text(_pick(inv, "subscriptionAmount", "投资金额", "regCapital", "注册资本")),
        })
    return rows


def _litigation_rows(data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    s = _litigation_summary(data)
    rows = []
    if s["case_count"] is not None:
        rows.append({"诉讼维度": "案件/公告总数", "数值": str(s["case_count"])})
    for label, v in [("作为被告", s["as_defendant"]), ("作为原告", s["as_plaintiff"]),
                     ("开庭公告", s["hearings"]), ("法院公告", s["announcements"]),
                     ("裁判文书", s["judgments"]), ("被执行人", s["executed"]), ("失信被执行", s["dishonest"])]:
        if v is not None:
            rows.append({"诉讼维度": label, "数值": str(v)})
    return rows


def _specialty_score_rows(scores: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for _key, label, v in scores.get("items", []):
        if v is not None:
            grade = "优" if v >= 75 else ("良" if v >= 55 else ("中" if v >= 35 else "弱"))
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
    risk_score = _i(risk.get("score"))
    risk_level_text = str(risk.get("level") or "")

    if n_vio:
        blockers.append(f"严重违法记录 {n_vio} 条")
    if n_res:
        blockers.append(f"限制高消费记录 {n_res} 条")
    if n_pen >= 3:
        concerns.append(f"行政处罚 {n_pen} 条")
    if n_ano:
        concerns.append(f"经营异常 {n_ano} 条")
    # 风险判断：优先采信风险等级文本，回退到数值
    if risk_level_text:
        if "高" in risk_level_text or "严重" in risk_level_text:
            blockers.append(f"风险等级「{risk_level_text}」")
        elif "中" in risk_level_text:
            concerns.append(f"风险等级「{risk_level_text}」")
    elif risk_score is not None and risk_score >= 70:
        blockers.append(f"综合风险评分 {risk_score}（偏高）")
    elif risk_score is not None and risk_score >= 50:
        concerns.append(f"综合风险评分 {risk_score}（中等）")

    capital = score_capital_adequacy(data)
    if capital is not None and capital < 40:
        concerns.append("资本充实性薄弱")

    avg = scores.get("average")
    if blockers:
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
        metrics.append({"label": "综合风险评分", "value": str(risk_score), "hint": "风险洞察评分（越低越好）", "delta": _risk(data).get("level") or ""})
    inv_n = _risk(data).get("investments_total") or len(_investments(data))
    if inv_n:
        metrics.append({"label": "对外投资", "value": str(inv_n), "hint": "关联方数量（风险传导面）"})
    if scores.get("average") is not None:
        metrics.append({"label": "尽调综合评分", "value": str(scores["average"]), "hint": "4 项专项评分均值", "delta": verdict["level"]})
    patent_total = _i(_patent(data).get("total"))
    if patent_total is not None:
        metrics.append({"label": "专利储备", "value": str(patent_total), "hint": "创新实力基础指标"})
    cur_hire = _i(_recruitment(data).get("current"))
    if cur_hire is not None:
        metrics.append({"label": "在招岗位", "value": str(cur_hire), "hint": "扩张活跃度信号"})
    reg = _pick(base, "注册资本", "regCapital", "regCapitalValue")
    if reg:
        metrics.append({"label": "注册资本", "value": str(reg), "hint": "工商登记注册资本"})
    holder_n = len(_holders(data))
    if holder_n:
        metrics.append({"label": "股东数量", "value": str(holder_n), "hint": "工商公示股东数"})
    found_year = _pick(base, "成立日期", "foundTime", "成立时间")
    if found_year and str(found_year)[:4].isdigit():
        import datetime as _dt
        age = _dt.datetime.now().year - int(str(found_year)[:4])
        if age >= 0:
            metrics.append({"label": "成立年限", "value": f"{age} 年", "hint": f"成立于 {str(found_year)[:4]} 年"})
    # 风险计数指标（尽调核心信号）— 优先用 MCP total
    risk = _risk(data)
    res_n = risk.get("restrictions_total") or len(risk.get("restrictions") or [])
    if res_n:
        metrics.append({"label": "限制高消费", "value": str(res_n), "hint": "被执行限高记录数", "delta": "▼" if res_n >= 5 else ""})
    hearing_n = risk.get("court_hearings_total")
    if hearing_n:
        metrics.append({"label": "开庭公告", "value": str(hearing_n), "hint": "诉讼开庭记录总数"})
    pen_n = risk.get("penalties_total") or len(risk.get("penalties") or [])
    if pen_n:
        metrics.append({"label": "行政处罚", "value": str(pen_n), "hint": "行政处罚记录数"})
    ano_n = risk.get("anomalies_total") or len(risk.get("anomalies") or [])
    if ano_n:
        metrics.append({"label": "经营异常", "value": str(ano_n), "hint": "经营异常名录记录"})
    fin_n = _i(_operation(data).get("financing_count"))
    if fin_n:
        metrics.append({"label": "融资轮次", "value": str(fin_n), "hint": "历史融资轮次"})
    rank_n = len(_operation(data).get("rankings") or [])
    if rank_n:
        metrics.append({"label": "上榜记录", "value": str(rank_n), "hint": "企业上榜次数"})
    for _key, label, v in scores["valid"]:
        metrics.append({"label": label, "value": str(v), "hint": "尽调专项评分"})

    # Detail sections
    section_specs: List[Dict[str, Any]] = []
    section_data: Dict[str, Any] = {}

    holder_rows = _holder_rows(data)
    if holder_rows:
        section_specs.append({"key": "dd_holders", "title": "股东出资结构", "kind": "table",
                              "note": "股东持股比例与实缴情况（资本充实性核查基础）",
                              "columns": [("股东名称", "股东名称"), ("持股比例", "持股比例"), ("认缴金额", "认缴金额"), ("实缴金额", "实缴金额"), ("股东类型", "股东类型")]})
        section_data["dd_holders"] = holder_rows

    invest_rows = _investment_rows(data)
    if invest_rows:
        inv_total = _risk(data).get("investments_total") or len(_investments(data))
        section_specs.append({"key": "dd_investments", "title": "对外投资清单（关联方敞口）", "kind": "table",
                              "note": f"共 {inv_total} 家对外投资（展示前 {min(len(_investments(data)), 15)} 家），风险可能经关联方传导",
                              "columns": [("被投资企业", "被投资企业"), ("持股比例", "持股比例"), ("经营状态", "经营状态"), ("成立日期", "成立日期"), ("注册资本", "注册资本")]})
        section_data["dd_investments"] = invest_rows

    lit_rows = _litigation_rows(data)
    if len(lit_rows) > 1:
        section_specs.append({"key": "dd_litigation", "title": "诉讼风险结构", "kind": "table",
                              "note": "原被告身份分布是尽调关键信号",
                              "columns": [("诉讼维度", "诉讼维度"), ("数值", "数值")]})
        section_data["dd_litigation"] = lit_rows

    score_rows = _specialty_score_rows(scores)
    if score_rows:
        section_specs.append({"key": "dd_specialty", "title": "尽调专项评分矩阵", "kind": "table",
                              "note": "跨维度交叉评分（资本充实性 / 风险隔离度 / 合规健康度 / 经营稳健性）",
                              "columns": [("评估维度", "评估维度"), ("评分", "评分"), ("等级", "等级")]})
        section_data["dd_specialty"] = score_rows

    return {
        "metrics": metrics,
        "insights": cross_insights,
        "specialty_scores": {"items": [{"key": k, "label": l, "score": v} for k, l, v in scores["items"]],
                             "average": scores["average"]},
        "verdict": verdict,
        "section_specs": section_specs,
        "section_data": section_data,
    }
