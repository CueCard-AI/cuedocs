from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError, TokenBackendError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.token_blacklist import models as blacklist_models
from django.utils.timezone import now
from core.models import User
import jwt

UserModel = get_user_model()


def blacklist_user_tokens(user):
    tokens = blacklist_models.OutstandingToken.objects.filter(user=user)
    for token in tokens:
        blacklist_models.BlacklistedToken.objects.get_or_create(token=token)


class CustomJWTAuthentication(JWTStatelessUserAuthentication):
    create_unknown_user = True

    def get_user(self, validated_token):
        """
        Returns a stateless user object which is backed by the given validated
        token.
        """

        user_id = validated_token.get(api_settings.USER_ID_CLAIM, None)
        email = validated_token.get('email', None)
        timeZone = validated_token.get('timeZone', "UTC")
        organizationId = validated_token.get('organizationId', None)
        
        if not user_id or not email:
            raise InvalidToken(_("Token contained no recognizable user identification"))

        if self.create_unknown_user:
            user, created = User.objects.get_or_create(
                defaults={
                    "id": user_id,
                    "username": user_id,
                    "email": email,
                    "timezone": timeZone,
                    "organization_id": organizationId,
                },
                email=email
            )
            user.username = user_id
            user.timezone = timeZone
            user.organization_id = organizationId
            user.save()

            if created:
                return user
        else:
            try:
                user = User.objects.get_by_natural_key(user_id)
            except UserModel.DoesNotExist:
                pass

        return user if self.user_can_authenticate(user) else None

    def user_can_authenticate(self, user):
        return user is not None and user.is_active


class JWKSAuthToken(Token):
    token_type = 'jwks'
    lifetime = api_settings.ACCESS_TOKEN_LIFETIME

    def __init__(self, token=None, verify=True):
        self.current_time = now()
        self.token = token
        
        if token is not None:
            try:
                jwks_client = self.get_jwks_client()
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                
                self.payload = jwt.decode(
                    token,
                    key=signing_key.key,
                    algorithms=[api_settings.ALGORITHM],
                    options={
                        'verify_signature': verify,
                        'verify_exp': verify,
                        'verify_iat': verify,
                        'verify_aud': verify,
                        'verify_iss': verify,
                    },
                    audience=api_settings.AUDIENCE,
                    issuer=api_settings.ISSUER,
                    leeway=api_settings.LEEWAY
                )
            except jwt.ExpiredSignatureError:
                raise TokenError(_("Token is expired"))
            except jwt.InvalidTokenError as e:
                raise TokenError(_(f"Token is invalid: {str(e)}"))
            
            self.set_jti()
            if verify:
                self.verify()
        else:
            self.payload = {}

    @classmethod
    def for_user(cls, user):
        raise NotImplementedError('Access tokens must be issued by Auth issuer.')

    def get_jwks_client(self):
        return jwt.PyJWKClient(api_settings.JWK_URL)

    def set_jti(self):
        self.payload['jti'] = self.payload.get('jti') or self.payload.get(api_settings.USER_ID_CLAIM, None)

    def verify(self):
        self.check_exp()

    def check_exp(self):
        try:
            exp = self.payload['exp']
        except KeyError:
            raise TokenError(_('Token has no expiration'))

        if self.current_time.timestamp() >= exp:
            raise TokenError(_('Token has expired'))