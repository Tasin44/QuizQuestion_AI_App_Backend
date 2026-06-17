from django.shortcuts import render
from django.contrib.auth import get_user_model
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

User = get_user_model() # User is referenced in the parental-control views but never defined. I added get_user_model() and bound User so those queries resolve.
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
 
        # Send OTP via email using Resend
        from django.conf import settings
        import requests
        import logging
        logger = logging.getLogger(__name__)

        message = (
            f"Your 2FA verification code is: {otp_code}\n"
            f"This code expires in 10 minutes.\n"
            f"If you did not request this, please ignore this email."
        )

        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": [email],
                    "subject": "Your Two-Factor Authentication Code",
                    "text": message,
                },
                timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send 2FA OTP via Resend: {str(e)}")
            if hasattr(e, 'response') and getattr(e, 'response') is not None:
                logger.error(f"Resend API response: {e.response.text}")
 
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

        # SELF-ADD CHECK
        if related_email.lower() == request.user.email.lower():
            return self.error_response(
                "You cannot add yourself as a parent or child.",
                status_code=400
            )

        # DUPLICATE CHECK
        already_exists = ParentalControl.objects.filter(
            user=request.user,
            related_email=related_email,
            relation_type=relation_type
        ).exists()
        if already_exists:
            return self.error_response(
                "This relation already exists.",
                status_code=400
            )

        try:
            related_user = User.objects.get(email=related_email, verified=True)
        except User.DoesNotExist:
            related_user = None

        # Create with status=pending
        obj = ParentalControl.objects.create(
            user=request.user,
            related_email=related_email,
            related_user=related_user,
            relation_type=relation_type,
            is_parent=(relation_type == 'child'),
            status='pending'     # always pending until accepted
        )

        # Build accept/reject links
        accept_url = f"https://api.quizquestion.ai/2fa/parental-control/accept/{obj.id}/"
        reject_url = f"https://api.quizquestion.ai/2fa/parental-control/reject/{obj.id}/"

        relation_label = "parent" if relation_type == "parent" else "child"
        body = (
            f"Hello,\n\n"
            f"Greeting from Quiz Question AI APP Team.\n"
            f"The user {request.user.email} wants to add you as their {relation_label}.\n\n"
            f"Click ACCEPT to confirm:\n{accept_url}\n\n"
            f"Click REJECT to decline:\n{reject_url}\n\n"
            f"If you did not expect this, please ignore this email."
        )
        try:
            from django.conf import settings
            import requests
            import logging
            logger = logging.getLogger(__name__)

            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": [related_email],
                    "subject": "Parental Control Request",
                    "text": body,
                },
                timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Parental Control email via Resend: {str(e)}")
            if hasattr(e, 'response') and getattr(e, 'response') is not None:
                logger.error(f"Resend API response: {e.response.text}")

        return self.success_response(
            {
                "id": obj.id,
                "related_email": obj.related_email,
                "relation_type": obj.relation_type,
                "status": obj.status,
            },
            message="Request sent. The person must accept via the email link.",
            status_code=201,
        )

from scanapp.models import ScanHistory
from scanapp.serializers import ScanHistorySerializer
from chatapp.models import AskChatHistory
from chatapp.serializers import AskHistorySerializer
from .models import ParentalControl

class ParentViewChildScansView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Find all users who added request.user as their parent (accepted only)
        child_relations = ParentalControl.objects.filter(
            related_email=request.user.email,
            relation_type='parent',
            status='accepted'
        )

        if not child_relations.exists():
            return self.error_response("You have no children added.", status_code=404)

        result = {}
        for relation in child_relations:
            child_email = relation.user.email
            scans = ScanHistory.objects.filter(user=relation.user)
            serializer = ScanHistorySerializer(scans, many=True, context={'request': request})
            result[child_email] = serializer.data

        return self.success_response(result, message="Children scan history fetched.")


class ParentViewChildChatsView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        child_relations = ParentalControl.objects.filter(
            related_email=request.user.email,
            relation_type='parent',
            status='accepted'
        )

        if not child_relations.exists():
            return self.error_response("You have no children added.", status_code=404)

        result = {}
        for relation in child_relations:
            child_email = relation.user.email
            chats = AskChatHistory.objects.filter(user=relation.user)
            serializer = AskHistorySerializer(chats, many=True, context={'request': request})
            result[child_email] = serializer.data

        return self.success_response(result, message="Children chat history fetched.")

from rest_framework.permissions import AllowAny

class ParentalControlAcceptView(StandardResponseMixin, APIView):
    """
    GET /2fa/parental-control/accept/<obj_id>/
    Called when the related person clicks accept link in email.
    No auth required — link is public like email verification.
    """
    permission_classes = [AllowAny]

    def get(self, request, obj_id):
        try:
            obj = ParentalControl.objects.get(id=obj_id, status='pending')
        except ParentalControl.DoesNotExist:
            return render(
                request,
                "parental_control_accept.html",
                {"status": "error", "message": "Invalid or already processed request."},
                status=404,
            )

        obj.status = 'accepted'
        obj.save(update_fields=['status'])

        # Now apply is_parent logic ONLY after acceptance
        if obj.relation_type == 'child':
            # obj.user added someone as child → obj.user is parent
            from profileapp.models import UserProfile
            UserProfile.objects.filter(user=obj.user).update(is_parent=True)

        if obj.relation_type == 'parent' and obj.related_user:
            # related_user is the parent → mark them
            from profileapp.models import UserProfile
            UserProfile.objects.filter(user=obj.related_user).update(is_parent=True)

        return render(
            request,
            "parental_control_accept.html",
            {
                "status": "accepted",
                "message": "Parental control relation accepted successfully.",
            },
        )


class ParentalControlRejectView(StandardResponseMixin, APIView):
    """
    GET /2fa/parental-control/reject/<obj_id>/
    Called when the related person clicks reject link in email.
    """
    permission_classes = [AllowAny]

    def get(self, request, obj_id):
        try:
            obj = ParentalControl.objects.get(id=obj_id, status='pending')
        except ParentalControl.DoesNotExist:
            return render(
                request,
                "parental_control_reject.html",
                {"status": "error", "message": "Invalid or already processed request."},
                status=404,
            )

        obj.status = 'rejected'
        obj.save(update_fields=['status'])

        return render(
            request,
            "parental_control_reject.html",
            {"status": "rejected", "message": "Parental control relation rejected."},
        )