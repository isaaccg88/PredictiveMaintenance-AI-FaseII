"""Presentation-only formatting for real UTC requests and synthetic UTC readings."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LOCAL_ZONE = ZoneInfo("America/Mexico_City")


def _parse_utc(value: str) -> datetime:
    """Require an ISO 8601 timestamp with an explicit UTC offset."""
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("El timestamp debe incluir su zona horaria UTC")
    return timestamp.astimezone(timezone.utc)


def format_request_local(value: str) -> str:
    """UTC -> local CDMX for display; the database value is unchanged."""
    return _parse_utc(value).astimezone(LOCAL_ZONE).strftime("%d/%m/%Y %H:%M:%S")


def format_simulated_utc(value: str) -> str:
    """Display synthetic observation time explicitly in UTC, never as real time."""
    return _parse_utc(value).strftime("%d/%m/%Y %H:%M:%S UTC")
