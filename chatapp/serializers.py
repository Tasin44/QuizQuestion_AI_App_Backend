


from rest_framework import serializers
from scanapp.models import SUBJECT_CHOICES
from .models import ChatMessage,ChatSession,AskChatHistory

##❓❓❓ what is the work of all of this individual serializer
class StartChatSerializer(serializers.Serializer):
    """Create a new chat session."""
    subject = serializers.ChoiceField(choices=[c[0] for c in SUBJECT_CHOICES])
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
 
 
class SendMessageSerializer(serializers.Serializer):
    """Send a message in an existing session."""
    message = serializers.CharField(min_length=1, max_length=2000)
    model = serializers.ChoiceField(
        choices=["gpt", "claude","gemini"],
        default="gpt"
    )

#❓❓❓what is the differnce between serializers.serializers and serializers.modelserializers?

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at']
 
 
class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ['id', 'subject', 'title', 'created_at', 'updated_at']
 

class AskAIMessageSerializer(serializers.Serializer):
    # message = serializers.CharField(min_length=1, max_length=2000)
    # subject = serializers.ChoiceField(choices=[c[0] for c in SUBJECT_CHOICES],required=False, allow_null=True)
    message = serializers.CharField(min_length=1, max_length=2000, required=False, allow_blank=True)
    subject = serializers.ChoiceField(choices=[c[0] for c in SUBJECT_CHOICES], required=False, allow_null=True)
    model = serializers.ChoiceField(
        choices=["gpt", "claude","gemini"],
        default="gpt",
        required=False
    )
    image = serializers.ImageField(required=False)
    file = serializers.FileField(required=False)
    ALLOWED_EXTENSIONS = ["pdf", "docx", "png", "jpg", "jpeg", "webp"]

    def validate_file(self, value):
        ext = value.name.split(".")[-1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("Unsupported file type.")
        return value

    def validate(self, attrs):
        message = attrs.get('message', '').strip()
        image = attrs.get('image')
        file = attrs.get('file')
        # Must have at least one of: message, image, or file
        if not message and not image and not file:
            raise serializers.ValidationError(
                "Provide at least a message, image, or file."
            )
        return attrs


class AskHistorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField() 
    class Meta:
        model = AskChatHistory
        fields = ['id','prompt', 'ai_response','image_url','file_url', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_file_url(self, obj):   # ADD
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None








