from typing import Any, Dict, Union

import hashlib
import hmac
import importlib
import json
import logging
from collections import OrderedDict
from decimal import Decimal
from django.conf import settings
from django.http import HttpRequest
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from pretix.base.decimal import round_decimal
from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import Event, Order, OrderPayment, OrderRefund
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import build_absolute_uri
from quickpay_api_client import QPClient

logger = logging.getLogger("pretix_quickpay")


class QuickpaySettingsHolder(BasePaymentProvider):
    identifier = "quickpay_settings"
    verbose_name = _("Quickpay")
    is_enabled = False
    is_meta = True
    payment_methods_settingsholder = []

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox("payment", self.identifier.split("_")[0], event)

    @property
    def settings_form_fields(self):
        fields = [
            (
                "privatekey",
                SecretKeySettingsField(
                    label=_("Private Key"),
                    help_text=_(
                        "Your merchant account's private key, "
                        "to be found in your payment provider's settings: "
                        "'Merchant' > scroll down to 'Merchant-Settings' and copy the key."
                    ),
                ),
            ),
            (
                "apikey",
                SecretKeySettingsField(
                    label=_("API Key"),
                    help_text=_(
                        "Your API key for an API user, "
                        "to be found in your payment provider's settings: 'User' where you select the 'System user' "
                        "that is configured to have rights to access only '/payments' functionality and copy it's key. "
                        "If you have no such user, please create one with the above mentioned permissions first."
                    ),
                ),
            ),
        ]
        d = OrderedDict(
            fields
            + self.payment_methods_settingsholder
            + list(super().settings_form_fields.items())
        )

        d.move_to_end("_enabled", last=False)
        return d


