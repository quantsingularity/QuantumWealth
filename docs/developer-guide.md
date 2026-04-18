# Developer Guide

---

## Project Structure

```
QuantumWealth/
|-- code/
|   |-- backend/                    Django REST API
|   |   |-- quantumwealth/          Django project package
|   |   |   |-- settings/
|   |   |   |   |-- base.py         Shared settings
|   |   |   |   |-- development.py  Dev overrides (DEBUG=True, relaxed throttling)
|   |   |   |   |-- production.py   Production hardening (HSTS, SSL, JSON logging)
|   |   |   |-- celery.py           Celery application and beat schedule
|   |   |   |-- middleware.py       Request logging with X-Request-ID header
|   |   |   |-- pagination.py       StandardPagination (50 per page, max 200)
|   |   |   |-- exceptions.py       Unified error envelope handler
|   |   |   |-- logging.py          JSON log formatter for production
|   |   |   |-- urls.py             Root URL routing
|   |   |   |-- wsgi.py             Gunicorn entry point
|   |   |   |-- asgi.py             ASGI entry point (future async support)
|   |   |-- apps/
|   |   |   |-- accounts/           User, auth, risk profiling, notifications
|   |   |   |-- portfolio/          Portfolio, Holding, Transaction, Goal, Snapshot
|   |   |   |-- market/             Quote cache, Watchlist, price tasks
|   |   |   |-- risk/               Risk views (stateless, delegates to ai_models)
|   |   |   |-- advisor/            Advisor views and services
|   |   |   |-- tax/                Tax service, views, harvest tasks
|   |   |-- manage.py               Django management entry point
|   |   |-- requirements.txt        Python dependencies
|   |   |-- Dockerfile              Production container image
|   |   |-- Makefile                Developer task shortcuts
|   |   |-- .env.example            Environment variable template
|   |
|   |-- ai_models/                  AI and ML modules (Python package)
|       |-- __init__.py             Package exports
|       |-- requirements.txt        AI-specific Python dependencies
|       |-- portfolio_optimizer/
|       |   |-- optimizer.py        Mean-Variance, BL, Risk Parity, HRP
|       |-- risk_engine/
|       |   |-- engine.py           VaR, CVaR, Monte Carlo, Stress, Correlation
|       |-- robo_advisor/
|       |   |-- advisor.py          Goal planning, rebalancing engine
|       |-- market_predictor/
|       |   |-- predictor.py        Price forecasting, regime detection, RSI
|       |-- tax_optimizer/
|       |   |-- optimizer.py        Harvest scheduling, after-tax return model
|       |-- sentiment_analyzer/
|       |   |-- analyzer.py         VADER + momentum + volume + RSI composite
|       |-- factor_models/
|       |   |-- models.py           Fama-French OLS, sector decomposition, BHB
|       |-- backtester/
|       |   |-- backtester.py       Event-driven historical simulation
|       |-- anomaly_detector/
|           |-- detector.py         Isolation Forest, Z-score, transaction anomalies
|
|-- docs/                           Documentation
|   |-- overview.md
|   |-- api-reference.md
|   |-- ai-models.md
|   |-- database-schema.md
|   |-- architecture.md
|   |-- developer-guide.md          (this file)
|   |-- deployment.md
|   |-- testing.md
|   |-- changelog.md
|
|-- infrastructure/
|   |-- nginx/nginx.conf            Reverse proxy configuration
|   |-- postgres/init.sql           Database initialization script
|
|-- scripts/                        Utility scripts
|-- docker-compose.yml              Full-stack orchestration
|-- README.md                       Project root readme
```

---

## Adding a New API Endpoint

Follow these steps to add a new endpoint while keeping the codebase consistent.

### Step 1: Define the Model (if needed)

Add the model class to the relevant app's `models.py`. Always use:

- `uuid.uuid4` as the primary key default.
- `auto_now_add=True` for `created_at` and `auto_now=True` for `updated_at`.
- `DecimalField` with `max_digits=18, decimal_places=4` for financial values.

```python
class NewModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # ... fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "app_new_models"
        ordering = ["-created_at"]
```

### Step 2: Create Migration

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Write the Serializer

Add to `serializers.py`. Use `read_only_fields` for computed and auto-set fields.

```python
class NewModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewModel
        fields = ["id", "field1", "field2", "created_at"]
        read_only_fields = ["id", "created_at"]
```

### Step 4: Write the View

Add to `views.py`. Always use:

- `@extend_schema(tags=["app_name"])` for API documentation grouping.
- `permissions.IsAuthenticated` unless the endpoint is public.
- Filter querysets by the requesting user to prevent data leakage.

