from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from rest_framework_simplejwt.tokens import RefreshToken

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import logging

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class GoogleLogin(SocialLoginView):
    permission_classes = [AllowAny]
    authentication_classes = []

    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    # Note:
    # - This endpoint is API-only (POST). It will NOT redirect to Google in the browser.
    # - callback_url is only needed when you exchange an auth "code".
    def get_callback_url(self, request, app):
        return (
            getattr(settings, 'GOOGLE_CALLBACK_URL', None)
            or request.build_absolute_uri('/accounts/google/login/callback/')
        )

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Site.DoesNotExist:
            return Response(
                {
                    'detail': (
                        'Django Sites framework is enabled but no Site row exists for SITE_ID. '
                        'Run migrations and create the Site record (Admin -> Sites), '
                        'or set SITE_ID to an existing site.'
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except SocialApp.DoesNotExist:
            # Most common cause of 500 on this endpoint:
            # Django Admin -> Social applications -> add Google app and attach your SITE_ID.
            return Response(
                {
                    'detail': (
                        'Google SocialApp is not configured. '
                        'Create a SocialApp for provider="google" and attach it to this SITE_ID.'
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            logger.exception('Google social login failed')
            return Response(
                {'detail': str(exc) if settings.DEBUG else 'Google social login failed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name='dispatch')
class FacebookLogin(SocialLoginView):
    permission_classes = [AllowAny]
    authentication_classes = []

    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client

    def get_callback_url(self, request, app):
        return (
            getattr(settings, 'FACEBOOK_CALLBACK_URL', None)
            or request.build_absolute_uri('/accounts/facebook/login/callback/')
        )

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Site.DoesNotExist:
            return Response(
                {
                    'detail': (
                        'Django Sites framework is enabled but no Site row exists for SITE_ID. '
                        'Run migrations and create the Site record (Admin -> Sites), '
                        'or set SITE_ID to an existing site.'
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except SocialApp.DoesNotExist:
            return Response(
                {
                    'detail': (
                        'Facebook SocialApp is not configured. '
                        'Create a SocialApp for provider="facebook" and attach it to this SITE_ID.'
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            logger.exception('Facebook social login failed')
            return Response(
                {'detail': str(exc) if settings.DEBUG else 'Facebook social login failed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView

class GoogleLoginRedirectView(OAuth2LoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    def get_callback_url(self, request, app):
        return (
            getattr(settings, 'GOOGLE_CALLBACK_URL', None)
            or request.build_absolute_uri('/accounts/google/login/callback/')
        )

    def dispatch(self, request, *args, **kwargs):
        try:
            self.adapter = self.adapter_class(request)
            return super().dispatch(request, *args, **kwargs)
        except Site.DoesNotExist:
            return Response(
                {
                    'detail': (
                        'Django Sites framework is enabled but no Site row exists for SITE_ID. '
                        'Run migrations and create the Site record (Admin -> Sites), '
                        'or set SITE_ID to an existing site.'
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except SocialApp.DoesNotExist:
            return Response(
                {
                    'detail': (
                        'Google SocialApp is not configured. '
                        'Create a SocialApp for provider="google" and attach it to this SITE_ID.'
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            logger.exception('Google social redirect failed')
            return Response(
                {'detail': str(exc) if settings.DEBUG else 'Google social redirect failed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SocialJWTCompleteView(View):
    """Complete a browser-based (django-allauth) social login and mint JWT tokens.

    Flow:
      Frontend -> /accounts/google/login/?next=<api>/auth/social/complete/?next=<frontend>/oauth-callback
      allauth logs in user (session) -> redirects to /auth/social/complete/
      this view issues SimpleJWT tokens -> redirects to frontend callback with tokens in URL fragment

    Tokens are placed in the URL fragment (#access=...&refresh=...) so they are not sent
    to the backend as query params on subsequent requests.
    """

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseBadRequest("Social login not completed (user not authenticated).")

        next_url = request.GET.get("next") or getattr(settings, "FRONTEND_OAUTH_SUCCESS_URL", "")
        if not next_url:
            return HttpResponseBadRequest("Missing next URL.")

        allowed_hosts = set(getattr(settings, "ACCOUNT_ALLOWED_REDIRECT_HOSTS", []) or [])
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts=allowed_hosts,
            require_https=not settings.DEBUG,
        ):
            return HttpResponseBadRequest("Invalid redirect host.")

        refresh = RefreshToken.for_user(request.user)
        access_value = str(refresh.access_token)
        refresh_value = str(refresh)

        parsed = urlparse(next_url)
        fragment_params = dict(parse_qsl(parsed.fragment, keep_blank_values=True))
        fragment_params.update({
            "access": access_value,
            "refresh": refresh_value,
            "token_type": "Bearer",
        })

        final_url = urlunparse(parsed._replace(fragment=urlencode(fragment_params)))
        return HttpResponseRedirect(final_url)