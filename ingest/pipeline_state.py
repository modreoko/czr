"""
Správa stavu pipeline – ukladá a načítava START_DATE medzi spusteniami.
"""

import json
from pathlib import Path
from datetime import datetime
from config import DATA_DIR

STATE_FILE = DATA_DIR / "pipeline_state.json"


def save_start_date(start_date: datetime) -> None:
    """
    Uloží START_DATE do stavu súboru.

    Args:
        start_date: datetime objekt na uloženie
    """
    state = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"✅ Uložený START_DATE: {start_date.strftime('%Y-%m-%d')}")


def load_start_date() -> datetime:
    """
    Načíta START_DATE zo stavu súboru.

    Returns:
        datetime objekt s uloženým START_DATE alebo None ak súbor neexistuje
    """
    if not STATE_FILE.exists():
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            start_date_str = state.get("start_date")
            if start_date_str:
                return datetime.strptime(start_date_str, "%Y-%m-%d")
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    return None
