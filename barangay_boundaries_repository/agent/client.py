from __future__ import annotations

import json
import logging
from typing import Any, Type, TypeVar

from openai import OpenAI

from barangay_boundaries_repository.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Any)


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is required. Set it in .env or pass api_key."
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def complete(
        self,
        system: str,
        user: str,
        output_model: Type[T] | None = None,
        temperature: float = 0.0,
        max_retries: int = 3,
    ) -> str | T:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 8192,
        }

        if output_model is not None:
            schema = json.dumps(output_model.model_json_schema())
            kwargs["extra_body"] = {
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": output_model.__name__,
                        "schema": json.loads(schema),
                    },
                }
            }

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if content is None:
                    raise RuntimeError("Empty response from LLM")

                usage = response.usage
                if usage:
                    logger.info(
                        "LLM call: model=%s, prompt_tokens=%d, completion_tokens=%d, total_tokens=%d",
                        self.model,
                        usage.prompt_tokens,
                        usage.completion_tokens,
                        usage.total_tokens,
                    )

                if output_model is not None:
                    return output_model.model_validate_json(content)

                return content

            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM call attempt %d/%d failed: %s", attempt + 1, max_retries, e
                )

        raise RuntimeError(
            f"LLM call failed after {max_retries} retries: {last_error}"
        ) from last_error
