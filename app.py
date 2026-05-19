import html
from fastapi import FastAPI, Request

from services.catalog_loader import (
    load_catalog,
)

from services.llm_service import (
    parse_user_query,
    generate_recommendation_explanation,
)

from services.search_engine import (
    search_titles,
    format_recommendations_message,
)

from services.telegram_service import (
    send_telegram_message,
)


app = FastAPI()


TOP_N = 3
MIN_SIMILARITY = 0.2


df, vectorizer, tfidf_matrix = load_catalog()


@app.get("/")
def health_check():
    return {
        "status": "ScreenBuddy Agent is running",
        "records_loaded": len(df),
    }


@app.get("/health")
def health_check_render():
    return {
        "status": "ok",
        "service": "ScreenBuddy Agent",
        "records_loaded": len(df),
    }


@app.head("/")
def root_head():
    return

@app.head("/health")
def health_head():
    return

@app.post("/webhook")
async def telegram_webhook(
    request: Request,
):
    data = await request.json()

    message = data.get("message", {})

    chat = message.get("chat", {})

    text = message.get("text", "")

    chat_id = chat.get("id")

    if not chat_id:
        return {
            "ok": False,
            "error": "missing chat_id",
        }

    if text == "/start":
        send_telegram_message(
            chat_id,
            (
                "Hi! I'm <b>ScreenBuddy</b> 🎬\n\n"
                "Write what kind of movie or show "
                "you want.\n\n"
                "Examples:\n"
                "<code>"
                "I want something like Game of Thrones "
                "but less violent"
                "</code>\n\n"
                "<code>"
                "Recommend Netflix thrillers after 2020"
                "</code>\n\n"
                "<code>"
                "Short family movies for kids"
                "</code>"
            ),
        )

        return {"ok": True}

    parsed_query = parse_user_query(text)

    debug_message = ( ##only for DEBUG
        "🧪 <b>DEBUG - LLM Parsed Query</b>\n"
        f"<code>{html.escape(str(parsed_query))}</code>\n\n"
    )

    recommendations = search_titles(
        user_query=text,
        parsed_query=parsed_query,
        df=df,
        vectorizer=vectorizer,
        tfidf_matrix=tfidf_matrix,
        top_n=TOP_N,
        min_similarity=MIN_SIMILARITY,
    )

    llm_explanation = (
        generate_recommendation_explanation(
            user_query=text,
            parsed_query=parsed_query,
            recommendations=recommendations,
        )
    )

    response_message = debug_message + (
        format_recommendations_message(
            recommendations=recommendations,
            llm_explanation=llm_explanation,
        )
    )

    send_telegram_message(
        chat_id,
        response_message,
    )

    return {"ok": True}