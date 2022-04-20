import base64
import json

import requests
from collections import OrderedDict
from decimal import Decimal
from typing import Dict, Any, Union
from django import forms
from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django_countries import countries
from pretix.base.decimal import round_decimal
from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import Order, Event, OrderPayment, OrderRefund
from pretix.base.payment import BasePaymentProvider
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import eventreverse


class UnzerSettingsHolder(BasePaymentProvider):
    identifier = 'unzer_settings'
    verbose_name = _('Unzer')
    is_enabled = False
    is_meta = True

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', 'unzer', event)

    @property
    def settings_form_fields(self):
        allcountries = list(countries)
        allcountries.insert(0, ('', _('Select country')))

        fields = [
            ('username',
             forms.CharField(
                 label=_('User name'),
                 validators=(),
                 help_text=_('ToDo'),
             )),
            ('password',
             SecretKeySettingsField(
                 label=_('Password'),
                 validators=(),
                 help_text=_('ToDo'),
             )),
        ]
        d = OrderedDict(
            fields + list(super().settings_form_fields.items())  # ToDo: add payment-methods
        )

        d.move_to_end('_enabled', last=False)
        return d  # ToDo


class UnzerMethod(BasePaymentProvider):
    identifier = ""
    method = ""
    verbose_name = ""  # ToDo
    # API:
    api_url = "api.unzerdirect.com/payments"
    version = "v10"

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', 'unzer', event)

    @property
    def headers(self):
        auth_token = ":".join([self.settings.get("username"), self.settings.get("password")])
        auth_token = auth_token.encode("UTF-8")
        auth_token = base64.b64encode(auth_token)
        return {
            "Accept-Version": self.version,
            "Authorization": "Basic " + str(auth_token),
        }

    @property
    def settings_form_fields(self):
        return {}

    @property
    def is_enabled(self) -> bool:  # ToDo: Check
        return self.settings.get('_enabled', as_type=bool) and self.settings.get('method_{}'.format(self.method))

    def is_allowed(self, request: HttpRequest, total: Decimal = None) -> bool:
        return super().is_allowed(request, total)

    def payment_form_render(self, request: HttpRequest, total: Decimal, order: Order = None) -> str:
        template = get_template("pretix_unzer/checkout_payment_form.html")  # ToDo: followup
        return template.render()

    def payment_is_valid_session(self, request: HttpRequest) -> bool:
        return False  # ToDo

    def checkout_prepare(self, request: HttpRequest, cart: Dict[str, Any]) -> Union[bool, str]:
        # Create Payment at Unzer:
        basket = {}
        for i in cart.get("positions"):
            basket[i] = {
                "qty": i["count"],
                "item_no": i,  # ToDo: is this meant to be like an index within the basket or a unique item number?
                "item_name": i,
                "item_price": i["total"] / i["count"],  # ToDo: is this what is actually wanted?
                "vat_rate": "ToDo",  # ToDo: where do I get the vat rate here?
            }
        payment_data = {
            "currency": self.event.currency,
            "order_id": "",  # ToDo: is this our order number? where is it at this point?
            "basket": basket,
        }
        unzer_payment = requests.post(self.api_url, headers=self.headers, data=payment_data)
        # ToDo: check answer and save ID from unzer_payment globally (to payment? order? what do we have for that?)
        # ------------------------------
        # Create Link for Authorization:
        link_data = {
            "amount": cart.get("total"),
            "continue_url": "",
            "cancel_url": "",
            "callback_url": "",
            "payment_methods": "",
        }
        unzer_payment_id = "ToDo"  # ToDo
        link_url = "/".join([
            self.api_url,
            unzer_payment_id,
            "link",
        ])
        link_response = requests.put(url=link_url, headers=self.headers, data=link_data)
        # Parse Response for Link:
        link_json = link_response.json()
        link_dict = json.loads(link_json)
        # Redirect customer:
        return link_dict["url"]

    def checkout_confirm_render(self, request, order: Order = None) -> str:
        template = get_template("pretix_unzer/checkout_payment_confirm.html")  # ToDo: display info in template
        ctx = {"request": request}
        return template.render(ctx)

    def execute_payment(self, request: HttpRequest, payment: OrderPayment) -> str:
        # Capture Payment:
        unzer_payment_id = "ToDo"  # ToDo
        url = "/".join([
            self.api_url,
            unzer_payment_id,
            "capture",
        ])
        capture_headers = self.headers
        capture_headers["QuickPay-Callback-Url"] = "ToDo"  # ToDo: create URLs (file)
        result = requests.post(url, headers=capture_headers)
        self.process_result(result)
        return redirect(
            eventreverse(
                self.event,
                "presale:event.order",
                kwargs={"order": payment.order.code, "secret": payment.order.secret},
            )
            + ("?paid=yes" if payment.order.status == Order.STATUS_PAID else "")
        )

    def api_payment_details(self, payment: OrderPayment):
        return None  # ToDo

    def matching_id(self, payment: OrderPayment):
        return None  # ToDo

    def payment_control_render(self, request: HttpRequest, payment: OrderPayment) -> str:
        return ""  # ToDo

    def payment_control_render_short(self, payment: OrderPayment) -> str:
        return ""  # ToDo

    def payment_refund_supported(self, payment: OrderPayment) -> bool:
        return False  # ToDo

    def payment_partial_refund_supported(self, payment: OrderPayment) -> bool:
        return False  # ToDo

    def execute_refund(self, refund: OrderRefund):
        pass  # ToDo

    def refund_control_render(self, request: HttpRequest, refund: OrderRefund) -> str:
        return ""  # ToDo

    def _amount_to_decimal(self, cents):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return round_decimal(float(cents) / (10 ** places), self.event.currency)

    def _decimal_to_int(self, amount):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return int(amount * 10 ** places)

    def process_result(self, result):
        pass  # ToDo