```python
@extend_schema(tags=["myapp"])
class NewModelView(generics.ListCreateAPIView):
    serializer_class = NewModelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NewModel.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

### Step 5: Register the URL

Add to `urls.py`:

```python
from .views import NewModelView
urlpatterns = [
    path("new/", NewModelView.as_view(), name="new-model-list"),
]
```

### Step 6: Register in Admin

Add to `admin.py`:

```python
@admin.register(NewModel)
class NewModelAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    search_fields = ("user__email",)
```

### Step 7: Write Tests

Add test cases to `apps/tests.py`:

```python
class NewModelTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)

    def test_create_success(self):
        resp = self.client.post("/api/v1/myapp/new/", {"field1": "value"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_isolation(self):
        other = make_user("other@t.ai")
        NewModel.objects.create(user=other, field1="x")
        resp = self.client.get("/api/v1/myapp/new/")
        self.assertEqual(resp.data["count"], 0)
```

---

## Adding a New AI Model Module

### Step 1: Create the Module Directory

```bash
mkdir code/ai_models/my_new_model
touch code/ai_models/my_new_model/__init__.py
touch code/ai_models/my_new_model/model.py
```

### Step 2: Implement the Module

All AI modules should:

- Accept plain Python data types (lists, dicts, floats) as inputs.
- Return plain Python dicts as outputs.
- Handle exceptions internally and return `{"error": "..."}` rather than raising.
- Log at `INFO` level on entry and `ERROR` level on failure.
- Be stateless (no Django model imports, no HTTP calls inside AI modules).

```python
import logging
logger = logging.getLogger("ai_models.my_new_model")

class MyNewModel:
    def predict(self, tickers: list, weights: list) -> dict:
        logger.info("Running MyNewModel for %d tickers", len(tickers))
        try:
            # ... computation
            return {"result": ..., "metadata": {...}}
        except Exception as e:
            logger.error("MyNewModel failed: %s", e)
            return {"error": str(e)}
```

### Step 3: Expose via a Django View

Create a view in the appropriate app that instantiates the model and calls it:

```python
from ai_models.my_new_model.model import MyNewModel

class MyNewModelView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIHeavyThrottle]

    def post(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        tickers = list(portfolio.holdings.values_list("ticker", flat=True))
        weights = [float(h.weight) for h in portfolio.holdings.all()]
        model = MyNewModel()
        return Response(model.predict(tickers, weights))
```

### Step 4: Export from Package Init

Add the class to `code/ai_models/__init__.py`:

```python
from .my_new_model.model import MyNewModel
```

---

## Code Style Guidelines

| Rule            | Tool            | Config                           |
| --------------- | --------------- | -------------------------------- |
| Line length     | Black           | 120 characters                   |
| Import ordering | isort           | black profile                    |
| Type hints      | Python standard | Preferred but not enforced       |
| Docstrings      | Google style    | For public classes and functions |
| Linting         | flake8          | max-line-length=120              |

Run formatters:

```bash
make format   # runs black and isort
make lint     # runs flake8
```

---

## Testing Guidelines

### Test File Organization

All tests live in `apps/tests.py`. Group tests by domain using `TestCase` subclasses.

| Test Class Pattern            | What to Test                                                         |
| ----------------------------- | -------------------------------------------------------------------- |
| `{Domain}Tests(APITestCase)`  | Integration tests against the REST API using an authenticated client |
| `{Model}ModelTests(TestCase)` | Unit tests for model methods and properties                          |
| `{Service}Tests(TestCase)`    | Unit tests for service and AI module functions                       |

### Authentication in Tests

Use the helper functions defined at the top of `tests.py`:

```python
user = make_user("test@example.com")
client = auth_client(user)  # Returns APIClient with Bearer token header
```

### Test Isolation

Each test method is wrapped in a database transaction that is rolled back after the test. Tests do not share state unless explicitly constructed to do so.

### Running Tests

```bash
# All tests
make test

# Specific test class
python manage.py test apps.tests.PortfolioTests --settings=quantumwealth.settings.development

# With coverage
make test-coverage
# Opens htmlcov/index.html
```

---

## Database Migrations

### Creating Migrations

```bash
python manage.py makemigrations
python manage.py makemigrations --name="descriptive_name"
```

### Applying Migrations

```bash
python manage.py migrate
python manage.py migrate accounts   # Apply only accounts app migrations
```

### Migration Best Practices

- Always review auto-generated migration files before committing.
- Use `--name` to give migrations descriptive names.
- Never edit or delete a migration that has been applied to a shared environment.
- For data migrations, use `RunPython` with both a forward and reverse function.
- Test migrations both forward (migrate) and backward (migrate app 000x) before merging.

---

## Error Handling Conventions

### In Views

Use DRF exceptions which produce appropriate HTTP status codes:

```python
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
raise NotFound("Portfolio not found.")
raise ValidationError({"amount": "Must be greater than zero."})
```

### In Services

Raise DRF exceptions that will be caught and formatted by the custom exception handler:

```python
from django.shortcuts import get_object_or_404
portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=user)
```

### In AI Modules

Return error dicts rather than raising:

```python
try:
    result = compute_something(tickers)
    return result
except Exception as e:
    logger.error("Computation failed: %s", e)
    return {"error": str(e)}
```

Views should check for the `"error"` key and return `400 Bad Request`:

```python
result = optimizer.optimize(tickers, strategy)
if "error" in result:
    return Response(result, status=status.HTTP_400_BAD_REQUEST)
return Response(result)
```
