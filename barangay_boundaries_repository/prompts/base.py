from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class PromptTemplate:
    id: str
    description: str
    system: str
    user_template: str
    output_schema: dict | None = None

    def render(self, **variables: str) -> str:
        text = self.user_template
        for key, value in variables.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        return text


_PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def load_prompt(name: str) -> PromptTemplate:
    path = _PROMPT_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return PromptTemplate(
        id=data["id"],
        description=data["description"],
        system=data["system"],
        user_template=data["user_template"],
        output_schema=data.get("output_schema"),
    )


def list_prompts() -> list[str]:
    if not _PROMPT_DIR.exists():
        return []
    return [p.stem for p in _PROMPT_DIR.glob("*.yaml")]
