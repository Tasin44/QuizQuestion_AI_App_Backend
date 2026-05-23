from django.shortcuts import render
from coreapp.mixins import StandardResponseMixin,extract_first_error
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from django.core.mail import send_mail
from authapp.models import OTP
from profileapp.models import UserProfile
from .serializers import TwoFASendSerializer,TwoFAVerifySerializer,ParentalControlSerializer
import random
import string
from django.utils import timezone
from datetime import timedelta
from .models import ParentalControl
# Create your views here.

class TwoFASendOTPView(StandardResponseMixin, APIView):
    """
    POST /2fa/send/
    Body: { "email": "user@example.com" }
    Sends a 6-digit OTP to the provided email for 2FA verification.
    """
    permission_classes = [IsAuthenticated]
 
    def post(self, request):
        serializer = TwoFASendSerializer(data=request.data)
        if not serializer.is_valid():
            reason = extract_first_error(serializer.errors)
            return self.error_response(f"2FA setup failed: {reason}", status_code=400)
 
        email = serializer.validated_data['email']
 
        # Generate fresh OTP — delete any unused previous ones
        otp_code = ''.join(random.choices(string.digits, k=6))
        expires_at = timezone.now() + timedelta(minutes=10)
 
        OTP.objects.filter(email=email, is_used=False).delete()##❓❓❓why not user=requst.user passed here? how this line working
        OTP.objects.create(email=email, otp_code=otp_code, expires_at=expires_at)
 
        # Send OTP via email
        send_mail(
            subject="Your Two-Factor Authentication Code",
            message=(
                f"Your 2FA verification code is: {otp_code}\n"
                f"This code expires in 10 minutes.\n"
                f"If you did not request this, please ignore this email."
            ),
            from_email='noreply@studyapp.com',
            recipient_list=[email],
        )
 
        return self.success_response(##❓❓❓ is self contains this success and error response method, how?
            {"email": email},
            message="A verification code has been sent to your email. Please check your inbox.",
            status_code=200
        )


 
class TwoFAVerifyView(StandardResponseMixin, APIView):
    """
    POST /2fa/verify/
    Body: { "email": "...", "otp_code": "123456" }
    Verifies OTP and marks 2FA as enabled on the user's profile.
    """
    permission_classes = [IsAuthenticated]
 
    def post(self, request):
        serializer = TwoFAVerifySerializer(data=request.data)
        if not serializer.is_valid():
            reason = extract_first_error(serializer.errors)
            return self.error_response(f"2FA verification failed: {reason}", status_code=400)
 
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
 
        # Find a valid OTP for this email+code combo
        try:
            otp = OTP.objects.get(email=email, otp_code=otp_code, is_used=False)
        except OTP.DoesNotExist:
            return self.error_response(
                "The verification code is incorrect. Please check the code and try again.",
                status_code=400
            )
 
        if not otp.is_valid():
            return self.error_response(
                "The verification code has expired. Please request a new one.",
                status_code=400
            )
 
        # Mark OTP as used
        otp.is_used = True
        otp.save(update_fields=['is_used'])
 
        # Enable 2FA on profile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)##❓❓❓ why _ using here
        profile.two_factor_enabled = True
        profile.two_factor_verified_at = timezone.now()
        profile.save(update_fields=['two_factor_enabled', 'two_factor_verified_at'])
 
        return self.success_response(
            {
                "two_factor_enabled": True,
                "verified_at": profile.two_factor_verified_at.isoformat(),
            },
            message="Two-factor authentication has been successfully enabled on your account.",
            status_code=200
        )
 
 
