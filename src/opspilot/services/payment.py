"""Payment service simulator."""

from opspilot.config import get_settings
from opspilot.services.common import create_service_app

settings = get_settings()
app = create_service_app("payment-service", "/charge", "1.0.0", settings=settings)
