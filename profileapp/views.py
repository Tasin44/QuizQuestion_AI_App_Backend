from django.shortcuts import render

# Create your views here.

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
 
from coreapp.mixins import StandardResponseMixin, extract_first_error
from .models import UserProfile
from .serializers import (
    ProfileSetupSerializer,
    ProfileEditSerializer,
    ProfileReadSerializer,
    ActivityUpdateSerializer,
)

class ProfileSetupView(StandardResponseMixin, APIView):
    """
    POST /profile/setup/
    First-time profile setup after signup (name, image, description).
    Idempotent — safe to call again if setup was incomplete.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # support file uploads#❓❓❓ why those used
 
    def post(self, request):#❓❓❓ why request used here?
        # get_or_create avoids duplicate profiles if called twice
        profile, created = UserProfile.objects.get_or_create(user=request.user)
 
        serializer = ProfileSetupSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request}
        )#❓❓❓ why partial true
        if serializer.is_valid():
            serializer.save()#❓❓❓ why?
            return self.success_response(
                serializer.data,
                message="Profile set up successfully. Welcome aboard!",
                status_code=200
            )
        #❓❓❓ tell me some method like serializer.save,.errors 
        reason = extract_first_error(serializer.errors)
        return self.error_response(
            f"Profile setup failed: {reason}",
            status_code=400,
            data=serializer.errors
        )



class ProfileView(StandardResponseMixin, APIView):
    """
    GET  /profile/   — fetch logged-in user's full profile
    PATCH /profile/  — update name and/or image (email NOT editable)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
 
    def _get_profile(self, user):#❓❓❓ why _ used before get, is it protected?
        """
        select_related is not needed (OneToOne), but we use get_or_create
        so profile always exists even if setup was skipped.
        """
        profile, _ = UserProfile.objects.get_or_create(user=user)#❓❓❓advantage of using get_or_create, why _ used
        return profile
 
    def get(self, request):
        profile = self._get_profile(request.user)
        # Pass request to serializer for building absolute image URL
        serializer = ProfileReadSerializer(profile, context={'request': request})#❓❓❓ why passing this two?
        return self.success_response(
            serializer.data,
            message="Profile fetched successfully."
        )
    
    '''
    def patch(self, request):
        profile = self._get_profile(request.user)
        image_file = request.FILES.get('image')
        data = request.data.copy()
        if 'image' in data and not image_file:
            data.pop('image')
        # partial=True allows updating only the provided fields
        serializer = ProfileEditSerializer(profile, data=data, partial=True)
        if serializer.is_valid():
            if image_file:
                serializer.save(image=image_file)
            else:
                serializer.save()
            profile.refresh_from_db()
            # Return full profile after update
            read_serializer = ProfileReadSerializer(profile, context={'request': request})
            return self.success_response(
                read_serializer.data,
                message="Profile updated successfully."
            )
        reason = extract_first_error(serializer.errors)
        return self.error_response(
            f"Profile update failed: {reason}",
            status_code=400,
            data=serializer.errors
        )
    '''
    def patch(self, request):
        profile = self._get_profile(request.user)
        
        data = request.data.copy()
        
        # Merge FILES into data so the serializer sees the image
        if 'image' in request.FILES:
            data['image'] = request.FILES['image']

        serializer = ProfileEditSerializer(profile, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            profile.refresh_from_db()
            read_serializer = ProfileReadSerializer(profile, context={'request': request})
            return self.success_response(
                read_serializer.data,
                message="Profile updated successfully."
            )
        reason = extract_first_error(serializer.errors)
        return self.error_response(
            f"Profile update failed: {reason}",
            status_code=400,
            data=serializer.errors
        )
 



class ActivityUpdateView(StandardResponseMixin, APIView):
    """
    PATCH /profile/activity/
    Frontend calls this to sync study_minutes and active_days.
    We INCREMENT values, not replace — prevents replay attacks.
    """
    permission_classes = [IsAuthenticated]
 
    def patch(self, request):
        serializer = ActivityUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            reason = extract_first_error(serializer.errors)
            return self.error_response(
                f"Activity update failed: {reason}",
                status_code=400
            )
 
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
 
        # F() expression does atomic increment — avoids race conditions
        from django.db.models import F
        study_add = serializer.validated_data.get('study_minutes_add', 0)
        days_add = serializer.validated_data.get('active_days_add', 0)
 
        if study_add > 0:
            UserProfile.objects.filter(pk=profile.pk).update(#❓❓❓ why pk used here? is it mean modlename.pk to acccess pk of a modle
                study_minutes=F('study_minutes') + study_add
            )
        if days_add > 0:
            UserProfile.objects.filter(pk=profile.pk).update(
                active_days=F('active_days') + days_add
            )
 
        profile.refresh_from_db()  # get fresh values after F() update
        return self.success_response(
            {
                "study_minutes": profile.study_minutes,
                "active_days": profile.active_days,
            },
            message="Activity stats updated successfully."
        )













