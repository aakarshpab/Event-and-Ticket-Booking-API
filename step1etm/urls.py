from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.bookings.views import BookingViewSet
from apps.events.views import EventViewSet, TicketTypeViewSet, VenueViewSet

router = DefaultRouter()
router.register("venues", VenueViewSet, basename="venue")
router.register("events", EventViewSet, basename="event")
router.register("ticket-types", TicketTypeViewSet, basename="tickettype")
router.register("bookings", BookingViewSet, basename="booking")

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("chat/", include("apps.chat.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("", include(router.urls)),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]
throttle_classes=[     
    path("schema/", SpectacularAPIView.as_view(throttle_classes=[]), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema", throttle_classes=[]), name="swagger-ui"),

]