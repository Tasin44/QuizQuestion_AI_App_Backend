from django.db import models
from django.contrib.auth import get_user_model
import uuid
from scanapp.models import SUBJECT_CHOICES
# Create your models here.

User=get_user_model()


#will convert this two id into int not uuid
class ChatSession(models.Model):
    """
    A chat session is a conversation thread tied to one subject.
    One user can have many sessions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
 
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='chat_sessions', db_index=True
    )
    subject = models.CharField(
        max_length=50,
        choices=SUBJECT_CHOICES,
        null=True,
        blank=True
    )#❓❓❓ what does choice , is it builtin
    title = models.CharField(max_length=200, blank=True, default='')  # auto-generated from first message
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            #models.Index(fields=['user', 'subject']),#❓❓❓ why I used user, subject together coupling, why not onl subject, only updated_at during indexing
            models.Index(fields=['user', 'updated_at']),
        ]
 
    def __str__(self):
        return f"ChatSession({self.user.email}, {self.subject})"


class ChatMessage(models.Model):
    """One message in a session. Role is 'user' or 'assistant'."""
    ROLE_USER = 'user'
    ROLE_AI = 'assistant'
    ROLE_CHOICES = [(ROLE_USER, 'User'), (ROLE_AI, 'Assistant')]
 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
 
    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE,
        related_name='messages', db_index=True
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['created_at']   # oldest first for conversation flow
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]

class AskChatHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ask_histories', db_index=True)
    # subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, null=True, blank=True)
    # model = models.CharField(max_length=20, default='gpt')
    prompt = models.TextField(blank=True, default='')
    ai_response = models.TextField()
    image = models.ImageField(upload_to='ask/images/', blank=True, null=True)   
    file = models.FileField(upload_to='ask/files/', blank=True, null=True)      
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at'])
            # models.Index(fields=['user', 'subject']),
        ]






