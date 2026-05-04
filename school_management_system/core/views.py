from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from django.contrib import messages
from .models import School, AcademicYear, Term
from students.models import Student, Guardian

def admin_required(user):
    return user.is_authenticated and (user.is_superadmin() or user.is_headteacher())

@login_required
def dashboard(request):
    """Enhanced dashboard with real statistics based on user role"""
    from django.contrib.auth import get_user_model
    from students.models import Student, Enrollment
    from academics.models import Grade, Subject, MarkEntry, ReportCard
    from fees.models import FeePayment, FeeBalance
    from timetable.models import TimetableSlot
    from datetime import datetime, timedelta
    from django.utils import timezone
    from django.db.models import Count, Avg, Sum, Q, Max, Min
    
    User = get_user_model()
    context = {"title": "Dashboard"}
    
    # Get school for current user
    school = request.user.school if hasattr(request.user, 'school') and request.user.school else None
    
    # Add academic years and terms for all users
    if school:
        academic_years = AcademicYear.objects.filter(school=school).order_by('-name')
    else:
        academic_years = AcademicYear.objects.all().order_by('-name')
    
    # Get selected academic year and terms
    selected_academic_year_id = request.session.get('selected_academic_year_id')
    selected_academic_year = None
    terms_for_selected_year = []
    
    if selected_academic_year_id:
        try:
            selected_academic_year = AcademicYear.objects.get(pk=selected_academic_year_id)
            terms_for_selected_year = Term.objects.filter(academic_year=selected_academic_year).order_by('name')
        except AcademicYear.DoesNotExist:
            pass
    
    context.update({
        'academic_years': academic_years,
        'selected_academic_year': selected_academic_year,
        'terms_for_selected_year': terms_for_selected_year,
    })
    
    # Common statistics
    if school:
        students = Student.objects.filter(enrollments__grade__school=school, enrollments__is_active=True).distinct()
        teachers = User.objects.filter(school=school, role='teacher')
        grades = Grade.objects.filter(school=school)
        enrollments = Enrollment.objects.filter(grade__school=school, is_active=True)
    else:
        students = Student.objects.filter(enrollments__is_active=True).distinct()
        teachers = User.objects.filter(role='teacher')
        grades = Grade.objects.all()
        enrollments = Enrollment.objects.filter(is_active=True)
    
    # Real statistics
    total_students = students.count()
    total_teachers = teachers.count()
    total_grades = grades.count()
    
    # Fee statistics
    if school:
        fee_balances = FeeBalance.objects.filter(enrollment__grade__school=school, enrollment__is_active=True).distinct()
        fee_payments_total = FeePayment.objects.filter(enrollment__grade__school=school).aggregate(total=Sum('amount_paid'))['total'] or 0
    else:
        fee_balances = FeeBalance.objects.all()
        fee_payments_total = FeePayment.objects.all().aggregate(total=Sum('amount_paid'))['total'] or 0
    
    total_fees_due = fee_balances.aggregate(total=Sum('total_fee'))['total'] or 0
    total_fees_paid = fee_balances.aggregate(total=Sum('amount_paid'))['total'] or fee_payments_total
    # Cap fee collection rate at 100%
    fee_collection_rate = min((total_fees_paid / total_fees_due * 100) if total_fees_due > 0 else 0, 100)
    
    # Academic statistics
    if school:
        active_year = Enrollment.objects.filter(grade__school=school, is_active=True).first()
        active_academic_year = active_year.academic_year if active_year else None
    else:
        active_academic_year = AcademicYear.objects.filter(is_active=True).first()
    
    context.update({
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_grades': total_grades,
        'fee_collection_rate': round(fee_collection_rate, 1),
        'total_fees_due': total_fees_due,
        'total_fees_paid': total_fees_paid,
        'school': school,
        'total_report_cards': ReportCard.objects.filter(enrollment__grade__school=school).count() if school else ReportCard.objects.count(),
    })

    # Dashboard add-ons: Timetable + recent activity
    try:
        today_weekday = timezone.localdate().weekday()
        now_time = timezone.localtime().time()
        DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        if request.user.is_teacher():
            all_slots = TimetableSlot.objects.filter(
                teacher=request.user
            ).select_related('subject', 'grade').order_by('day_of_week', 'start_time')
        elif school:
            all_slots = TimetableSlot.objects.filter(
                grade__school=school
            ).select_related('subject', 'grade', 'teacher').order_by('day_of_week', 'start_time')
        else:
            all_slots = TimetableSlot.objects.none()

        # Build today's schedule (compact list for hero panel)
        today_schedule = []
        # Full week timetable grouped by day
        week_timetable = {i: [] for i in range(6)}
        for s in all_slots:
            entry = {
                "start": s.start_time.strftime("%H:%M"),
                "end": s.end_time.strftime("%H:%M"),
                "start_time": s.start_time,
                "end_time": s.end_time,
                "subject": getattr(s.subject, "name", "Subject"),
                "grade": getattr(s.grade, "name", "Class"),
                "room": getattr(s, "room", "") or "",
                "day": s.day_of_week,
            }
            week_timetable[s.day_of_week].append(entry)
            if s.day_of_week == today_weekday:
                status = "Now" if s.start_time <= now_time <= s.end_time else "Upcoming"
                entry_today = dict(entry)
                entry_today["status"] = status
                today_schedule.append(entry_today)

        # Convert week_timetable to ordered list with day names
        week_days = []
        for day_idx, slots in week_timetable.items():
            if slots or day_idx == today_weekday:
                week_days.append({
                    'day_idx': day_idx,
                    'day_name': DAY_NAMES[day_idx],
                    'is_today': day_idx == today_weekday,
                    'slots': slots,
                })

        context["today_schedule"] = today_schedule
        context["today_schedule_count"] = len(today_schedule)
        context["week_timetable"] = week_days
        context["today_day_name"] = DAY_NAMES[today_weekday]

        from core.models import Notification
        notif_qs = Notification.objects.filter(user=request.user).order_by('-created_at')[:4]
        icon_map = {
            "academic": "fas fa-user-graduate",
            "fee": "fas fa-dollar-sign",
            "attendance": "fas fa-calendar-check",
            "system": "fas fa-gear",
            "success": "fas fa-circle-check",
            "warning": "fas fa-triangle-exclamation",
            "error": "fas fa-circle-xmark",
            "info": "fas fa-circle-info",
        }
        recent_activity = []
        for n in notif_qs:
            recent_activity.append({
                "title": n.title,
                "message": (n.message[:80] + "…") if n.message and len(n.message) > 80 else (n.message or ""),
                "time": timezone.localtime(n.created_at).strftime("%H:%M"),
                "icon": icon_map.get(getattr(n, "notification_type", "info"), "fas fa-circle-info"),
            })
        context["recent_activity"] = recent_activity
    except Exception:
        context["today_schedule"] = []
        context["today_schedule_count"] = 0
        context["week_timetable"] = []
        context["today_day_name"] = ""
        context["recent_activity"] = []
    
    # Role-specific dashboard content
    if request.user.is_headteacher() or request.user.is_superadmin():
        # Headteacher/Admin statistics
        # Filter subjects by school level
        if school:
            # Get distinct levels in this school
            school_levels = Grade.objects.filter(school=school).values_list('level', flat=True).distinct()
            subjects = Subject.objects.filter(level__in=school_levels)
            recent_payments = FeePayment.objects.filter(enrollment__grade__school=school).select_related('enrollment__student')[:5]
        else:
            subjects = Subject.objects.all()
            recent_payments = FeePayment.objects.all().select_related('enrollment__student')[:5]
        
        # Group subjects by level
        subjects_by_level = {}
        # Use the defined choices from the Grade model
        level_choices = Grade._meta.get_field('level').choices
        for level_choice, level_name in level_choices:
            subjects_by_level[level_name] = subjects.filter(level=level_choice).count()

        total_subjects = subjects.count()
        context.update({
            'subjects_by_level': subjects_by_level,
            'total_subjects': total_subjects,
        })
        
        # Performance statistics
        if school:
            report_cards = ReportCard.objects.filter(enrollment__grade__school=school)
            enrollments_for_chart = enrollments
        else:
            report_cards = ReportCard.objects.all()
            enrollments_for_chart = Enrollment.objects.all()
        
        avg_performance = report_cards.aggregate(avg=Avg('average_score'))['avg'] or 0
        total_report_cards = report_cards.count()
        
        # Performance by grade for charts
        performance_by_grade = {}
        grade_student_counts = {}
        for enrollment in enrollments_for_chart[:100]:  # Limit for performance
            grade_name = enrollment.grade.name
            if grade_name not in performance_by_grade:
                performance_by_grade[grade_name] = []
                grade_student_counts[grade_name] = 0
            
            card = ReportCard.objects.filter(enrollment=enrollment).first()
            if card:
                performance_by_grade[grade_name].append(float(card.average_score))
            grade_student_counts[grade_name] += 1
        
        # Calculate averages per grade
        grade_averages = {}
        for grade_name, scores in performance_by_grade.items():
            if scores:
                grade_averages[grade_name] = sum(scores) / len(scores)
        
        # Subject performance data
        subject_performance = {}
        if school:
            marks = MarkEntry.objects.filter(enrollment__grade__school=school).select_related('subject')
        else:
            marks = MarkEntry.objects.all().select_related('subject')
        
        for mark in marks[:500]:  # Limit for performance
            subject_name = mark.subject.name
            if subject_name not in subject_performance:
                subject_performance[subject_name] = []
            # MarkEntry has 'score' field, not 'total_score'
            subject_performance[subject_name].append(float(mark.score))
        
        subject_averages = {}
        for subject_name, scores in subject_performance.items():
            if scores:
                subject_averages[subject_name] = sum(scores) / len(scores)
        
        # Convert to JSON-serializable format for charts
        import json
        grade_averages_json = json.dumps({k: round(v, 2) for k, v in grade_averages.items()})
        subject_averages_json = json.dumps({k: round(v, 2) for k, v in list(subject_averages.items())[:10]})
        
        context.update({
            'total_subjects': total_subjects,
            'recent_payments': recent_payments,
            'avg_performance': round(avg_performance, 2),
            'total_report_cards': total_report_cards,
            'grade_averages': grade_averages,
            'subject_averages': subject_averages,
            'grade_student_counts': grade_student_counts,
            'grade_averages_json': grade_averages_json,
            'subject_averages_json': subject_averages_json,
        })
    
    elif request.user.is_teacher():
        # Check if teacher is a class teacher
        class_grades = Grade.objects.filter(class_teacher=request.user)
        is_class_teacher = class_grades.exists()
        
        if is_class_teacher:
            # Class teacher dashboard - restricted view
            class_enrollments = Enrollment.objects.filter(grade__in=class_grades, is_active=True)
            class_students_count = class_enrollments.values('student').distinct().count()
            
            # Get report cards for this class only
            teacher_report_cards = ReportCard.objects.filter(enrollment__in=class_enrollments).select_related('enrollment__student', 'term').order_by('-term__academic_year__name', '-term__name')[:10]
            total_report_cards = ReportCard.objects.filter(enrollment__in=class_enrollments).count()
            
            # Get class name(s) for display
            class_names = ", ".join([g.name for g in class_grades])
            
            context.update({
                'is_class_teacher': True,
                'class_grades': class_grades,
                'class_names': class_names,
                'class_students_count': class_students_count,
                'teacher_report_cards': teacher_report_cards,
                'total_report_cards': total_report_cards,
            })
        else:
            # Subject teacher dashboard - normal view
            # Teacher-specific: Upcoming timetable slots
            now = timezone.now()
            today_date = now.date()
            current_time = now.time()
            day_of_week = today_date.weekday()  # Monday=0, Sunday=6
            
            # Get teacher's timetable for today
            today_slots = TimetableSlot.objects.filter(
                teacher=request.user,
                day_of_week=day_of_week
            ).filter(
                start_time__gte=current_time
            ).order_by('start_time')[:5]
            
            # Get next lesson (most immediate)
            next_lesson = today_slots.first() if today_slots else None
            
            # Get upcoming slots for this week
            upcoming_slots = []
            for day in range(day_of_week, 7):
                slots = TimetableSlot.objects.filter(
                    teacher=request.user,
                    day_of_week=day
                ).order_by('start_time')
                if day == day_of_week:
                    slots = slots.filter(start_time__gte=current_time)
                upcoming_slots.extend(slots[:3])
            
            # Teacher's mark entries
            teacher_marks = MarkEntry.objects.filter(teacher=request.user)
            total_marks_entered = teacher_marks.count()
            
            context.update({
                'is_class_teacher': False,
                'today_slots': today_slots,
                'next_lesson': next_lesson,
                'upcoming_slots': upcoming_slots[:5],
                'total_marks_entered': total_marks_entered,
            })
    
    elif request.user.is_bursar():
        # Bursar statistics
        outstanding_balances = fee_balances.filter(balance__gt=0).count()
        paid_balances = fee_balances.filter(is_paid=True).count()
        
        context.update({
            'outstanding_balances': outstanding_balances,
            'paid_balances': paid_balances,
        })
    
    elif request.user.is_student():
        # Student-specific: their own data
        student_profile = getattr(request.user, 'student_profile', None)
        if student_profile:
            student_enrollments = Enrollment.objects.filter(student=student_profile, is_active=True)
            student_report_cards = ReportCard.objects.filter(enrollment__in=student_enrollments)
            
            # Student's timetable
            if student_enrollments.exists():
                current_enrollment = student_enrollments.first()
                today_date = timezone.now().date()
                today_slots = TimetableSlot.objects.filter(
                    grade=current_enrollment.grade,
                    day_of_week=today_date.weekday()
                ).order_by('start_time')
                
                context.update({
                    'student_report_cards': student_report_cards[:5],
                    'today_slots': today_slots,
                })
    
    elif request.user.is_parent():
        # Parent: children's information - only show their children's data
        # Try to find students by guardian phone (parent username)
        guardian_phone = request.user.username
        guardians = Guardian.objects.filter(phone__icontains=guardian_phone)
        children = Student.objects.filter(guardian__in=guardians)
        
        # Get terms for parent's children's school
        if children.exists():
            child_school = children.first().enrollments.filter(is_active=True).first()
            if child_school:
                school = child_school.grade.school
                if school:
                    parent_academic_years = AcademicYear.objects.filter(school=school).order_by('-name')
                    selected_academic_year_id = request.session.get('selected_academic_year_id')
                    if selected_academic_year_id:
                        try:
                            selected_academic_year = AcademicYear.objects.get(pk=selected_academic_year_id, school=school)
                            terms_for_selected_year = Term.objects.filter(academic_year=selected_academic_year).order_by('name')
                        except AcademicYear.DoesNotExist:
                            terms_for_selected_year = []
                    else:
                        # Use active academic year
                        active_year = parent_academic_years.filter(is_active=True).first()
                        if active_year:
                            selected_academic_year = active_year
                            terms_for_selected_year = Term.objects.filter(academic_year=active_year).order_by('name')
                        else:
                            terms_for_selected_year = []
                else:
                    parent_academic_years = AcademicYear.objects.none()
                    terms_for_selected_year = []
            else:
                parent_academic_years = AcademicYear.objects.none()
                terms_for_selected_year = []
        else:
            parent_academic_years = AcademicYear.objects.none()
            terms_for_selected_year = []
        
        context.update({
            'children': children,
            'academic_years': parent_academic_years,
            'terms_for_selected_year': terms_for_selected_year,
        })
    
    return render(request, "dashboard.html", context)

