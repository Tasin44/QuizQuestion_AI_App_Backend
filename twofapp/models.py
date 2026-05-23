
# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ParentalControl(models.Model):
    RELATION_CHOICES = [
        ('parent', 'Parent'),
        ('child', 'Child'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parental_controls')
    related_email = models.EmailField()
    related_user = models.ForeignKey(          # ADD: link to actual User if they exist
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parental_control_references'
    )
    relation_type = models.CharField(max_length=10, choices=RELATION_CHOICES)
    is_parent = models.BooleanField(default=False)   # ADD: True if THIS user is a parent of someone
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Hello, Grettings from Smart Study AI app team. The user {self.user.email} added you {self.related_email} as {self.relation_type}"