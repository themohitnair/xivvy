from datetime import datetime, timezone


def iso_date_to_unix(iso_date_str: str):
    return int(datetime.fromisoformat(iso_date_str).timestamp())


def unix_to_iso(unix_timestamp: int) -> str:
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