@login_required
@user_passes_test(admin_required)
def school_settings(request):
    from .forms import SchoolForm
    # Get school for current user (superadmin sees first school, others see their school)
    if request.user.is_superadmin():
        school = School.objects.first()
    else:
        school = getattr(request.user, 'school', None) or School.objects.first()
    
    if request.method == "POST":
        form = SchoolForm(request.POST, request.FILES, instance=school)
        if form.is_valid():
            form.save()
            return redirect("school_settings")
    else:
        form = SchoolForm(instance=school)
    
    # Filter academic years and terms by school
    if school:
        academic_years = AcademicYear.objects.filter(school=school).order_by('-name')
        # Get all terms for all academic years of this school
        terms = Term.objects.filter(academic_year__school=school).select_related('academic_year').order_by('-academic_year__name', 'name')
    else:
        academic_years = AcademicYear.objects.none()
        terms = Term.objects.none()
    
    return render(request, "core/school_settings.html", {
        "form": form, 
        "academic_years": academic_years,
        "terms": terms,
        "school": school,
    })

@login_required
@user_passes_test(admin_required)
def academic_year_create(request):
    from .forms import AcademicYearForm
    # Get school for current user
    if request.user.is_superadmin():
        school = School.objects.first()
    else:
        school = getattr(request.user, 'school', None)
    
    if not school:
        messages.error(request, "No school found. Please contact administrator.")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'No school found. Please contact administrator.'}, status=400)
        return redirect("school_settings")
    
    if request.method == "POST":
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            academic_year = form.save(commit=False)
            academic_year.school = school
            if academic_year.is_active:
                AcademicYear.objects.filter(school=school, is_active=True).update(is_active=False)
            academic_year.save()
            messages.success(request, "Academic year created successfully!")
            # If AJAX request, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': True, 'message': 'Academic year created successfully!'})
            return redirect("school_settings")
        else:
            # If AJAX request with errors, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = AcademicYearForm()
    
    # If AJAX request, return form HTML only
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "core/academic_year_form.html", {"form": form, "title": "Create Academic Year", "school": school})
    
    return render(request, "core/academic_year_form.html", {"form": form, "title": "Create Academic Year", "school": school})

