
from rest_framework import serializers
from .models import UserProfile

class ProfileSetupSerializer(serializers.ModelSerializer):
    """
    Used when a new user sets up their profile for the first time.
    Accepts: name, image, description
    """
 
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ['name', 'image', 'image_url', 'description','birth_date']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None
 
    def validate_name(self, value): 
        '''
        why serializer name validation necessary? 
        
        Model blocks NULL/empty, but won’t catch " " (spaces)
        '''
     
        # Strip whitespace and enforce non-empty
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value
 
    def validate_description(self, value):
        # Optional field — just strip whitespace
        return value.strip()


class ProfileEditSerializer(serializers.ModelSerializer):
    """
    Used when updating name or image (email is NOT editable per requirement).
    """
 
    class Meta:
        model = UserProfile
        fields = ['name', 'image', 'description', 'birth_date']
        #❓❓❓How does this extra_kwargs works actually, is it changing the model filed required?
        extra_kwargs = {
            'name': {'required': False},
            'image': {'required': False},
            'description': {'required': False},
            'birth_date': {'required': False},
        }
 
    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value
 
    #❓❓❓ what is serializerMethodField#
class ProfileReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for GET /profile/.
    Includes computed fields: badges, level, problems_solved etc.
    """
    email = serializers.EmailField(source='user.email', read_only=True)
    badges = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
 
    class Meta:
        model = UserProfile
        fields = [
            'id', 'email', 'name', 'image_url', 'description',
            'problems_solved', 'study_minutes', 'active_days',
            'two_factor_enabled', 'badges', 'level','birth_date','is_parent',
            'created_at', 'updated_at',
        ]
 
    def get_badges(self, obj):#❓❓❓why obj used here, can't I directly access it using self?
        # Computed — no extra DB query
        return obj.get_earned_badges()
 
    def get_level(self, obj):
        return obj.get_level()
 
    def get_image_url(self, obj):
        # Return absolute URL or None
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None



class ActivityUpdateSerializer(serializers.Serializer):#❓❓❓ why here serializers.serializers
    """
    Frontend sends study_minutes and active_days periodically.
    We only INCREMENT — never overwrite with raw value to prevent cheating.
    """
    study_minutes_add = serializers.IntegerField(min_value=0, required=False, default=0)
    active_days_add = serializers.IntegerField(min_value=0, max_value=1, required=False, default=0)
    # active_days_add max 1 per call — frontend calls once per day














