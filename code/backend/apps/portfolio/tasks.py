"""Celery tasks for portfolio app."""

import logging

from celery import shared_task

logger = logging.getLogger("apps.portfolio")


@shared_task
def check_all_portfolio_drift():
    """Check all active portfolios for allocation drift; notify if threshold exceeded."""
    from ai_models.robo_advisor import compute_rebalance

    from .models import Portfolio

    portfolios = Portfolio.objects.filter(is_active=True).prefetch_related("holdings")
    logger.info("Checking drift for %d portfolios", portfolios.count())
    for portfolio in portfolios:
        if not portfolio.target_allocation:
            continue
        holdings_data = [
            {
                "ticker": h.ticker,
                "current_weight": float(h.weight),
                "market_value": float(h.market_value),
                "average_cost": float(h.average_cost),
                "current_price": float(h.current_price),
            }
            for h in portfolio.holdings.all()
        ]
        result = compute_rebalance(
            holdings=holdings_data,
            target_allocation=portfolio.target_allocation,
            portfolio_value=float(portfolio.total_value),
            drift_threshold=0.05,
        )
        if result["needs_rebalancing"]:
            from apps.accounts.tasks import create_notification

            create_notification.delay(
                user_id=str(portfolio.user_id),
                notification_type="rebalance",
                title=f"Portfolio '{portfolio.name}' needs rebalancing",
                message=f"Total drift: {result['total_drift']:.1%}. {len(result['trades'])} trades recommended.",
                data={
                    "portfolio_id": str(portfolio.id),
                    "drift": result["total_drift"],
                },
            )


@shared_task
def take_daily_snapshots():
    """Take daily portfolio value snapshots for all active portfolios."""
    from .models import Portfolio
    from .services import PortfolioService

    portfolios = Portfolio.objects.filter(is_active=True)
    for portfolio in portfolios:
        try:
            PortfolioService.take_snapshot(portfolio)
        except Exception as e:
            logger.error("Snapshot failed for portfolio %s: %s", portfolio.id, e)
