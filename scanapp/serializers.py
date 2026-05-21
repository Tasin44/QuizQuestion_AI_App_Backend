

from rest_framework import serializers
from .models import ScanHistory,SUBJECT_CHOICES, AiPersonalization


class ScanRequestSerializer(serializers.Serializer):
    """Validates incoming scan request before AI call."""
    subject = serializers.ChoiceField(choices=[c[0] for c in SUBJECT_CHOICES],required=False,default='general')#❓❓❓why choicefield used, isn't choice field , method field used when the field isn't present in model?
    image = serializers.ImageField(required=False)#❓❓❓ why I mentioned image separately here evenif its included on the model?
    file = serializers.FileField(
        required=False
    )
    question = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):

        image = attrs.get('image')
        file = attrs.get('file')

        # user must send at least one
        if not image and not file:
            raise serializers.ValidationError(
                "Either image or file is required."
            )

        return attrs
    ALLOWED_EXTENSIONS = ["pdf", "docx", "png", "jpg", "jpeg", "webp"]

    def validate_file(self, value):
        ext = value.name.split(".")[-1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("Unsupported file type.")
        return value
#❓❓❓why some serializers contain class Meta some not

class ScanHistorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ScanHistory
        fields = ['id','subject','image_url','question','ai_response']

    def get_image_url(self, obj):
        request = self.context.get('request')#❓❓❓ what does this line means, what does obj contain,all the scanhistory model field?
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class AiPersonalizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiPersonalization
        fields = ['model', 'response_sytel', 'dificulty_level', 'language', 'subject_focus_area']
















