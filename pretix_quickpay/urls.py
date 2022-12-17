from django.urls import include, re_path
from pretix.multidomain import event_url

from .views import CallbackView, ReturnView


def get_event_patterns(brand):
    return [
        re_path(
            r"^(?P<payment_provider>{})/".format(brand),
            include(
                [
                    event_url(
                        r"^return/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[^/]+)/$",
                        ReturnView.as_view(),
                        name="return",
                        require_live=False,
                    ),
                    event_url(
                        r"^callback/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[^/]+)/$",
                        CallbackView.as_view(),
                        name="callback",
                        require_live=False,
                    ),
                ]
            ),
        ),
    ]


event_patterns = get_event_patterns("quickpay")
