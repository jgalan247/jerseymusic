from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "events"

urlpatterns = [
    path("", views.home, name="home"),
    path("events/", views.events_list, name="events_list"),
    path("event/<int:pk>/", views.event_detail, name="event_detail"),
    path("create-event/", views.create_event, name="create_event"),
    path("my-events/", views.my_events, name="my_events"),

    # Additional pages
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("organisers/", views.organisers_list, name="organisers"),
    path("privacy/", TemplateView.as_view(template_name="events/privacy.html"), name="privacy"),
    path("terms/", TemplateView.as_view(template_name="events/terms.html"), name="terms"),
    path("refund-policy/", TemplateView.as_view(template_name="events/refund.html"), name="refund_policy"),
]