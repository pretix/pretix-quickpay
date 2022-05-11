import hashlib
import importlib
import json
from django.utils.timezone import now
from quickpay_api_client import QPClient
from collections import OrderedDict
from decimal import Decimal
from typing import Dict, Any, Union
from django.conf import settings
from django.http import HttpRequest
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django_countries import countries
from pretix.base.decimal import round_decimal
from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import Order, Event, OrderPayment, OrderRefund
from pretix.base.payment import BasePaymentProvider
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import eventreverse, build_absolute_uri


class UnzerSettingsHolder(BasePaymentProvider):
    identifier = 'unzer_settings'
    verbose_name = _('Unzer')
    is_enabled = False
    is_meta = True
    payment_methods_settingsholder = []

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', 'unzer', event)

    @property
    def settings_form_fields(self):
        allcountries = list(countries)
        allcountries.insert(0, ('', _('Select country')))

        fields = [
            ('apikey',
             SecretKeySettingsField(
                 label=_('Api-Key'),
                 validators=(),
                 help_text=_('Your Unzer API-key for an API user, '
                             'that is configured to have rights to access /payments functionality only'),
             )),
        ]
        d = OrderedDict(
            fields +
            self.payment_methods_settingsholder +
            list(super().settings_form_fields.items())
        )

        d.move_to_end('_enabled', last=False)
        return d


