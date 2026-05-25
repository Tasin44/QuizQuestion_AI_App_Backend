"""
URL configuration for aamyproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # After browser-based Google login, allauth redirects to LOGIN_REDIRECT_URL which defaults to /accounts/profile/.
    # Provide a simple success page there.
    path('accounts/profile/', TemplateView.as_view(template_name='account/profile.html'), name='account_profile'),

    # django-allauth (browser-based OAuth redirect endpoints)
    path('accounts/', include('allauth.urls')),

    path('adminapp/', include('adminapp.urls')),
    path('auth/', include('authapp.urls')),
    path('chat/', include('chatapp.urls')),
    path('scan/', include('scanapp.urls')),
    path('profile/', include('profileapp.urls')),
    path('library/', include('libraryapp.urls')),
    path('2fa/', include('twofapp.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)