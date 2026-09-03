"""
6+7. CONFIDENCE ENGINE (deterministic scoring — no LLM calls)
"""

def confidence_score(freshness_mins: float, expected_cadence_mins: float, history_days: float,
                      expected_history_days: float, missing_rate: float, signals_agree: float,
                      evidence_count: int) -> dict:
    freshness = max(0.0, 100 - max(0.0, freshness_mins - expected_cadence_mins) / expected_cadence_mins * 40)
    history = min(100.0, (history_days / expected_history_days) * 100)
    completeness = max(0.0, (1 - missing_rate) * 100)
    agreement = signals_agree * 100
    evidence = min(100.0, evidence_count * 18)
    score = freshness * 0.20 + history * 0.30 + completeness * 0.15 + agreement * 0.25 + evidence * 0.10
    band = "high" if score >= 78 else "medium" if score >= 52 else "low"
    return {
        "score": round(score), "band": band,
        "breakdown": {"freshness": round(freshness), "history": round(history),
                      "completeness": round(completeness), "agreement": round(agreement),
                      "evidence": round(evidence)},
    }
