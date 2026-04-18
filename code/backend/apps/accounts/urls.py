from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    NotificationViewSet,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PriceAlertViewSet,
    RegisterView,
    RiskQuestionnaireView,
    VerifyEmailView,
)

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notifications")
router.register("price-alerts", PriceAlertViewSet, basename="price-alerts")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("verify-email/<uuid:token>/", VerifyEmailView.as_view(), name="verify-email"),
    path(
        "risk-questionnaire/",
        RiskQuestionnaireView.as_view(),
        name="risk-questionnaire",
    ),
    path("", include(router.urls)),
]
