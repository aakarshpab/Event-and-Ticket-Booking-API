
"""The ONLY place that talks to the AI service. Views never call the API directly."""

import requests
from django.conf import settings
from rest_framework.exceptions import APIException


SYSTEM_PROMPT = """You are the Event Assistant for an event and ticket booking platform.

Rules:
- Only answer questions about the platform's events, venues, dates, prices and ticket availability.
- Use ONLY the event data given below. Never invent events, prices or availability.
- If the data does not contain the answer, say clearly that you don't know.
- If the question is not about events or tickets, politely say you can only help with events and tickets.
- You are read-only: you cannot book or cancel tickets. If asked, explain how to use the booking endpoint or the app instead.
- Keep answers short and friendly. Prices are in Indian rupees (Rs).
"""


class LLMServiceError(APIException):
    status_code = 503
    default_detail = "The AI assistant is temporarily unavailable. Please try again later."
    default_code = "ai_service_unavailable"


def generate_reply(*, history, user_message, event_context):
    """Generate an AI response using FreeLLMAPI."""

    if not settings.FREELLM_API_KEY:
        raise LLMServiceError("The AI assistant is not configured.")

    # Ensure conversation starts with a user message.
    while history and history[0]["role"] != "user":
        history = history[1:]

    # OpenAI-compatible API endpoint.
    api_url = (
        f"{settings.FREELLM_BASE_URL.rstrip('/')}/chat/completions"
    )

    # Prepare conversation messages.
    messages = [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\nCURRENT EVENT DATA:\n{event_context}",
        },
        *history,
        {
            "role": "user",
            "content": user_message,
        },
    ]

    # Prepare API request.
    payload = {
        "model": settings.FREELLM_MODEL,
        "messages": messages,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {settings.FREELLM_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=settings.LLM_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        raise LLMServiceError()

