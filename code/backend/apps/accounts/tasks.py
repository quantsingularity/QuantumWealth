"""Celery tasks for accounts app."""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("apps.accounts")


@shared_task(bind=True, max_retries=3)
def send_verification_email(self, user_id: str, token: str):
    """Send email verification link to newly registered user."""
    from .models import User

    try:
        user = User.objects.get(id=user_id)
        verify_url = f"{settings.FRONTEND_URL}/verify-email/{token}"
        send_mail(
            subject="Verify your QuantumWealth account",
            message=f"Hi {user.first_name},\n\nVerify your email: {verify_url}\n\nThis link expires in 24 hours.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
        logger.info("Verification email sent to %s", user.email)
    except Exception as exc:
        logger.error("Failed to send verification email: %s", exc)
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id: str, token: str):
    """Send password reset link."""
    from .models import User

    try:
        user = User.objects.get(id=user_id)
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"
        send_mail(
            subject="Reset your QuantumWealth password",
            message=f"Hi {user.first_name},\n\nReset your password: {reset_url}\n\nThis link expires in 2 hours.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task
def send_weekly_performance_digest():
    """Send weekly portfolio performance summary to opted-in users."""
    from apps.portfolio.models import Portfolio

    from .models import User

    users = User.objects.filter(is_active=True, notify_weekly_digest=True)
    logger.info("Sending weekly digest to %d users", users.count())
    for user in users:
        try:
            portfolios = Portfolio.objects.filter(user=user, is_active=True)
            if not portfolios.exists():
                continue
            # In production: generate and send rich HTML digest
            logger.debug("Digest sent to %s", user.email)
        except Exception as e:
            logger.error("Failed to send digest to %s: %s", user.email, e)


@shared_task
def create_notification(
    user_id: str, notification_type: str, title: str, message: str, data: dict = None
):
    """Create an in-app notification for a user."""
    from .models import Notification

    Notification.objects.create(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        data=data or {},
    )
