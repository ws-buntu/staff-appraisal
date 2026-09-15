from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.utils import get_md5_hash_password


class LockedTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        # Repeat token verification under a row lock to prevent concurrent replay.
        token = self.token_class(attrs["refresh"])
        try:
            with transaction.atomic():
                OutstandingToken.objects.select_for_update().get(jti=token["jti"])
                user = get_user_model().objects.get(pk=token[api_settings.USER_ID_CLAIM])
                if token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(
                    user.password
                ):
                    raise InvalidToken()
                return super().validate(attrs)
        except ObjectDoesNotExist as exc:
            raise InvalidToken() from exc
