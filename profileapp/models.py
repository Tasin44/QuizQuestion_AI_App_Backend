from django.db import models

# Create your models here.
from django.contrib.auth import get_user_model
import uuid
User=get_user_model()


class UserProfile(models.Model):
    """
    Extended profile for each user.
    One-to-one with User — created automatically after signup verification.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
 
    # Link to the auth user — CASCADE deletes profile when user is deleted
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
 
    # Display name (editable; email is NOT editable per requirement)
    name = models.CharField(max_length=150)
 
    # Profile photo stored in media/profiles/
    image = models.ImageField(upload_to='profiles/', blank=True, null=True)
 
    # Short bio / about section
    description = models.TextField(blank=True, default='')
 
    # Tracks how many AI prompts the user has submitted (incremented on each AI call)
    problems_solved = models.PositiveIntegerField(default=0)
 
    # Study duration in minutes — frontend sends this periodically via PATCH
    study_minutes = models.PositiveIntegerField(default=0)
 
    birth_date = models.DateField(null=True, blank=True)

    # Number of calendar days the user has been active (frontend increments daily)
    active_days = models.PositiveIntegerField(default=0)

    # Placeholder subscription status used by admin user management.
    subscription_status = models.CharField(max_length=20, default='monthly')
 
    # Two-factor auth toggle — set True after OTP verification in 2FA flow
    two_factor_enabled = models.BooleanField(default=False)

    is_parent = models.BooleanField(default=False)
    two_factor_verified_at = models.DateTimeField(null=True, blank=True)
 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        indexes = [
            models.Index(fields=['user']),  #❓what if I want to use here id instead of user, what is user contianing here?
        ]
 
    def __str__(self):
        return f"Profile({self.user.email})"
 
    # ── Badge & Level Logic ─────────────────────────────────────────────────
 
    BADGE_RULES = [
        # (badge_id, label, description, min_study_minutes)
        ("bookworm",     "Bookworm",       "Studied for 60+ minutes",    60),
        ("dedicated",    "Dedicated",      "Studied for 300+ minutes",   300),
        ("scholar",      "Scholar",        "Studied for 600+ minutes",   600),
        ("top_solver",   "Top Solver",     "Solved 10+ problems",        None),   # problems-based
        ("problem_guru", "Problem Guru",   "Solved 50+ problems",        None),
        ("marathon",     "Marathon",       "Active 7+ days",             None),   # days-based
        ("streak_king",  "Streak King",    "Active 30+ days",            None),
    ]
 
    def get_earned_badges(self):
        """
        Returns list of badges the user has earned.
        Evaluated in real-time — no extra DB table needed.
        """
        earned = []
        for badge_id, label, desc, min_minutes in self.BADGE_RULES:
            if min_minutes and self.study_minutes >= min_minutes:
                earned.append({"id": badge_id, "label": label, "description": desc})
            elif badge_id == "top_solver" and self.problems_solved >= 10:
                earned.append({"id": badge_id, "label": label, "description": desc})
            elif badge_id == "problem_guru" and self.problems_solved >= 50:
                earned.append({"id": badge_id, "label": label, "description": desc})
            elif badge_id == "marathon" and self.active_days >= 7:
                earned.append({"id": badge_id, "label": label, "description": desc})
            elif badge_id == "streak_king" and self.active_days >= 30:
                earned.append({"id": badge_id, "label": label, "description": desc})
        return earned
 
    def get_level(self):
        """
        Level is derived from badge count — no separate column needed.
        Level 1 = 0-1 badges, Level 2 = 2-3 badges, Level 3 = 4+ badges
        """
        badge_count = len(self.get_earned_badges())
        if badge_count >= 4:
            return 3
        elif badge_count >= 2:
            return 2
        return 1