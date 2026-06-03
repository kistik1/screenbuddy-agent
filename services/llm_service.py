import json
import os
from typing import Any, Dict, Optional

from openai import OpenAI


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def load_prompt(file_name: str) -> str:
    path = f"prompts/{file_name}"

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def safe_json_loads(
    text: str,
    fallback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        return (fallback or {}).copy()
