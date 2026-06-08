from __future__ import annotations

import asyncio
from pathlib import Path


async def extract_pdf_text(path: Path) -> str:
    import kreuzberg

    raw_bytes = path.read_bytes()
    result = await kreuzberg.extract_bytes(raw_bytes, mime_type="application/pdf")
    return str(result.content)


def extract_pdf_text_sync(path: Path) -> str:
    return asyncio.run(extract_pdf_text(path))
