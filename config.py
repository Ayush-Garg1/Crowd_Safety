import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv_if_available():
    try:
        from dotenv import load_dotenv
    except Exception:
        load_dotenv = None

    if load_dotenv:
        env_path = Path.cwd() / ".env"
        load_dotenv(env_path, override=True)


def _get_int(name: str, default: int) -> int:
    v = os.getenv(name, "").strip()
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    v = os.getenv(name, "").strip()
    if not v:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _get_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v.strip() if isinstance(v, str) and v.strip() else default


def _get_csv(name: str) -> list[str]:
    raw = _get_str(name, "")
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    # Camera
    camera_index: int

    # Risk thresholds (people count)
    risk_medium: int
    risk_high: int

    # Risk thresholds (density-based, people per m²)
    room_area_m2: float
    density_medium: float
    density_high: float

    # Email / SMTP
    email_cooldown_seconds: int
    smtp_host: str
    smtp_port: int
    email_sender: str
    email_password: str
    email_recipients: list[str]

    # Persistence
    db_path: str
    sample_seconds: int


def get_settings() -> Settings:
    _load_dotenv_if_available()

    db_path = _get_str("CM_DB_PATH", "data/crowd_monitor.sqlite3")
    # Normalize to absolute path (relative to repo root if possible)
    try:
        db_path = str(Path(db_path).resolve())
    except Exception:
        pass

    return Settings(
        camera_index=_get_int("CM_CAMERA_INDEX", 0),
        risk_medium=_get_int("CM_RISK_MEDIUM", 2),
        risk_high=_get_int("CM_RISK_HIGH", 4),
        room_area_m2=_get_float("CM_ROOM_AREA_M2", 50.0),
        density_medium=_get_float("CM_DENSITY_MEDIUM", 0.5),
        density_high=_get_float("CM_DENSITY_HIGH", 2.0),
        email_cooldown_seconds=_get_int("CM_EMAIL_COOLDOWN_SECONDS", 60),
        smtp_host=_get_str("CM_SMTP_HOST", "smtp.gmail.com"),
        smtp_port=_get_int("CM_SMTP_PORT", 587),
        email_sender=_get_str("CM_EMAIL_SENDER", ""),
        email_password=_get_str("CM_EMAIL_PASSWORD", ""),
        email_recipients=_get_csv("CM_EMAIL_RECIPIENTS"),
        db_path=db_path,
        sample_seconds=max(1, _get_int("CM_SAMPLE_SECONDS", 10)),
    )

