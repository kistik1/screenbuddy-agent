import html

from fastapi import FastAPI, Request

from services.catalog_loader import load_catalog
from services.llm_service import (
    generate_recommendation_explanation,
)
from services.search_engine import (
    format_recommendations_message,
    search_titles,
)
from services.telegram_service import (
    send_telegram_message,
)
from services.user_state_analyzer import (
    PendingConversationStore,
    analyze_user_state,
    build_search_query_from_user_state,
    combine_conversation_messages,
)


app = FastAPI()


TOP_N = 3
MIN_SIMILARITY = 0.2
conversation_store = PendingConversationStore()


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


def _build_follow_up_message(questions: list[str]) -> str:
    question_lines = "\n".join(
        f"• {html.escape(question)}"
        for question in questions
    )
    return (
        "I need a bit more to tune the recommendation.\n\n"
        f"{question_lines}"
    )


@app.post("/webhook")
async def telegram_webhook(
    request: Request,
):
    data = await request.json()
    message = data.get("message", {})
    chat = message.get("chat", {})
    text = (message.get("text") or "").strip()
    chat_id = chat.get("id")

    if not chat_id:
        return {
            "ok": False,
            "error": "missing chat_id",
        }

    if text == "/start":
        conversation_store.clear(chat_id)
        send_telegram_message(
            chat_id,
            (
                "Hi! I'm <b>ScreenBuddy</b>\n\n"
                "Tell me how you feel and what kind of movie or series fits today.\n\n"
                "Examples:\n"
                "<code>I had a very exhausting day, I want something light</code>\n\n"
                "<code>I'm bored and want something exciting</code>\n\n"
                "<code>I feel sad, maybe something comforting</code>"
            ),
        )
        return {"ok": True}

    pending_state = conversation_store.get(chat_id)
    if pending_state:
        conversation_messages = pending_state[
            "conversation_messages"
        ] + [text]
        original_message = pending_state[
            "original_message"
        ]
    else:
        conversation_messages = [text]
        original_message = text

    analysis_input = combine_conversation_messages(
        conversation_messages
    )
    analysis = analyze_user_state(analysis_input)

    if analysis["needs_follow_up"]:
        conversation_store.set(
            chat_id=chat_id,
            original_message=original_message,
            conversation_messages=conversation_messages,
            analysis=analysis,
        )
        send_telegram_message(
            chat_id,
            _build_follow_up_message(
                analysis["follow_up_questions"]
            ),
        )
        return {"ok": True}

    conversation_store.clear(chat_id)

    parsed_query = build_search_query_from_user_state(
        user_state=analysis["user_state"],
        original_text=original_message,
    )

    debug_message = (
        "DEBUG - User State\n"
        f"<code>{html.escape(str(analysis['user_state']))}</code>\n\n"
        "DEBUG - Search Query\n"
        f"<code>{html.escape(str(parsed_query))}</code>\n\n"
    )

    recommendations = search_titles(
        user_query=original_message,
        parsed_query=parsed_query,
        df=df,
        vectorizer=vectorizer,
        tfidf_matrix=tfidf_matrix,
        top_n=TOP_N,
        min_similarity=MIN_SIMILARITY,
    )

    llm_explanation = (
        generate_recommendation_explanation(
            user_query=original_message,
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
