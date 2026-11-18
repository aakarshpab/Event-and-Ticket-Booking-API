from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from step1etm.throttles import AuthRateThrottle

from .serializers import RegisterSerializer, UserSerializer


def get_tokens_for_user(user):
    """Create a JWT pair: a short-lived access token and a longer-lived refresh token."""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class AuthResponseSerializer(serializers.Serializer):
    """Only used to document the response in Swagger."""
    user = UserSerializer()
    access = serializers.CharField()
    refresh = serializers.CharField()


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ -> creates a user and returns JWT tokens."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]

    @extend_schema(responses={201: AuthResponseSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserSerializer(user).data, **get_tokens_for_user(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginSerializer(TokenObtainPairSerializer):
    """Normal JWT login, plus the user's details in the response."""

    def validate(self, attrs):
        data = super().validate(attrs)  # {"refresh": ..., "access": ...}
        data["user"] = UserSerializer(self.user).data
        return data


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ with username + password -> access + refresh tokens."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]

    @extend_schema(responses={200: AuthResponseSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RefreshView(TokenRefreshView):
    """POST /api/v1/auth/token/refresh/ with {"refresh": "..."} -> new access token."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]


class MeView(generics.RetrieveAPIView):
    """GET /api/v1/auth/me/ -> the logged in user."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user