class TwoFAStatusView(StandardResponseMixin, APIView):
    """
    GET /2fa/status/
    Returns current 2FA status for the logged-in user.
    Frontend shows "Already 2FA verified" if enabled = True.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return self.success_response(
            {
                "two_factor_enabled": profile.two_factor_enabled,
                "verified_at": (
                    profile.two_factor_verified_at.isoformat()
                    if profile.two_factor_verified_at else None
                ),
            },
            message="2FA status fetched successfully."
        )




class ParentalControlCreateView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ParentalControlSerializer(data=request.data)
        if not serializer.is_valid():
            reason = extract_first_error(serializer.errors)
            return self.error_response(f"Invalid request: {reason}", status_code=400, data=serializer.errors)

        related_email = serializer.validated_data['related_email']
        relation_type = serializer.validated_data['relation_type']

        # Try to find the related user in the system
        try:
            related_user = User.objects.get(email=related_email, verified=True)
        except User.DoesNotExist:
            related_user = None

        # Create the parental control record
        obj = ParentalControl.objects.create(
            user=request.user,
            related_email=related_email,
            related_user=related_user,
            relation_type=relation_type,
            # This user is a parent if they declared the related person as their child
            is_parent=(relation_type == 'child')
        )

        # If current user declared someone as their parent:
        # → mark that related user as is_parent=True on their own record (if they exist)
        if relation_type == 'parent' and related_user:
            # Mark all of related_user's parental control entries to reflect is_parent=True
            # Also create/update the reverse record so related_user knows they are a parent
            ParentalControl.objects.filter(user=related_user).update(is_parent=True)

            # If no record exists for related_user yet, mark on their profile via a flag
            # We store is_parent on UserProfile for easy access
            from profileapp.models import UserProfile
            UserProfile.objects.filter(user=related_user).update(is_parent=True)

        # If current user declared someone as their child:
        # → this user is now a parent, mark them
        if relation_type == 'child':
            from profileapp.models import UserProfile
            UserProfile.objects.filter(user=request.user).update(is_parent=True)

        # Send notification email
        relation_label = "parent" if relation_type == "parent" else "child"
        body = (
            f"Hello, Greeting from Smart Study AI APP Team. "
            f"The user {request.user.last_name or request.user.email} "
            f"added you {related_email} as a {relation_label}."
        )
        send_mail(
            subject="Parental Control Notification",
            message=body,
            from_email="noreply@studyapp.com",
            recipient_list=[related_email],
        )

        return self.success_response(
            {
                "id": obj.id,
                "related_email": obj.related_email,
                "relation_type": obj.relation_type,
                "is_parent": relation_type == 'child',  # current user is parent if they added a child
            },
            message="Parental control relation created and email sent.",
            status_code=201,
        )

from scanapp.models import ScanHistory
from scanapp.serializers import ScanHistorySerializer
from chatapp.models import AskChatHistory
from chatapp.serializers import AskHistorySerializer
from .models import ParentalControl

class ParentViewChildScansView(StandardResponseMixin, APIView):
    """
    GET /2fa/parental-control/child-scans/<child_email>/
    Parent can view a child's scan history.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, child_email):
        # Confirm request.user is actually a parent of child_email
        is_parent = ParentalControl.objects.filter(
            user=request.user,
            related_email=child_email,
            relation_type='child'   # current user added child_email as their child → user is parent
        ).exists()

        if not is_parent:
            return self.error_response(
                "You are not a parent of this user or the user does not exist.",
                status_code=403
            )

        # Get the child user
        try:
            child_user = User.objects.get(email=child_email, verified=True)
        except User.DoesNotExist:
            return self.error_response("Child user not found.", status_code=404)

        scans = ScanHistory.objects.filter(user=child_user)
        serializer = ScanHistorySerializer(scans, many=True, context={'request': request})
        return self.success_response(serializer.data, message="Child scan history fetched.")


class ParentViewChildChatsView(StandardResponseMixin, APIView):
    """
    GET /2fa/parental-control/child-chats/<child_email>/
    Parent can view a child's ask/chat history.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, child_email):
        is_parent = ParentalControl.objects.filter(
            user=request.user,
            related_email=child_email,
            relation_type='child'
        ).exists()

        if not is_parent:
            return self.error_response(
                "You are not a parent of this user or the user does not exist.",
                status_code=403
            )

        try:
            child_user = User.objects.get(email=child_email, verified=True)
        except User.DoesNotExist:
            return self.error_response("Child user not found.", status_code=404)

        chats = AskChatHistory.objects.filter(user=child_user)
        serializer = AskHistorySerializer(chats, many=True, context={'request': request})
        return self.success_response(serializer.data, message="Child chat history fetched.")