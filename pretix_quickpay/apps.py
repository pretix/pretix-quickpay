from django.utils.translation import gettext_lazy
from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_quickpay"
    verbose_name = "Quickpay payments for pretix"

    class PretixPluginMeta:
        name = gettext_lazy("Quickpay")
        author = gettext_lazy("the pretix team")
        description = gettext_lazy(
            "Use Quickpay as a payment provider, where you can activate various payment methods for your customers."
        )
        visible = True
        version = __version__
        category = "PAYMENT"
        picture = "pretix_quickpay/logo.svg"
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