@login_required
@user_passes_test(admin_required)
def academic_year_edit(request, pk):
    from .forms import AcademicYearForm
    academic_year = get_object_or_404(AcademicYear, pk=pk)
    school = academic_year.school
    
    # Check permissions
    if not request.user.is_superadmin():
        user_school = getattr(request.user, 'school', None)
        if user_school != school:
            messages.error(request, "You don't have permission to edit this academic year!")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'error': 'You don\'t have permission to edit this academic year!'}, status=403)
            return redirect('school_settings')
    
    if request.method == "POST":
        form = AcademicYearForm(request.POST, instance=academic_year)
        if form.is_valid():
            academic_year = form.save(commit=False)
            if academic_year.is_active:
                AcademicYear.objects.filter(school=academic_year.school, is_active=True).exclude(pk=academic_year.pk).update(is_active=False)
            academic_year.save()
            messages.success(request, "Academic year updated successfully!")
            # If AJAX request, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': True, 'message': 'Academic year updated successfully!'})
            return redirect("school_settings")
        else:
            # If AJAX request with errors, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = AcademicYearForm(instance=academic_year)
    
    # If AJAX request, return form HTML only
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "core/academic_year_form.html", {"form": form, "title": "Edit Academic Year", "school": school})
    
    return render(request, "core/academic_year_form.html", {"form": form, "title": "Edit Academic Year", "school": school})

