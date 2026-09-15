from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import LockedTokenRefreshSerializer


class NoStoreMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        response["Pragma"] = "no-cache"
        return response


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class LoginView(NoStoreMixin, TokenObtainPairView):
    throttle_classes = [LoginThrottle]


class RefreshView(NoStoreMixin, TokenRefreshView):
    serializer_class = LockedTokenRefreshSerializer
    throttle_classes = [LoginThrottle]


class MeView(NoStoreMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": str(user.pk),
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": user.role,
            }
        )


class LogoutInput(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutView(NoStoreMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = LogoutInput(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            token = RefreshToken(payload.validated_data["refresh"])
        except TokenError as exc:
            raise InvalidToken() from exc
        if str(token.get("user_id")) != str(request.user.pk):
            raise PermissionDenied("This refresh token belongs to another user.")
        try:
            with transaction.atomic():
                OutstandingToken.objects.select_for_update().get(jti=token["jti"])
                token = RefreshToken(payload.validated_data["refresh"])
                token.blacklist()
        except (TokenError, ObjectDoesNotExist) as exc:
            raise InvalidToken() from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
