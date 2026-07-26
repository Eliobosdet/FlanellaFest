from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('register/', views.register, name='register'),
    path('checked-in-partecipants/', views.checked_in_partecipants, name='checked_in_partecipants'),
    path('participant/<int:pk>/', views.participant_detail, name='participant_detail'),
    path('check-qr/', views.check_qr, name='check_qr'),
    path('check-qr-result/', views.check_qr_result, name='check_qr_result'),
    path('all-participants', views.all_participants, name='all_participants'),
    path('all-participants/excel', views.export_participants_excel, name='export_participants_excel'),
    path('register/success/', views.payment_success, name='payment_success'),
    path('register/cancel/', views.payment_cancel, name='payment_cancel'),
    path('statuto/', views.statuto_view, name='statuto'),
    path('privacy-policy/', views.privacy_view, name='privacy'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('logout/', views.logout, name='logout'),
    path('admin-management/', views.admin_management, name='admin_management'),
    path('admin-management/test-stripe/', views.stripe_test_checkout, name='stripe_test_checkout')
]