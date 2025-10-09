from django.urls import path
from django.views.generic import TemplateView
from . import views
from . import listing_fee_views

app_name = "events"

urlpatterns = [
    path("", views.home, name="home"),
    path("events/", views.events_list, name="events_list"),
    path("event/<int:pk>/", views.event_detail, name="event_detail"),
    path("create-event/", views.create_event, name="create_event"),
    path("my-events/", views.my_events, name="my_events"),

    # Listing fee payments
    path("event/<int:event_id>/pay-listing-fee/", listing_fee_views.pay_listing_fee, name="pay_listing_fee"),
    path("event/<int:event_id>/listing-fee/success/", listing_fee_views.listing_fee_success, name="listing_fee_success"),
    path("event/<int:event_id>/listing-fee/cancel/", listing_fee_views.listing_fee_cancel, name="listing_fee_cancel"),
    path("event/<int:event_id>/listing-fee/status/", listing_fee_views.listing_fee_status, name="listing_fee_status"),
    path("webhooks/listing-fee/", listing_fee_views.listing_fee_webhook, name="listing_fee_webhook"),
    path('pricing/', views.pricing, name='pricing'),
    # Additional pages
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("organisers/", views.organisers_list, name="organisers"),
    path("privacy/", TemplateView.as_view(template_name="events/privacy.html"), name="privacy"),
    path("terms/", TemplateView.as_view(template_name="events/terms.html"), name="terms"),
    path("refund-policy/", TemplateView.as_view(template_name="events/refund.html"), name="refund_policy"),
    path("why-choose-us/", TemplateView.as_view(template_name="why_choose_us.html"), name="why_choose_us"),
]