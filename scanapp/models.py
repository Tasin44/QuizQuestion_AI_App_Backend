# scanapp/models.py
# Stores each image scan and its AI response for history/reuse
 
from django.db import models
from django.contrib.auth import get_user_model
import uuid
 
User = get_user_model()

## Here all okay but user will choose ai model and based on this response will arrive , I think the code of this app mising this thing 

SUBJECT_CHOICES = [ #❓❓❓ what left side math and right side Mathematics meaning
    ('math',        'Mathematics'),
    ('physics',     'Physics'),
    ('chemistry',   'Chemistry'),
    ('biology',     'Biology'),
    ('english',     'English'),
    ('history',     'History'),
    ('general',     'General'),
]
 
class ScanHistory(models.Model):
    """
    Each row = one image scan + AI response.
    Indexed by user and subject for fast filtering.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
 
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='scans',
        db_index=True
    )
 
    # Subject filter chosen by user
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES,null=True,blank=True,default='general', db_index=True)
 
    # Uploaded image stored in media/scans/<user_id>/
    image = models.ImageField(upload_to='scans/images/',blank=True,null=True)

    # optional document
    file = models.FileField(
        upload_to='scans/files/',
        blank=True,
        null=True
    )
 
    # Optional extra question the user typed along with the image
    question = models.TextField(blank=True, default='')
 
    # AI response stored as text
    ai_response = models.TextField(blank=True, default='')
 
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-created_at']    # newest first
        indexes = [
            models.Index(fields=['user', 'subject']),   # used in list/filter queries
            models.Index(fields=['user', 'created_at']),
        ]
 
    def __str__(self):
        return f"Scan({self.user.email}, {self.subject})"


class AiPersonalization(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_personalizations',
        db_index=True,
    )
    model = models.CharField(max_length=100)
    response_sytel = models.CharField(max_length=100)
    dificulty_level = models.CharField(max_length=100)
    language = models.CharField(max_length=100)
    subject_focus_area = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AiPersonalization({self.user_id}, {self.model})"