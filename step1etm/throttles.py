from rest_framework.throttling import UserRateThrottle


class AuthRateThrottle(UserRateThrottle):
    scope = "auth"


class BookingRateThrottle(UserRateThrottle):
    scope = "booking"


class ChatRateThrottle(UserRateThrottle):
    scope = "chat"
