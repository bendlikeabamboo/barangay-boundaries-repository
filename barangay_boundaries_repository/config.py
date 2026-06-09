from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(
        default_factory=lambda: os.getenv(
            "OPENAI_BASE_URL", "https://api.z.ai/api/paas/v4/"
        )
    )
    openai_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "glm-4.7")
    )
    psgc_data_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("PSGC_DATA_DIR", "~/commons/barangay")
        ).expanduser()
    )


settings = Settings()
