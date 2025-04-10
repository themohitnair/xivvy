from datetime import datetime
from config import LAST_UPDATED_FILE


def load_last_updated() -> datetime:
    try:
        with open(LAST_UPDATED_FILE, "r") as f:
            return datetime.fromisoformat(f.read().strip())
    except Exception:
        return datetime(2000, 1, 1)


def save_last_updated(dt: datetime):
    with open(LAST_UPDATED_FILE, "w") as f:
        f.write(dt.isoformat())
