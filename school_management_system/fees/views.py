from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from .models import FeeStructure, FeePayment, FeeBalance
from .forms import FeeStructureForm
from students.models import Enrollment, Student, Guardian
from core.models import Term

def admin_required(user):
    return user.is_authenticated and (user.is_superadmin() or user.is_headteacher())

def bursar_required(user):
    return user.is_authenticated and (user.is_superadmin() or user.is_headteacher() or user.is_bursar())

def headteacher_bursar_required(user):
    return user.is_authenticated and (user.is_superadmin() or user.is_headteacher() or user.is_bursar())

@login_required
@user_passes_test(bursar_required)
def fee_structure_create(request):
    # Get current school for filtering grades
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    if request.method == "POST":
        form = FeeStructureForm(request.POST, school=school)
        if form.is_valid():
            form.save()
            return redirect("fee_list")
    else:
        form = FeeStructureForm(school=school)
    return render(request, "fees/fee_structure_form.html", {"form": form, "title": "Create Fee Structure"})

@login_required
@user_passes_test(bursar_required)
def fee_structure_edit(request, pk):
    fee = get_object_or_404(FeeStructure, pk=pk)
    # Get current school for filtering grades
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    if request.method == "POST":
        form = FeeStructureForm(request.POST, instance=fee, school=school)
        if form.is_valid():
            form.save()
            return redirect("fee_list")
    else:
        form = FeeStructureForm(instance=fee, school=school)
    return render(request, "fees/fee_structure_form.html", {"form": form, "title": "Edit Fee Structure"})

@login_required
@user_passes_test(admin_required)
def fee_view(request):
    fees = FeeStructure.objects.all()
    return render(request, "fees/fee_list.html", {"fees": fees, "title": "View Fees"})

@login_required
@user_passes_test(headteacher_bursar_required)
def fee_list(request):
    fees = FeeStructure.objects.all()
    return render(request, "fees/fee_list.html", {"fees": fees, "title": "Manage Fees"})


# Fee Payment and Balance Views
@login_required
@user_passes_test(headteacher_bursar_required)
def fee_balance_list(request):
    """View fee balances - accessible to headteacher and bursar"""
    # Get current school for filtering
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    term_id = request.GET.get('term')
    grade_id = request.GET.get('grade')
    
    balances = FeeBalance.objects.all()
    
    # Filter by school if not superadmin
    if school:
        balances = balances.filter(enrollment__grade__school=school)
    
    if term_id:
        balances = balances.filter(term_id=term_id)
    if grade_id:
        balances = balances.filter(enrollment__grade_id=grade_id)
    
    # Filter by payment status
    payment_status = request.GET.get('payment_status', '')
    if payment_status == 'paid':
        balances = balances.filter(is_paid=True, balance__lte=0)
    elif payment_status == 'defaulters':
        balances = balances.filter(balance__gt=0)
    elif payment_status == 'partial':
        balances = balances.filter(amount_paid__gt=0, balance__gt=0)
    
    balances = balances.select_related('enrollment__student', 'enrollment__grade', 'term')
    
    # Filter terms by school
    if school:
        terms = Term.objects.filter(academic_year__school=school).order_by('-academic_year__name', 'name')
    else:
        terms = Term.objects.filter(academic_year__is_active=True).order_by('-academic_year__name', 'name')
    from academics.models import Grade
    grades = Grade.objects.filter(school=school) if school else Grade.objects.all()
    
    # Get enrollments for the payment modal
    enrollments = Enrollment.objects.filter(is_active=True).select_related('student', 'grade')
    if school:
        enrollments = enrollments.filter(grade__school=school)
    
    context = {
        'balances': balances,
        'terms': terms,
        'grades': grades,
        'enrollments': enrollments,
        'selected_term': int(term_id) if term_id else None,
        'selected_grade': int(grade_id) if grade_id else None,
    }
    return render(request, "fees/fee_balance_list.html", context)

@login_required
def fee_payment_receipt_parent(request, pk):
    """Allow parents to view their child's receipt"""
    payment = get_object_or_404(FeePayment, pk=pk)
    
    # Check if this is the parent's child
    if request.user.is_parent():
        viewing_student_id = request.session.get('viewing_student_id')
        if viewing_student_id and payment.enrollment.student.id == viewing_student_id:
            # Parent viewing their child's receipt
            school_obj = payment.enrollment.grade.school if payment.enrollment.grade.school else None
            
            # Get fee balance
            fee_balance = None
            if payment.fee_structure and payment.fee_structure.term:
                fee_balance = FeeBalance.objects.filter(
                    enrollment=payment.enrollment,
                    term=payment.fee_structure.term
                ).first()
                if fee_balance:
                    fee_balance.calculate_balance()
            
            context = {
                'payment': payment,
                'school': school_obj,
                'student': payment.enrollment.student,
                'grade': payment.enrollment.grade,
                'fee_balance': fee_balance,
            }
            return render(request, "fees/receipt.html", context)
    
    messages.error(request, "You don't have permission to view this receipt!")
    return redirect('fee_balance_view')

