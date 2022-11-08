from pretix_quickpay.paymentmethods import (
    get_payment_method_classes,
    payment_methods as payment_methods_repo,
)

from .payment import UnzerdirectMethod, UnzerdirectSettingsHolder

supported_methods = [
    # "creditcard", note: disabled so merchants can enable each card as needed
    "mastercard",
    "visa",
    "apple-pay",
    "google-pay",
    "klarna-payments",
    "paypal",
    "sofort",
    "unzer-pay-later-invoice",
]
payment_methods = [
    item for item in payment_methods_repo if item.get("method") in supported_methods
]

payment_method_classes = get_payment_method_classes(
    "Unzerdirect", payment_methods, UnzerdirectMethod, UnzerdirectSettingsHolder
)
