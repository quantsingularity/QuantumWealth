# Testing Guide

---

## Test Suite Overview

The QuantumWealth test suite covers authentication, portfolio CRUD, AI model logic, and tax and advisor service functions. All tests use Django's built-in test runner with a dedicated test database.

| Test Category                      | Location                                                 | Count |
| ---------------------------------- | -------------------------------------------------------- | ----- |
| Authentication and user management | `apps/tests.py` - RegistrationTests, LoginTests, MeTests | 10    |
| Risk questionnaire                 | `apps/tests.py` - RiskQuestionnaireTests                 | 2     |
| Notifications                      | `apps/tests.py` - NotificationTests                      | 3     |
| Portfolio CRUD                     | `apps/tests.py` - PortfolioTests                         | 5     |
| Holdings management                | `apps/tests.py` - HoldingTests                           | 3     |
| Transaction recording              | `apps/tests.py` - TransactionTests                       | 3     |
| Financial goals                    | `apps/tests.py` - FinancialGoalTests                     | 2     |
| Model unit tests                   | `apps/tests.py` - HoldingModelTests, UserModelTests      | 5     |
| Robo advisor AI                    | `apps/tests.py` - RoboAdvisorTests                       | 3     |
| Tax service                        | `apps/tests.py` - TaxServiceTests                        | 4     |
| Advisor service                    | `apps/tests.py` - AdvisorServiceTests                    | 2     |

---

## Running Tests

### Full Test Suite

```bash
cd code/backend
python manage.py test apps --settings=quantumwealth.settings.development -v 2
```

### Single Test Class

```bash
python manage.py test apps.tests.PortfolioTests --settings=quantumwealth.settings.development
```

### Single Test Method

```bash
python manage.py test apps.tests.HoldingTests.test_holding_upsert_averages_cost \
  --settings=quantumwealth.settings.development
```

### With Coverage

```bash
coverage run manage.py test apps --settings=quantumwealth.settings.development
coverage report -m
coverage html
# Open htmlcov/index.html in a browser
```

---

## Test Configuration

The development settings module is used for tests. Key differences from production:

| Setting                  | Test Value                                 | Why                    |
| ------------------------ | ------------------------------------------ | ---------------------- |
| DEBUG                    | True                                       | Verbose error output   |
| DATABASE                 | Creates `test_quantumwealth` automatically | Isolated test database |
| EMAIL_BACKEND            | console                                    | No real emails sent    |
| DEFAULT_THROTTLE_CLASSES | []                                         | Throttling disabled    |
| CACHES                   | In-memory (if configured)                  | No Redis required      |

---

## Test Helpers

Located at the top of `apps/tests.py`:

| Helper         | Signature                                    | Description                                   |
| -------------- | -------------------------------------------- | --------------------------------------------- |
| make_user      | `make_user(email, password, **kwargs)`       | Creates a User with defaults                  |
| auth_client    | `auth_client(user)`                          | Returns APIClient with Bearer token           |
| make_portfolio | `make_portfolio(user, name, cash)`           | Creates a Portfolio                           |
| add_holding    | `add_holding(portfolio, ticker, qty, price)` | Creates a Holding and updates portfolio total |

---

## What Each Test Verifies

### Registration Tests

| Test                            | Verifies                          |
| ------------------------------- | --------------------------------- |
| test_register_success           | Returns 201 with user data        |
| test_register_duplicate_email   | Returns 400 when email exists     |
| test_register_password_mismatch | Returns 400 when passwords differ |

### Portfolio Tests

| Test                          | Verifies                                  |
| ----------------------------- | ----------------------------------------- |
| test_create_portfolio         | Returns 201 with portfolio data           |
| test_list_portfolios          | Only returns current user portfolios      |
| test_get_portfolio_detail     | Includes holdings and transactions        |
| test_other_user_cannot_access | Returns 404 for another user portfolio    |
| test_soft_delete              | Sets is_active=False rather than deleting |

### Holding Tests

| Test                              | Verifies                                           |
| --------------------------------- | -------------------------------------------------- |
| test_add_holding                  | Creates holding and returns 201                    |
| test_holding_upsert_averages_cost | Merges two purchases with correct weighted average |
| test_list_holdings                | Returns all holdings for the portfolio             |

### AI Model Tests

| Test                                 | Verifies                                            |
| ------------------------------------ | --------------------------------------------------- |
| test_plan_goal_on_track              | Returns probability, milestones, scenarios          |
| test_compute_rebalance_detects_drift | Flags drift above threshold, sequences sells first  |
| test_compute_rebalance_no_drift      | Returns needs_rebalancing=False for minor drift     |
| test_wash_sale_check_no_violation    | Returns is_wash_sale=False with no conflicting buys |
| test_asset_location_recommendation   | Fixed income assets recommended for tax_advantaged  |

---

## Writing New Tests

### API Integration Test Pattern

```python
class NewFeatureTests(APITestCase):
    def setUp(self):
        self.user = make_user("test@qw.ai")
        self.client = auth_client(self.user)
        self.portfolio = make_portfolio(self.user)

    def test_happy_path(self):
        resp = self.client.post(f"/api/v1/portfolio/{self.portfolio.id}/new-feature/", {
            "param": "value"
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("expected_field", resp.data)

    def test_unauthorized(self):
        self.client.credentials()
        resp = self.client.post(f"/api/v1/portfolio/{self.portfolio.id}/new-feature/", {})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_user_gets_404(self):
        other = make_user("other@qw.ai")
        other_portfolio = make_portfolio(other)
        resp = self.client.post(f"/api/v1/portfolio/{other_portfolio.id}/new-feature/", {})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
```

### AI Module Unit Test Pattern

```python
class MyNewModelTests(TestCase):
    def test_returns_valid_structure(self):
        from ai_models.my_new_model.model import MyNewModel
        model = MyNewModel()
        result = model.predict(["AAPL", "MSFT"], [0.6, 0.4])
        # Should not have an error key
        self.assertNotIn("error", result)
        # Should have expected keys
        self.assertIn("result_field", result)

    def test_handles_invalid_ticker(self):
        from ai_models.my_new_model.model import MyNewModel
        model = MyNewModel()
        result = model.predict(["INVALIDXXX"], [1.0])
        # Should gracefully return error dict, not raise
        self.assertIn("error", result)
```
