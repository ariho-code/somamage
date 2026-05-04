from django.contrib import admin
from .models import FeeStructure, FeePayment, FeeBalance

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('grade', 'term', 'amount', 'description')
    list_filter = ('grade', 'term')
    search_fields = ('grade__name', 'description')

@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'amount_paid', 'payment_date', 'payment_method', 'receipt_number', 'recorded_by')
    list_filter = ('payment_date', 'payment_method')
    search_fields = ('enrollment__student__admission_number', 'receipt_number')

@admin.register(FeeBalance)
class FeeBalanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'term', 'total_fee', 'amount_paid', 'balance', 'is_paid')
    list_filter = ('term', 'is_paid')
    search_fields = ('enrollment__student__admission_number',)
