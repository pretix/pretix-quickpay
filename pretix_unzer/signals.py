from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _  # NoQA
from pretix.base.signals import logentry_display, register_payment_providers


@receiver(register_payment_providers, dispatch_uid="payment_unzer")
def register_payment_provider(sender, **kwargs):
    from .payment import UnzerSettingsHolder
    return UnzerSettingsHolder


@receiver(signal=logentry_display, dispatch_uid="payment_unzer_logentry_display")
def logentry_display(sender, logentry, **kwargs):
    if logentry.action_type != "pretix_unzer.event":
        return

    return _("Unzer reported an event")