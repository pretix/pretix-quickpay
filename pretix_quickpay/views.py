import hashlib
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pretix.base.models import Order
from pretix.multidomain.urlreverse import eventreverse


class QuickpayOrderView:
    def dispatch(self, request, *args, **kwargs):
        try:
            self.order = request.event.orders.get(code=kwargs["order"])
            if (
                hashlib.sha1(self.order.secret.lower().encode()).hexdigest()
                != kwargs["hash"].lower()
            ):
                raise Http404("Unknown order")
        except Order.DoesNotExist:
            # Do a hash comparison as well to harden timing attacks
            if (
                "abcdefghijklmnopq".lower()
                == hashlib.sha1("abcdefghijklmnopq".encode()).hexdigest()
            ):
                raise Http404("Unknown order")
            else:
                raise Http404("Unknown order")
        return super().dispatch(request, *args, **kwargs)

    @cached_property
    def pprov(self):
        return self.payment.payment_provider

    @property
    def payment(self):
        return get_object_or_404(
            self.order.payments,
            pk=self.kwargs["payment"],
            provider__istartswith=self.kwargs["payment_provider"],
        )

    def _redirect_to_order(self):
        return redirect(
            eventreverse(
                self.request.event,
                "presale:event.order",
                kwargs={"order": self.order.code, "secret": self.order.secret},
            )
            + ("?paid=yes" if self.order.status == Order.STATUS_PAID else "")
        )


@method_decorator(csrf_exempt, name="dispatch")
class ReturnView(QuickpayOrderView, View):
    def post(self, request, *args, **kwargs):
        self.pprov.get_current_payment(self.payment)
        return self._redirect_to_order()

    def get(self, request, *args, **kwargs):
        self.pprov.get_current_payment(self.payment)
        return self._redirect_to_order()


@method_decorator(csrf_exempt, name="dispatch")
class CallbackView(QuickpayOrderView, View):
    def post(self, request, *args, **kwargs):
        self.pprov.handle_callback(request, self.payment)
        return HttpResponse("[accepted]", status=200)
