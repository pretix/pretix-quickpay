from collections import OrderedDict

from django import forms
from django.http import HttpRequest

from django.utils.translation import gettext_lazy as _
from django_countries import countries

from pretix.base.models import Order, Event
from pretix.base.payment import BasePaymentProvider
from pretix.base.plugins import get_all_plugins
from pretix.base.settings import SettingsSandbox


class UnzerSettingsHolder(BasePaymentProvider):
    def payment_is_valid_session(self, request: HttpRequest) -> bool:
        pass

    def checkout_confirm_render(self, request, order: Order = None) -> str:
        pass

    identifier = 'unzer_settings'
    verbose_name = _('Unzer')
    is_enabled = False
    is_meta = True

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', 'unzer', event)

    @property
    def settings_form_fields(self):
        return


class UnzerMethod(BasePaymentProvider):
    identifier = ''
    method = ''

    def payment_is_valid_session(self, request: HttpRequest) -> bool:
        pass

    def checkout_confirm_render(self, request, order: Order = None) -> str:
        pass

    @property
    def verbose_name(self) -> str:
        pass