class UnzerMethod(BasePaymentProvider):
    identifier = ""
    method = ""
    verbose_name = ""

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', 'unzer', event)

    def _init_client(self):
        auth_token = ":{0}".format(self.settings.get("apikey"))
        client = QPClient(auth_token)
        return client

    @property
    def settings_form_fields(self):
        return {}

    @property
    def is_enabled(self) -> bool:
        if self.type == "meta":
            module = importlib.import_module(
                __name__.replace("unzer", self.identifier.split("_")[0]).replace(
                    ".payment", ".paymentmethods"
                )
            )
            for method in list(
                    filter(
                        lambda d: d["type"] in ["meta", "scheme"], module.payment_methods
                    )
            ):
                if self.settings.get("_enabled", as_type=bool) and self.settings.get(
                        "method_{}".format(method["method"]), as_type=bool
                ):
                    return True
            return False
        else:
            return self.settings.get("_enabled", as_type=bool) and self.settings.get(
                "method_{}".format(self.method), as_type=bool
            )

    def is_allowed(self, request: HttpRequest, total: Decimal = None) -> bool:
        return super().is_allowed(request, total)

    def payment_form_render(self, request: HttpRequest, total: Decimal, order: Order = None) -> str:
        template = get_template("pretix_unzer/checkout_payment_form.html")
        return template.render()

    def payment_is_valid_session(self, request: HttpRequest) -> bool:
        return True

    def checkout_prepare(self, request: HttpRequest, cart: Dict[str, Any]) -> Union[bool, str]:
        return True

    def checkout_confirm_render(self, request, order: Order = None) -> str:
        template = get_template("pretix_unzer/checkout_payment_confirm.html")
        ctx = {"request": request}
        return template.render(ctx)

    def execute_payment(self, request: HttpRequest, payment: OrderPayment) -> str:
        client = self._init_client()
        payment_data = {
            "currency": self.event.currency,
            "order_id": payment.full_id,
        }
        unzer_payment = client.post('/payments', body=payment_data)
        # Create Link for Authorization:
        ident = self.identifier.split("_")[0]
        return_url = build_absolute_uri(
            self.event,
            "plugins:pretix_{}:return".format(ident),
            kwargs={
                "order": payment.order.code,
                "hash": hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
                "payment": payment.pk,
                "payment_provider": ident,
            },
        )
        callback_url = build_absolute_uri(
            self.event,
            "plugins:pretix_{}:callback".format(ident),
            kwargs={
                "order": payment.order.code,
                "hash": hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
                "payment": payment.pk,
                "payment_provider": ident,
            },
        )
        link_data = {
            "amount": self._decimal_to_int(payment.amount),
            "continue_url": return_url,
            "cancel_url": return_url,
            "callback_url": callback_url,
            "payment_methods": self.method,
        }
        link = client.put('/payments/%s/link' % unzer_payment['id'], body=link_data)
        payment.info_data = client.get('/payments/%s' % unzer_payment['id'])
        payment.save(update_fields=["info"])
        # Redirect customer:
        return link['url']

    def api_payment_details(self, payment: OrderPayment):
        return {
            "id": payment.info_data.get("id", None),
        }

    def matching_id(self, payment: OrderPayment):
        return payment.info_data.get("id", None)

    def payment_control_render(self, request: HttpRequest, payment: OrderPayment) -> str:
        template = get_template("pretix_unzer/control.html")
        ctx = {
            "request": request,
            "event": self.event,
            "settings": self.settings,
            "payment_info": payment.info_data,
            "payment": payment,
            "method": self.method,
            "provider": self,
        }
        return template.render(ctx)

    def payment_control_render_short(self, payment: OrderPayment) -> str:
        payment_info = payment.info_data
        r = str(payment_info.get("id", ""))
        if payment_info.get("acquirer"):
            if r:
                r += " / "
            r += payment_info.get("acquirer")
        return r

    def payment_refund_supported(self, payment: OrderPayment) -> bool:
        if "id" in payment.info_data and "link" in payment.info_data and "amount" in payment.info_data.get("link"):
            return True
        return False

    def payment_partial_refund_supported(self, payment: OrderPayment) -> bool:
        if "id" in payment.info_data and "link" in payment.info_data and "amount" in payment.info_data.get("link"):
            return True
        return False

    def execute_refund(self, refund: OrderRefund):
        client = self._init_client()
        status, body, headers = client.post('/payments/%s/refund' % refund.payment.info_data.get("id"),
                                            body={"amount": self._decimal_to_int(refund.amount)},
                                            raw=True)
        # OK
        if status == 202:
            refund.info_data = json.loads(body)
            refund.save(update_fields=["info"])
            refund.done()
        # Error || Invalid parameters or Not authorized
        elif status == 400 or status == 403:
            refund.state = OrderRefund.REFUND_STATE_FAILED
            refund.execution_date = now()
            refund.info_data = json.loads(body)
            refund.save(update_fields=["state", "execution_date", "info"])
        else:
            refund.state = OrderRefund.REFUND_STATE_FAILED
            refund.execution_date = now()
            refund.info_data = json.loads(body)
            refund.save(update_fields=["state", "execution_date", "info"])

    def refund_control_render(self, request: HttpRequest, refund: OrderRefund) -> str:
        return self.payment_control_render(request, refund)

    def _amount_to_decimal(self, cents):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return round_decimal(float(cents) / (10 ** places), self.event.currency)

    def _decimal_to_int(self, amount):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return int(amount * 10 ** places)

    def _handle_state_change(self, payment: OrderPayment):
        state = payment.info_data.get("state")
        # if state == "rejected":
        # payment.fail()
        if state == "processed":
            if payment.info_data.get("balance") == self._decimal_to_int(payment.amount):  # ToDo: what about else?
                payment.confirm()

    def handle_callback(self, request: HttpRequest, payment: OrderPayment):
        # ToDo: validate "QuickPay-Checksum-Sha256"
        client = self._init_client()
        current_payment_info = payment.info_data
        new_payment_info = client.get('/payments/%s' % current_payment_info.get("id"))
        prev_payment_state = current_payment_info.get("state", "")
        new_payment_state = new_payment_info.get("state", "")
        # Save newest payment object to info
        payment.info_data = new_payment_info
        payment.save(update_fields=["info"])
        if new_payment_state != prev_payment_state:
            print(prev_payment_state, "=>", new_payment_state)  # ToDo
            self._handle_state_change(payment)

    def capture_payment(self, payment: OrderPayment):
        client = self._init_client()

        current_payment_info = payment.info_data
        new_payment_info = client.get('/payments/%s' % current_payment_info.get("id"))

        payment.info_data = new_payment_info
        payment.save(update_fields=["info"])

        if current_payment_info.get("order_id") == new_payment_info.get("order_id") \
                and payment.full_id == new_payment_info.get("order_id"):

            if new_payment_info.get("accepted") and new_payment_info.get("state") == "new":
                #    and self._decimal_to_int(payment.amount) == new_payment_info.get(operations->amount?):
                # ToDo: Check if payment and authorization amounts are the same

                ident = self.identifier.split("_")[0]
                callback_url = build_absolute_uri(
                    self.event,
                    "plugins:pretix_{}:callback".format(ident),
                    kwargs={
                        "order": payment.order.code,
                        "hash": hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
                        "payment": payment.pk,
                        "payment_provider": ident,
                    },
                )

                capture = client.post(
                    '/payments/%s/capture' % payment.info_data.get("id"),
                    headers={"QuickPay-Callback-Url": callback_url},
                    body={"amount": self._decimal_to_int(payment.amount)},
                )
                payment.info_data = capture
                payment.save(update_fields=["info"])

                if capture.get("state") == "processed" and capture.get("balance") == self._decimal_to_int(payment.amount):
                    payment.confirm()
            else:
                self._handle_state_change(payment)
