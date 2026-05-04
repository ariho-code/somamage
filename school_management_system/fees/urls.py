from django.urls import path
from fees import views

urlpatterns = [
    # Fee Structure
    path("", views.fee_list, name="fee_list"),
    path("create/", views.fee_structure_create, name="fee_structure_create"),
    path("edit/<int:pk>/", views.fee_structure_edit, name="fee_structure_edit"),
    path("view/", views.fee_view, name="fee_view"),
    path("status/", views.fee_balance_view, name="fee_status"),
    
    # Fee Payments and Balances
    path("balances/", views.fee_balance_list, name="fee_balance_list"),
    path("balance/view/", views.fee_balance_view, name="fee_balance_view"),
    path("payments/", views.fee_payment_list, name="fee_payment_list"),
    path("payments/add/", views.fee_payment_create, name="fee_payment_create"),
    path("payments/<int:pk>/edit/", views.fee_payment_edit, name="fee_payment_edit"),
    path("payments/<int:pk>/delete/", views.fee_payment_delete, name="fee_payment_delete"),
    path("payments/<int:pk>/receipt/", views.fee_payment_receipt, name="fee_payment_receipt"),
    path("payments/<int:pk>/receipt/parent/", views.fee_payment_receipt_parent, name="fee_payment_receipt_parent"),
]