@login_required
@user_passes_test(admin_required)
def term_create(request):
    from .forms import TermForm
    # Get school for current user
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    if request.method == "POST":
        form = TermForm(request.POST, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Term created successfully!")
            # If AJAX request, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': True, 'message': 'Term created successfully!'})
            return redirect("school_settings")
        else:
            # If AJAX request with errors, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = TermForm(school=school)
    
    # If AJAX request, return form HTML only
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "core/term_form.html", {"form": form, "title": "Create Term", "school": school})
    
    return render(request, "core/term_form.html", {"form": form, "title": "Create Term", "school": school})

@login_required
@user_passes_test(admin_required)
def term_edit(request, pk):
    from .forms import TermForm
    term = get_object_or_404(Term, pk=pk)
    # Get school from term's academic year
    school = term.academic_year.school
    
    # Check permissions - ensure user has access to this school's terms
    if not request.user.is_superadmin():
        user_school = getattr(request.user, 'school', None)
        if user_school != school:
            messages.error(request, "You don't have permission to edit this term!")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'error': 'You don\'t have permission to edit this term!'}, status=403)
            return redirect('school_settings')
    
    if request.method == "POST":
        form = TermForm(request.POST, instance=term, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Term updated successfully!")
            # If AJAX request, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': True, 'message': 'Term updated successfully!'})
            return redirect("school_settings")
        else:
            # If AJAX request with errors, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = TermForm(instance=term, school=school)
    
    # If AJAX request, return form HTML only
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "core/term_form.html", {"form": form, "title": "Edit Term", "school": school})
    
    return render(request, "core/term_form.html", {"form": form, "title": "Edit Term", "school": school})

