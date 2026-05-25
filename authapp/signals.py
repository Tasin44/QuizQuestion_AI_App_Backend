from __future__ import annotations

from django.dispatch import receiver
from django.utils import timezone

from allauth.account.signals import user_logged_in
from allauth.socialaccount.signals import social_account_added, social_account_updated


def _mark_user_verified(user) -> None:
    """Mark our custom User.verified flag True after successful social login.

    Note: django-allauth already tracks email verification via EmailAddress.
    This project also uses a custom boolean field `verified` (used by OTP flow).
    """
    if not hasattr(user, 'verified'):
        return

    if user.verified:
        return

    update_fields = ['verified']
    # Keep updated_at in sync if the custom model has it.
    if hasattr(user, 'updated_at'):
        update_fields.append('updated_at')

    user.verified = True
    # If updated_at exists and is auto_now, it only updates when included in update_fields
    if hasattr(user, 'updated_at'):
        user.updated_at = timezone.now()

    user.save(update_fields=update_fields)


@receiver(user_logged_in)
def mark_verified_on_login(request, user, **kwargs):
    # This will also run for normal username/password logins; harmless.
    _mark_user_verified(user)


@receiver(social_account_added)
def mark_verified_on_social_added(request, sociallogin, **kwargs):
    _mark_user_verified(sociallogin.user)


@receiver(social_account_updated)
def mark_verified_on_social_updated(request, sociallogin, **kwargs):
    _mark_user_verified(sociallogin.user)
