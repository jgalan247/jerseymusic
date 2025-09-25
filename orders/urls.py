from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Customer views
    path('my-orders/', views.CustomerOrderListView.as_view(), name='my_orders'),  # Changed name to 'my_orders'
    path('confirmation/<int:pk>/', views.OrderConfirmationView.as_view(), name='confirmation'),
    path('order/<str:order_number>/', views.OrderDetailView.as_view(), name='detail'),
    path('track/', views.GuestOrderTrackingView.as_view(), name='track'),
    path('order/<str:order_number>/refund/', views.RequestRefundView.as_view(), name='request_refund'),
    path('order/<str:order_number>/invoice/', views.DownloadInvoiceView.as_view(), name='download_invoice'),
    
    # Artist views (removed duplicates)
    path('artist/dashboard/', views.ArtistDashboardView.as_view(), name='artist_dashboard'),
    path('artist/orders/', views.ArtistOrderListView.as_view(), name='artist_list'),
    path('artist/order/<str:order_number>/', views.ArtistOrderDetailView.as_view(), name='artist_order_detail'),
    path('artist/refunds/', views.ArtistRefundListView.as_view(), name='artist_refund_list'),
    path('artist/refund/<int:refund_id>/', views.ArtistHandleRefundView.as_view(), name='artist_handle_refund'),
    path('artist/sales-report/', views.ArtistSalesReportView.as_view(), name='artist_sales_report'),
    path('artist/statistics/', views.OrderStatisticsView.as_view(), name='statistics'),
    path('artist-orders/', views.artist_orders, name='artist_orders'),
]