@login_required
def exam_list(request):
    """Delegates to academics.views.exam_list for proper exam management"""
    from academics import views as academics_views
    return academics_views.exam_list(request)


@login_required
def logout_view(request):
    """Custom logout view that works for all user types"""
    if request.method == 'POST':
        # Get user information before logout
        user_role = request.user.role if hasattr(request.user, 'role') else 'user'
        username = request.user.get_full_name() or request.user.username
        
        # Perform logout
        logout(request)
        
        # Show success message
        messages.success(request, f'You have been successfully logged out. Goodbye, {username}!')
        
        # Redirect to login page
        return redirect('login')
    else:
        # Show logout confirmation page
        user_role = request.user.role if hasattr(request.user, 'role') else 'user'
        user_name = request.user.get_full_name() or request.user.username
        
        return render(request, 'core/logout.html', {
            'user_name': user_name,
            'user_role': user_role,
            'title': 'Logout'
        })


@login_required
def select_academic_context(request):
    """Set the selected academic year and term in session so dashboard and other views can show historical data."""
    if request.method == 'POST':
        year_id = request.POST.get('academic_year')
        term_id = request.POST.get('term')
        if year_id:
            request.session['selected_academic_year_id'] = int(year_id)
        else:
            request.session.pop('selected_academic_year_id', None)

        if term_id:
            request.session['selected_term_id'] = int(term_id)
        else:
            request.session.pop('selected_term_id', None)

    # Redirect back to dashboard or referer
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)


