# twofa/urls.py
 
from django.urls import path
from .views import TwoFASendOTPView, TwoFAVerifyView, TwoFAStatusView,ParentalControlCreateView,ParentViewChildChatsView,ParentViewChildScansView,ParentalControlAcceptView,ParentalControlRejectView
 
urlpatterns = [
    path('send/', TwoFASendOTPView.as_view(), name='2fa-send'),
    path('verify/', TwoFAVerifyView.as_view(), name='2fa-verify'),
    path('status/', TwoFAStatusView.as_view(), name='2fa-status'),
    path('parental-control/', ParentalControlCreateView.as_view(), name='parental-control-create'),
    path('parental-control/child-scans/', ParentViewChildScansView.as_view()),  # ADD
    path('parental-control/child-chats/', ParentViewChildChatsView.as_view()),  # ADD
        # CHANGE these two lines
    path('parental-control/accept/<int:obj_id>/', ParentalControlAcceptView.as_view()),
    path('parental-control/reject/<int:obj_id>/', ParentalControlRejectView.as_view()),
]

