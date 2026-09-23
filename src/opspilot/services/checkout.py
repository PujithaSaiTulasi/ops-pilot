"""Checkout API simulator."""

from opspilot.config import get_settings
from opspilot.services.common import create_service_app

settings = get_settings()
app = create_service_app(
    "checkout-api",
    "/checkout",
    "1.0.0",
    settings=settings,
    downstreams={
        "payment": settings.payment_url,
        "inventory": settings.inventory_url,
    },
)