def get_school_type(request, school_id):
    """AJAX endpoint to get school type"""
    from django.http import JsonResponse
    school = get_object_or_404(School, pk=school_id)
    return JsonResponse({'school_type': school.school_type})


@login_required
def logout_view(request):
    """Handle logout with optional modal confirmation"""
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('login')
    # If GET request (shouldn't happen with modal), show logout page for backward compatibility
    return render(request, 'core/logout.html', {
        'user_name': request.user.get_full_name() or request.user.username,
        'user_role': request.user.get_role_display() if hasattr(request.user, 'get_role_display') else request.user.role
    })


# ==================== EduAI Assistant Views ====================

@login_required
def ai_assistant_chat(request):
    """Handle AI assistant chat requests with streaming support"""
    from django.http import JsonResponse, StreamingHttpResponse
    from .ai_assistant import EduAIService
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        stream = data.get('stream', False)
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Get context
        context = {
            'students_count': data.get('students_count'),
            'teachers_count': data.get('teachers_count'),
            'current_term': data.get('current_term')
        }
        
        # Initialize AI service
        ai_service = EduAIService(user=request.user)
        
        # Handle streaming response
        if stream:
            def generate():
                stream_gen = ai_service.chat(user_message, context, stream=True)
                if isinstance(stream_gen, dict) and 'stream' in stream_gen:
                    for chunk in stream_gen['stream']:
                        if chunk:
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    yield f"data: {json.dumps({'done': True})}\n\n"
                else:
                    yield f"data: {json.dumps({'error': 'Streaming failed'})}\n\n"
            
            response = StreamingHttpResponse(generate(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
        else:
            # Get chat response (non-streaming)
            try:
                # Add more context for better understanding
                if not context:
                    context = {}
                
                # Add current user context
                context['user_role'] = request.user.role if request.user else None
                context['user_school'] = request.user.school.name if hasattr(request.user, 'school') and request.user.school else None
                
                result = ai_service.chat(user_message, context, stream=False)
                
                # Ensure response is always a string
                if result and 'response' in result:
                    if not isinstance(result['response'], str):
                        result['response'] = str(result['response'])
                    
                    # If response is empty, provide a helpful message
                    if not result['response'] or not result['response'].strip():
                        result['response'] = "I received your message. Could you please rephrase your question or be more specific? I can help with:\n- Information about students and teachers\n- Generating report cards\n- Academic data and analysis\n- Educational questions and research\n- And much more!"
                
                # Ensure success is set
                if 'success' not in result:
                    result['success'] = True
                    
                return JsonResponse(result)
            except Exception as e:
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.error(f"AI chat error in view: {str(e)}\n{traceback.format_exc()}")
                return JsonResponse({
                    'error': str(e),
                    'response': f'I encountered an error: {str(e)}. Please try rephrasing your question or try again in a moment.',
                    'success': False
                }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AI chat error: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred',
            'response': 'I apologize, but I encountered an error. Please try again.',
            'success': False
        }, status=500)


@login_required
def ai_assistant_upload(request):
    """Handle file uploads for AI analysis"""
    from django.http import JsonResponse
    from .ai_assistant import EduAIService
    import logging
    
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed', 'success': False}, status=405)
    
    try:
        # Check if file was uploaded
        if 'file' not in request.FILES:
            logger.warning("No file in request.FILES")
            return JsonResponse({'error': 'No file provided', 'success': False}, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Check file size before reading
        if uploaded_file.size > 10 * 1024 * 1024:  # 10MB
            return JsonResponse({'error': 'File too large. Maximum size is 10MB', 'success': False}, status=400)
        
        # Read file content
        try:
            file_content = uploaded_file.read()
            file_name = uploaded_file.name
            file_type = uploaded_file.content_type or 'application/octet-stream'
            
            logger.info(f"Processing file upload: {file_name}, type: {file_type}, size: {len(file_content)} bytes")
            
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return JsonResponse({'error': f'Error reading file: {str(e)}', 'success': False}, status=400)
        
        # Process with AI service
        try:
            ai_service = EduAIService(user=request.user)
            result = ai_service.process_file_upload(file_content, file_name, file_type)
            
            # Ensure success field is present
            if 'success' not in result:
                result['success'] = True
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"AI service error: {str(e)}")
            return JsonResponse({
                'error': f'Error processing file: {str(e)}',
                'success': False,
                'file_name': file_name
            }, status=500)
        
    except Exception as e:
        logger.error(f"AI file upload error: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': f'An error occurred: {str(e)}',
            'success': False
        }, status=500)