@login_required
def fee_balance_view(request):
    """View fee balances - parents can see their children's balances"""
    if request.user.is_parent():
        # Parents see their children's fee balances (via student admission number)
        viewing_student_id = request.session.get('viewing_student_id')
        
        if viewing_student_id:
            student = Student.objects.filter(id=viewing_student_id).first()
            if student:
                enrollments = Enrollment.objects.filter(student=student, is_active=True)
                balances = FeeBalance.objects.filter(
                    enrollment__in=enrollments
                ).select_related('enrollment__student', 'term')
                
                # Get receipts for this student
                payments = FeePayment.objects.filter(
                    enrollment__in=enrollments
                ).select_related('enrollment__student', 'fee_structure__term').order_by('-payment_date')
            else:
                balances = FeeBalance.objects.none()
                payments = FeePayment.objects.none()
        else:
            # Fallback: try to find by guardian phone
            guardian_phone = request.user.username
            guardians = Guardian.objects.filter(phone__icontains=guardian_phone)
            students = Student.objects.filter(guardian__in=guardians)
            enrollments = Enrollment.objects.filter(student__in=students)
            balances = FeeBalance.objects.filter(
                enrollment__in=enrollments
            ).select_related('enrollment__student', 'term')
            
            # Get receipts for these students
            payments = FeePayment.objects.filter(
                enrollment__in=enrollments
            ).select_related('enrollment__student', 'fee_structure__term').order_by('-payment_date')
    elif request.user.is_student():
        # Students see their own fee balances
        student = getattr(request.user, 'student_profile', None)
        if student:
            enrollments = Enrollment.objects.filter(student=student)
            balances = FeeBalance.objects.filter(
                enrollment__in=enrollments
            ).select_related('enrollment__student', 'term')
        else:
            balances = FeeBalance.objects.none()
    else:
        # Admin/Headteacher/Bursar see all
        balances = FeeBalance.objects.all().select_related('enrollment__student', 'term')
    
    # Get payments/receipts for parents
    payments = None
    if request.user.is_parent():
        viewing_student_id = request.session.get('viewing_student_id')
        if viewing_student_id:
            student = Student.objects.filter(id=viewing_student_id).first()
            if student:
                enrollments = Enrollment.objects.filter(student=student, is_active=True)
                payments = FeePayment.objects.filter(
                    enrollment__in=enrollments
                ).select_related('enrollment__student', 'fee_structure__term', 'enrollment__grade').order_by('-payment_date')
    
    context = {
        'balances': balances,
        'payments': payments,
    }
    return render(request, "fees/fee_balance_view.html", context)

@login_required
@user_passes_test(headteacher_bursar_required)
def fee_payment_create(request):
    """Record fee payment"""
    # Get current school for filtering
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    if request.method == "POST":
        enrollment_id = request.POST.get('enrollment')
        amount_paid = request.POST.get('amount_paid')
        payment_method = request.POST.get('payment_method', 'cash')
        # Receipt number will be auto-generated by the model's save() method
        notes = request.POST.get('notes', '')
        term_id = request.POST.get('term')
        
        enrollment = get_object_or_404(Enrollment, id=enrollment_id)
        term = get_object_or_404(Term, id=term_id)
        
        # Get or create fee balance
        fee_balance, created = FeeBalance.objects.get_or_create(
            enrollment=enrollment,
            term=term,
            defaults={'total_fee': 0}
        )
        
        # Get fee structure for this grade and term
        fee_structure = FeeStructure.objects.filter(
            grade=enrollment.grade,
            term=term
        ).first()
        
        # Update total_fee from fee_structure if it exists
        if fee_structure:
            if fee_balance.total_fee == 0 or fee_balance.total_fee != fee_structure.amount:
                fee_balance.total_fee = fee_structure.amount
                fee_balance.save()
        
        # Create payment record (receipt_number will be auto-generated)
        payment = FeePayment.objects.create(
            enrollment=enrollment,
            fee_structure=fee_structure,
            amount_paid=amount_paid,
            payment_method=payment_method,
            receipt_number=None,  # Will be auto-generated by save() method
            notes=notes,
            recorded_by=request.user
        )
        
        # Update balance
        fee_balance.calculate_balance()
        
        messages.success(request, f"Payment of {amount_paid} recorded successfully!")
        # Redirect back to balance list with filters if they were set
        redirect_url = 'fee_balance_list'
        if term_id:
            redirect_url += f'?term={term_id}'
        if enrollment_id:
            redirect_url += f'&grade={enrollment.grade.id}' if term_id else f'?grade={enrollment.grade.id}'
        return redirect(redirect_url)
    
    # Get terms filtered by school
    if school:
        terms = Term.objects.filter(academic_year__school=school).order_by('-academic_year__name', 'name')
    else:
        terms = Term.objects.filter(academic_year__is_active=True).order_by('-academic_year__name', 'name')
    
    enrollments = Enrollment.objects.filter(is_active=True).select_related('student', 'grade')
    
    # Filter enrollments by school if not superadmin
    if school:
        enrollments = enrollments.filter(grade__school=school)
    
    context = {
        'terms': terms,
        'enrollments': enrollments,
        'school': school,
    }
    
    # If this is an AJAX request, return modal content only
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "fees/fee_payment_form.html", context)
    
    return render(request, "fees/fee_payment_form.html", context)

