"""The ONLY place that talks to the AI service. Views never call the API directly."""
import requests
from django.conf import settings
from rest_framework.exceptions import APIException

API_URL = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """You are the Event Assistant for an event and ticket booking platform.
Rules:
- Only answer questions about the platform's events, venues, dates, prices and ticket availability.
- Use ONLY the event data given below. Never invent events, prices or availability.
- If the data does not contain the answer, say clearly that you don't know.
- If the question is not about events or tickets, politely say you can only help with events and tickets.
- You are read-only: you cannot book or cancel tickets. If asked, explain how to use the booking endpoint
  or the app instead.
- Keep answers short and friendly. Prices are in Indian rupees (Rs)."""


class LLMServiceError(APIException):
    status_code = 503
    default_detail = "The AI assistant is temporarily unavailable. Please try again later."
    default_code = "ai_service_unavailable"


def generate_reply(*, history, user_message, event_context):
    """history: list of {"role": "user"|"assistant", "content": "..."} (already trimmed)."""
    if not settings.ANTHROPIC_API_KEY:
        raise LLMServiceError("The AI assistant is not configured.")

    # The API wants the conversation to start with a user message.
    while history and history[0]["role"] != "user":
        history = history[1:]

    payload = {
        "model": settings.LLM_MODEL,
        "max_tokens": settings.LLM_MAX_TOKENS,  # cap the reply length
        "system": f"{SYSTEM_PROMPT}\n\nCURRENT EVENT DATA:\n{event_context}",
        "messages": [*history, {"role": "user", "content": user_message}],
    }
    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=settings.LLM_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return "".join(b["text"] for b in data["content"] if b.get("type") == "text").strip()
    except (requests.RequestException, KeyError, ValueError):
        raise LLMServiceError()