class QuickpayMethod(BasePaymentProvider):
    identifier = "quickpay"
    method = ""
    verbose_name = ""

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox("payment", self.identifier.split("_")[0], event)

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
                __name__.replace("quickpay", self.identifier.split("_")[0]).replace(
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

    def payment_form_render(
        self, request: HttpRequest, total: Decimal, order: Order = None
    ) -> str:
        template = get_template("pretix_quickpay/checkout_payment_form.html")
        return template.render()

    def payment_is_valid_session(self, request: HttpRequest) -> bool:
        return True

    def checkout_prepare(
        self, request: HttpRequest, cart: Dict[str, Any]
    ) -> Union[bool, str]:
        return True

    def checkout_confirm_render(self, request, order: Order = None) -> str:
        template = get_template("pretix_quickpay/checkout_payment_confirm.html")
        ctx = {"request": request}
        return template.render(ctx)

    def test_mode_message(self) -> str:
        return mark_safe(
            _(
                "The {ident} plugin is operating in test mode. You can use one of <a {cardargs}>many test "
                "cards</a> to perform a transaction. Be aware: If you use a different card, actual money may be "
                "transferred. The plugin does not accept payments from test cards outside of test mode, "
                "though {ident} will allow them to be entered. "
            ).format(
                ident=self.verbose_name,
                cardargs='href="https://learn.quickpay.net/tech-talk/appendixes/test/#credit-card-test-numbers" '
                'target="_blank"',
            )
        )

    def execute_payment(self, request: HttpRequest, payment: OrderPayment) -> str:
        client = self._init_client()
        payment_data = {
            "currency": self.event.currency,
            "order_id": payment.full_id,
        }
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
            "auto_capture": True,
        }
        try:
            # Create payment:
            quickpay_payment = client.post("/payments", body=payment_data)
            # Create Link for Authorization:
            link = client.put(
                "/payments/%s/link" % quickpay_payment["id"], body=link_data
            )
            payment.info_data = client.get("/payments/%s" % quickpay_payment["id"])
        except Exception as e:
            logger.exception("Quickpay Payments error: %s" % e)
            raise PaymentException(
                _(
                    "We had trouble communicating with the payment provider. Please try again and get in touch "
                    "with us if this problem persists."
                )
            )
        payment.save(update_fields=["info"])
        # Redirect customer:
        return link["url"]

    def api_payment_details(self, payment: OrderPayment):
        return {
            "id": payment.info_data.get("id", None),
        }

    def matching_id(self, payment: OrderPayment):
        return payment.info_data.get("id", None)

    def payment_pending_render(self, request, payment) -> str:
        if payment.info:
            payment_info = json.loads(payment.info)
        else:
            payment_info = None
        template = get_template("pretix_quickpay/pending.html")
        ctx = {
            "payment_info": payment_info,
            "payment": payment,
            "operation": payment_info.get("operations")[-1],
        }
        return template.render(ctx)

    def payment_control_render(
        self, request: HttpRequest, payment: OrderPayment
    ) -> str:
        template = get_template("pretix_quickpay/control.html")
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
        if (
            "id" in payment.info_data
            and "link" in payment.info_data
            and "amount" in payment.info_data.get("link")
        ):
            return True
        return False

    def payment_partial_refund_supported(self, payment: OrderPayment) -> bool:
        if (
            "id" in payment.info_data
            and "link" in payment.info_data
            and "amount" in payment.info_data.get("link")
        ):
            return True
        return False

    def execute_refund(self, refund: OrderRefund):
        client = self._init_client()
        try:
            status, body, headers = client.post(
                "/payments/%s/refund" % refund.payment.info_data.get("id"),
                body={"amount": self._decimal_to_int(refund.amount)},
                raw=True,
            )
        except Exception as e:
            logger.exception("Quickpay Payments error: %s" % e)
            raise PaymentException(
                _(
                    "We had trouble communicating with the payment provider. Please try again and get in touch "
                    "with us if this problem persists."
                )
            )

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
        return round_decimal(float(cents) / (10**places), self.event.currency)

    def _decimal_to_int(self, amount):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return int(amount * 10**places)

    def _handle_state_change(self, payment: OrderPayment):
        state = payment.info_data.get("state")
        if state == "rejected":
            payment.fail()
        elif state == "pending":
            payment.state = OrderPayment.PAYMENT_STATE_PENDING
            payment.save(update_fields=["state"])
        elif state == "processed":
            if payment.info_data.get("balance") == self._decimal_to_int(payment.amount):
                if payment.info_data.get("test_mode") == payment.order.testmode:
                    payment.confirm()
                else:
                    payment.fail()
            else:
                operations = payment.info_data.get("operations", "")
                for operation in operations:
                    if (
                        operation.get("type") == "capture"
                        and int(operation.get("qp_status_code")) >= 40000
                    ):
                        payment.fail()

    def handle_callback(self, request: HttpRequest, payment: OrderPayment):
        # Checksum validation
        request_body = request.body
        checksum = hmac.new(
            self.settings.get("privatekey").encode("UTF-8"),
            request_body,
            hashlib.sha256,
        ).hexdigest()
        validated = checksum == request.headers.get("QuickPay-Checksum-Sha256")
        if validated:
            payment.order.log_action(
                f"pretix_{self.identifier.split('_')[0]}.event",
                data=json.loads(request.body.decode("utf-8")),
            )
            self.get_current_payment(payment)
        else:
            logger.warning("Quickpay Callback with invalid checksum: %s", request_body)

    def get_current_payment(self, payment):
        current_payment_info = payment.info_data
        payment_id = current_payment_info.get("id")
        try:
            client = self._init_client()
            # get the current info from provider, as we can run into race conditions here
            new_payment_info = client.get("/payments/%s" % payment_id)
        except Exception as e:
            logger.exception("Quickpay Payments error: %s" % e)
            return
        # Save newest payment object to info
        payment.info_data = new_payment_info
        payment.save(update_fields=["info"])
        prev_payment_state = current_payment_info.get("state", "")
        new_payment_state = new_payment_info.get("state", "")
        if new_payment_state != prev_payment_state:
            self._handle_state_change(payment)
