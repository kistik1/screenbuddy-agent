import json
import os
from typing import Any, Dict, List, Optional

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


def generate_recommendation_explanation(
    user_query: str,
    parsed_query: Dict[str, Any],
    recommendations: List[Dict[str, Any]],
) -> str:
    if not client:
        return ""

    if not recommendations:
        return ""

    system_prompt = load_prompt("generate_recommendation.txt")

    safe_recommendations = []

    for item in recommendations:
        safe_recommendations.append(
            {
                "title": item.get("title"),
                "description": item.get("description"),
                "genres": item.get("genres"),
                "release_year": item.get("release_year"),
                "duration": item.get("duration"),
                "target_audience": item.get("target_audience"),
                "age_category": item.get("age_category"),
                "streaming": item.get("streaming"),
                "type": item.get("type"),
                "similarity_score": item.get("similarity_score"),
                "cluster_name": item.get("cluster_name"),
            }
        )

    user_prompt = f"""
User original request:
{user_query}

Parsed query:
{json.dumps(parsed_query, ensure_ascii=False)}

Selected recommendations:
{json.dumps(safe_recommendations, ensure_ascii=False)}
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        return response.choices[0].message.content.strip()

    except Exception as error:
        print(f"OpenAI explanation error: {error}")
        return ""
