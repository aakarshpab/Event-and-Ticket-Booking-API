from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from step1etm.throttles import ChatRateThrottle

from .models import Conversation, Message
from .serializers import (
    ChatRequestSerializer, ChatResponseSerializer,
    ConversationDetailSerializer, ConversationListSerializer,
)
from .services import llm
from .services.context import build_event_context


class ChatView(APIView):
    """POST /api/v1/chat/  {"message": "...", "conversation_id": optional}"""

    throttle_classes = [ChatRateThrottle]  # stricter limit, each call costs money

    @extend_schema(request=ChatRequestSerializer, responses=ChatResponseSerializer)
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")

        if conversation_id:
            try:  # only YOUR conversations
                conversation = Conversation.objects.get(pk=conversation_id, user=request.user)
            except Conversation.DoesNotExist:
                raise NotFound("Conversation not found.")
        else:
            conversation = None

        # only send the last few messages as history
        history = []
        if conversation:
            recent = conversation.messages.order_by("-created_at", "-id")[: settings.LLM_HISTORY_MESSAGES]
            history = [{"role": m.role, "content": m.content} for m in reversed(list(recent))]

        reply = llm.generate_reply(
            history=history, user_message=message, event_context=build_event_context(message)
        )  # raises LLMServiceError -> clean 503 in the standard error format

        if conversation is None:
            conversation = Conversation.objects.create(user=request.user, title=message[:50])
        Message.objects.create(conversation=conversation, role=Message.Role.USER, content=message)
        Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content=reply)
        conversation.save()  # bumps updated_at

        return Response({"conversation_id": conversation.id, "reply": reply}, status=status.HTTP_200_OK)


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # lets Swagger generate docs
            return Conversation.objects.none()
        return Conversation.objects.filter(user=self.request.user)  # own chats only

    def get_serializer_class(self):
        return ConversationDetailSerializer if self.action == "retrieve" else ConversationListSerializer
