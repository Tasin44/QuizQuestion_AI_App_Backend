# twofa/urls.py
 
from django.urls import path
from .views import TwoFASendOTPView, TwoFAVerifyView, TwoFAStatusView,ParentalControlCreateView,ParentViewChildChatsView,ParentViewChildScansView
 
urlpatterns = [
    path('send/', TwoFASendOTPView.as_view(), name='2fa-send'),
    path('verify/', TwoFAVerifyView.as_view(), name='2fa-verify'),
    path('status/', TwoFAStatusView.as_view(), name='2fa-status'),
    path('parental-control/', ParentalControlCreateView.as_view(), name='parental-control-create'),
    path('parental-control/child-scans/<str:child_email>/', ParentViewChildScansView.as_view()),  # ADD
    path('parental-control/child-chats/<str:child_email>/', ParentViewChildChatsView.as_view()),  # ADD
]
 