@login_required
@user_passes_test(headteacher_bursar_required)
def fee_payment_list(request):
    """List all fee payments"""
    # Get current school for filtering
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    payments = FeePayment.objects.all().select_related(
        'enrollment__student', 'enrollment__grade', 'enrollment__grade__school', 
        'fee_structure', 'recorded_by'
    ).order_by('-payment_date')
    
    # Filter by school if not superadmin
    if school:
        payments = payments.filter(enrollment__grade__school=school)
    
    context = {
        'payments': payments,
        'school': school,
    }
    return render(request, "fees/fee_payment_list.html", context)

@login_required
@user_passes_test(headteacher_bursar_required)
def fee_payment_edit(request, pk):
    """Edit fee payment"""
    payment = get_object_or_404(FeePayment, pk=pk)
    
    # Check permissions - ensure user has access to this school's payments
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    if school and payment.enrollment.grade.school != school:
        messages.error(request, "You don't have permission to edit this payment!")
        return redirect('fee_payment_list')
    
    if request.method == "POST":
        from django.http import JsonResponse
        from decimal import Decimal
        
        try:
            amount_paid = Decimal(request.POST.get('amount_paid', '0'))
            payment_method = request.POST.get('payment_method', 'cash')
            notes = request.POST.get('notes', '')
            
            if amount_paid <= 0:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Amount paid must be greater than 0'}, status=400)
                messages.error(request, 'Amount paid must be greater than 0')
                return redirect('fee_payment_list')
            
            payment.amount_paid = amount_paid
            payment.payment_method = payment_method
            payment.notes = notes
            payment.save()
            
            # Recalculate balance
            term = payment.fee_structure.term if payment.fee_structure else None
            if term:
                fee_balance = FeeBalance.objects.filter(
                    enrollment=payment.enrollment,
                    term=term
                ).first()
                if fee_balance:
                    fee_balance.calculate_balance()
            
            messages.success(request, "Payment updated successfully!")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Payment updated successfully!'})
            return redirect('fee_payment_list')
        except (ValueError, InvalidOperation) as e:
            error_msg = str(e) if str(e) else 'Invalid input. Please check your values.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('fee_payment_list')
    
    # Get terms filtered by school
    if school:
        terms = Term.objects.filter(academic_year__school=school).order_by('-academic_year__name', 'name')
    else:
        terms = Term.objects.filter(academic_year__is_active=True).order_by('-academic_year__name', 'name')
    
    enrollments = Enrollment.objects.filter(is_active=True).select_related('student', 'grade')
    if school:
        enrollments = enrollments.filter(grade__school=school)
    
    context = {
        'payment': payment,
        'terms': terms,
        'enrollments': enrollments,
        'school': school,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "fees/fee_payment_form.html", context)
    
    return render(request, "fees/fee_payment_form.html", context)

@login_required
@user_passes_test(headteacher_bursar_required)
def fee_payment_delete(request, pk):
    """Delete fee payment"""
    payment = get_object_or_404(FeePayment, pk=pk)
    
    # Check permissions
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    if school and payment.enrollment.grade.school != school:
        messages.error(request, "You don't have permission to delete this payment!")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'You don\'t have permission to delete this payment!'}, status=403)
        return redirect('fee_payment_list')
    
    # Store term for balance recalculation
    term = payment.fee_structure.term if payment.fee_structure else None
    enrollment = payment.enrollment
    
    if request.method == "POST":
        # Delete payment
        payment.delete()
        
        # Recalculate balance
        if term:
            fee_balance = FeeBalance.objects.filter(
                enrollment=enrollment,
                term=term
            ).first()
            if fee_balance:
                fee_balance.calculate_balance()
        
        messages.success(request, "Payment deleted successfully!")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': True, 'message': 'Payment deleted successfully!'})
        return redirect('fee_payment_list')
    
    # If GET request, show confirmation (handled by modal)
    return redirect('fee_payment_list')

@login_required
@user_passes_test(headteacher_bursar_required)
def fee_payment_receipt(request, pk):
    """Print receipt for fee payment"""
    payment = get_object_or_404(FeePayment, pk=pk)
    
    # Check permissions
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    if school and payment.enrollment.grade.school != school:
        messages.error(request, "You don't have permission to view this receipt!")
        return redirect('fee_payment_list')
    
    # Get school details
    school_obj = payment.enrollment.grade.school if payment.enrollment.grade.school else school
    
    # Get fee balance for this enrollment and term
    fee_balance = None
    if payment.fee_structure and payment.fee_structure.term:
        fee_balance = FeeBalance.objects.filter(
            enrollment=payment.enrollment,
            term=payment.fee_structure.term
        ).first()
        # Recalculate balance to ensure it's up to date
        if fee_balance:
            fee_balance.calculate_balance()
    
    context = {
        'payment': payment,
        'school': school_obj,
        'student': payment.enrollment.student,
        'grade': payment.enrollment.grade,
        'fee_balance': fee_balance,
    }
    
    return render(request, "fees/receipt.html", context)
