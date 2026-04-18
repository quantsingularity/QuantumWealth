"""Accounts serializers — registration, login, profile, notifications."""

from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Notification, PriceAlert, User

# ─── Auth Serializers ─────────────────────────────────────────────────────────


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Add user data to the token response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["full_name"] = user.full_name
        token["risk_profile"] = user.risk_profile
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        # Update last_login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        data["user"] = UserResponse(user).data
        return data


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirm password")

    class Meta:
        model = User
        fields = [
            "email",
            "full_name",
            "phone_number",
            "date_of_birth",
            "country",
            "currency",
            "password",
            "password2",
        ]

    def validate(self, data):
        if data["password"] != data.pop("password2"):
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserResponse(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone_number",
            "date_of_birth",
            "country",
            "currency",
            "risk_profile",
            "risk_score",
            "annual_income",
            "net_worth",
            "investment_horizon_years",
            "tax_bracket_pct",
            "is_verified",
            "created_at",
            "updated_at",
            "notify_price_alerts",
            "notify_rebalance",
            "notify_weekly_digest",
            "notify_tax_opportunities",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "is_verified",
            "risk_score",
        ]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "full_name",
            "phone_number",
            "date_of_birth",
            "country",
            "currency",
            "annual_income",
            "net_worth",
            "investment_horizon_years",
            "tax_bracket_pct",
            "notify_price_alerts",
            "notify_rebalance",
            "notify_weekly_digest",
            "notify_tax_opportunities",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError(
                {"new_password2": "Passwords do not match."}
            )
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password2 = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError(
                {"new_password2": "Passwords do not match."}
            )
        return data


# ─── Risk Questionnaire ───────────────────────────────────────────────────────


class RiskAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(min_value=1, max_value=10)
    answer = serializers.IntegerField(min_value=1, max_value=5)


class RiskQuestionnaireSerializer(serializers.Serializer):
    answers = RiskAnswerSerializer(many=True, min_length=5)


class RiskProfileResponseSerializer(serializers.Serializer):
    risk_score = serializers.IntegerField()
    risk_profile = serializers.CharField()
    description = serializers.CharField()
    suggested_allocation = serializers.DictField()
    updated = serializers.BooleanField()


# ─── Notifications & Alerts ───────────────────────────────────────────────────


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "data",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class PriceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceAlert
        fields = [
            "id",
            "ticker",
            "alert_type",
            "threshold",
            "is_active",
            "triggered_at",
            "created_at",
        ]
        read_only_fields = ["id", "triggered_at", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
