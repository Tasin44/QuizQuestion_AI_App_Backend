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