@login_required
def ai_assistant_analyze(request):
    """Handle AI assistant analysis requests"""
    from django.http import JsonResponse
    from .ai_assistant import EduAIService
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        analysis_type = data.get('type', 'performance')
        filters = data.get('filters', {})
        
        ai_service = EduAIService(user=request.user)
        
        if analysis_type == 'performance':
            result = ai_service.analyze_performance(filters)
        elif analysis_type == 'fees':
            result = ai_service.analyze_fees(filters)
        elif analysis_type == 'security':
            result = ai_service.detect_security_issues()
        else:
            return JsonResponse({'error': f'Unknown analysis type: {analysis_type}'}, status=400)
        
        return JsonResponse(result)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AI analysis error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def ai_assistant_automate(request):
    """Handle AI assistant automation requests"""
    from django.http import JsonResponse
    from .ai_assistant import EduAIService
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Check permissions
    if not (request.user.is_superadmin() or request.user.is_headteacher()):
        return JsonResponse({
            'error': 'Insufficient permissions',
            'message': 'Only administrators can execute automation tasks'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        task_type = data.get('task_type', '')
        params = data.get('params', {})
        
        if not task_type:
            return JsonResponse({'error': 'Task type is required'}, status=400)
        
        ai_service = EduAIService(user=request.user)
        result = ai_service.automate_task(task_type, params)
        
        return JsonResponse(result)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AI automation error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== Notifications Views ====================

@login_required
def notifications_list(request):
    """View all notifications"""
    from .models import Notification
    from django.core.paginator import Paginator
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page', 1)
    page_notifications = paginator.get_page(page)
    
    return render(request, 'core/notifications.html', {
        'notifications': page_notifications,
        'title': 'Notifications'
    })


@login_required
def notifications_api(request):
    """API endpoint for notifications"""
    from django.http import JsonResponse
    from .models import Notification
    import json
    
    if request.method == 'GET':
        # Get unread count and recent notifications
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        recent = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
        
        notifications_data = [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'link': n.link or ''
        } for n in recent]
        
        return JsonResponse({
            'unread_count': unread_count,
            'notifications': notifications_data
        })
    
    elif request.method == 'POST':
        # Mark notification as read
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        if notification_id:
            Notification.objects.filter(id=notification_id, user=request.user).update(is_read=True)
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Notification ID required'}, status=400)


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    from django.http import JsonResponse
    from .models import Notification
    
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


# ==================== Profile Views ====================

@login_required
def profile_view(request):
    """View user profile"""
    from .models import LoginHistory
    
    recent_logins = LoginHistory.objects.filter(user=request.user).order_by('-login_time')[:10]
    
    return render(request, 'core/profile.html', {
        'user': request.user,
        'recent_logins': recent_logins,
        'title': 'My Profile'
    })


@login_required
def profile_settings(request):
    """Profile settings page"""
    from .forms import ProfileForm, PasswordChangeForm
    from django.contrib import messages
    from django.contrib.auth import update_session_auth_hash
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            form = ProfileForm(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('profile_settings')
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully!')
                return redirect('profile_settings')
    else:
        form = ProfileForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)
    
    return render(request, 'core/profile_settings.html', {
        'form': form,
        'password_form': password_form,
        'title': 'Profile Settings'
    })


@login_required
def login_history_view(request):
    """View login history"""
    from .models import LoginHistory
    from django.core.paginator import Paginator
    
    logins = LoginHistory.objects.filter(user=request.user).order_by('-login_time')
    paginator = Paginator(logins, 20)
    page = request.GET.get('page', 1)
    page_logins = paginator.get_page(page)
    
    return render(request, 'core/login_history.html', {
        'logins': page_logins,
        'title': 'Login History'
    })
