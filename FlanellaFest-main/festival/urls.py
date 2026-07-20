from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('register/', views.register, name='register'),
    path('approved-requests/', views.approved_requests, name='approved_requests'),
    path('approved-partecipants/', views.approved_partecipants, name='approved_partecipants'),
    path('checked-in-partecipants/', views.checked_in_partecipants, name='checked_in_partecipants'),
    path('participant/<int:pk>/', views.participant_detail, name='participant_detail'),
    path('registration/<int:pk>/', views.registration_detail, name='registration_detail'),
    path('check-qr/', views.check_qr, name='check_qr'),
    path('check-qr-result/', views.check_qr_result, name='check_qr_result'),
    path('all-participants', views.all_participants, name='all_participants'),
    path('all-participants/pdf', views.all_participants_pdf, name='all_participants_pdf'),
    path('register/success/', views.payment_success, name='payment_success'),
    path('register/cancel/', views.payment_cancel, name='payment_cancel'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('logout/', views.logout, name='logout'),
    path('admin-management/', views.admin_management, name='admin_management'),
    path('admin-management/test-stripe/', views.stripe_test_checkout, name='stripe_test_checkout')
]
