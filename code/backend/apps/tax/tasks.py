"""Celery tasks for tax app."""

import logging

from celery import shared_task

logger = logging.getLogger("apps.tax")


@shared_task
def scan_harvest_opportunities():
    """Daily scan: find tax-loss harvesting opportunities across all portfolios."""
    from apps.accounts.tasks import create_notification
    from apps.portfolio.models import Holding

    # Find holdings with meaningful unrealized losses
    losers = Holding.objects.filter(
        portfolio__is_active=True, unrealized_pnl__lt=-100
    ).select_related("portfolio__user")

    notified_users = set()
    for holding in losers:
        user = holding.portfolio.user
        if not user.notify_tax_opportunities or str(user.id) in notified_users:
            continue
        notified_users.add(str(user.id))
        create_notification.delay(
            user_id=str(user.id),
            notification_type="tax_harvest",
            title="Tax-Loss Harvesting Opportunity",
            message=(
                f"{holding.ticker} has an unrealized loss of "
                f"${abs(float(holding.unrealized_pnl)):,.0f}. "
                "Review tax optimization to capture this loss."
            ),
            data={
                "portfolio_id": str(holding.portfolio_id),
                "ticker": holding.ticker,
                "unrealized_pnl": float(holding.unrealized_pnl),
            },
        )
    logger.info("Tax harvest scan: notified %d users", len(notified_users))
