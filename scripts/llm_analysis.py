#!/usr/bin/env python3
"""LLM-powered analysis: generate report narrative (abstract, insights) from
real-time structured data using a language model.

Falls back to template-based text if the LLM API is unavailable, so reports
always produce valid output.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional


def _get_client():
    """Lazily create an Anthropic client; return None if not configured."""
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    if not token:
        return None
    try:
        import anthropic
        base_url = os.environ.get("ANTHROPIC_BASE_URL")
        return anthropic.Anthropic(api_key=token, base_url=base_url) if base_url else anthropic.Anthropic(api_key=token)
    except Exception:
        return None


def _call_llm(client, system: str, user: str, max_tokens: int = 800) -> Optional[str]:
    """Call the LLM; return the text response or None on failure."""
    model = os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-20250514"
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = []
        for block in resp.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts).strip() if parts else None
    except Exception as exc:
        print(f"⚠️  LLM 调用失败，使用模板文案: {exc}", file=sys.stderr)
        return None


def _build_data_summary(data: Mapping[str, Any], verdict: Mapping[str, Any], scores: Mapping[str, Any]) -> str:
    """Compress the normalized data into a concise text summary for the LLM."""
    parts: List[str] = []
    base = data.get("enterprise", {}).get("base", {})
    risk = data.get("risk", {})
    op = data.get("operation", {})
    patent = data.get("patent", {})
    rec = data.get("recruitment", {})
    # enterprise
    parts.append(f"企业: {base.get('企业名称', '?')}, 注册资本: {base.get('注册资本','?')}, 成立: {base.get('成立日期','?')}, 行业: {base.get('行业','?')}")
    # risk
    rs = risk.get("score")
    rl = risk.get("level")
    res_total = risk.get("restrictions_total") or len(risk.get("restrictions") or [])
    hear_total = risk.get("court_hearings_total") or len(risk.get("court_hearings") or [])
    pen_total = risk.get("penalties_total") or len(risk.get("penalties") or [])
    parts.append(f"风险: 评分{rs}({rl}), 限高{res_total}条, 开庭{hear_total}条, 处罚{pen_total}条")
    # operation
    scale = op.get("scale", {})
    fin = op.get("financing_count")
    parts.append(f"经营: 规模{scale.get('staff','?')}, 营业额{scale.get('turnover','?')}, 融资{fin}轮")
    # patent
    pt = patent.get("total")
    parts.append(f"专利: {pt}件" if pt is not None else "专利: 无数据")
    # recruitment
    cur = rec.get("current")
    parts.append(f"招聘: 在招{cur}人" if cur is not None else "招聘: 无数据")
    # investments
    inv_total = risk.get("investments_total") or len(data.get("enterprise", {}).get("investments") or [])
    parts.append(f"对外投资: {inv_total}家")
    # scores
    score_items = scores.get("items", [])
    valid = [f"{s['label']}={s['score']}" for s in score_items if s.get("score") is not None]
    parts.append(f"专项评分: {', '.join(valid) if valid else '无'}")
    parts.append(f"结论: {verdict.get('recommendation','?')}, 阻断: {verdict.get('blockers',[])}, 关注: {verdict.get('key_concerns',[])}")
    return "\n".join(parts)


def generate_abstract(data: Mapping[str, Any], enterprise: str, verdict: Mapping[str, Any],
                      scores: Mapping[str, Any]) -> str:
    """Generate a data-accurate report abstract via LLM (fallback to template)."""
    client = _get_client()
    if not client:
        return ""  # caller handles fallback
    data_text = _build_data_summary(data, verdict, scores)
    system = "你是企业尽调分析专家。基于提供的结构化数据，生成一段精准的尽调报告摘要（150-250字）。要求：数据必须与提供的一致，不得编造；语言专业凝练；突出核心风险与关键发现。直接输出摘要正文，不要加标题或前缀。"
    user = f"以下是「{enterprise}」的尽调结构化数据，请生成报告摘要：\n\n{data_text}"
    result = _call_llm(client, system, user, max_tokens=400)
    return result or ""


def refine_insights(insights: List[Dict[str, Any]], data: Mapping[str, Any],
                    verdict: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Refine insight interpretations via LLM (fallback to original template text)."""
    client = _get_client()
    if not client:
        return insights
    data_text = _build_data_summary(data, verdict, {})
    # Build a compact representation of current insights
    insight_text = "\n".join(f"{i+1}. [{ins['feature']}] 证据: {ins['evidence']}" for i, ins in enumerate(insights))
    system = "你是企业尽调分析专家。基于提供的结构化数据和已有洞察，为每条洞察生成更精准、更有深度的解读（interpretation）。要求：解读必须基于数据，不得编造；每条解读50-100字；语言专业。以JSON数组输出，每个元素含feature和interpretation字段。"
    user = f"数据：\n{data_text}\n\n已有洞察：\n{insight_text}\n\n请输出JSON数组，每条含feature和interpretation。"
    result = _call_llm(client, system, user, max_tokens=800)
    if not result:
        return insights
    # Parse JSON array from LLM response
    try:
        # strip markdown code fence if present
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        items = json.loads(clean)
        refined_map = {item["feature"]: item["interpretation"] for item in items if isinstance(item, dict) and "feature" in item}
        for ins in insights:
            if ins["feature"] in refined_map:
                ins["interpretation"] = refined_map[ins["feature"]]
    except (json.JSONDecodeError, KeyError, TypeError):
        pass  # keep original insights if LLM output is unparseable
    return insights
