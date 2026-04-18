"""
Tests for apps.accounts:
  - User registration (validation, duplicate detection, password rules)
  - Login / JWT token issuance
  - Token refresh and logout (blacklisting)
  - Profile retrieval and update (GET/PATCH /auth/me/)
  - Password change
  - Password reset request and confirmation
  - Email verification
  - Risk questionnaire scoring and profile assignment
  - Notification list, mark-read, mark-all-read, unread count
  - Price alert CRUD
"""

import uuid
from decimal import Decimal

from apps.accounts.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from tests.conftest import (
    anon_client,
    auth_client,
    make_notification,
    make_price_alert,
    make_user,
)

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class RegistrationTests(APITestCase):
    URL = "/api/v1/auth/register/"

    def _post(self, data):
        return self.client.post(self.URL, data, format="json")

    def test_register_returns_201_with_user_data(self):
        resp = self._post(
            {
                "email": "new@qw.ai",
                "full_name": "New Investor",
                "password": "Secure123!",
                "password2": "Secure123!",
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["email"], "new@qw.ai")
        self.assertEqual(resp.data["full_name"], "New Investor")
        self.assertNotIn("password", resp.data)

    def test_register_creates_user_in_database(self):
        self._post(
            {
                "email": "db@qw.ai",
                "full_name": "DB User",
                "password": "Secure123!",
                "password2": "Secure123!",
            }
        )
        self.assertTrue(User.objects.filter(email="db@qw.ai").exists())

    def test_register_duplicate_email_returns_400(self):
        make_user("dup@qw.ai")
        resp = self._post(
            {
                "email": "dup@qw.ai",
                "full_name": "Dup",
                "password": "Secure123!",
                "password2": "Secure123!",
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch_returns_400(self):
        resp = self._post(
            {
                "email": "pw@qw.ai",
                "full_name": "PW Test",
                "password": "Secure123!",
                "password2": "Different456!",
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password_returns_400(self):
        resp = self._post(
            {
                "email": "weak@qw.ai",
                "full_name": "Weak PW",
                "password": "123",
                "password2": "123",
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_email_returns_400(self):
        resp = self._post(
            {
                "full_name": "No Email",
                "password": "Secure123!",
                "password2": "Secure123!",
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email_format_returns_400(self):
        resp = self._post(
            {
                "email": "not-an-email",
                "full_name": "Bad Email",
                "password": "Secure123!",
                "password2": "Secure123!",
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_sets_default_risk_profile(self):
        self._post(
            {
                "email": "default@qw.ai",
                "full_name": "Default",
                "password": "Secure123!",
                "password2": "Secure123!",
            }
        )
        user = User.objects.get(email="default@qw.ai")
        self.assertEqual(user.risk_profile, "moderate")

    def test_register_unauthenticated_access_allowed(self):
        """Registration endpoint must be publicly accessible."""
        client = anon_client()
        resp = client.post(
            self.URL,
            {
                "email": "anon@qw.ai",
                "full_name": "Anon",
                "password": "Secure123!",
                "password2": "Secure123!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginTests(APITestCase):
    URL = "/api/v1/auth/login/"

    def setUp(self):
        self.user = make_user("login@qw.ai", "Test1234!")

    def _post(self, email, password):
        return self.client.post(
            self.URL, {"email": email, "password": password}, format="json"
        )

    def test_login_returns_access_and_refresh_tokens(self):
        resp = self._post("login@qw.ai", "Test1234!")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_login_response_includes_user_object(self):
        resp = self._post("login@qw.ai", "Test1234!")
        self.assertIn("user", resp.data)
        self.assertEqual(resp.data["user"]["email"], "login@qw.ai")

    def test_login_wrong_password_returns_401(self):
        resp = self._post("login@qw.ai", "WrongPass!")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unknown_email_returns_401(self):
        resp = self._post("nobody@qw.ai", "Test1234!")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user_returns_401(self):
        self.user.is_active = False
        self.user.save()
        resp = self._post("login@qw.ai", "Test1234!")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_updates_last_login_timestamp(self):
        before = self.user.last_login
        self._post("login@qw.ai", "Test1234!")
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)
        if before:
            self.assertGreater(self.user.last_login, before)


# ---------------------------------------------------------------------------
# Token Refresh and Logout
# ---------------------------------------------------------------------------


class TokenLifecycleTests(APITestCase):
    def setUp(self):
        self.user = make_user("token@qw.ai", "Test1234!")
        resp = self.client.post(
            "/api/v1/auth/login/",
            {"email": "token@qw.ai", "password": "Test1234!"},
            format="json",
        )
        self.access = resp.data["access"]
        self.refresh = resp.data["refresh"]
        self.client = auth_client(self.user)

    def test_token_refresh_returns_new_access_token(self):
        resp = self.client.post(
            "/api/v1/auth/token/refresh/", {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)

    def test_logout_blacklists_refresh_token(self):
        resp = self.client.post(
            "/api/v1/auth/logout/", {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Subsequent refresh with the same token should fail
        resp2 = self.client.post(
            "/api/v1/auth/token/refresh/", {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(resp2.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_with_invalid_token_returns_400(self):
        resp = self.client.post(
            "/api/v1/auth/logout/", {"refresh": "not.a.token"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Me (profile)
# ---------------------------------------------------------------------------


class ProfileTests(APITestCase):
    URL = "/api/v1/auth/me/"

    def setUp(self):
        self.user = make_user("me@qw.ai", phone_number="+12025550100")
        self.client = auth_client(self.user)

    def test_get_profile_returns_200_with_correct_email(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "me@qw.ai")

    def test_get_profile_does_not_expose_password(self):
        resp = self.client.get(self.URL)
        self.assertNotIn("password", resp.data)

    def test_patch_full_name_updates_correctly(self):
        resp = self.client.patch(self.URL, {"full_name": "Updated Name"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["full_name"], "Updated Name")
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")

    def test_patch_financial_fields(self):
        resp = self.client.patch(
            self.URL,
            {
                "annual_income": "120000.00",
                "net_worth": "350000.00",
                "investment_horizon_years": 20,
                "tax_bracket_pct": "24.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.investment_horizon_years, 20)
        self.assertEqual(self.user.tax_bracket_pct, Decimal("24.00"))

    def test_patch_notification_preferences(self):
        resp = self.client.patch(
            self.URL,
            {
                "notify_price_alerts": False,
                "notify_weekly_digest": False,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.notify_price_alerts)
        self.assertFalse(self.user.notify_weekly_digest)

    def test_unauthenticated_returns_401(self):
        resp = anon_client().get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_change_email_via_patch(self):
        """Email is read-only; the field should be ignored or rejected."""
        resp = self.client.patch(self.URL, {"email": "hacked@evil.ai"}, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "me@qw.ai")


# ---------------------------------------------------------------------------
# Password Change
# ---------------------------------------------------------------------------


class ChangePasswordTests(APITestCase):
    URL = "/api/v1/auth/change-password/"

    def setUp(self):
        self.user = make_user("chpw@qw.ai", "OldPass123!")
        self.client = auth_client(self.user)

    def test_change_password_success(self):
        resp = self.client.post(
            self.URL,
            {
                "old_password": "OldPass123!",
                "new_password": "NewPass456!",
                "new_password2": "NewPass456!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass456!"))

    def test_wrong_old_password_returns_400(self):
        resp = self.client.post(
            self.URL,
            {
                "old_password": "WrongOld!",
                "new_password": "NewPass456!",
                "new_password2": "NewPass456!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_password_mismatch_returns_400(self):
        resp = self.client.post(
            self.URL,
            {
                "old_password": "OldPass123!",
                "new_password": "NewPass456!",
                "new_password2": "Mismatch789!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_new_password_returns_400(self):
        resp = self.client.post(
            self.URL,
            {
                "old_password": "OldPass123!",
                "new_password": "abc",
                "new_password2": "abc",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------


class PasswordResetTests(APITestCase):
    REQUEST_URL = "/api/v1/auth/password-reset/"
    CONFIRM_URL = "/api/v1/auth/password-reset/confirm/"

    def setUp(self):
        self.user = make_user("reset@qw.ai", "OldPass123!")

    def test_reset_request_returns_200_for_known_email(self):
        resp = self.client.post(
            self.REQUEST_URL, {"email": "reset@qw.ai"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_reset_request_returns_200_for_unknown_email(self):
        """Must not reveal whether the email exists (timing-safe response)."""
        resp = self.client.post(
            self.REQUEST_URL, {"email": "nobody@nowhere.ai"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_reset_confirm_with_valid_token_changes_password(self):
        token = uuid.uuid4()
        self.user.password_reset_token = token
        self.user.password_reset_expires = timezone.now() + timezone.timedelta(hours=2)
        self.user.save()

        resp = self.client.post(
            self.CONFIRM_URL,
            {
                "token": str(token),
                "new_password": "ResetPass789!",
                "new_password2": "ResetPass789!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ResetPass789!"))
        self.assertIsNone(self.user.password_reset_token)

    def test_reset_confirm_with_expired_token_returns_400(self):
        token = uuid.uuid4()
        self.user.password_reset_token = token
        self.user.password_reset_expires = timezone.now() - timezone.timedelta(hours=1)
        self.user.save()

        resp = self.client.post(
            self.CONFIRM_URL,
            {
                "token": str(token),
                "new_password": "ResetPass789!",
                "new_password2": "ResetPass789!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_confirm_with_fake_token_returns_400(self):
        resp = self.client.post(
            self.CONFIRM_URL,
            {
                "token": str(uuid.uuid4()),
                "new_password": "ResetPass789!",
                "new_password2": "ResetPass789!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------


class EmailVerificationTests(APITestCase):
    def setUp(self):
        self.user = make_user("verify@qw.ai", is_verified=False)
        self.token = uuid.uuid4()
        self.user.verification_token = self.token
        self.user.is_verified = False
        self.user.save()

    def test_valid_token_verifies_account(self):
        resp = self.client.get(f"/api/v1/auth/verify-email/{self.token}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        self.assertIsNone(self.user.verification_token)

    def test_already_used_token_returns_400(self):
        self.client.get(f"/api/v1/auth/verify-email/{self.token}/")
        resp = self.client.get(f"/api/v1/auth/verify-email/{self.token}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_token_returns_400(self):
        resp = self.client.get(f"/api/v1/auth/verify-email/{uuid.uuid4()}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Risk Questionnaire
# ---------------------------------------------------------------------------


class RiskQuestionnaireTests(APITestCase):
    URL = "/api/v1/auth/risk-questionnaire/"

    def setUp(self):
        self.user = make_user("risk@qw.ai")
        self.client = auth_client(self.user)

    def _answers(self, score: int = 3, count: int = 8):
        return [{"question_id": i + 1, "answer": score} for i in range(count)]

    def test_conservative_answers_produce_conservative_profile(self):
        resp = self.client.post(
            self.URL, {"answers": self._answers(score=1)}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["risk_profile"], "conservative")
        self.assertLessEqual(resp.data["risk_score"], 20)

    def test_aggressive_answers_produce_aggressive_profile(self):
        resp = self.client.post(
            self.URL, {"answers": self._answers(score=5)}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["risk_profile"], "aggressive")
        self.assertGreaterEqual(resp.data["risk_score"], 81)

    def test_moderate_answers_produce_moderate_profile(self):
        resp = self.client.post(
            self.URL, {"answers": self._answers(score=3)}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(
            resp.data["risk_profile"],
            ["moderate", "moderate_conservative", "moderate_aggressive"],
        )

    def test_questionnaire_updates_user_risk_profile(self):
        self.client.post(self.URL, {"answers": self._answers(score=5)}, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.risk_profile, "aggressive")

    def test_response_includes_suggested_allocation(self):
        resp = self.client.post(self.URL, {"answers": self._answers()}, format="json")
        self.assertIn("suggested_allocation", resp.data)
        self.assertIsInstance(resp.data["suggested_allocation"], dict)

    def test_too_few_answers_returns_400(self):
        resp = self.client.post(
            self.URL, {"answers": [{"question_id": 1, "answer": 3}]}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_answer_out_of_range_returns_400(self):
        answers = self._answers()
        answers[0]["answer"] = 6  # max is 5
        resp = self.client.post(self.URL, {"answers": answers}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_returns_401(self):
        resp = anon_client().post(self.URL, {"answers": self._answers()}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class NotificationTests(APITestCase):
    LIST_URL = "/api/v1/auth/notifications/"
    UNREAD_URL = "/api/v1/auth/notifications/unread_count/"
    MARK_ALL_URL = "/api/v1/auth/notifications/mark_all_read/"

    def setUp(self):
        self.user = make_user("notif@qw.ai")
        self.client = auth_client(self.user)
        self.n1 = make_notification(self.user, title="Alert 1")
        self.n2 = make_notification(self.user, title="Alert 2")
        self.n3 = make_notification(self.user, title="Alert 3", is_read=True)

    def test_list_returns_only_current_user_notifications(self):
        other = make_user("other@qw.ai")
        make_notification(other, title="Other user notif")
        resp = self.client.get(self.LIST_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        emails_in_results = [n["title"] for n in resp.data["results"]]
        self.assertNotIn("Other user notif", emails_in_results)

    def test_unread_count_returns_correct_number(self):
        resp = self.client.get(self.UNREAD_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["unread_count"], 2)

    def test_mark_all_read_sets_all_unread_to_read(self):
        resp = self.client.post(self.MARK_ALL_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        unread = self.user.notifications.filter(is_read=False).count()
        self.assertEqual(unread, 0)

    def test_mark_single_notification_read(self):
        resp = self.client.post(f"/api/v1/auth/notifications/{self.n1.id}/mark_read/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)
        self.assertIsNotNone(self.n1.read_at)

    def test_cannot_access_other_users_notification(self):
        other = make_user("other2@qw.ai")
        other_notif = make_notification(other, title="Private")
        resp = self.client.post(
            f"/api/v1/auth/notifications/{other_notif.id}/mark_read/"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Price Alerts
# ---------------------------------------------------------------------------


class PriceAlertTests(APITestCase):
    LIST_URL = "/api/v1/auth/price-alerts/"

    def setUp(self):
        self.user = make_user("alert@qw.ai")
        self.client = auth_client(self.user)

    def test_create_price_alert_returns_201(self):
        resp = self.client.post(
            self.LIST_URL,
            {
                "ticker": "AAPL",
                "alert_type": "above",
                "threshold": "200.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["ticker"], "AAPL")

    def test_list_alerts_returns_only_own_alerts(self):
        make_price_alert(self.user, "AAPL")
        other = make_user("other_alert@qw.ai")
        make_price_alert(other, "MSFT")
        resp = self.client.get(self.LIST_URL)
        tickers = [a["ticker"] for a in resp.data["results"]]
        self.assertIn("AAPL", tickers)
        self.assertNotIn("MSFT", tickers)

    def test_delete_own_alert(self):
        alert = make_price_alert(self.user)
        resp = self.client.delete(f"{self.LIST_URL}{alert.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_other_user_alert_returns_404(self):
        other = make_user("other_del@qw.ai")
        alert = make_price_alert(other)
        resp = self.client.delete(f"{self.LIST_URL}{alert.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_alert_type_below_is_valid(self):
        resp = self.client.post(
            self.LIST_URL,
            {
                "ticker": "TSLA",
                "alert_type": "below",
                "threshold": "150.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_alert_type_change_pct_is_valid(self):
        resp = self.client.post(
            self.LIST_URL,
            {
                "ticker": "SPY",
                "alert_type": "change_pct",
                "threshold": "5.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# User model unit tests
# ---------------------------------------------------------------------------


class UserModelTests(APITestCase):
    def test_create_user_sets_defaults(self):
        u = User.objects.create_user(
            email="model@qw.ai", password="Test1234!", full_name="Model User"
        )
        self.assertTrue(u.is_active)
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_verified)
        self.assertEqual(u.risk_profile, "moderate")
        self.assertEqual(u.risk_score, 50)

    def test_create_superuser_sets_staff_and_superuser(self):
        u = User.objects.create_superuser(email="super@qw.ai", password="Super1234!")
        self.assertTrue(u.is_staff)
        self.assertTrue(u.is_superuser)
        self.assertTrue(u.is_verified)

    def test_first_name_property_extracts_first_word(self):
        u = User(full_name="Jane Marie Doe")
        self.assertEqual(u.first_name, "Jane")

    def test_first_name_property_handles_single_name(self):
        u = User(full_name="Cher")
        self.assertEqual(u.first_name, "Cher")

    def test_first_name_property_handles_empty_name(self):
        u = User(full_name="")
        self.assertEqual(u.first_name, "")

    def test_str_representation(self):
        u = User(full_name="Jane Doe", email="jane@qw.ai")
        self.assertIn("jane@qw.ai", str(u))
        self.assertIn("Jane Doe", str(u))

    def test_password_is_hashed(self):
        u = User.objects.create_user(
            email="hash@qw.ai", password="PlainText1!", full_name="Hash User"
        )
        self.assertNotEqual(u.password, "PlainText1!")
        self.assertTrue(u.check_password("PlainText1!"))

    def test_email_is_normalized_to_lowercase_domain(self):
        u = User.objects.create_user(
            email="User@EXAMPLE.COM", password="Test1234!", full_name="Case User"
        )
        self.assertEqual(u.email, "User@example.com")
