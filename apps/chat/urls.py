from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import ChatView, ConversationViewSet

router = SimpleRouter()
router.register("conversations", ConversationViewSet, basename="conversation")

urlpatterns = [
    path("", ChatView.as_view(), name="chat"),
    path("", include(router.urls)),
]
