import uuid
from datetime import datetime, timezone


def string_to_uuid(string_id: str):
    namespace = uuid.NAMESPACE_DNS
    return str(uuid.uuid5(namespace, string_id))


def iso_date_to_unix(iso_date_str: str):
    return int(datetime.fromisoformat(iso_date_str).timestamp())


def unix_to_iso(unix_timestamp: int) -> str:
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
