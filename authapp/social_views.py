from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

@method_decorator(csrf_exempt, name='dispatch')
class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    # UPDATE this to your actual callback URL
    callback_url = "https://api.quizquestion.ai/accounts/google/login/callback/"


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client
    # UPDATE this to your actual callback URL
    callback_url = "https://api.quizquestion.ai/accounts/facebook/login/callback/"
    authentication_classes = []   # required for FB social login to work