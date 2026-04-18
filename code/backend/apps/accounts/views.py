"""Accounts views — registration, auth, profile, risk questionnaire, notifications."""

import logging
import uuid

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Notification, PriceAlert, User
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    NotificationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PriceAlertSerializer,
    RiskQuestionnaireSerializer,
    UserCreateSerializer,
    UserResponse,
    UserUpdateSerializer,
)

logger = logging.getLogger("apps.accounts")

RISK_PROFILE_MAP = [
    (
        20,
        "conservative",
        "Preservation-focused. Minimal volatility, capital protection.",
    ),
    (40, "moderate_conservative", "Stability with modest growth. Low equity exposure."),
    (60, "moderate", "Balanced growth and stability. Diversified across assets."),
    (80, "moderate_aggressive", "Growth-oriented. Higher equity allocation accepted."),
    (
        100,
        "aggressive",
        "Maximum growth. High volatility accepted for long-term gains.",
    ),
]

PROFILE_ALLOCATIONS = {
    "conservative": {"bonds": 0.60, "equity": 0.25, "cash": 0.10, "real_estate": 0.05},
    "moderate_conservative": {
        "bonds": 0.45,
        "equity": 0.40,
        "cash": 0.05,
        "real_estate": 0.10,
    },
    "moderate": {"bonds": 0.30, "equity": 0.55, "cash": 0.05, "real_estate": 0.10},
    "moderate_aggressive": {
        "bonds": 0.15,
        "equity": 0.70,
        "cash": 0.05,
        "real_estate": 0.10,
    },
    "aggressive": {"bonds": 0.05, "equity": 0.85, "cash": 0.02, "real_estate": 0.08},
}


@extend_schema(tags=["auth"])
class RegisterView(generics.CreateAPIView):
    """Register a new user account."""

    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Send verification email (async in production)
        verification_token = uuid.uuid4()
        user.verification_token = verification_token
        user.save(update_fields=["verification_token"])
        logger.info("User registered: %s", user.email)
        return Response(UserResponse(user).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["auth"])
class LoginView(TokenObtainPairView):
    """Login — returns JWT access + refresh tokens with user data."""

    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(tags=["auth"])
class LogoutView(generics.GenericAPIView):
    """Blacklist the refresh token (logout)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Successfully logged out."})
        except Exception:
            return Response(
                {"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(tags=["auth"])
class MeView(generics.RetrieveUpdateAPIView):
    """Get or update the authenticated user's profile."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserResponse

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


@extend_schema(tags=["auth"])
class ChangePasswordView(generics.GenericAPIView):
    """Change password for the authenticated user."""

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        logger.info("Password changed for user: %s", user.email)
        return Response({"detail": "Password updated successfully."})


@extend_schema(tags=["auth"])
class PasswordResetRequestView(generics.GenericAPIView):
    """Request a password reset email."""

    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email=email, is_active=True)
            token = uuid.uuid4()
            user.password_reset_token = token
            user.password_reset_expires = timezone.now() + timezone.timedelta(hours=2)
            user.save(update_fields=["password_reset_token", "password_reset_expires"])
            # In production: send email with reset link
            logger.info("Password reset requested for: %s", email)
        except User.DoesNotExist:
            pass  # Don't reveal whether email exists
        return Response(
            {"detail": "If an account exists, a reset email has been sent."}
        )


@extend_schema(tags=["auth"])
class PasswordResetConfirmView(generics.GenericAPIView):
    """Confirm password reset with token."""

    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        try:
            user = User.objects.get(password_reset_token=token)
            if user.password_reset_expires < timezone.now():
                return Response({"detail": "Reset token has expired."}, status=400)
            user.set_password(serializer.validated_data["new_password"])
            user.password_reset_token = None
            user.password_reset_expires = None
            user.save()
            return Response({"detail": "Password reset successful."})
        except User.DoesNotExist:
            return Response({"detail": "Invalid token."}, status=400)


@extend_schema(tags=["auth"])
class VerifyEmailView(generics.GenericAPIView):
    """Verify email address via token."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            user = User.objects.get(verification_token=token, is_verified=False)
            user.is_verified = True
            user.verification_token = None
            user.save(update_fields=["is_verified", "verification_token"])
            return Response({"detail": "Email verified successfully."})
        except User.DoesNotExist:
            return Response({"detail": "Invalid or already used token."}, status=400)


@extend_schema(tags=["auth"])
class RiskQuestionnaireView(generics.GenericAPIView):
    """Submit risk questionnaire and update user's risk profile."""

    serializer_class = RiskQuestionnaireSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers = serializer.validated_data["answers"]

        total_score = sum(a["answer"] for a in answers)
        max_score = len(answers) * 5
        normalized = int((total_score / max_score) * 100)

        profile = "moderate"
        description = ""
        for threshold, p, desc in RISK_PROFILE_MAP:
            if normalized <= threshold:
                profile = p
                description = desc
                break

        user = request.user
        user.risk_score = normalized
        user.risk_profile = profile
        user.save(update_fields=["risk_score", "risk_profile"])

        return Response(
            {
                "risk_score": normalized,
                "risk_profile": profile,
                "description": description,
                "suggested_allocation": PROFILE_ALLOCATIONS[profile],
                "updated": True,
            }
        )


@extend_schema(tags=["auth"])
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """List and manage user notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response({"detail": "Marked as read."})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        updated = (
            self.get_queryset()
            .filter(is_read=False)
            .update(is_read=True, read_at=timezone.now())
        )
        return Response({"detail": f"{updated} notifications marked as read."})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})


@extend_schema(tags=["auth"])
class PriceAlertViewSet(viewsets.ModelViewSet):
    """CRUD for user price alerts."""

    serializer_class = PriceAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user)
