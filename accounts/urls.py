from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import sumup_views
from . import views_diagnostic

app_name = 'accounts'

urlpatterns = [
    # Registration
    path('register/customer/', views.register_customer, name='register_customer'),
    path('register/organiser/', views.register_organiser, name='register_organiser'),

    # Email verification
    path('verify/<uuid:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),

    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('organiser-dashboard/', views.organiser_dashboard, name='organiser_dashboard'),
    path('dashboard/', views.organiser_dashboard, name='dashboard'),  # Alias

    # SumUp OAuth Integration
    path('sumup/connect/', sumup_views.SumUpConnectView.as_view(), name='sumup_connect'),
    path('sumup/callback/', sumup_views.SumUpCallbackView.as_view(), name='sumup_callback'),
    path('sumup/disconnect/', sumup_views.SumUpDisconnectView.as_view(), name='sumup_disconnect'),
    path('sumup/status/', sumup_views.SumUpStatusView.as_view(), name='sumup_status'),

    # Diagnostic endpoints (superuser only)
    path('diagnostic/sumup-env/', views_diagnostic.check_sumup_env, name='diagnostic_sumup_env'),

    # Password reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             success_url='/accounts/password-reset/done/'
         ),
         name='password_reset'),
    
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/accounts/password-reset-complete/'
         ),
         name='password_reset_confirm'),
    
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]