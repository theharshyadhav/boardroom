import sqlite3
from .config import settings

BASELINE = {"rec_replenish_inventory": 87, "rec_pause_campaign": 64, "rec_price_hold": 58}


def _conn():
    con = sqlite3.connect(settings.SQLITE_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS feedback (
        rec_id TEXT PRIMARY KEY, accepted INTEGER DEFAULT 0, rejected INTEGER DEFAULT 0, modified INTEGER DEFAULT 0
    )""")
    return con


def get_stats(rec_id: str) -> dict:
    con = _conn()
    row = con.execute("SELECT accepted, rejected, modified FROM feedback WHERE rec_id=?", (rec_id,)).fetchone()
    con.close()
    accepted, rejected, modified = row if row else (0, 0, 0)
    total = accepted + rejected + modified
    prior_n = 10
    baseline_pct = BASELINE.get(rec_id, 70)
    blended = round(((baseline_pct / 100) * prior_n + accepted) / (prior_n + total) * 100)
    return {"accepted": accepted, "rejected": rejected, "modified": modified, "blended": blended}


def submit_feedback(rec_id: str, action: str) -> dict:
    if action not in ("accepted", "rejected", "modified"):
        raise ValueError("invalid action")
    con = _conn()
    con.execute("INSERT INTO feedback (rec_id, accepted, rejected, modified) VALUES (?,0,0,0) "
                "ON CONFLICT(rec_id) DO NOTHING", (rec_id,))
    con.execute(f"UPDATE feedback SET {action} = {action} + 1 WHERE rec_id=?", (rec_id,))
    con.commit()
    con.close()
    return get_stats(rec_id)


def reset_all():
    con = _conn()
    con.execute("DELETE FROM feedback")
    con.commit()
    con.close()
