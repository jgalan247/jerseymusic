from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "artworks"

urlpatterns = [
    path("", views.home, name="home"),
    path("gallery/", views.gallery, name="gallery"),
    path("artwork/<int:pk>/", views.artwork_detail, name="artwork_detail"),  # Note: renamed from 'detail'
    path("upload/", views.artwork_upload, name="upload"),  # Using the actual function
    path("my-artworks/", views.my_artworks, name="my_artworks"),
    
    # Additional pages
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("artists/", views.artists_list, name="artists"),
    path("privacy/", TemplateView.as_view(template_name="artworks/privacy.html"), name="privacy"),
    path("terms/", TemplateView.as_view(template_name="artworks/terms.html"), name="terms"),
    path("refund-policy/", TemplateView.as_view(template_name="artworks/refund.html"), name="refund_policy"),
]