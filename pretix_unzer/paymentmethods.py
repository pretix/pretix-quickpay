from django import forms
from django.utils.translation import gettext_lazy as _

from .payment import UnzerMethod, UnzerSettingsHolder

payment_methods = [
    {
        "method": "creditcard",
        "type": "other",
        "public_name": _("Credit card"),
        "verbose_name": _("Credit card"),
    },
    # {
    #     "method": "american-express",
    #     "type": "other",
    #     "public_name": _("Credit card: American Express"),
    #     "verbose_name": _("Credit card: American Express"),
    # },
    # {
    #     "method": "dankort",
    #     "type": "other",
    #     "public_name": _("Credit card: Dankort"),
    #     "verbose_name": _("Credit card: Dankort"),
    # },
    # {
    #     "method": "diners",
    #     "type": "other",
    #     "public_name": _("Credit card: Diners Club"),
    #     "verbose_name": _("Credit card: Diners Club"),
    # },
    # {
    #     "method": "jcb",
    #     "type": "other",
    #     "public_name": _("Credit card: JCB"),
    #     "verbose_name": _("Credit card: JCB"),
    # },
    # {
    #     "method": "maestro",
    #     "type": "other",
    #     "public_name": _("Credit card: Maestro"),
    #     "verbose_name": _("Credit card: Maestro"),
    # },
    # {
    #     "method": "mastercard",
    #     "type": "other",
    #     "public_name": _("Credit card: Mastercard"),
    #     "verbose_name": _("Credit card: Mastercard"),
    # },
    # {
    #     "method": "mastercard-debet",  # sic?
    #     "type": "other",
    #     "public_name": _("Debit card: Mastercard"),
    #     "verbose_name": _("Debit card: Mastercard"),
    # },
    # {
    #     "method": "visa",
    #     "type": "other",
    #     "public_name": _("Credit card: Visa"),
    #     "verbose_name": _("Credit card: Visa"),
    # },
    # {
    #     "method": "visa-electron",
    #     "type": "other",
    #     "public_name": _("Debit card: Visa"),
    #     "verbose_name": _("Debit card: Visa"),
    # },
    {
        "method": "fbg1886",
        "type": "other",
        "public_name": _("Forbrugsforeningen af 1886"),
        "verbose_name": _("Forbrugsforeningen af 1886"),
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
                    required=False,
                ),
            )
        )

    # We do not want the "scheme"-methods listed as a payment-method, since they are covered by the meta methods
    return [settingsholder] + [
        type(
            f'Unzer{"".join(m["public_name"].split())}',
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
    "Unzer", payment_methods, UnzerMethod, UnzerSettingsHolder
)
