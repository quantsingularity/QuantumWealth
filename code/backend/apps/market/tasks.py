"""Celery tasks for market data refresh."""

import logging

from celery import shared_task

logger = logging.getLogger("apps.market")


@shared_task
def refresh_all_portfolio_prices():
    """Refresh current prices for all tickers held across active portfolios."""
    from apps.portfolio.models import Holding, Portfolio
    from django.utils import timezone

    from .services import MarketService

    tickers = list(
        Holding.objects.filter(portfolio__is_active=True)
        .values_list("ticker", flat=True)
        .distinct()
    )
    if not tickers:
        return

    logger.info("Refreshing prices for %d tickers", len(tickers))
    quotes = MarketService.get_quotes_bulk(tickers)

    for ticker, quote in quotes.items():
        if "error" in quote or not quote.get("price"):
            continue
        price = quote["price"]
        change = quote.get("change", 0) or 0
        change_pct = quote.get("change_pct", 0) or 0

        updated = Holding.objects.filter(
            ticker=ticker, portfolio__is_active=True
        ).update(
            current_price=price,
            day_change=change,
            day_change_pct=change_pct,
            price_updated_at=timezone.now(),
        )

        # Trigger portfolio recalculation
        from apps.portfolio.services import PortfolioService

        portfolios_with_ticker = Portfolio.objects.filter(
            holdings__ticker=ticker, is_active=True
        ).distinct()
        for portfolio in portfolios_with_ticker:
            try:
                portfolio.refresh_from_db()
                PortfolioService.recalculate_portfolio(portfolio)
            except Exception as e:
                logger.error("Recalc failed for portfolio %s: %s", portfolio.id, e)

    # Check price alerts
    check_price_alerts.delay(quotes)


@shared_task
def check_price_alerts(quotes: dict):
    """Check if any user price alerts have been triggered."""
    from apps.accounts.models import PriceAlert
    from apps.accounts.tasks import create_notification
    from django.utils import timezone

    alerts = PriceAlert.objects.filter(is_active=True, triggered_at__isnull=True)
    for alert in alerts:
        quote = quotes.get(alert.ticker)
        if not quote or not quote.get("price"):
            continue
        price = float(quote["price"])
        threshold = float(alert.threshold)
        triggered = False

        if alert.alert_type == "above" and price >= threshold:
            triggered = True
            msg = f"{alert.ticker} has risen above ${threshold:.2f}. Current: ${price:.2f}"
        elif alert.alert_type == "below" and price <= threshold:
            triggered = True
            msg = f"{alert.ticker} has dropped below ${threshold:.2f}. Current: ${price:.2f}"
        elif alert.alert_type == "change_pct":
            change_pct = abs(quote.get("change_pct", 0) or 0)
            if change_pct >= threshold:
                triggered = True
                msg = f"{alert.ticker} moved {change_pct:.1f}% today. Current: ${price:.2f}"

        if triggered:
            alert.triggered_at = timezone.now()
            alert.save(update_fields=["triggered_at"])
            create_notification.delay(
                user_id=str(alert.user_id),
                notification_type="price_alert",
                title=f"Price Alert: {alert.ticker}",
                message=msg,
                data={"ticker": alert.ticker, "price": price},
            )
