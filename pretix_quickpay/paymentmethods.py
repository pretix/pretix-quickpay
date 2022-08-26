from django import forms
from django.utils.translation import gettext_lazy as _

from .payment import QuickpayMethod, QuickpaySettingsHolder

creditcard = _("Credit card")
debitcard = _("Debit card")

payment_methods = [
    {
        "method": "creditcard",
        "type": "other",
        "public_name": creditcard,
        "verbose_name": creditcard,
        "help_text": "Use this if you want your customers to choose any credit card brand that you have enabled in "
        "your payment provider's account.",
    },
    {
        "method": "american-express",
        "type": "other",
        "public_name": f"{creditcard}: American Express",
        "verbose_name": f"{creditcard}: American Express",
    },
    {
        "method": "dankort",
        "type": "other",
        "public_name": f"{creditcard}: Dankort",
        "verbose_name": f"{creditcard}: Dankort",
    },
    {
        "method": "diners",
        "type": "other",
        "public_name": f"{creditcard}: Diners Club",
        "verbose_name": f"{creditcard}: Diners Club",
    },
    {
        "method": "jcb",
        "type": "other",
        "public_name": f"{creditcard}: JCB",
        "verbose_name": f"{creditcard}: JCB",
    },
    {
        "method": "maestro",
        "type": "other",
        "public_name": f"{creditcard}: Maestro",
        "verbose_name": f"{creditcard}: Maestro",
    },
    {
        "method": "mastercard",
        "type": "other",
        "public_name": f"{creditcard}: Mastercard",
        "verbose_name": f"{creditcard}: Mastercard",
    },
    {
        "method": "mastercard-debet",  # sic?
        "type": "other",
        "public_name": f"{debitcard}: Mastercard",
        "verbose_name": f"{debitcard}: Mastercard",
    },
    {
        "method": "visa",
        "type": "other",
        "public_name": f"{creditcard}: Visa",
        "verbose_name": f"{creditcard}: Visa",
    },
    {
        "method": "visa-electron",
        "type": "other",
        "public_name": f"{debitcard}: Visa",
        "verbose_name": f"{debitcard}: Visa",
    },
    {
        "method": "fbg1886",
        "type": "other",
        "public_name": _("Forbrugsforeningen af 1886"),
        "verbose_name": _("Forbrugsforeningen af 1886"),
    },
    {
        "method": "apple-pay",
        "type": "other",
        "public_name": _("Apple Pay"),
        "verbose_name": _("Apple Pay"),
    },
    {
        "method": "google-pay",
        "type": "other",
        "public_name": _("Google Pay"),
        "verbose_name": _("Google Pay"),
    },
    {
        "method": "anyday-split",
        "type": "other",
        "public_name": _("ANYDAY Split"),
        "verbose_name": _("ANYDAY Split"),
    },
    {
        "method": "mobilepay",
        "type": "other",
        "public_name": _("MobilePay online"),
        "verbose_name": _("MobilePay online"),
    },
    {
        "method": "mobilepay-subscriptions",
        "type": "other",
        "public_name": _("MobilePay Subscriptions"),
        "verbose_name": _("MobilePay Subscriptions"),
    },
    {
        "method": "paypal",
        "type": "other",
        "public_name": _("PayPal"),
        "verbose_name": _("PayPal"),
    },
    {
        "method": "sofort",
        "type": "other",
        "public_name": _("Sofort"),
        "verbose_name": _("Sofort"),
    },
    {
        "method": "viabill",
        "type": "other",
        "public_name": _("ViaBill"),
        "verbose_name": _("ViaBill"),
    },
    {
        "method": "resurs",
        "type": "other",
        "public_name": _("Resurs Bank"),
        "verbose_name": _("Resurs Bank"),
    },
    {
        "method": "klarna-payments",
        "type": "other",
        "public_name": _("Klarna Payments"),
        "verbose_name": _("Klarna Payments"),
    },
    {
        "method": "bitcoin",
        "type": "other",
        "public_name": _("Bitcoin through Coinify"),
        "verbose_name": _("Bitcoin through Coinify"),
    },
    {
        "method": "swish",
        "type": "other",
        "public_name": _("Swish"),
        "verbose_name": _("Swish"),
    },
    {
        "method": "trustly",
        "type": "other",
        "public_name": _("Trustly"),
        "verbose_name": _("Trustly"),
    },
    {
        "method": "ideal",
        "type": "other",
        "public_name": _("iDEAL"),
        "verbose_name": _("iDEAL"),
    },
    {
        "method": "vipps",
        "type": "other",
        "public_name": _("Vipps"),
        "verbose_name": _("Vipps"),
    },
    {
        "method": "paysafecard",
        "type": "other",
        "public_name": _("Paysafecard"),
        "verbose_name": _("Paysafecard"),
    },
    {
        "method": "unzer-pay-later-invoice",
        "type": "other",
        "public_name": _("Unzer Pay Later Invoice"),
        "verbose_name": _("Unzer Pay Later Invoice"),
    },
]


def get_payment_method_classes(brand, payment_methods, baseclass, settingsholder):
    settingsholder.payment_methods_settingsholder = []
    for m in payment_methods:
        settingsholder.payment_methods_settingsholder.append(
            (
                "method_{}".format(m["method"]),
                forms.BooleanField(
                    label="{} {}".format(
                        '<span class="fa fa-credit-card"></span>'
                        if m["type"] in ["scheme", "meta"]
                        else "",
                        m["verbose_name"],
                    ),
                    help_text=_(
                        "Needs to be enabled in your payment provider's account first. {m_help_text}"
                    ).format(m_help_text=m.get("help_text", "")),
                    required=False,
                ),
            )
        )

    # We do not want the "scheme"-methods listed as a payment-method, since they are covered by the meta methods
    return [settingsholder] + [
        type(
            f'Quickpay{"".join(m["public_name"].split())}',
            (m["baseclass"] if "baseclass" in m else baseclass,),
            {
                "identifier": "{payment_provider}_{payment_method}".format(
                    payment_method=m["method"], payment_provider=brand.lower()
                ),
                "verbose_name": _("{payment_method} via {payment_provider}").format(
                    payment_method=m["verbose_name"], payment_provider=brand
                ),
                "public_name": m["public_name"],
                "method": m["method"],
                "type": m["type"],
            },
        )
        for m in payment_methods
        if m["type"] != "scheme"
    ]


payment_method_classes = get_payment_method_classes(
    "Quickpay", payment_methods, QuickpayMethod, QuickpaySettingsHolder
)
