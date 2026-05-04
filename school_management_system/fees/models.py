from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import random
import string

User = settings.AUTH_USER_MODEL

class FeeStructure(models.Model):
    grade = models.ForeignKey("academics.Grade", on_delete=models.CASCADE)
    term = models.ForeignKey("core.Term", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.grade} - {self.term} - {self.amount}"


class FeePayment(models.Model):
    """Track fee payments made by students"""
    enrollment = models.ForeignKey("students.Enrollment", on_delete=models.CASCADE, related_name='fee_payments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, null=True, blank=True)
    
    # Payment details
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    payment_method = models.CharField(
        max_length=50,
        choices=[
            ('cash', 'Cash'),
            ('bank', 'Bank Transfer'),
            ('mobile', 'Mobile Money'),
            ('cheque', 'Cheque'),
            ('other', 'Other'),
        ],
        default='cash'
    )
    receipt_number = models.CharField(max_length=100, unique=True, blank=True, null=True, db_index=True)
    notes = models.TextField(blank=True)
    
    # Recorded by
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='fee_payments_recorded')
    
    def generate_receipt_number(self):
        """Generate a unique receipt number"""
        if self.receipt_number:
            return self.receipt_number
        
        # Get school code if available
        school_code = ''
        if self.enrollment and self.enrollment.grade and self.enrollment.grade.school:
            school_code = self.enrollment.grade.school.code or ''
        
        # Generate unique receipt number: SCHOOL-YYYYMMDD-XXXXXX
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Try to create unique receipt number
        max_attempts = 10
        for attempt in range(max_attempts):
            if school_code:
                receipt_num = f"{school_code}-{date_str}-{random_str}"
            else:
                receipt_num = f"REC-{date_str}-{random_str}"
            
            # Check if receipt number already exists
            if not FeePayment.objects.filter(receipt_number=receipt_num).exists():
                self.receipt_number = receipt_num
                return receipt_num
            
            # Generate new random string if collision
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Fallback to UUID if all attempts fail
        receipt_num = f"REC-{date_str}-{str(uuid.uuid4())[:8].upper()}"
        self.receipt_number = receipt_num
        return receipt_num
    
    def save(self, *args, **kwargs):
        # Auto-generate receipt number if not provided
        if not self.receipt_number:
            self.generate_receipt_number()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.enrollment.student} - {self.amount_paid} - {self.receipt_number or 'No Receipt'}"


class FeeBalance(models.Model):
    """Track fee balances for students"""
    enrollment = models.OneToOneField("students.Enrollment", on_delete=models.CASCADE, related_name='fee_balance')
    term = models.ForeignKey("core.Term", on_delete=models.CASCADE)
    
    # Fee breakdown
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    is_paid = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('enrollment', 'term')
    
    def __str__(self):
        return f"{self.enrollment.student} - {self.term.name} - Balance: {self.balance}"
    
    def calculate_balance(self):
        """Calculate and update balance - balance = total_fee - amount_paid"""
        payments = FeePayment.objects.filter(
            enrollment=self.enrollment,
            fee_structure__term=self.term
        )
        total_paid = sum(payment.amount_paid for payment in payments)
        self.amount_paid = total_paid
        self.balance = self.total_fee - total_paid
        self.is_paid = (self.balance <= 0)
        self.save()
        return self.balance
    
    @property
    def payment_percentage(self):
        """Calculate percentage of fees paid (max 100%)"""
        if self.total_fee > 0:
            percentage = (self.amount_paid / self.total_fee) * 100
            return min(percentage, 100)
        return 0
