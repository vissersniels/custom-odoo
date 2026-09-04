from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, BaseModel, Field, ValidationError


class Settings(BaseModel):
    odoo_url: AnyHttpUrl = Field(alias="ODOO_URL")
    odoo_db: str = Field(alias="ODOO_DB", min_length=1)
    odoo_username: str = Field(alias="ODOO_USERNAME", min_length=1)
    odoo_api_key: str = Field(alias="ODOO_API_KEY", min_length=1)

    sample_emails_dir: Path = Field(alias="SAMPLE_EMAILS_DIR", default=Path("sample_emails"))
    log_file: Path = Field(alias="LOG_FILE", default=Path("audit.log"))
    processed_emails_file: Path = Field(
        alias="PROCESSED_EMAILS_FILE",
        default=Path("processed_emails.json"),
    )

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
        "str_strip_whitespace": True,
    }


def load_settings(env_file: str | Path = ".env") -> Settings:
    env_path = Path(env_file)
    load_dotenv(dotenv_path=env_path, override=False)

    try:
        data = {
            "ODOO_URL": os.getenv("ODOO_URL"),
            "ODOO_DB": os.getenv("ODOO_DB"),
            "ODOO_USERNAME": os.getenv("ODOO_USERNAME"),
            "ODOO_API_KEY": os.getenv("ODOO_API_KEY"),
            "SAMPLE_EMAILS_DIR": os.getenv("SAMPLE_EMAILS_DIR", "sample_emails"),
            "LOG_FILE": os.getenv("LOG_FILE", "audit.log"),
            "PROCESSED_EMAILS_FILE": os.getenv("PROCESSED_EMAILS_FILE", "processed_emails.json"),
        }
        return Settings(**data)
    except ValidationError as exc:
        # Bubble up a clear startup failure with all missing/invalid config keys.
        raise RuntimeError(f"Invalid configuration in {env_path}: {exc}") from exc
