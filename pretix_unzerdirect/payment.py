import logging
from django.utils.translation import gettext_lazy as _

from pretix_quickpay.payment import (
    QuickpayMethod as SuperQuickpayMethod,
    QuickpaySettingsHolder,
)

logger = logging.getLogger("pretix_unzerdirect")


class UnzerdirectSettingsHolder(QuickpaySettingsHolder):
    identifier = "unzerdirect_settings"
    verbose_name = _("Unzer Direct")
    is_enabled = False
    is_meta = True
    payment_methods_settingsholder = []


class UnzerdirectMethod(SuperQuickpayMethod):
    identifier = "unzerdirect"
