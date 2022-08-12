from django.conf.urls import include, url

from .views import CallbackView, ReturnView


def get_event_patterns(brand):
    return [
        url(
            r"^(?P<payment_provider>{})/".format(brand),
            include(
                [
                    url(
                        r"^return/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[^/]+)/$",
                        ReturnView.as_view(),
                        name="return",
                    ),
                    url(
                        r"^callback/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[^/]+)/$",
                        CallbackView.as_view(),
                        name="callback",
                    ),
                ]
            ),
        ),
    ]


event_patterns = get_event_patterns("quickpay")
