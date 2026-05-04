from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Sum, Avg, Case, When, IntegerField
from django.db import models
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from academics.models import Grade, Subject, SubjectPaper, TeacherSubject, Exam, MarkEntry, ReportCard, Stream, Combination
from academics.forms import GradeForm, SubjectForm, SubjectPaperForm, CombinationForm, ExamForm
from timetable.models import TimetableSlot
from students.models import Guardian
from django.template.loader import render_to_string
from io import BytesIO
from decimal import Decimal

# Import from stream_views
from academics.stream_views import (
    manage_streams, add_stream, edit_stream, delete_stream,
    add_combination, edit_combination, delete_combination, add_stream_to_combination
)

# Import helper functions
def headteacher_required(user):
    """Check if user is headteacher or superadmin"""
    if not user.is_authenticated:
        return False
    return user.is_superadmin() or user.is_headteacher()

def headteacher_or_dos_required(user):
    """Check if user is headteacher, director of studies, or superadmin"""
    if not user.is_authenticated:
        return False
    return user.is_superadmin() or user.is_headteacher() or user.is_director_of_studies()

def teacher_required(user):
    """Check if user is teacher"""
    if not user.is_authenticated:
        return False
    return user.is_teacher() or user.is_headteacher() or user.is_superadmin()

# Grade Management Views
@login_required
@user_passes_test(headteacher_required)
def grade_list(request):
    """List all grades"""
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    grades = Grade.objects.all()
    if school:
        grades = grades.filter(school=school)
    return render(request, 'academics/grade_list.html', {'grades': grades, 'title': 'Manage Grades'})

@login_required
@user_passes_test(headteacher_required)
def grade_create(request):
    """Create a new grade"""
    if request.method == 'POST':
        form = GradeForm(request.POST, school=getattr(request.user, 'school', None), user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade created successfully!')
            return redirect('grade_list')
    else:
        form = GradeForm(school=getattr(request.user, 'school', None), user=request.user)
    return render(request, 'academics/grade_form.html', {'form': form, 'title': 'Create Grade'})

@login_required
@user_passes_test(headteacher_required)
def grade_edit(request, pk):
    """Edit a grade"""
    grade = get_object_or_404(Grade, pk=pk)
    if not request.user.is_superadmin() and grade.school != request.user.school:
        messages.error(request, "You don't have permission to edit this grade.")
        return redirect('grade_list')
    
    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade, school=getattr(request.user, 'school', None), user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade updated successfully!')
            return redirect('grade_list')
    else:
        form = GradeForm(instance=grade, school=getattr(request.user, 'school', None), user=request.user)
    return render(request, 'academics/grade_form.html', {'form': form, 'grade': grade, 'title': 'Edit Grade'})

@login_required
@user_passes_test(headteacher_required)
def grade_delete(request, pk):
    """Delete a grade"""
    grade = get_object_or_404(Grade, pk=pk)
    if not request.user.is_superadmin() and grade.school != request.user.school:
        messages.error(request, "You don't have permission to delete this grade.")
        return redirect('grade_list')
    
    grade.delete()
    messages.success(request, 'Grade deleted successfully!')
    return redirect('grade_list')

# Subject Management Views
@login_required
@user_passes_test(headteacher_required)
def subject_list(request):
    """List all subjects"""
    # Subject model doesn't have a school field - it's global
    # Filter by level if needed based on school type
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    subjects = Subject.objects.all()
    
    # Optionally filter by level based on school type
    if school:
        if school.is_primary():
            subjects = subjects.filter(level='P')
        elif school.is_high_school():
            subjects = subjects.filter(level__in=['O', 'A'])
    
    # Group subjects by level for template
    subjects_by_level = {}
    for subject in subjects:
        level = subject.get_level_display()
        if level not in subjects_by_level:
            subjects_by_level[level] = []
        subjects_by_level[level].append(subject)
    
    # Sort levels: Primary, O-Level, A-Level
    level_order = {'Primary': 0, 'O-Level': 1, 'A-Level': 2}
    subjects_by_level = dict(sorted(subjects_by_level.items(), key=lambda x: level_order.get(x[0], 999)))
    
    return render(request, 'academics/subject_list.html', {
        'subjects': subjects,
        'subjects_by_level': subjects_by_level,
        'title': 'Manage Subjects'
    })

@login_required
@user_passes_test(headteacher_required)
def subject_create(request):
    """Create a new subject"""
    if request.method == 'POST':
        form = SubjectForm(request.POST, school=getattr(request.user, 'school', None))
        if form.is_valid():
            form.save()
            messages.success(request, 'Subject created successfully!')
            return redirect('subject_list')
    else:
        form = SubjectForm(school=getattr(request.user, 'school', None))
    return render(request, 'academics/subject_form.html', {'form': form, 'title': 'Create Subject'})

@login_required
@user_passes_test(headteacher_required)
def cleanup_compulsory_subjects(request):
    """Clean up incorrectly marked compulsory subjects"""
    from students.models import EnrollmentSubject, Enrollment
    from django.db import transaction
    
    if request.method == 'POST':
        with transaction.atomic():
            # Get all O-Level subjects that are actually compulsory
            actual_compulsory_subjects = Subject.objects.filter(
                level='O',
                is_compulsory=True
            )
            actual_compulsory_subject_ids = set(actual_compulsory_subjects.values_list('id', flat=True))
            
            # Get all O-Level enrollments
            o_level_enrollments = Enrollment.objects.filter(
                grade__level='O',
                is_active=True
            )
            
            removed_count = 0
            
            # Remove EnrollmentSubject records that are marked as compulsory
            # but the subject is not actually compulsory
            for enrollment in o_level_enrollments:
                enrollment_subjects = EnrollmentSubject.objects.filter(
                    enrollment=enrollment,
                    is_compulsory=True
                ).select_related('subject')
                
                for enrollment_subject in enrollment_subjects:
                    subject_id = enrollment_subject.subject.id
                    if subject_id not in actual_compulsory_subject_ids:
                        # Subject is not actually compulsory, remove it
                        enrollment_subject.delete()
                        removed_count += 1
            
            messages.success(request, f'Successfully cleaned up {removed_count} incorrectly marked compulsory subjects.')
            return redirect('subject_list')
    
    # Show confirmation page
    actual_compulsory_count = Subject.objects.filter(level='O', is_compulsory=True).count()
    total_marked_compulsory = EnrollmentSubject.objects.filter(
        enrollment__grade__level='O',
        enrollment__is_active=True,
        is_compulsory=True
    ).count()
    
    # Calculate how many need to be removed
    # Get actual compulsory subject IDs
    actual_compulsory_subject_ids = set(Subject.objects.filter(
        level='O',
        is_compulsory=True
    ).values_list('id', flat=True))
    
    # Count how many EnrollmentSubject records are marked as compulsory
    # but the subject is not actually compulsory
    incorrectly_marked = EnrollmentSubject.objects.filter(
        enrollment__grade__level='O',
        enrollment__is_active=True,
        is_compulsory=True
    ).exclude(subject_id__in=actual_compulsory_subject_ids).count()
    
    return render(request, 'academics/cleanup_compulsory_subjects.html', {
        'actual_compulsory_count': actual_compulsory_count,
        'total_marked_compulsory': total_marked_compulsory,
        'incorrectly_marked_count': incorrectly_marked,
        'title': 'Cleanup Compulsory Subjects'
    })

@login_required
@user_passes_test(headteacher_required)
def subject_edit(request, subject_id):
    """Edit a subject"""
    from django.http import JsonResponse
    subject = get_object_or_404(Subject, pk=subject_id)
    # Subject model doesn't have a school field - it's global
    # All headteachers can edit subjects
    
    if request.method == 'POST':
        # Store old values to detect changes
        old_is_compulsory = subject.is_compulsory
        old_level = subject.level
        
        form = SubjectForm(request.POST, instance=subject, school=getattr(request.user, 'school', None))
        if form.is_valid():
            # Save the subject (this will trigger sync_enrollments if needed)
            updated_subject = form.save()
            
            # Explicitly sync enrollments if compulsory status or level changed
            # (The save() method handles this, but we'll also do it here to be sure)
            if (updated_subject.level == 'O' or updated_subject.level == 'P') and \
               (old_is_compulsory != updated_subject.is_compulsory or old_level != updated_subject.level):
                # The save() method should have already synced, but we can verify
                messages.success(request, f'Subject updated successfully! Enrollment assignments have been synced.')
            else:
                messages.success(request, 'Subject updated successfully!')
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Subject updated successfully! Enrollment assignments have been synced.' if 
                              ((updated_subject.level == 'O' or updated_subject.level == 'P') and 
                               (old_is_compulsory != updated_subject.is_compulsory or old_level != updated_subject.level)) 
                              else 'Subject updated successfully!',
                    'subject': {
                        'id': updated_subject.id,
                        'name': updated_subject.name,
                        'code': updated_subject.code or '',
                        'level': updated_subject.level,
                        'is_compulsory': updated_subject.is_compulsory,
                        'has_papers': updated_subject.has_papers,
                        'has_elective_papers': updated_subject.has_elective_papers,
                        'paper_selection_mode': updated_subject.paper_selection_mode
                    }
                })
            
            return redirect('subject_list')
        else:
            # Form validation failed
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Validation failed',
                    'errors': form.errors
                }, status=400)
    else:
        form = SubjectForm(instance=subject, school=getattr(request.user, 'school', None))
    return render(request, 'academics/subject_form.html', {'form': form, 'subject': subject, 'title': 'Edit Subject'})

@login_required
@user_passes_test(headteacher_required)
def subject_delete(request, subject_id):
    """Delete a subject"""
    from django.http import JsonResponse
    subject = get_object_or_404(Subject, pk=subject_id)
    # Subject model doesn't have a school field - it's global
    # All headteachers can delete subjects
    
    if request.method == 'POST':
        subject_name = subject.name
        subject.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Subject "{subject_name}" deleted successfully!'})
        
        messages.success(request, 'Subject deleted successfully!')
        return redirect('subject_list')
    
    # If GET request, return error for AJAX or redirect for normal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    messages.error(request, 'Invalid request method.')
    return redirect('subject_list')

# Subject Paper Management Views
@login_required
@user_passes_test(headteacher_required)
def subject_paper_list(request, subject_id):
    """List papers for a subject (AJAX endpoint)"""
    from django.http import JsonResponse
    subject = get_object_or_404(Subject, pk=subject_id)
    papers = SubjectPaper.objects.filter(subject=subject).order_by('paper_number', 'name')
    
    # Get paper selection mode
    paper_selection_mode = subject.paper_selection_mode if subject.has_papers else None
    
    # If user is a teacher (and not headteacher/superadmin), filter by teacher's assigned papers
    if request.user.is_teacher() and not request.user.is_headteacher() and not request.user.is_superadmin():
        teacher_assignments = TeacherSubject.objects.filter(
            teacher=request.user,
            subject=subject
        ).first()
        
        if teacher_assignments and teacher_assignments.papers.exists():
            # Teacher has specific papers assigned, show only those
            papers = papers.filter(id__in=teacher_assignments.papers.values_list('id', flat=True))
        # If teacher has no specific papers assigned, show all papers (teaches all papers)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        papers_data = []
        for paper in papers:
            papers_data.append({
                'id': paper.id,
                'name': paper.name,
                'paper_number': paper.paper_number or 0,
                'code': paper.code or '',
                'description': paper.description or '',
                'is_active': paper.is_active
            })
        return JsonResponse({
            'papers': papers_data, 
            'subject_name': subject.name, 
            'has_papers': subject.has_papers,
            'paper_selection_mode': paper_selection_mode or 'selective',
            'has_elective_papers': getattr(subject, 'has_elective_papers', False)
        })
    
    return render(request, 'academics/subject_paper_list.html', {'subject': subject, 'papers': papers, 'title': f'Papers for {subject.name}'})

@login_required
@user_passes_test(headteacher_required)
def subject_paper_create(request):
    """Create a new subject paper (AJAX endpoint)"""
    from django.http import JsonResponse
    from academics.forms import SubjectPaperForm
    
    if request.method == 'POST':
        form = SubjectPaperForm(request.POST, school=getattr(request.user, 'school', None))
        if form.is_valid():
            paper = form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'paper': {
                        'id': paper.id,
                        'name': paper.name,
                        'paper_number': paper.paper_number or 0,
                        'code': paper.code or '',
                        'description': paper.description or '',
                        'is_active': paper.is_active
                    }
                })
            messages.success(request, 'Subject paper created successfully!')
            return redirect('subject_paper_list', subject_id=form.cleaned_data['subject'].id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = SubjectPaperForm(school=getattr(request.user, 'school', None))
    return render(request, 'academics/subject_paper_form.html', {'form': form, 'title': 'Create Subject Paper'})

@login_required
@user_passes_test(headteacher_required)
def subject_paper_edit(request, paper_id):
    """Edit a subject paper (AJAX endpoint)"""
    from django.http import JsonResponse
    from academics.forms import SubjectPaperForm
    
    paper = get_object_or_404(SubjectPaper, pk=paper_id)
    
    if request.method == 'POST':
        form = SubjectPaperForm(request.POST, instance=paper, school=getattr(request.user, 'school', None))
        if form.is_valid():
            paper = form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'paper': {
                        'id': paper.id,
                        'name': paper.name,
                        'paper_number': paper.paper_number or 0,
                        'code': paper.code or '',
                        'description': paper.description or '',
                        'is_active': paper.is_active
                    }
                })
            messages.success(request, 'Subject paper updated successfully!')
            return redirect('subject_paper_list', subject_id=paper.subject.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = SubjectPaperForm(instance=paper, school=getattr(request.user, 'school', None))
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'paper': {
                    'id': paper.id,
                    'name': paper.name,
                    'paper_number': paper.paper_number or 0,
                    'code': paper.code or '',
                    'description': paper.description or '',
                    'is_active': paper.is_active,
                    'subject_id': paper.subject.id
                }
            })
    
    return render(request, 'academics/subject_paper_form.html', {'form': form, 'paper': paper, 'title': 'Edit Subject Paper'})

@login_required
@user_passes_test(headteacher_required)
def subject_paper_delete(request, paper_id):
    """Delete a subject paper (AJAX endpoint)"""
    from django.http import JsonResponse
    paper = get_object_or_404(SubjectPaper, pk=paper_id)
    subject_id = paper.subject.id
    paper_name = paper.name
    
    if request.method == 'POST':
        paper.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Paper "{paper_name}" deleted successfully!'})
        messages.success(request, 'Subject paper deleted successfully!')
        return redirect('subject_paper_list', subject_id=subject_id)
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
        return redirect('subject_paper_list', subject_id=subject_id)

# Combination Management Views
@login_required
@user_passes_test(headteacher_required)
def combination_manage(request):
    """Manage A-Level combinations"""
    from django.db.models import Q
    
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    combinations = Combination.objects.all()
    
    if school:
        # Show combinations that:
        # 1. Are assigned to grades in this school, OR
        # 2. Have grade=None (available for all A-Level)
        combinations = combinations.filter(
            Q(grade__school=school) | Q(grade__isnull=True)
        ).distinct()
    
    # Order by grade (nulls last), then by name
    combinations = combinations.order_by('grade', 'name')
    
    return render(request, 'academics/combination_list.html', {'combinations': combinations, 'title': 'Manage Combinations'})

@login_required
@user_passes_test(headteacher_required)
def combination_create(request):
    """Create a new combination"""
    if request.method == 'POST':
        form = CombinationForm(request.POST, school=getattr(request.user, 'school', None))
        if form.is_valid():
            combination = form.save(commit=False)
            combination.created_by = request.user
            combination.save()
            form.save_m2m()
            messages.success(request, 'Combination created successfully!')
            return redirect('combination_manage')
    else:
        form = CombinationForm(school=getattr(request.user, 'school', None))
    return render(request, 'academics/combination_form.html', {'form': form, 'title': 'Create Combination'})

@login_required
@user_passes_test(headteacher_required)
def combination_edit(request, combination_id):
    """Edit a combination"""
    combination = get_object_or_404(Combination, pk=combination_id)
    if not request.user.is_superadmin() and combination.grade and combination.grade.school != request.user.school:
        messages.error(request, "You don't have permission to edit this combination.")
        return redirect('combination_manage')
    
    if request.method == 'POST':
        form = CombinationForm(request.POST, instance=combination, school=getattr(request.user, 'school', None))
        if form.is_valid():
            form.save()
            messages.success(request, 'Combination updated successfully!')
            return redirect('combination_manage')
    else:
        form = CombinationForm(instance=combination, school=getattr(request.user, 'school', None))
    return render(request, 'academics/combination_form.html', {'form': form, 'combination': combination, 'title': 'Edit Combination'})

@login_required
@user_passes_test(headteacher_required)
def combination_delete(request, combination_id):
    """Delete a combination"""
    combination = get_object_or_404(Combination, pk=combination_id)
    if not request.user.is_superadmin() and combination.grade and combination.grade.school != request.user.school:
        messages.error(request, "You don't have permission to delete this combination.")
        return redirect('combination_manage')
    
    combination.delete()
    messages.success(request, 'Combination deleted successfully!')
    return redirect('combination_manage')

@login_required
@user_passes_test(headteacher_required)
def get_combinations_by_grade(request, grade_id):
    """Get combinations for a specific grade (AJAX)"""
    grade = get_object_or_404(Grade, pk=grade_id)
    combinations = Combination.objects.filter(grade=grade)
    data = [{'id': c.id, 'name': c.name, 'code': c.code or ''} for c in combinations]
    return JsonResponse({'combinations': data})

# Additional combination views (from stream_views)
def combination_list(request):
    """List all combinations"""
    return combination_manage(request)

# Timetable Views
DAYS = [(0,'Monday'),(1,'Tuesday'),(2,'Wednesday'),(3,'Thursday'),(4,'Friday'),(5,'Saturday')]

@login_required
@user_passes_test(headteacher_required)
def timetable_list(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    selected_grade_id = request.GET.get('grade')

    grades = Grade.objects.all()
    if school:
        grades = grades.filter(school=school)

    subjects = Subject.objects.all()
    if school:
        if school.is_primary():
            subjects = subjects.filter(level='P')
        elif school.is_high_school():
            subjects = subjects.filter(level__in=['O', 'A'])

    teachers = User.objects.filter(role='teacher')
    if school:
        teachers = teachers.filter(school=school)

    # Auto-select first grade if none chosen
    if not selected_grade_id and grades.exists():
        selected_grade_id = str(grades.first().pk)

    selected_grade = None
    grid = {d: [] for d, _ in DAYS}
    if selected_grade_id:
        try:
            selected_grade = grades.get(pk=selected_grade_id)
            slots = TimetableSlot.objects.filter(grade=selected_grade).select_related('subject', 'teacher').order_by('start_time')
            for slot in slots:
                grid[slot.day_of_week].append(slot)
        except Grade.DoesNotExist:
            pass

    total_slots = TimetableSlot.objects.filter(grade__in=grades).count()

    context = {
        'grades': grades,
        'subjects': subjects,
        'teachers': teachers,
        'days': DAYS,
        'grid': grid,
        'selected_grade': selected_grade,
        'selected_grade_id': selected_grade_id,
        'total_slots': total_slots,
        'title': 'Timetable',
    }
    return render(request, 'academics/timetable_list.html', context)


@login_required
@user_passes_test(headteacher_required)
def timetable_create(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    grade_id  = request.POST.get('grade')
    subj_id   = request.POST.get('subject')
    teacher_id= request.POST.get('teacher') or None
    day       = request.POST.get('day_of_week')
    start     = request.POST.get('start_time')
    end       = request.POST.get('end_time')
    room      = request.POST.get('room', '').strip()
    if not all([grade_id, subj_id, day, start, end]):
        return JsonResponse({'success': False, 'error': 'All required fields must be filled'}, status=400)
    grade   = get_object_or_404(Grade, pk=grade_id)
    subject = get_object_or_404(Subject, pk=subj_id)
    if school and grade.school != school:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    # Overlap check
    overlap = TimetableSlot.objects.filter(grade=grade, day_of_week=day, start_time__lt=end, end_time__gt=start)
    if overlap.exists():
        return JsonResponse({'success': False, 'error': 'Time slot overlaps with an existing slot for this class'}, status=400)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    teacher = User.objects.filter(pk=teacher_id).first() if teacher_id else None
    slot = TimetableSlot.objects.create(
        grade=grade, subject=subject, teacher=teacher,
        day_of_week=int(day), start_time=start, end_time=end, room=room
    )
    return JsonResponse({'success': True, 'slot_id': slot.pk,
        'subject': subject.name, 'teacher': teacher.get_full_name() if teacher else '',
        'start_time': start, 'end_time': end, 'room': room, 'day': int(day)})


@login_required
@user_passes_test(headteacher_required)
def timetable_edit(request, slot_id):
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    slot = get_object_or_404(TimetableSlot, pk=slot_id)
    if school and slot.grade.school != school:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    if request.method == 'GET':
        return JsonResponse({'success': True, 'slot': {
            'id': slot.pk, 'grade': slot.grade_id, 'subject': slot.subject_id,
            'teacher': slot.teacher_id or '', 'day_of_week': slot.day_of_week,
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M'), 'room': slot.room or '',
        }})
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    grade_id  = request.POST.get('grade')
    subj_id   = request.POST.get('subject')
    teacher_id= request.POST.get('teacher') or None
    day       = request.POST.get('day_of_week')
    start     = request.POST.get('start_time')
    end       = request.POST.get('end_time')
    room      = request.POST.get('room', '').strip()
    if not all([grade_id, subj_id, day, start, end]):
        return JsonResponse({'success': False, 'error': 'All required fields must be filled'}, status=400)
    grade   = get_object_or_404(Grade, pk=grade_id)
    subject = get_object_or_404(Subject, pk=subj_id)
    overlap = TimetableSlot.objects.filter(grade=grade, day_of_week=day, start_time__lt=end, end_time__gt=start).exclude(pk=slot_id)
    if overlap.exists():
        return JsonResponse({'success': False, 'error': 'Time slot overlaps with an existing slot'}, status=400)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    teacher = User.objects.filter(pk=teacher_id).first() if teacher_id else None
    slot.grade = grade; slot.subject = subject; slot.teacher = teacher
    slot.day_of_week = int(day); slot.start_time = start; slot.end_time = end; slot.room = room
    slot.save()
    return JsonResponse({'success': True})


@login_required
@user_passes_test(headteacher_required)
def timetable_delete(request, slot_id):
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    slot = get_object_or_404(TimetableSlot, pk=slot_id)
    if school and slot.grade.school != school:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    if request.method == 'POST':
        slot.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

# Teacher Subject Assignment Views
@login_required
@user_passes_test(headteacher_required)
def assign_teacher_subject(request):
    """Assign a teacher to a subject"""
    # Placeholder - implement based on your TeacherSubject model
    messages.info(request, 'Teacher subject assignment feature coming soon.')
    return redirect('subject_list')

@login_required
@user_passes_test(headteacher_required)
def teacher_subject_delete(request, assignment_id):
    """Delete a teacher subject assignment"""
    assignment = get_object_or_404(TeacherSubject, pk=assignment_id)
    assignment.delete()
    messages.success(request, 'Teacher subject assignment deleted successfully!')
    return redirect('subject_list')

# Mark Entry Views
@login_required
@user_passes_test(teacher_required)
def mark_entry_list(request):
    """List mark entries"""
    from students.models import Enrollment
    from core.models import Term
    
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    term_id = request.GET.get('term')
    grade_id = request.GET.get('grade')
    subject_id = request.GET.get('subject')
    exam_id = request.GET.get('exam')
    
    marks = MarkEntry.objects.all()
    if school:
        marks = marks.filter(enrollment__grade__school=school)
    
    if term_id:
        marks = marks.filter(exam__term_id=term_id)
    if grade_id:
        marks = marks.filter(enrollment__grade_id=grade_id)
    if subject_id:
        marks = marks.filter(subject_id=subject_id)
    if exam_id:
        marks = marks.filter(exam_id=exam_id)
    
    # Get filter options
    terms = Term.objects.all()
    if school:
        terms = terms.filter(academic_year__school=school)
    
    grades = Grade.objects.all()
    if school:
        grades = grades.filter(school=school)
    
    # Filter subjects based on teacher assignments if user is a teacher
    subjects = Subject.objects.all()
    if request.user.is_teacher() and not request.user.is_headteacher() and not request.user.is_superadmin():
        # Get subjects assigned to this teacher
        teacher_assignments = TeacherSubject.objects.filter(teacher=request.user)
        if teacher_assignments.exists():
            assigned_subject_ids = teacher_assignments.values_list('subject_id', flat=True)
            subjects = subjects.filter(id__in=assigned_subject_ids)
    
    # Subject model doesn't have a school field - it's global
    # Filter by level if needed based on school type
    if school:
        if school.is_primary():
            subjects = subjects.filter(level='P')
        elif school.is_high_school():
            subjects = subjects.filter(level__in=['O', 'A'])
    
    exams = Exam.objects.all()
    if school:
        exams = exams.filter(term__academic_year__school=school)
    
    context = {
        'marks': marks,
        'terms': terms,
        'grades': grades,
        'subjects': subjects,
        'exams': exams,
        'selected_term': term_id,
        'selected_grade': grade_id,
        'selected_subject': subject_id,
        'selected_exam': exam_id,
        'title': 'Mark Entry'
    }
    return render(request, 'academics/mark_entry.html', context)

@login_required
@user_passes_test(teacher_required)
def mark_entry_create(request):
    """Create/Update mark entries"""
    from django.http import JsonResponse
    from students.models import Enrollment
    from academics.models import StudentPaperAssignment
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    exam_id = request.POST.get('exam')
    subject_id = request.POST.get('subject')
    grade_id = request.POST.get('grade')
    
    if not exam_id or not subject_id or not grade_id:
        return JsonResponse({'success': False, 'error': 'Missing required parameters'}, status=400)
    
    exam = get_object_or_404(Exam, pk=exam_id)
    subject = get_object_or_404(Subject, pk=subject_id)
    grade = get_object_or_404(Grade, pk=grade_id)
    
    # Get enrollments for this grade
    enrollments = Enrollment.objects.filter(grade=grade, is_active=True)
    
    # Filter by students taking this subject
    from students.models import EnrollmentSubject
    students_taking_subject = []
    for enrollment in enrollments:
        if enrollment.grade.level == 'A' and enrollment.combination:
            if subject in enrollment.combination.subjects.all():
                students_taking_subject.append(enrollment)
        else:
            if EnrollmentSubject.objects.filter(enrollment=enrollment, subject=subject).exists():
                students_taking_subject.append(enrollment)
    
    # Process each student's marks
    saved_count = 0
    errors = []
    
    for enrollment in students_taking_subject:
        student_id = enrollment.student.id
        score_str = request.POST.get(f'score_{student_id}')
        comments = request.POST.get(f'comments_{student_id}', '')
        paper_id = request.POST.get(f'paper_{student_id}', '') or None
        
        # If subject has papers, paper_id is required
        if subject.has_papers and not paper_id:
            errors.append(f"Paper selection required for {enrollment.student.get_full_name()}")
            continue
        
        # If subject has papers, validate paper assignment
        if subject.has_papers and paper_id:
            paper = get_object_or_404(SubjectPaper, pk=paper_id, subject=subject)
            
            # Check if teacher is assigned to this paper
            if request.user.is_teacher() and not request.user.is_headteacher() and not request.user.is_superadmin():
                teacher_assignment = TeacherSubject.objects.filter(
                    teacher=request.user,
                    subject=subject
                ).first()
                
                if teacher_assignment and teacher_assignment.papers.exists():
                    if paper not in teacher_assignment.papers.all():
                        errors.append(f"You are not assigned to teach {paper.name} for {subject.name}")
                        continue
            
            # Check if student is assigned to this paper
            student_assignment = StudentPaperAssignment.objects.filter(
                enrollment=enrollment,
                subject=subject
            ).first()
            
            if student_assignment and student_assignment.papers.exists():
                if paper not in student_assignment.papers.all():
                    errors.append(f"{enrollment.student.get_full_name()} is not assigned to {paper.name}")
                    continue
        
        if not score_str:
            continue  # Skip if no score provided
        
        try:
            score = float(score_str)
            if score < 0 or score > 100:
                errors.append(f"Invalid score for {enrollment.student.get_full_name()}: must be between 0 and 100")
                continue
        except ValueError:
            errors.append(f"Invalid score format for {enrollment.student.get_full_name()}")
            continue
        
        # Get or create mark entry
        # For subjects with papers, use paper in unique constraint
        if subject.has_papers and paper_id:
            mark_entry, created = MarkEntry.objects.get_or_create(
                enrollment=enrollment,
                subject=subject,
                exam=exam,
                subject_paper_id=paper_id,
                defaults={
                    'teacher': request.user,
                    'score': score,
                    'comments': comments
                }
            )
        else:
            # For subjects without papers, don't include paper in unique constraint
            mark_entry, created = MarkEntry.objects.get_or_create(
                enrollment=enrollment,
                subject=subject,
                exam=exam,
                defaults={
                    'teacher': request.user,
                    'score': score,
                    'comments': comments,
                    'subject_paper': None
                }
            )
        
        if not created:
            # Update existing mark
            mark_entry.score = score
            mark_entry.comments = comments
            mark_entry.teacher = request.user
            if subject.has_papers and paper_id:
                mark_entry.subject_paper_id = paper_id
            mark_entry.save()
        
        saved_count += 1
    
    if errors:
        return JsonResponse({
            'success': False,
            'error': 'Some marks could not be saved',
            'errors': errors,
            'saved_count': saved_count
        }, status=400)
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully saved {saved_count} mark{"s" if saved_count != 1 else ""}',
        'saved_count': saved_count
    })

@login_required
@user_passes_test(teacher_required)
def get_students_for_subject(request):
    """Get students for a subject with their existing marks and paper assignments (AJAX)"""
    subject_id = request.GET.get('subject_id')
    grade_id = request.GET.get('grade_id')
    exam_id = request.GET.get('exam_id')
    
    if not subject_id or not grade_id or not exam_id:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    from students.models import Enrollment, EnrollmentSubject
    from academics.models import StudentPaperAssignment
    
    enrollments = Enrollment.objects.filter(grade_id=grade_id, is_active=True)
    subject = get_object_or_404(Subject, pk=subject_id)
    exam = get_object_or_404(Exam, pk=exam_id)
    
    # Get papers for this subject (filtered by teacher assignments if applicable)
    papers = SubjectPaper.objects.filter(subject=subject, is_active=True).order_by('paper_number', 'name')
    
    # Filter papers by teacher's assigned papers if user is a teacher
    if request.user.is_teacher() and not request.user.is_headteacher() and not request.user.is_superadmin():
        teacher_assignments = TeacherSubject.objects.filter(
            teacher=request.user,
            subject=subject
        ).first()
        
        if teacher_assignments and teacher_assignments.papers.exists():
            papers = papers.filter(id__in=teacher_assignments.papers.values_list('id', flat=True))
    
    papers_data = []
    for paper in papers:
        papers_data.append({
            'id': paper.id,
            'name': paper.name,
            'paper_number': paper.paper_number or 0,
            'code': paper.code or ''
        })
    
    # For A-Level, check combination subjects
    # For O-Level, check enrollment subjects
    students_data = []
    for enrollment in enrollments:
        include_student = False
        
        if enrollment.grade.level == 'A' and enrollment.combination:
            # Check if subject is in combination
            if subject in enrollment.combination.subjects.all():
                include_student = True
        else:
            # Check if subject is in enrollment subjects
            if EnrollmentSubject.objects.filter(enrollment=enrollment, subject=subject).exists():
                include_student = True
        
        if include_student:
            # Get existing marks for this student, subject, and exam
            existing_marks = MarkEntry.objects.filter(
                enrollment=enrollment,
                subject=subject,
                exam=exam
            ).select_related('subject_paper')
            
            # Get student's paper assignments
            student_paper_assignment = StudentPaperAssignment.objects.filter(
                enrollment=enrollment,
                subject=subject
            ).first()
            
            assigned_paper_ids = []
            if student_paper_assignment and student_paper_assignment.papers.exists():
                assigned_paper_ids = list(student_paper_assignment.papers.values_list('id', flat=True))
            
            # Build marks data (grouped by paper if subject has papers)
            marks_data = {}
            if subject.has_papers:
                for mark in existing_marks:
                    if mark.subject_paper:
                        paper_id = mark.subject_paper.id
                        marks_data[paper_id] = {
                            'score': float(mark.score) if mark.score else None,
                            'grade': mark.grade,
                            'points': float(mark.points) if mark.points else None,
                            'comments': mark.comments or ''
                        }
            else:
                # Subject doesn't have papers - single mark entry
                if existing_marks.exists():
                    mark = existing_marks.first()
                    marks_data['default'] = {
                        'score': float(mark.score) if mark.score else None,
                        'grade': mark.grade,
                        'points': float(mark.points) if mark.points else None,
                        'comments': mark.comments or ''
                    }
            
                students_data.append({
                    'id': enrollment.student.id,
                'enrollment_id': enrollment.id,
                    'name': enrollment.student.get_full_name(),
                'admission_number': enrollment.student.admission_number,
                'marks': marks_data,
                'assigned_paper_ids': assigned_paper_ids
            })
    
    return JsonResponse({
        'students': students_data,
        'papers': papers_data,
        'subject_has_papers': subject.has_papers
    })

# Report Card Views
@login_required
def report_card_list(request):
    """Professional report cards list with class selection and role-based access"""
    from core.models import Term
    from django.db.models import Avg as DjAvg

    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    is_headteacher = request.user.is_headteacher() or request.user.is_superadmin()

    # Determine which grades are accessible
    if is_headteacher:
        accessible_grades = Grade.objects.filter(school=school) if school else Grade.objects.all()
    else:
        # Class teachers: only their assigned class; subject teachers: none
        accessible_grades = Grade.objects.filter(class_teacher=request.user)
        if school:
            accessible_grades = accessible_grades.filter(school=school)

    accessible_grades = accessible_grades.order_by('level', 'name')

    # If teacher has no class assignment, deny access
    if not is_headteacher and not accessible_grades.exists():
        return render(request, 'academics/report_card_list.html', {
            'no_access': True, 'title': 'Report Cards',
            'accessible_grades': accessible_grades,
        })

    # Filters from GET
    selected_grade_id = request.GET.get('grade')
    selected_term_id  = request.GET.get('term')

    # Default to first accessible grade
    if not selected_grade_id and accessible_grades.exists():
        selected_grade_id = str(accessible_grades.first().pk)

    selected_grade = None
    if selected_grade_id:
        try:
            selected_grade = accessible_grades.get(pk=selected_grade_id)
        except Grade.DoesNotExist:
            pass

    # Terms
    terms = Term.objects.all()
    if school:
        terms = terms.filter(academic_year__school=school)
    terms = terms.select_related('academic_year').order_by('-academic_year__start_date', 'start_date')

    selected_term = None
    if selected_term_id:
        try:
            selected_term = terms.get(pk=selected_term_id)
        except Term.DoesNotExist:
            pass

    # Build report card queryset
    report_cards = ReportCard.objects.none()
    if selected_grade:
        report_cards = ReportCard.objects.filter(
            enrollment__grade=selected_grade, enrollment__is_active=True
        ).select_related('enrollment__student', 'term', 'term__academic_year').order_by(
            'term__academic_year__name', 'term__name', 'position'
        )
        if selected_term:
            report_cards = report_cards.filter(term=selected_term)

    published_count = report_cards.filter(is_published=True).count()
    draft_count     = report_cards.filter(is_published=False).count()
    class_avg       = report_cards.aggregate(avg=DjAvg('average_score'))['avg']

    return render(request, 'academics/report_card_list.html', {
        'report_cards': report_cards,
        'accessible_grades': accessible_grades,
        'selected_grade': selected_grade,
        'selected_grade_id': selected_grade_id,
        'selected_term': selected_term,
        'selected_term_id': selected_term_id,
        'terms': terms,
        'published_count': published_count,
        'draft_count': draft_count,
        'class_avg': round(class_avg, 1) if class_avg else None,
        'is_headteacher': is_headteacher,
        'title': 'Report Cards',
    })

@login_required
def report_card_detail(request, report_card_id):
    """Display a report card detail"""
    from academics.uace_grading import (
        assign_numerical_grade, get_numerical_grade_label,
        compute_principal_letter_grade, compute_subsidiary_grade,
        calculate_uace_points, get_grade_category, is_subsidiary_subject,
        get_required_subsidiaries
    )
    from students.models import EnrollmentSubject
    
    from academics.models import UACEGradingConfig, ReportCard
    
    report_card = get_object_or_404(ReportCard, pk=report_card_id)
    enrollment = report_card.enrollment
    
    # Get UACE grading config for the school (if A-Level)
    uace_config = None
    if enrollment.grade.level == 'A':
        school = enrollment.grade.school
        try:
            uace_config = UACEGradingConfig.objects.get(school=school)
        except UACEGradingConfig.DoesNotExist:
            # Config not created yet - will use defaults
            pass
    
    # Check permissions
    if not request.user.is_superadmin():
        if hasattr(request.user, 'school') and enrollment.grade.school != request.user.school:
            messages.error(request, "You don't have permission to view this report card.")
            return redirect('report_card_list')
    
    # Get marks for this term - filter by school exams only
    school = enrollment.grade.school
    
    # Get all exams for this school and term
    # Use Q object to check both direct school field and term's academic_year's school
    from django.db.models import Q
    school_exams = Exam.objects.filter(
        term=report_card.term
    ).filter(
        Q(school=school) | Q(term__academic_year__school=school)
    ).distinct()
    
    # Get marks for this term, filtered by school exams
    marks = MarkEntry.objects.filter(
        enrollment=enrollment,
        exam__term=report_card.term,
        exam__in=school_exams
    ).select_related('subject', 'subject_paper', 'teacher', 'exam')
    
    # Group marks by subject
    marks_by_subject = {}
    principal_grades = {}
    subsidiary_grades = {}
    
    # Get enrolled subjects for this student
    enrolled_subjects = EnrollmentSubject.objects.filter(
        enrollment=enrollment
    ).select_related('subject')
    
    # Initialize subjects in marks_by_subject (for Primary/O-Level only)
    # For A-Level, we ONLY show subjects from the combination (handled separately below)
    # This ensures we show all subjects the student is enrolled in, even if they have no marks yet
    # BUT for A-Level, we skip this and only use combination subjects
    if enrollment.grade.level != 'A':
        for enrollment_subject in enrolled_subjects:
            subject = enrollment_subject.subject
            subject_id = subject.id
            
            if subject_id not in marks_by_subject:
                is_subsidiary = False
                marks_by_subject[subject_id] = {
                    'subject': subject,
                    'papers': {},
                    'is_subsidiary': is_subsidiary,
                    'is_compulsory': enrollment_subject.is_compulsory,
                    'letter_grade': None,
                    'numerical_grades': [],
                    'points': 0,
                    'grade_category': None,
                    'paper_grades': [],
                    'weighted_average': 0
                }
                
                # If subject has papers, initialize paper entries based on student's paper assignments
                if subject.has_papers:
                    from academics.models import StudentPaperAssignment
                    student_assignment = StudentPaperAssignment.objects.filter(
                        enrollment=enrollment,
                        subject=subject
                    ).first()
                    
                    if student_assignment and student_assignment.papers.exists():
                        # Student has specific paper assignments - only show those papers
                        subject_papers = student_assignment.papers.all().order_by('paper_number', 'name')
                    else:
                        # No assignments - show all papers for this subject (for display purposes)
                        subject_papers = subject.get_papers()
                    
                    if subject_papers.exists():
                        for paper in subject_papers:
                            paper_key = paper.id
                            marks_by_subject[subject_id]['papers'][paper_key] = {
                                'paper': paper,
                                'marks': [],
                                'average': 0,
                                'weighted_average': 0,
                                'mot': None,
                                'eot': None,
                                'avg': None,
                                'numerical_grade': None,
                                'numerical_grade_label': None,
                                'comment': None,
                                'teacher': None,
                                'paper_name': paper.name,
                                'paper_number': paper.paper_number or 1,
                                'grade': None,
                                'points': None,
                                'exam_marks': {}
                            }
                    else:
                        # Subject has papers but none defined - create default
                        marks_by_subject[subject_id]['papers']['default'] = {
                            'paper': None,
                            'marks': [],
                            'average': 0,
                            'weighted_average': 0,
                            'mot': None,
                            'eot': None,
                            'avg': None,
                            'numerical_grade': None,
                            'numerical_grade_label': None,
                            'comment': None,
                            'teacher': None,
                            'paper_name': 'Paper 1',
                            'paper_number': 1,
                            'grade': None,
                            'points': None,
                            'exam_marks': {}
                        }
                else:
                    # Subject doesn't have papers - create default paper entry
                    marks_by_subject[subject_id]['papers']['default'] = {
                        'paper': None,
                        'marks': [],
                        'average': 0,
                        'weighted_average': 0,
                        'mot': None,
                        'eot': None,
                        'avg': None,
                        'numerical_grade': None,
                        'numerical_grade_label': None,
                        'comment': None,
                        'teacher': None,
                        'paper_name': 'N/A',
                        'paper_number': 0,
                        'grade': None,
                        'points': None,
                        'exam_marks': {}
                    }
    
    # For A-Level: ONLY initialize subjects from combination (principals + subsidiaries)
    # Do NOT show other subjects that are not in the combination
    if enrollment.grade.level == 'A':
        # A-Level: ONLY show subjects from combination (principals) AND enrolled subsidiaries
        # This ensures we don't show subjects the student is not doing
        if enrollment.combination:
            combination_subjects = enrollment.combination.subjects.all()
            
            # Get subsidiaries from enrollment
            enrollment_subsidiaries = EnrollmentSubject.objects.filter(
                enrollment=enrollment,
                subject__level='A'
            ).select_related('subject')
            
            # Combine principals and subsidiaries - ALL subjects the student offers
            all_subjects = list(combination_subjects)
            for es in enrollment_subsidiaries:
                if is_subsidiary_subject(es.subject.name) and es.subject not in all_subjects:
                    all_subjects.append(es.subject)
            
            # Initialize ALL subjects in marks_by_subject (even if no marks yet)
            for subject in all_subjects:
                subject_id = subject.id
                if subject_id not in marks_by_subject:
                    marks_by_subject[subject_id] = {
                        'subject': subject,
                        'papers': {},
                        'is_subsidiary': is_subsidiary_subject(subject.name),
                        'letter_grade': None,
                        'numerical_grades': [],
                        'points': 0,
                        'grade_category': None,
                        'paper_grades': []
                    }
                    
                    # For subsidiaries without marks, create paper entries based on subject papers (like principals)
                    if is_subsidiary_subject(subject.name):
                        # Get actual papers for subsidiary subjects (e.g., Subsidiary ICT may have 2 papers)
                        # Filter by student paper assignments if they exist
                        from academics.models import StudentPaperAssignment
                        student_assignment = StudentPaperAssignment.objects.filter(
                            enrollment=enrollment,
                            subject=subject
                        ).first()
                        
                        if student_assignment and student_assignment.papers.exists():
                            subject_papers = student_assignment.papers.all()
                        else:
                            subject_papers = subject.get_papers()
                        
                        if subject_papers.exists():
                            for paper in subject_papers:
                                paper_key = paper.id
                                marks_by_subject[subject_id]['papers'][paper_key] = {
                                    'paper': paper,
                                    'marks': [],
                                    'average': 0,
                                    'mot': None,
                                    'eot': None,
                                    'avg': None,
                                    'numerical_grade': None,
                                    'numerical_grade_label': None,
                                    'comment': None,
                                    'teacher': None,
                                    'paper_name': paper.name,
                                    'paper_number': paper.paper_number or 1
                                }
                        else:
                            # If no papers defined, create a default paper entry
                            marks_by_subject[subject_id]['papers']['default'] = {
                                'paper': None,
                                'marks': [],
                                'average': 0,
                                'mot': None,
                                'eot': None,
                                'avg': None,
                                'numerical_grade': None,
                                'numerical_grade_label': None,
                                'comment': None,
                                'teacher': None,
                                'paper_name': 'Paper 1',
                                'paper_number': 1
                            }
                    else:
                        # For principals without marks, create default paper entries based on subject papers
                        # Filter by student paper assignments if they exist
                        from academics.models import StudentPaperAssignment
                        student_assignment = StudentPaperAssignment.objects.filter(
                            enrollment=enrollment,
                            subject=subject
                        ).first()
                        
                        if student_assignment and student_assignment.papers.exists():
                            subject_papers = student_assignment.papers.all()
                        else:
                            subject_papers = subject.get_papers()
                        
                        if subject_papers.exists():
                            for paper in subject_papers:
                                paper_key = paper.id
                                marks_by_subject[subject_id]['papers'][paper_key] = {
                                    'paper': paper,
                                    'marks': [],
                                    'average': 0,
                                    'mot': None,
                                    'eot': None,
                                    'avg': None,
                                    'numerical_grade': None,
                                    'numerical_grade_label': None,
                                    'comment': None,
                                    'teacher': None,
                                    'paper_name': paper.name,
                                    'paper_number': paper.paper_number or 1
                                }
                        else:
                            # If no papers defined, create a default
                            marks_by_subject[subject_id]['papers']['default'] = {
                                'paper': None,
                                'marks': [],
                                'average': 0,
                                'mot': None,
                                'eot': None,
                                'avg': None,
                                'numerical_grade': None,
                                'numerical_grade_label': None,
                                'comment': None,
                                'teacher': None,
                                'paper_name': 'Paper 1',
                                'paper_number': 1
                            }
            
            # Now get marks for these subjects - filter by school exams only
            school = enrollment.grade.school
            from django.db.models import Q
            school_exams = Exam.objects.filter(
                term=report_card.term
            ).filter(
                Q(school=school) | Q(term__academic_year__school=school)
            ).distinct()
            
            marks = MarkEntry.objects.filter(
                enrollment=enrollment,
                exam__term=report_card.term,
                subject__in=all_subjects,
                exam__in=school_exams
            ).select_related('subject', 'subject_paper', 'teacher', 'exam')
        else:
            # No combination assigned - show no marks
            marks = MarkEntry.objects.none()
            all_subjects = []
    
    # Process marks - add marks to existing subjects
    # Filter marks by student paper assignments if subject has papers
    # For A-Level, also filter by combination subjects only
    from academics.models import StudentPaperAssignment
    
    # For A-Level, get the list of allowed subjects (combination + subsidiaries)
    allowed_subject_ids = None
    if enrollment.grade.level == 'A' and enrollment.combination:
        combination_subjects = enrollment.combination.subjects.all()
        enrollment_subsidiaries = EnrollmentSubject.objects.filter(
            enrollment=enrollment,
            subject__level='A'
        ).select_related('subject')
        allowed_subject_ids = list(combination_subjects.values_list('id', flat=True))
        for es in enrollment_subsidiaries:
            if is_subsidiary_subject(es.subject.name) and es.subject.id not in allowed_subject_ids:
                allowed_subject_ids.append(es.subject.id)
    
    for mark in marks:
        subject_id = mark.subject.id
        subject = mark.subject
        
        # For A-Level, only process marks for subjects in the combination
        if enrollment.grade.level == 'A' and allowed_subject_ids is not None:
            if subject_id not in allowed_subject_ids:
                continue  # Skip this mark - subject not in combination
        
        # If subject has papers, check if student is assigned to this paper
        if subject.has_papers and mark.subject_paper:
            student_assignment = StudentPaperAssignment.objects.filter(
                enrollment=enrollment,
                subject=subject
            ).first()
            
            # If student has paper assignments, only include marks for assigned papers
            if student_assignment and student_assignment.papers.exists():
                if mark.subject_paper not in student_assignment.papers.all():
                    continue  # Skip this mark - student not assigned to this paper
        
        if subject_id not in marks_by_subject:
            # Should not happen if A-Level, but handle it
            marks_by_subject[subject_id] = {
                'subject': subject,
                'papers': {},
                'is_subsidiary': is_subsidiary_subject(subject.name),
                'letter_grade': None,
                'numerical_grades': [],
                'points': 0,
                'grade_category': None,
                'paper_grades': []
            }
        
        paper_key = mark.subject_paper.id if mark.subject_paper else 'default'
        if paper_key not in marks_by_subject[subject_id]['papers']:
            marks_by_subject[subject_id]['papers'][paper_key] = {
                'paper': mark.subject_paper,
                'marks': [],
                'average': 0,
                'mot': None,
                'eot': None,
                'avg': None,
                'numerical_grade': None,
                'numerical_grade_label': None,
                'comment': None,
                'teacher': None,
                'paper_name': mark.subject_paper.name if mark.subject_paper else 'Paper 1',
                'paper_number': mark.subject_paper.paper_number if mark.subject_paper else 1
            }
        
        marks_by_subject[subject_id]['papers'][paper_key]['marks'].append(mark)
    
    # Calculate grades for each subject
    for subject_id, subject_data in marks_by_subject.items():
        subject = subject_data['subject']
        is_subsidiary = is_subsidiary_subject(subject.name)
        subject_data['is_subsidiary'] = is_subsidiary
        
        # Collect all paper marks and process them
        all_paper_marks = []
        processed_papers = []
        
        for paper_key, paper_data in subject_data['papers'].items():
            # Get marks for this paper
            paper_marks_list = paper_data['marks']
            
            if paper_marks_list:
                # Group marks by exam (dynamic exam names from school exams)
                from collections import defaultdict
                marks_by_exam = defaultdict(list)
                for mark in paper_marks_list:
                    if mark.exam:
                        exam_name = mark.exam.name
                        marks_by_exam[exam_name].append(mark)
                
                # Calculate scores per exam
                exam_scores_dict = {}
                all_scores = []
                total_weighted_score = Decimal('0.00')
                total_weight = Decimal('0.00')
                
                for exam_name, exam_marks_list in marks_by_exam.items():
                    exam_scores = [float(m.score) for m in exam_marks_list if m.score is not None]
                    if exam_scores:
                        exam_avg = sum(exam_scores) / len(exam_scores)
                        exam_scores_dict[exam_name] = exam_avg
                        all_scores.extend(exam_scores)
                        
                        # Calculate weighted average
                        if exam_marks_list and exam_marks_list[0].exam:
                            exam_weight = exam_marks_list[0].exam.percentage_weight
                            total_weighted_score += Decimal(str(exam_avg)) * (Decimal(str(exam_weight)) / Decimal('100.00'))
                            total_weight += Decimal(str(exam_weight))
                
                # Calculate overall average from all marks
                if all_scores:
                    paper_avg = sum(all_scores) / len(all_scores)
                    paper_data['avg'] = paper_avg
                    paper_data['average'] = paper_avg
                    
                    # Calculate weighted average
                    if total_weight > 0:
                        weighted_avg = (total_weighted_score / (total_weight / Decimal('100.00')))
                        paper_data['weighted_average'] = float(weighted_avg)
                    else:
                        paper_data['weighted_average'] = paper_avg
                    
                    # Store exam marks for display (dynamic, not hardcoded MOT/EOT)
                    paper_data['exam_marks'] = exam_scores_dict
                    
                    # For backward compatibility, keep first/last as MOT/EOT if only 2 exams
                    sorted_exam_names = sorted(exam_scores_dict.keys())
                    if len(sorted_exam_names) == 2:
                        paper_data['mot'] = exam_scores_dict[sorted_exam_names[0]]
                        paper_data['eot'] = exam_scores_dict[sorted_exam_names[1]]
                    elif len(sorted_exam_names) == 1:
                        paper_data['mot'] = exam_scores_dict[sorted_exam_names[0]]
                        paper_data['eot'] = exam_scores_dict[sorted_exam_names[0]]
                    elif all_scores:
                        # Multiple exams - use first and last scores
                        paper_data['mot'] = all_scores[0]
                        paper_data['eot'] = all_scores[-1]
                    
                    # Get grade and points for this paper
                    # For A-Level: Use numerical grade
                    if enrollment.grade.level == 'A':
                        # Convert to numerical grade (use config if available)
                        numerical_grade = assign_numerical_grade(paper_avg, config=uace_config)
                        numerical_grade_label = get_numerical_grade_label(numerical_grade)
                        paper_data['numerical_grade'] = numerical_grade
                        paper_data['numerical_grade_label'] = numerical_grade_label
                        all_paper_marks.append(numerical_grade)
                        subject_data['numerical_grades'].append(numerical_grade)
                    else:
                        # For O-Level/Primary: Use grading system
                        from academics.models import GradingSystem
                        level_map = {'P': 'Primary', 'O': 'O-Level', 'A': 'A-Level'}
                        grading_level = level_map.get(enrollment.grade.level, 'Primary')
                        grade_scale = GradingSystem.get_grade_for_score(paper_avg, school, grading_level)
                        if grade_scale:
                            paper_data['grade'] = grade_scale.grade
                            paper_data['points'] = float(grade_scale.points) if grade_scale.points else 0
                    
                    # Get comment and teacher from first mark
                    first_mark = paper_marks_list[0]
                    paper_data['comment'] = first_mark.comments if hasattr(first_mark, 'comments') else ''
                    paper_data['teacher'] = first_mark.teacher if hasattr(first_mark, 'teacher') else None
            
            # Add to processed papers list (convert dict values to list for template)
            processed_papers.append(paper_data)
        
        # Convert papers dict to sorted list for template iteration
        # For subsidiaries, filter out papers without marks (no avg and no exam_marks with scores)
        all_papers_list = sorted(processed_papers, key=lambda p: p.get('paper_number', 1))
        
        if is_subsidiary:
            # For subsidiaries, only include papers that have marks
            papers_with_marks = []
            for paper in all_papers_list:
                has_marks = False
                # Check if paper has average score
                if paper.get('avg'):
                    has_marks = True
                # Check if paper has any exam marks with scores
                elif paper.get('exam_marks'):
                    for e_name, e_score in paper.get('exam_marks', {}).items():
                        if e_score is not None:
                            has_marks = True
                            break
                
                if has_marks:
                    papers_with_marks.append(paper)
            
            subject_data['papers'] = papers_with_marks
        else:
            # For principals, show all papers
            subject_data['papers'] = all_papers_list
        
        # Calculate letter grade
        if is_subsidiary:
            if all_paper_marks:
                # For subsidiaries with multiple papers (e.g., Subsidiary ICT with 2 papers),
                # use the BEST (lowest numerical grade = highest score) paper for Pass/Fail determination
                # This ensures if student has Paper 1 = C3 and Paper 2 = C5, we use C3 (best grade)
                best_paper_grade = min(all_paper_marks)  # Lower number = better grade (1 is best, 9 is worst)
                letter_grade = compute_subsidiary_grade(best_paper_grade, config=uace_config)
                # Change "Pass" to "O" for subsidiaries (O stands for one point)
                if letter_grade == 'Pass':
                    letter_grade = 'O'
                subject_data['letter_grade'] = letter_grade
                # Don't set paper_grades for subsidiaries (not needed)
                subject_data['paper_grades'] = []
                # Don't set grade_category for subsidiaries (not needed)
                subject_data['grade_category'] = None
                # Use config points if available
                if uace_config:
                    subject_data['points'] = uace_config.points_subsidiary_pass if letter_grade == 'O' else uace_config.points_subsidiary_fail
                else:
                    subject_data['points'] = 1 if letter_grade == 'O' else 0
                subsidiary_grades[subject.name] = letter_grade
        else:
            # For O-Level/Primary: Calculate letter grade based on weighted average using GradingSystem
            # For A-Level: Use A-Level grading functions
            if enrollment.grade.level == 'A':
                if all_paper_marks:
                    num_papers = len(all_paper_marks)
                    letter_grade = compute_principal_letter_grade(all_paper_marks, num_papers)
                    subject_data['letter_grade'] = letter_grade
                    subject_data['grade_category'] = get_grade_category(letter_grade)
                    # Format paper grades as labels (D1, C3, etc.)
                    subject_data['paper_grades'] = [get_numerical_grade_label(g) for g in all_paper_marks]
                    
                    # Calculate points using config if available
                    if uace_config:
                        points_map = {
                            'A': uace_config.points_a, 'B': uace_config.points_b, 'C': uace_config.points_c,
                            'D': uace_config.points_d, 'E': uace_config.points_e, 'O': uace_config.points_o, 'F': uace_config.points_f
                        }
                    else:
                        points_map = {'A': 6, 'B': 5, 'C': 4, 'D': 3, 'E': 2, 'O': 1, 'F': 0}
                    subject_data['points'] = points_map.get(letter_grade, 0)
                    principal_grades[subject.name] = letter_grade
            else:
                # For O-Level/Primary: Calculate letter grade from weighted average
                if subject_data.get('weighted_average', 0) > 0:
                    weighted_avg = subject_data['weighted_average']
                elif processed_papers:
                    # Calculate weighted average from all papers
                    total_weighted = 0
                    total_weight = 0
                    for paper in processed_papers:
                        if paper.get('weighted_average'):
                            total_weighted += paper['weighted_average']
                            total_weight += 1
                        elif paper.get('avg'):
                            total_weighted += paper['avg']
                            total_weight += 1
                    weighted_avg = total_weighted / total_weight if total_weight > 0 else 0
                else:
                    weighted_avg = 0
                
                if weighted_avg > 0:
                    # Get grade from GradingSystem
                    from academics.models import GradingSystem
                    level_map = {'P': 'Primary', 'O': 'O-Level', 'A': 'A-Level'}
                    grading_level = level_map.get(enrollment.grade.level, 'Primary')
                    grade_scale = GradingSystem.get_grade_for_score(weighted_avg, school, grading_level)
                    if grade_scale:
                        subject_data['letter_grade'] = grade_scale.grade
                        subject_data['points'] = float(grade_scale.points) if grade_scale.points else 0
                    else:
                        subject_data['letter_grade'] = None
                        subject_data['points'] = 0
                else:
                    subject_data['letter_grade'] = None
                    subject_data['points'] = 0
    
    # Calculate total UACE points (use config if available)
    uace_total_points = calculate_uace_points(principal_grades, subsidiary_grades, config=uace_config)
    
    # IMPORTANT: Collect all unique exam names from ALL school exams for the term (not just from papers with marks)
    # This ensures we show all exam columns even if students have no marks yet
    # Note: school variable is already defined earlier (line 584), but we'll use it here for clarity
    school_exams = Exam.objects.filter(
        term=report_card.term,
        school=school,
        is_active=True
    ).order_by('order', 'name')
    
    # Get exam names from school exams (this is the source of truth)
    all_exam_names = [exam.name for exam in school_exams]
    
    # Also collect exam names from papers that have marks (for consistency)
    exam_names_from_marks = set()
    for subject_data in marks_by_subject.values():
        for paper in subject_data.get('papers', []):
            if paper.get('exam_marks'):
                exam_names_from_marks.update(paper['exam_marks'].keys())
    
    # Combine both sources (school exams + marks) to ensure we have all exam names
    all_exam_names = sorted(list(set(all_exam_names + list(exam_names_from_marks))))
    
    # Ensure all papers have all exam names in their exam_marks dict (even if None) for template consistency
    # This makes it easier to display in the template - we can iterate and find matches
    for subject_data in marks_by_subject.values():
        for paper in subject_data.get('papers', []):
            if 'exam_marks' not in paper or paper.get('exam_marks') is None:
                paper['exam_marks'] = {}
            # Add all exam names to this paper's exam_marks dict (with None if not present)
            for exam_name in all_exam_names:
                if exam_name not in paper['exam_marks']:
                    paper['exam_marks'][exam_name] = None
    
    # For O-Level: Filter to only show compulsory subjects and enrolled optionals
    if enrollment.grade.level == 'O':
        # Get the actual list of compulsory subjects from the Subject model
        # This is the source of truth for what subjects are compulsory
        from academics.models import Subject
        actual_compulsory_subjects = Subject.objects.filter(
            level='O',
            is_compulsory=True
        )
        actual_compulsory_subject_ids = set(actual_compulsory_subjects.values_list('id', flat=True))
        
        # Only keep subjects that are:
        # 1. Actually compulsory according to Subject model (is_compulsory=True in Subject), OR
        # 2. Optional but enrolled (in enrolled_subjects but not in actual_compulsory_subjects)
        filtered_marks_by_subject = {}
        enrolled_subject_ids = set(enrolled_subjects.values_list('subject_id', flat=True))
        
        for subject_id, subject_data in marks_by_subject.items():
            subject = subject_data.get('subject')
            # Check if subject is actually compulsory in the Subject model
            is_actually_compulsory = subject_id in actual_compulsory_subject_ids if subject else False
            
            # Update the is_compulsory flag to match the actual Subject model
            if subject:
                subject_data['is_compulsory'] = is_actually_compulsory
            
            # Keep if actually compulsory OR if optional but enrolled
            if is_actually_compulsory or (subject_id in enrolled_subject_ids and not is_actually_compulsory):
                filtered_marks_by_subject[subject_id] = subject_data
        
        marks_by_subject = filtered_marks_by_subject
    
    # Sort subjects: principals first (by name), then subsidiaries (by name)
    principals = {k: v for k, v in marks_by_subject.items() if not v.get('is_subsidiary', False)}
    subsidiaries = {k: v for k, v in marks_by_subject.items() if v.get('is_subsidiary', False)}
    
    sorted_principals = dict(sorted(principals.items(), key=lambda x: x[1]['subject'].name))
    sorted_subsidiaries = dict(sorted(subsidiaries.items(), key=lambda x: x[1]['subject'].name))
    
    # Combine: principals first, then subsidiaries
    marks_by_subject = {**sorted_principals, **sorted_subsidiaries}
    
    # Check if EOT (End of Term) exam exists - indicates term has ended
    has_eot_exam = False
    current_exam_name = None
    eot_exams = school_exams.filter(name__icontains='eot').first()
    if eot_exams:
        has_eot_exam = True
    else:
        # If no EOT exam, use the first/last exam name as current exam
        if school_exams.exists():
            # Get the exam with the highest order or last exam
            current_exam = school_exams.order_by('-order', 'name').first()
            if current_exam:
                current_exam_name = current_exam.name
    
    # Get next term start date (next term in the same academic year)
    from core.models import Term
    next_term = None
    next_term_start_date = None
    try:
        # Get the next term in the same academic year, ordered by start_date
        next_term = Term.objects.filter(
            academic_year=report_card.term.academic_year,
            start_date__gt=report_card.term.start_date
        ).order_by('start_date').first()
        if next_term:
            next_term_start_date = next_term.start_date
    except:
        pass
    
    # Calculate Principal Passes
    # Principal passes begin from E (E, D, C, B, A are passes)
    # O and F are not principal passes
    principal_passes = 0
    principal_letter_grades = list(principal_grades.values())
    
    if principal_letter_grades:
        # Count passes (E, D, C, B, A)
        passes = [g for g in principal_letter_grades if g in ['A', 'B', 'C', 'D', 'E']]
        fails = [g for g in principal_letter_grades if g in ['O', 'F']]
        
        if len(passes) == 3:
            # All 3 are E to A = 3 principal passes
            principal_passes = 3
        elif len(passes) == 2:
            # 2 passes, 1 O or F = 2 principal passes
            principal_passes = 2
        elif len(passes) == 1:
            # 1 pass (E or above), rest are O or F = 1 principal pass
            principal_passes = 1
        elif len(passes) == 0:
            # All are O or F = 0 principal passes
            principal_passes = 0
    
    # Calculate Subsidiary Passes
    # Subsidiaries: O = 1 point (changed from "Pass" to "O"), Fail = 0 points
    subsidiary_passes = 0
    subsidiary_letter_grades = list(subsidiary_grades.values())
    
    if subsidiary_letter_grades:
        # Count how many subsidiaries are "O" (changed from "Pass" to "O")
        passed_subsidiaries = [g for g in subsidiary_letter_grades if g == 'O']
        subsidiary_passes = len(passed_subsidiaries)
    
    # For O-Level: Calculate class position based on average score
    class_position = None
    total_students = None
    if enrollment.grade.level == 'O':
        # Get all report cards for the same grade and term
        # Note: ReportCard is already imported at the top of the function
        class_report_cards = ReportCard.objects.filter(
            term=report_card.term,
            enrollment__grade=enrollment.grade
        ).select_related('enrollment').order_by('-average_score')
        
        total_students = class_report_cards.count()
        
        # Find the position of the current student
        # Position is 1-indexed (1 = best, highest average)
        # Handle ties: if multiple students have the same average, they share the same position
        # Count how many students have a higher average
        current_avg = float(report_card.average_score) if report_card.average_score else 0
        students_with_higher_avg = class_report_cards.filter(
            average_score__gt=current_avg
        ).count()
        class_position = students_with_higher_avg + 1
    
    # Determine template based on grade level
    if enrollment.grade.level == 'A':
        template = 'academics/report_card_alevel.html'
    elif enrollment.grade.level == 'O':
        template = 'academics/report_card_olevel.html'
    else:
        template = 'academics/report_card_detail.html'
    
    context = {
        'report_card': report_card,
        'enrollment': enrollment,
        'marks_by_subject': marks_by_subject,
        'principal_grades': principal_grades,
        'subsidiary_grades': subsidiary_grades,
        'uace_total_points': uace_total_points,
        'all_exam_names': all_exam_names,  # Dynamic exam names from school
        'uace_config': uace_config,  # Pass UACE config to template
        'has_eot_exam': has_eot_exam,  # Whether EOT exam exists (term has ended)
        'current_exam_name': current_exam_name,  # Current exam name if no EOT
        'next_term_start_date': next_term_start_date,  # Next term start date
        'principal_passes': principal_passes,  # Number of principal passes
        'subsidiary_passes': subsidiary_passes,  # Number of subsidiary passes
        'class_position': class_position,  # Position in class (for O-Level)
        'total_students': total_students,  # Total students in class (for O-Level)
        'user': request.user,  # Pass user to template for permission checks
        'title': 'Report Card'
    }
    
    return render(request, template, context)

@login_required
def report_card_export_pdf(request, report_card_id):
    """Export report card as PDF using WeasyPrint."""
    from django.http import HttpResponse
    from django.template.loader import render_to_string

    report_card = get_object_or_404(ReportCard, pk=report_card_id)
    enrollment = report_card.enrollment
    grade_level = enrollment.grade.level

    # Re-use the same context-building logic as report_card_detail
    # (call the detail view in "data-only" mode by reconstructing the context)
    # We delegate to a helper so we don't duplicate the logic.
    context = _build_report_card_context(request, report_card)
    if context is None:
        messages.error(request, "You don't have permission to export this report card.")
        return redirect('report_card_list')

    # Choose the PDF template
    if grade_level == 'A':
        template_name = 'academics/report_card_alevel_pdf.html'
    else:
        template_name = 'academics/report_card_pdf.html'

    try:
        from weasyprint import HTML, CSS
        html_string = render_to_string(template_name, context, request=request)
        pdf_file = HTML(
            string=html_string,
            base_url=request.build_absolute_uri('/')
        ).write_pdf(
            stylesheets=[CSS(string='@page { size: A4; margin: 1.5cm; }')]
        )
        student_name = enrollment.student.get_full_name().replace(' ', '_')
        term_name = report_card.term.name.replace(' ', '_')
        filename = f'ReportCard_{student_name}_{term_name}.pdf'
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    except Exception as exc:
        import traceback
        messages.error(request, f'PDF generation failed: {exc}')
        return redirect('report_card_detail', report_card_id=report_card_id)


def _build_report_card_context(request, report_card):
    """
    Build the template context for a report card.
    Returns None if the user has no permission.
    Re-uses the logic from report_card_detail to avoid duplication.
    """
    from academics.uace_grading import (
        assign_numerical_grade, get_numerical_grade_label,
        compute_principal_letter_grade, compute_subsidiary_grade,
        calculate_uace_points, get_grade_category, is_subsidiary_subject,
    )
    from students.models import EnrollmentSubject
    from academics.models import UACEGradingConfig

    enrollment = report_card.enrollment

    # Permission check
    if not request.user.is_superadmin():
        if hasattr(request.user, 'school') and enrollment.grade.school != request.user.school:
            return None

    grade_level = enrollment.grade.level
    school = enrollment.grade.school

    uace_config = None
    if grade_level == 'A':
        try:
            uace_config = UACEGradingConfig.objects.get(school=school)
        except UACEGradingConfig.DoesNotExist:
            pass

    from django.db.models import Q
    school_exams = Exam.objects.filter(term=report_card.term).filter(
        Q(school=school) | Q(term__academic_year__school=school)
    ).distinct()

    marks = MarkEntry.objects.filter(
        enrollment=enrollment,
        exam__term=report_card.term,
        exam__in=school_exams,
    ).select_related('subject', 'subject_paper', 'teacher', 'exam')

    marks_by_subject = {}
    enrolled_subjects = EnrollmentSubject.objects.filter(enrollment=enrollment).select_related('subject')

    if grade_level != 'A':
        for es in enrolled_subjects:
            sid = es.subject.id
            marks_by_subject[sid] = {
                'subject': es.subject,
                'papers': {},
                'is_subsidiary': False,
                'is_compulsory': es.is_compulsory,
                'letter_grade': None,
                'numerical_grades': [],
                'points': 0,
                'grade_category': None,
                'weighted_average': None,
            }

    for mark in marks:
        sid = mark.subject.id
        if sid not in marks_by_subject:
            marks_by_subject[sid] = {
                'subject': mark.subject,
                'papers': {},
                'is_subsidiary': is_subsidiary_subject(mark.subject.name) if grade_level == 'A' else False,
                'is_compulsory': True,
                'letter_grade': None,
                'numerical_grades': [],
                'points': 0,
                'grade_category': None,
                'weighted_average': None,
            }
        paper_key = mark.subject_paper.id if mark.subject_paper else 'main'
        marks_by_subject[sid]['papers'][paper_key] = {
            'paper': mark.subject_paper,
            'mark': mark,
            'score': float(mark.score) if mark.score is not None else None,
            'numerical_grade': assign_numerical_grade(float(mark.score), uace_config) if mark.score is not None else None,
        }

    # Calculate weighted averages
    subject_averages = report_card.get_weighted_average_per_subject()
    for sid, subj_data in marks_by_subject.items():
        subj_name = subj_data['subject'].name
        if subj_name in subject_averages:
            subj_data['weighted_average'] = float(subject_averages[subj_name].get('weighted_average', 0))

    # A-Level: compute letter grades
    principal_grades = {}
    subsidiary_grades = {}
    if grade_level == 'A':
        for sid, subj_data in marks_by_subject.items():
            paper_grades = [p['numerical_grade'] for p in subj_data['papers'].values() if p['numerical_grade'] is not None]
            subj = subj_data['subject']
            if subj_data.get('is_subsidiary'):
                if paper_grades:
                    subj_data['letter_grade'] = compute_subsidiary_grade(paper_grades[0], uace_config)
                    subsidiary_grades[subj.name] = subj_data['letter_grade']
            else:
                if paper_grades:
                    letter = compute_principal_letter_grade(paper_grades, len(paper_grades))
                    subj_data['letter_grade'] = letter
                    subj_data['grade_category'] = get_grade_category(letter)
                    principal_grades[subj.name] = letter

    total_uace_points = 0
    if grade_level == 'A' and principal_grades:
        total_uace_points = calculate_uace_points(principal_grades, subsidiary_grades, uace_config)

    next_term = None
    from core.models import Term
    try:
        current_term_end = report_card.term.end_date
        next_term = Term.objects.filter(
            academic_year__school=school,
            start_date__gt=current_term_end
        ).order_by('start_date').first()
    except Exception:
        pass

    return {
        'report_card': report_card,
        'enrollment': enrollment,
        'student': enrollment.student,
        'school': school,
        'marks_by_subject': marks_by_subject,
        'principal_grades': principal_grades,
        'subsidiary_grades': subsidiary_grades,
        'total_uace_points': total_uace_points,
        'uace_config': uace_config,
        'next_term': next_term,
        'title': 'Report Card',
    }

@login_required
def report_card_add_comment(request, report_card_id):
    """Add or update comment to report card"""
    report_card = get_object_or_404(ReportCard, pk=report_card_id)
    
    # Check permissions - only class teacher of the grade, headteacher, or superadmin can add/edit
    if not request.user.is_superadmin() and not request.user.is_headteacher():
        # Check if user is the class teacher for this student's grade
        if not (report_card.enrollment.grade.class_teacher == request.user):
            messages.error(request, "You don't have permission to add comments to this report card.")
            return redirect('report_card_detail', report_card_id=report_card_id)
    
    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        report_card.class_teacher_comment = comment
        report_card.save()
        messages.success(request, 'Comment saved successfully!')
    return redirect('report_card_detail', report_card_id=report_card_id)

@login_required
@user_passes_test(headteacher_required)
def report_card_add_headteacher_comment(request, report_card_id):
    """Add headteacher comment to report card"""
    report_card = get_object_or_404(ReportCard, pk=report_card_id)
    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        if comment:
            report_card.headteacher_comment = comment
            report_card.save()
            messages.success(request, 'Headteacher comment added successfully!')
    return redirect('report_card_detail', report_card_id=report_card_id)

@login_required
@user_passes_test(headteacher_required)
def generate_report_cards(request):
    """Generate report cards for all students"""
    from core.models import Term, AcademicYear
    from students.models import Enrollment
    from academics.models import ReportCard
    
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    # Get terms for this school
    terms = Term.objects.all()
    if school:
        terms = terms.filter(academic_year__school=school, academic_year__is_active=True)
    terms = terms.select_related('academic_year').order_by('-academic_year__start_date', 'start_date')
    
    # Get selected term from request
    selected_term_id = request.GET.get('term') or request.POST.get('term')
    selected_term = None
    exams = Exam.objects.none()
    exam_count = 0
    
    if selected_term_id:
        try:
            selected_term = Term.objects.get(pk=selected_term_id)
            # Get exams for this term using the same logic as mark_entry_list
            from django.db.models import Q
            exams_query = Exam.objects.filter(term=selected_term)
            
            if school:
                exams_query = exams_query.filter(
                    Q(school=school) | Q(term__academic_year__school=school)
                ).distinct()
            
            # Try active exams first, then fall back to all exams
            active_exams = exams_query.filter(is_active=True)
            exam_count = active_exams.count()
            
            if exam_count > 0:
                exams = active_exams
            else:
                all_exams = exams_query
                exam_count = all_exams.count()
                if exam_count > 0:
                    exams = all_exams
            
            exams = exams.order_by('order', 'name')
        except Term.DoesNotExist:
            pass
    
    # Auto-generate report cards when term is selected (GET request with term parameter)
    if selected_term_id and request.method == 'GET' and selected_term:
        try:
            term = selected_term  # Use the already-fetched term
            # Get all active enrollments for this school
            enrollments = Enrollment.objects.filter(is_active=True)
            if school:
                enrollments = enrollments.filter(grade__school=school)
            
            # Auto-generate or update report cards for all students
            generated_count = 0
            updated_count = 0
            for enrollment in enrollments:
                report_card, created = ReportCard.objects.get_or_create(
                    enrollment=enrollment,
                    term=term,
                    defaults={}
                )
                if created:
                    generated_count += 1
                else:
                    updated_count += 1
                # Save to trigger calculation of aggregates, points, etc.
                # This will recalculate even if marks are still being entered
                report_card.save()
            
            if generated_count > 0 or updated_count > 0:
                messages.info(request, f'Auto-generated {generated_count} new report cards and updated {updated_count} existing ones for {term.name}. Report cards are available for viewing even if marks are still being entered.')
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error auto-generating report cards: {str(e)}")
            print(error_trace)
            # Don't show error to user, just log it
    
    if request.method == 'POST':
        term_id = request.POST.get('term')
        if not term_id:
            messages.error(request, 'Please select a term.')
            return render(request, 'academics/generate_report_cards.html', {
                'terms': terms,
                'selected_term': selected_term,
                'exams': exams,
                'exam_count': exam_count,
                'title': 'Generate Report Cards'
            })
        
        try:
            term = Term.objects.get(pk=term_id)
            # Get all active enrollments for this school
            enrollments = Enrollment.objects.filter(is_active=True)
            if school:
                enrollments = enrollments.filter(grade__school=school)
            
            # Generate report cards for all students
            generated_count = 0
            for enrollment in enrollments:
                report_card, created = ReportCard.objects.get_or_create(
                    enrollment=enrollment,
                    term=term,
                    defaults={}
                )
                if created:
                    generated_count += 1
                # Save to trigger calculation of aggregates, points, etc.
                report_card.save()
            
            messages.success(request, f'Successfully generated {generated_count} new report cards and updated {len(enrollments) - generated_count} existing ones.')
            return redirect('report_card_list')
        except Term.DoesNotExist:
            messages.error(request, 'Selected term does not exist.')
            return render(request, 'academics/generate_report_cards.html', {
                'terms': terms,
                'selected_term': selected_term,
                'exams': exams,
                'exam_count': exam_count,
                'title': 'Generate Report Cards'
            })
    
    return render(request, 'academics/generate_report_cards.html', {
        'terms': terms,
        'selected_term': selected_term,
        'exams': exams,
        'exam_count': exam_count,
        'title': 'Generate Report Cards'
    })

@login_required
@user_passes_test(headteacher_required)
def report_cards_export_all(request):
    """Export all report cards"""
    # Placeholder - implement bulk PDF export
    messages.info(request, 'Bulk PDF export feature coming soon.')
    return redirect('report_card_list')

# Exam Management Views
@login_required
@user_passes_test(headteacher_required)
def exam_list(request):
    """List all exams"""
    from core.models import Term
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    exams = Exam.objects.all()
    if school:
        # Check both direct school field and term's academic_year's school
        from django.db.models import Q
        exams = exams.filter(
            Q(school=school) | Q(term__academic_year__school=school)
        ).distinct()
    
    # Get terms for the school
    terms = Term.objects.all()
    if school:
        terms = terms.filter(academic_year__school=school)
    terms = terms.select_related('academic_year').order_by('-academic_year__start_date', 'start_date', 'name')
    
    # Group exams by term
    exams_by_term = {}
    for exam in exams.select_related('term', 'term__academic_year'):
        term_key = f"{exam.term.name} ({exam.term.academic_year.name})"
        if term_key not in exams_by_term:
            exams_by_term[term_key] = {
                'exams': [],
                'total_weight': 0
            }
        exams_by_term[term_key]['exams'].append(exam)
        exams_by_term[term_key]['total_weight'] += float(exam.percentage_weight)
    
    # Sort exams within each term by order, then name
    for term_data in exams_by_term.values():
        term_data['exams'].sort(key=lambda x: (x.order, x.name))
    
    # Get current term (if applicable)
    current_term = None
    if terms.exists():
        current_term = terms.first()
    
    return render(request, 'academics/exam_list.html', {
        'exams': exams,
        'exams_by_term': exams_by_term,
        'terms': terms,
        'current_term': current_term,
        'title': 'Manage Exams'
    })

@login_required
@user_passes_test(headteacher_required)
def exam_create(request):
    """Create a new exam"""
    if request.method == 'POST':
        form = ExamForm(request.POST, school=getattr(request.user, 'school', None), user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam created successfully!')
            return redirect('exam_list')
    else:
        form = ExamForm(school=getattr(request.user, 'school', None), user=request.user)
    return render(request, 'academics/exam_form.html', {'form': form, 'title': 'Create Exam'})

@login_required
@user_passes_test(headteacher_required)
def exam_edit(request, exam_id):
    """Edit an exam"""
    exam = get_object_or_404(Exam, pk=exam_id)
    if not request.user.is_superadmin() and exam.term.academic_year.school != request.user.school:
        messages.error(request, "You don't have permission to edit this exam.")
        return redirect('exam_list')
    
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam, school=getattr(request.user, 'school', None), user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam updated successfully!')
            return redirect('exam_list')
    else:
        form = ExamForm(instance=exam, school=getattr(request.user, 'school', None), user=request.user)
    return render(request, 'academics/exam_form.html', {'form': form, 'exam': exam, 'title': 'Edit Exam'})

@login_required
@user_passes_test(headteacher_required)
def exam_delete(request, exam_id):
    """Delete an exam"""
    exam = get_object_or_404(Exam, pk=exam_id)
    if not request.user.is_superadmin() and exam.term.academic_year.school != request.user.school:
        messages.error(request, "You don't have permission to delete this exam.")
        return redirect('exam_list')
    
    exam.delete()
    messages.success(request, 'Exam deleted successfully!')
    return redirect('exam_list')

# UACE Grading Configuration
@login_required
@user_passes_test(headteacher_or_dos_required)
def uace_grading_config(request):
    """UACE Grading System Configuration Page - Editable for Headteachers and DOS"""
    from academics.models import UACEGradingConfig
    from academics.forms import UACEGradingConfigForm
    
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    if not school:
        messages.error(request, "You must be associated with a school to configure UACE grading.")
        return redirect('home')
    
    # Get or create config for this school
    config, created = UACEGradingConfig.objects.get_or_create(school=school)
    
    if request.method == 'POST':
        form = UACEGradingConfigForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            config.created_by = request.user
            config.save()
            messages.success(request, 'UACE grading configuration updated successfully!')
            return redirect('uace_grading_config')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UACEGradingConfigForm(instance=config)
    
    # Build grading ranges from config for display
    grading_ranges = []
    for grade_num in range(1, 10):
        min_val, max_val = config.get_grade_range(grade_num)
        labels = {1: 'D1', 2: 'D2', 3: 'C3', 4: 'C4', 5: 'C5', 6: 'C6', 7: 'P7', 8: 'P8', 9: 'F9'}
        categories = {1: 'Distinction', 2: 'Distinction', 3: 'Credit', 4: 'Credit', 5: 'Credit', 6: 'Credit', 7: 'Pass', 8: 'Pass', 9: 'Fail'}
        grading_ranges.append({
            'range': f'{float(min_val)}-{float(max_val)}',
            'grade': grade_num,
            'label': labels[grade_num],
            'category': categories[grade_num]
        })
    
    # Points system from config
    points_system = [
        {'grade': 'A', 'points': config.points_a, 'type': 'Principal'},
        {'grade': 'B', 'points': config.points_b, 'type': 'Principal'},
        {'grade': 'C', 'points': config.points_c, 'type': 'Principal'},
        {'grade': 'D', 'points': config.points_d, 'type': 'Principal'},
        {'grade': 'E', 'points': config.points_e, 'type': 'Principal'},
        {'grade': 'O', 'points': config.points_o, 'type': 'Principal'},
        {'grade': 'F', 'points': config.points_f, 'type': 'Principal'},
        {'grade': 'Pass', 'points': config.points_subsidiary_pass, 'type': 'Subsidiary'},
        {'grade': 'Fail', 'points': config.points_subsidiary_fail, 'type': 'Subsidiary'},
    ]
    
    # Principal letter grade conditions (these are logic-based, not editable)
    principal_grades_2paper = [
        {'letter': 'A', 'condition': 'Both distinctions: e.g., (1,1), (1,2), (2,2)'},
        {'letter': 'B', 'condition': 'At worst one C3, with the other better or equal: e.g., (1,3), (2,3), (3,3)'},
        {'letter': 'C', 'condition': 'At worst one C4, with the other better or equal: e.g., (1,4), (3,4), (4,4)'},
        {'letter': 'D', 'condition': 'At worst one C5, with the other better or equal: e.g., (1,5), (4,5), (5,5)'},
        {'letter': 'E', 'condition': 'At worst one P7, with the other a credit or better: e.g., (1,7), (6,7), but not (7,7)'},
        {'letter': 'O', 'condition': 'Combinations like (7,7), (7,8), (8,8) – passes but not qualifying for E'},
        {'letter': 'F', 'condition': 'At least one F9 with the other P8 or worse: e.g., (8,9), (9,9)'},
    ]
    
    principal_grades_3paper = [
        {'letter': 'A', 'condition': 'At worst one C3, with the other two distinctions: e.g., (1,1,3), (1,2,3), (2,2,3)'},
        {'letter': 'B', 'condition': 'At worst one C4, with the other two better: e.g., (1,1,4), (2,3,4), (3,3,4)'},
        {'letter': 'C', 'condition': 'At worst one C5, with the other two better: e.g., (1,1,5), (3,4,5), (4,4,5)'},
        {'letter': 'D', 'condition': 'At worst one C6, with the other two better: e.g., (1,1,6), (4,5,6), (5,5,6)'},
        {'letter': 'E', 'condition': 'At worst one P7, with the other two credits or better: e.g., (1,1,7), (5,6,7), (6,6,7)'},
        {'letter': 'O', 'condition': 'Combinations like (6,7,8), (7,7,7) – moderate passes not qualifying for E'},
        {'letter': 'F', 'condition': 'Severe failures: e.g., (9,9,9), or two F9s with one P8'},
    ]
    
    # Subsidiary rules
    subsidiary_rules = [
        {'rule': 'General Paper (GP)', 'condition': 'ALWAYS required for all A-Level students'},
        {'rule': 'Subsidiary ICT', 'condition': 'Required if Mathematics is a principal subject'},
        {'rule': 'Subsidiary Mathematics', 'condition': 'Required if Economics is principal (but no Math) OR Science combination without Math'},
        {'rule': 'Subsidiary Choice', 'condition': 'Can be set per combination (Auto, Sub-Math, or Sub-ICT)'},
        {'rule': 'Subsidiary Pass Threshold', 'condition': f'Numerical grades 1-{config.subsidiary_pass_max_grade} = Pass (editable below)'},
    ]
    
    context = {
        'form': form,
        'config': config,
        'grading_ranges': grading_ranges,
        'principal_grades_2paper': principal_grades_2paper,
        'principal_grades_3paper': principal_grades_3paper,
        'points_system': points_system,
        'subsidiary_rules': subsidiary_rules,
    }
    
    return render(request, 'academics/uace_grading_config.html', context)

# ── Grading Settings ──────────────────────────────────────────────────────
@login_required
@user_passes_test(headteacher_required)
def grading_settings(request):
    """Unified grading configuration page — O-Level (NLSC) + A-Level + Primary"""
    from academics.forms import GradingSystemForm
    from academics.models import GradingSystem, GradeScale

    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        action = request.POST.get('action', 'create')

        # ── create a new grading system ──────────────────────────────────────
        if action == 'create':
            form = GradingSystemForm(request.POST, school=school)
            if form.is_valid():
                gs = form.save(commit=False)
                if school:
                    gs.school = school
                if GradingSystem.objects.filter(school=gs.school, level=gs.level).exists():
                    msg = f'A {gs.level} grading system already exists.'
                    if is_ajax:
                        return JsonResponse({'success': False, 'error': msg}, status=400)
                    messages.warning(request, msg)
                else:
                    gs.save()
                    if is_ajax:
                        return JsonResponse({'success': True, 'message': f'{gs.level} system created.'})
                    messages.success(request, f'{gs.level} grading system created with Uganda curriculum defaults.')
            else:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': 'Invalid form data.'}, status=400)
                messages.error(request, 'Please correct the errors below.')

        # ── add a grade scale ─────────────────────────────────────────────────
        elif action == 'scale_add':
            gs_id = request.POST.get('grading_system_id')
            gs = get_object_or_404(GradingSystem, pk=gs_id)
            if school and gs.school != school:
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
            try:
                scale = GradeScale.objects.create(
                    grading_system=gs,
                    grade=request.POST.get('grade', '').strip(),
                    min_score=request.POST.get('min_score'),
                    max_score=request.POST.get('max_score'),
                    points=request.POST.get('points'),
                    remark=request.POST.get('remark', '').strip(),
                )
                return JsonResponse({
                    'success': True,
                    'scale': {
                        'id': scale.pk,
                        'grade': scale.grade,
                        'min_score': str(scale.min_score),
                        'max_score': str(scale.max_score),
                        'points': str(scale.points),
                        'remark': scale.remark,
                    }
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)

        # ── delete a grade scale ──────────────────────────────────────────────
        elif action == 'scale_delete':
            scale_id = request.POST.get('scale_id')
            gs_id = request.POST.get('grading_system_id')
            gs = get_object_or_404(GradingSystem, pk=gs_id)
            if school and gs.school != school:
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
            GradeScale.objects.filter(pk=scale_id, grading_system=gs).delete()
            return JsonResponse({'success': True})

        # ── reset to defaults ─────────────────────────────────────────────────
        elif action == 'scale_reset':
            gs_id = request.POST.get('grading_system_id')
            gs = get_object_or_404(GradingSystem, pk=gs_id)
            if school and gs.school != school:
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
            gs.scales.all().delete()
            if gs.level == 'Primary':
                gs.initialize_primary_grading_scales()
            elif gs.level == 'O-Level':
                gs.initialize_olevel_grading_scales()
            elif gs.level == 'A-Level':
                gs.initialize_alevel_grading_scales()
            scales = list(gs.scales.order_by('-min_score').values(
                'id', 'grade', 'min_score', 'max_score', 'points', 'remark'))
            for s in scales:
                s['min_score'] = str(s['min_score'])
                s['max_score'] = str(s['max_score'])
                s['points'] = str(s['points'])
            return JsonResponse({'success': True, 'scales': scales})

        if not is_ajax:
            return redirect('grading_settings')

    # ── GET ───────────────────────────────────────────────────────────────────
    form = GradingSystemForm(school=school)
    systems = GradingSystem.objects.all()
    if school:
        systems = systems.filter(school=school)

    # Auto-initialize missing systems for known levels so the page always shows all three
    if school:
        for lvl in ['O-Level', 'A-Level', 'Primary']:
            if not systems.filter(level=lvl).exists():
                gs_new = GradingSystem(school=school, level=lvl)
                gs_new.save()
        systems = GradingSystem.objects.filter(school=school)

    systems = systems.prefetch_related('scales').order_by(
        Case(
            When(level='O-Level', then=0),
            When(level='A-Level', then=1),
            When(level='Primary', then=2),
            default=3,
            output_field=IntegerField(),
        )
    )

    return render(request, 'academics/grading_settings.html', {
        'form': form,
        'systems': systems,
        'school': school,
        'title': 'Grading Settings',
    })


@login_required
@user_passes_test(headteacher_required)
def grading_scales(request, grading_system_id):
    """Manage grade scales for a grading system"""
    from academics.models import GradingSystem, GradeScale

    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    grading_system = get_object_or_404(GradingSystem, pk=grading_system_id)
    if school and grading_system.school != school:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add':
            grade = request.POST.get('grade', '').strip()
            min_score = request.POST.get('min_score', '')
            max_score = request.POST.get('max_score', '')
            points    = request.POST.get('points', '')
            remark    = request.POST.get('remark', '').strip()
            try:
                scale = GradeScale.objects.create(
                    grading_system=grading_system,
                    grade=grade, min_score=min_score,
                    max_score=max_score, points=points, remark=remark
                )
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'scale_id': scale.pk,
                        'grade': scale.grade, 'min_score': str(scale.min_score),
                        'max_score': str(scale.max_score), 'points': str(scale.points),
                        'remark': scale.remark})
                messages.success(request, 'Grade scale added.')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
                messages.error(request, f'Error: {e}')

        elif action == 'delete':
            scale_id = request.POST.get('scale_id')
            GradeScale.objects.filter(pk=scale_id, grading_system=grading_system).delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, 'Grade scale deleted.')

        elif action == 'reset_defaults':
            grading_system.scales.all().delete()
            if grading_system.level == 'Primary':
                grading_system.initialize_primary_grading_scales()
            elif grading_system.level == 'O-Level':
                grading_system.initialize_olevel_grading_scales()
            elif grading_system.level == 'A-Level':
                grading_system.initialize_alevel_grading_scales()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, 'Scales reset to Uganda curriculum defaults.')

        return redirect('grading_scales', grading_system_id=grading_system_id)

    scales = GradeScale.objects.filter(grading_system=grading_system).order_by('-min_score')
    return render(request, 'academics/grading_scales.html', {
        'grading_system': grading_system,
        'scales': scales,
        'title': f'{grading_system.level} — Grading Scales',
    })


# ── Mark Sheet ────────────────────────────────────────────────────────────
@login_required
def marksheet_view(request):
    """Advanced class mark sheet — headteacher (all classes), class teacher (their class), subject teacher (their subjects)"""
    from core.models import Term
    from students.models import Enrollment, EnrollmentSubject
    from academics.models import GradingSystem

    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    is_headteacher = request.user.is_headteacher() or request.user.is_superadmin()

    if is_headteacher:
        grades = Grade.objects.all()
        if school:
            grades = grades.filter(school=school)
    else:
        grades = Grade.objects.filter(class_teacher=request.user)
        if school:
            grades = grades.filter(school=school)
    grades = grades.order_by('level', 'name')

    terms = Term.objects.all()
    if school:
        terms = terms.filter(academic_year__school=school)
    terms = terms.select_related('academic_year').order_by('-academic_year__start_date', 'start_date')

    selected_grade_id  = request.GET.get('grade')
    selected_term_id   = request.GET.get('term')
    selected_exam_id   = request.GET.get('exam')

    from datetime import date
    today = date.today()
    if not selected_grade_id and grades.exists():
        selected_grade_id = str(grades.first().pk)
    if not selected_term_id:
        ct = terms.filter(start_date__lte=today, end_date__gte=today).first()
        if ct:
            selected_term_id = str(ct.pk)

    selected_grade = None
    selected_term  = None
    selected_exam  = None
    exams = Exam.objects.none()
    subjects = []
    students_data = []
    subject_stats = {}
    available_streams = []
    selected_stream = request.GET.get('stream', '')

    if selected_grade_id:
        try:
            selected_grade = grades.get(pk=selected_grade_id)
        except Grade.DoesNotExist:
            pass

    if selected_term_id:
        try:
            selected_term = terms.get(pk=selected_term_id)
            exams = Exam.objects.filter(term=selected_term)
            if school:
                exams = exams.filter(
                    Q(school=school) | Q(term__academic_year__school=school)
                ).distinct()
            exams = exams.order_by('order', 'name')
            if not selected_exam_id and exams.exists():
                selected_exam_id = str(exams.first().pk)
        except Term.DoesNotExist:
            pass

    if selected_exam_id and exams.exists():
        try:
            selected_exam = exams.get(pk=selected_exam_id)
        except Exam.DoesNotExist:
            pass

    if selected_grade and selected_exam:
        base_enrollments = Enrollment.objects.filter(
            grade=selected_grade, is_active=True
        ).select_related('student')

        # Collect available streams for this grade
        available_streams = sorted(set(
            v for v in base_enrollments.values_list('stream', flat=True).distinct()
            if v
        ))

        enrollments = base_enrollments.order_by('student__last_name', 'student__first_name')
        if selected_stream:
            enrollments = enrollments.filter(stream=selected_stream)

        if selected_grade.level == 'A':
            subj_set = set()
            for enr in enrollments:
                if enr.combination:
                    for s in enr.combination.subjects.all():
                        subj_set.add(s)
            subjects = sorted(list(subj_set), key=lambda s: s.name)
        else:
            subj_ids = EnrollmentSubject.objects.filter(
                enrollment__grade=selected_grade,
                enrollment__is_active=True
            ).values_list('subject_id', flat=True).distinct()
            subjects = list(Subject.objects.filter(id__in=subj_ids).order_by('name'))

        # Build subject-level score lists for class stats
        subject_scores = {subj.pk: [] for subj in subjects}

        # Determine grading level label for grade lookup
        level_map = {'P': 'Primary', 'O': 'O-Level', 'A': 'A-Level'}
        grading_level = level_map.get(selected_grade.level, 'O-Level') if selected_grade else 'O-Level'

        for enr in enrollments:
            marks_map = {}
            total = 0
            cnt = 0
            for subj in subjects:
                me = MarkEntry.objects.filter(enrollment=enr, subject=subj, exam=selected_exam).first()
                if me:
                    score_val = float(me.score)
                    marks_map[subj.pk] = {'score': score_val, 'grade': me.grade or ''}
                    total += score_val
                    cnt += 1
                    subject_scores[subj.pk].append(score_val)
                else:
                    marks_map[subj.pk] = None
            avg = round(total / cnt, 1) if cnt > 0 else None
            # Look up overall grade from grading system
            overall_grade = ''
            if avg is not None and school:
                gs_scale = GradingSystem.get_grade_for_score(avg, school, grading_level)
                if gs_scale:
                    overall_grade = gs_scale.grade
            students_data.append({
                'enrollment': enr,
                'student': enr.student,
                'marks': marks_map,
                'total': round(total, 1),
                'count': cnt,
                'average': avg,
                'overall_grade': overall_grade,
            })

        students_data.sort(key=lambda x: x['average'] if x['average'] is not None else -1, reverse=True)
        for i, s in enumerate(students_data):
            s['position'] = i + 1 if s['average'] is not None else None

        # Build per-subject stats
        subject_stats = {}
        for subj in subjects:
            scores = subject_scores.get(subj.pk, [])
            if scores:
                subject_stats[subj.pk] = {
                    'max': round(max(scores), 1),
                    'min': round(min(scores), 1),
                    'avg': round(sum(scores) / len(scores), 1),
                    'count': len(scores),
                }
            else:
                subject_stats[subj.pk] = None

        # Compute pass/fail counts (pass = average >= 50)
        pass_count = sum(1 for s in students_data if s['average'] is not None and s['average'] >= 50)
        fail_count = sum(1 for s in students_data if s['average'] is not None and s['average'] < 50)
        class_average = round(
            sum(s['average'] for s in students_data if s['average'] is not None) /
            max(1, sum(1 for s in students_data if s['average'] is not None)), 1
        ) if students_data else None
        top_score = max((s['average'] for s in students_data if s['average'] is not None), default=None)
    else:
        pass_count = fail_count = 0
        class_average = top_score = None

    from datetime import date as _date
    return render(request, 'academics/marksheet.html', {
        'grades': grades,
        'terms': terms,
        'exams': exams,
        'subjects': subjects,
        'students_data': students_data,
        'subject_stats': subject_stats,
        'available_streams': available_streams,
        'selected_stream': selected_stream,
        'selected_grade': selected_grade,
        'selected_grade_id': selected_grade_id,
        'selected_term': selected_term,
        'selected_term_id': selected_term_id,
        'selected_exam': selected_exam,
        'selected_exam_id': selected_exam_id,
        'school': school,
        'print_date': _date.today(),
        'is_headteacher': is_headteacher,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'class_average': class_average,
        'top_score': top_score,
        'title': 'Mark Sheet',
    })


@login_required
@user_passes_test(headteacher_required)
def stream_list(request):
    """List all streams"""
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    streams = Stream.objects.all()
    if school:
        streams = streams.filter(school=school)
    return render(request, 'academics/stream_list.html', {'streams': streams, 'title': 'Manage Streams'})

@login_required
@user_passes_test(headteacher_required)
def assign_teacher_role(request, teacher_id):
    """Assign role to teacher"""
    messages.info(request, 'Teacher role assignment feature coming soon.')
    return redirect('home')


@login_required
@user_passes_test(teacher_required)
def get_teacher_entry_context(request):
    """AJAX: Returns teacher's assigned classes/subjects and active exams for mark entry."""
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    is_ht = request.user.is_headteacher() or request.user.is_superadmin()
    from core.models import Term

    if is_ht:
        grades_qs = Grade.objects.filter(school=school).order_by('level', 'name') if school else Grade.objects.all().order_by('level', 'name')
        grades_data = []
        for g in grades_qs:
            subjects_qs = Subject.objects.filter(level=g.level).order_by('name')
            grades_data.append({
                'id': g.pk, 'name': g.name, 'level': g.level,
                'subjects': [{'id': s.pk, 'name': s.name, 'has_papers': s.has_papers} for s in subjects_qs],
            })
    else:
        assignments = TeacherSubject.objects.filter(teacher=request.user).select_related('grade', 'subject')
        if school:
            assignments = assignments.filter(grade__school=school)
        grade_map = {}
        for a in assignments:
            if not a.grade:
                continue
            gid = a.grade.pk
            if gid not in grade_map:
                grade_map[gid] = {'id': gid, 'name': a.grade.name, 'level': a.grade.level, 'subjects': []}
            existing_ids = [s['id'] for s in grade_map[gid]['subjects']]
            if a.subject.pk not in existing_ids:
                grade_map[gid]['subjects'].append({
                    'id': a.subject.pk, 'name': a.subject.name, 'has_papers': a.subject.has_papers
                })
        grades_data = sorted(grade_map.values(), key=lambda x: x['name'])

    terms = Term.objects.all()
    if school:
        terms = terms.filter(academic_year__school=school)
    terms_data = []
    for t in terms.order_by('-academic_year__start_date', 'start_date')[:10]:
        exams_qs = Exam.objects.filter(term=t)
        if school:
            exams_qs = exams_qs.filter(Q(school=school) | Q(term__academic_year__school=school)).distinct()
        exams_data = [{'id': e.pk, 'name': e.name} for e in exams_qs.order_by('order', 'name')]
        if exams_data:
            terms_data.append({'id': t.pk, 'name': f"{t.name} – {t.academic_year.name}", 'exams': exams_data})

    return JsonResponse({'grades': grades_data, 'terms': terms_data})


# Teacher Subject Assignment Views
@login_required
@user_passes_test(headteacher_required)
def assign_teacher_subject(request):
    """Assign teachers to subjects with optional paper selection"""
    from django.http import JsonResponse
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    # Get all teachers for this school
    User = get_user_model()
    teachers = User.objects.filter(role='teacher')
    if school:
        teachers = teachers.filter(school=school)
    
    # Get subjects - For teachers, show ALL subjects with papers (not just elective papers)
    # This is because different teachers can teach different papers of the same subject
    # (e.g., History Paper 1, History Paper 2 can be taught by different teachers)
    subjects = Subject.objects.all()
    if school:
        if school.is_primary():
            subjects = subjects.filter(level='P')
        elif school.is_high_school():
            subjects = subjects.filter(level__in=['O', 'A'])
    
    # For editing mode (when assignment_id is provided), filter to only show subjects
    # that the teacher is already assigned to (to assign papers to)
    assignment_id = request.GET.get('assignment_id') or request.POST.get('assignment_id')
    if assignment_id:
        try:
            assignment = TeacherSubject.objects.get(pk=assignment_id)
            # When editing, only show subjects this teacher is already assigned to
            teacher_assigned_subjects = TeacherSubject.objects.filter(
                teacher=assignment.teacher
            ).values_list('subject_id', flat=True).distinct()
            subjects = subjects.filter(id__in=teacher_assigned_subjects)
        except TeacherSubject.DoesNotExist:
            pass
    
    # Get all grades for this school
    grades = Grade.objects.all()
    if school:
        grades = grades.filter(school=school)
    
    # Get existing assignments
    teacher_subjects = TeacherSubject.objects.all()
    if school:
        teacher_subjects = teacher_subjects.filter(teacher__school=school)
    teacher_subjects = teacher_subjects.select_related('teacher', 'subject', 'grade').prefetch_related('papers')
    
    if request.method == 'POST':
        try:
            assignment_id = request.POST.get('assignment_id')
            teacher_id = request.POST.get('teacher')
            subject_id = request.POST.get('subject')
            grade_id = request.POST.get('grade') or None
            paper_ids = request.POST.getlist('papers')  # Get list of selected papers
            
            if not teacher_id or not subject_id:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Teacher and Subject are required'}, status=400)
                messages.error(request, 'Teacher and Subject are required.')
                return redirect('assign_teacher_subject')
            
            teacher = get_object_or_404(User, pk=teacher_id, role='teacher')
            subject = get_object_or_404(Subject, pk=subject_id)
            
            # Handle grade - can be None (for all grades)
            grade = None
            if grade_id:
                try:
                    grade = Grade.objects.get(pk=grade_id)
                except (Grade.DoesNotExist, ValueError, TypeError):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': 'Invalid grade selected'}, status=400)
                    messages.error(request, 'Invalid grade selected.')
                    return redirect('assign_teacher_subject')
            
            # If editing existing assignment
            if assignment_id:
                try:
                    assignment = TeacherSubject.objects.get(pk=assignment_id)
                    # Update fields
                    assignment.teacher = teacher
                    assignment.subject = subject
                    assignment.grade = grade
                    assignment.save()
                    created = False
                except TeacherSubject.DoesNotExist:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': 'Assignment not found'}, status=404)
                    messages.error(request, 'Assignment not found.')
                    return redirect('assign_teacher_subject')
            else:
                # Check if assignment already exists
                assignment, created = TeacherSubject.objects.get_or_create(
                    teacher=teacher,
                    subject=subject,
                    grade=grade,
                    defaults={}
                )
            
            # Set papers if subject has papers
            # For TEACHERS: Allow paper selection for ALL subjects with papers
            # (Not restricted to has_elective_papers because different teachers teach different papers)
            if subject.has_papers:
                if paper_ids:
                    # Convert paper_ids to integers and filter
                    try:
                        paper_ids_int = [int(pid) for pid in paper_ids if pid]
                        papers = SubjectPaper.objects.filter(id__in=paper_ids_int, subject=subject)
                        
                        # Verify all requested papers exist
                        found_paper_ids = set(papers.values_list('id', flat=True))
                        requested_paper_ids = set(paper_ids_int)
                        
                        if found_paper_ids != requested_paper_ids:
                            invalid_ids = requested_paper_ids - found_paper_ids
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return JsonResponse({
                                    'success': False,
                                    'error': f'Invalid paper IDs: {list(invalid_ids)}. These papers do not exist or do not belong to this subject.'
                                }, status=400)
                            messages.error(request, f'Invalid paper IDs: {list(invalid_ids)}')
                            return redirect('assign_teacher_subject')
                        
                        assignment.papers.set(papers)
                    except (ValueError, TypeError) as e:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': False,
                                'error': f'Invalid paper ID format: {str(e)}'
                            }, status=400)
                        messages.error(request, f'Invalid paper ID format: {str(e)}')
                        return redirect('assign_teacher_subject')
                else:
                    # No papers selected: clear all (teacher teaches all papers for this subject)
                    assignment.papers.clear()
            
            # Save assignment after setting papers
            assignment.save()
            
            if created:
                messages.success(request, f'Teacher {teacher.get_full_name()} assigned to {subject.name} successfully!')
            else:
                messages.success(request, f'Teacher assignment updated successfully!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Get paper names safely
                paper_names = []
                try:
                    paper_names = [p.name for p in assignment.papers.all()]
                except Exception as e:
                    print(f"Error getting paper names: {str(e)}")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Assignment created successfully' if created else 'Assignment updated successfully',
                    'assignment': {
                        'id': assignment.id,
                        'teacher': teacher.get_full_name(),
                        'subject': subject.name,
                        'grade': grade.name if grade else 'All',
                        'papers': paper_names
                    }
                })
            
            return redirect('assign_teacher_subject')
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            error_msg = f'Error assigning teacher to subject: {str(e)}'
            print(error_msg)
            print(error_trace)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg,
                    'traceback': error_trace if request.user.is_superuser else None
                }, status=500)
            
            messages.error(request, error_msg)
            return redirect('assign_teacher_subject')
    
    return render(request, 'academics/assign_teacher_subject.html', {
        'teachers': teachers,
        'subjects': subjects,
        'grades': grades,
        'teacher_subjects': teacher_subjects,
        'title': 'Assign Teachers to Subjects'
    })

@login_required
@user_passes_test(headteacher_required)
def teacher_subject_delete(request, assignment_id):
    """Delete a teacher-subject assignment"""
    assignment = get_object_or_404(TeacherSubject, pk=assignment_id)
    
    # Check permissions
    if not request.user.is_superadmin() and hasattr(request.user, 'school'):
        if assignment.teacher.school != request.user.school:
            messages.error(request, "You don't have permission to delete this assignment.")
            return redirect('assign_teacher_subject')
    
    assignment.delete()
    messages.success(request, 'Assignment deleted successfully!')
    return redirect('assign_teacher_subject')

@login_required
@user_passes_test(headteacher_required)
def get_subjects_for_teacher(request):
    """Get subjects for teacher assignment (AJAX endpoint)"""
    from django.http import JsonResponse
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    subjects = Subject.objects.all()
    if school:
        if school.is_primary():
            subjects = subjects.filter(level='P')
        elif school.is_high_school():
            subjects = subjects.filter(level__in=['O', 'A'])
    
    subjects_data = [{
        'id': s.id,
        'name': s.name,
        'has_papers': s.has_papers
    } for s in subjects.order_by('name')]
    
    return JsonResponse({'subjects': subjects_data})

@login_required
@user_passes_test(headteacher_required)
def get_grades_for_teacher(request):
    """Get grades for teacher assignment (AJAX endpoint)"""
    from django.http import JsonResponse
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    grades = Grade.objects.all()
    if school:
        grades = grades.filter(school=school)
    
    grades_data = [{
        'id': g.id,
        'name': g.name
    } for g in grades.order_by('name')]
    
    return JsonResponse({'grades': grades_data})

@login_required
@user_passes_test(headteacher_required)
def get_teachers_for_school(request, school_id):
    """Get teachers for a specific school (AJAX endpoint for grade form)"""
    from django.http import JsonResponse
    from core.models import School
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    try:
        school = School.objects.get(pk=school_id)
        # Check permissions - user must be from this school or superadmin
        if not request.user.is_superadmin() and hasattr(request.user, 'school'):
            if request.user.school != school:
                return JsonResponse({'teachers': [], 'error': 'Permission denied'}, status=403)
        
        teachers = User.objects.filter(role='teacher', school=school).order_by('first_name', 'last_name')
        
        teachers_data = [{
            'id': t.id,
            'name': t.get_full_name() or t.username
        } for t in teachers]
        
        return JsonResponse({'teachers': teachers_data})
    except School.DoesNotExist:
        return JsonResponse({'teachers': [], 'error': 'School not found'}, status=404)

# Student Paper Assignment Views
@login_required
@user_passes_test(headteacher_required)
def assign_student_papers(request, enrollment_id):
    """Assign papers to a student for subjects with multiple papers"""
    from django.http import JsonResponse, HttpResponse
    from django.template.loader import render_to_string
    from students.models import Enrollment
    from academics.models import StudentPaperAssignment
    
    try:
        enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error loading enrollment {enrollment_id}: {str(e)}")
        print(error_trace)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': f'Error loading enrollment: {str(e)}'
            }, status=500)
        messages.error(request, f'Error loading enrollment: {str(e)}')
        return redirect('student_list')
    
    # Check permissions
    try:
        if not request.user.is_superadmin() and hasattr(request.user, 'school'):
            if enrollment.grade.school != request.user.school:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': "You don't have permission to access this enrollment."
                    }, status=403)
                messages.error(request, "You don't have permission to access this enrollment.")
                return redirect('student_list')
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error checking permissions: {str(e)}")
        print(error_trace)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': f'Error checking permissions: {str(e)}'
            }, status=500)
        messages.error(request, f'Error checking permissions: {str(e)}')
        return redirect('student_list')
    
    # Get subjects with papers for this student's level
    # BUT only show subjects the student is enrolled in (from EnrollmentSubject)
    # AND only show subjects with elective papers (has_elective_papers=True)
    try:
        # Check if enrollment has a grade
        if not hasattr(enrollment, 'grade') or enrollment.grade is None:
            error_msg = 'Enrollment does not have a grade assigned'
            print(error_msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)
            messages.error(request, error_msg)
            return redirect('student_list')
        
        # Check if enrollment.grade has level attribute
        if not hasattr(enrollment.grade, 'level') or enrollment.grade.level is None:
            error_msg = 'Enrollment grade does not have a level assigned'
            print(error_msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)
            messages.error(request, error_msg)
            return redirect('student_list')
        
        from students.models import EnrollmentSubject
        enrolled_subjects_qs = EnrollmentSubject.objects.filter(
            enrollment=enrollment
        )
        
        # Convert to list of IDs
        enrolled_subject_ids = list(enrolled_subjects_qs.values_list('subject_id', flat=True))
        
        # If no enrolled subjects, return empty list (not an error)
        if not enrolled_subject_ids:
            subjects_with_papers = Subject.objects.none()
        else:
            # Only show subjects with elective papers (has_elective_papers=True)
            # These are subjects like History, Art, French that have papers students can choose from
            subjects_with_papers = Subject.objects.filter(
                has_papers=True,
                has_elective_papers=True,  # Only show subjects with elective papers
                level=enrollment.grade.level,
                id__in=enrolled_subject_ids  # Only show subjects the student is enrolled in
            )
        
        # Get existing assignments
        existing_assignments = StudentPaperAssignment.objects.filter(
            enrollment=enrollment
        ).prefetch_related('papers', 'subject')
    except AttributeError as e:
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f'Error accessing enrollment attributes: {str(e)}'
        print(error_msg)
        print(error_trace)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=500)
        messages.error(request, error_msg)
        return redirect('student_list')
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f'Error loading subjects: {str(e)}'
        print(error_msg)
        print(error_trace)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=500)
        messages.error(request, error_msg)
        return redirect('student_list')
    
    if request.method == 'POST':
        try:
            subject_id = request.POST.get('subject')
            paper_ids = request.POST.getlist('papers')
            
            # Convert paper_ids to integers
            try:
                paper_ids = [int(pid) for pid in paper_ids if pid]
            except (ValueError, TypeError) as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'error': f'Invalid paper ID format: {str(e)}'
                    }, status=400)
                messages.error(request, f'Invalid paper ID format: {str(e)}')
                return redirect('assign_student_papers', enrollment_id=enrollment_id)
            
            if not subject_id:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Subject is required'}, status=400)
                messages.error(request, 'Subject is required.')
                return redirect('assign_student_papers', enrollment_id=enrollment_id)
            
            try:
                subject_id = int(subject_id)
            except (ValueError, TypeError):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Invalid subject ID'}, status=400)
                messages.error(request, 'Invalid subject ID.')
                return redirect('assign_student_papers', enrollment_id=enrollment_id)
            
            subject = get_object_or_404(Subject, pk=subject_id, has_papers=True)
            
            # Verify the subject is one the student is enrolled in
            from students.models import EnrollmentSubject
            if not EnrollmentSubject.objects.filter(enrollment=enrollment, subject=subject).exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Student is not enrolled in this subject'}, status=400)
                messages.error(request, 'Student is not enrolled in this subject.')
                return redirect('assign_student_papers', enrollment_id=enrollment_id)
            
            # Validate papers first
            if paper_ids:
                papers = SubjectPaper.objects.filter(id__in=paper_ids, subject=subject)
                
                # Verify all papers exist and belong to the subject
                found_paper_ids = set(papers.values_list('id', flat=True))
                requested_paper_ids = set(paper_ids)
                
                if found_paper_ids != requested_paper_ids:
                    invalid_ids = requested_paper_ids - found_paper_ids
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False, 
                            'error': f'Invalid paper IDs: {list(invalid_ids)}. These papers do not exist or do not belong to this subject.'
                        }, status=400)
                    messages.error(request, f'Invalid paper IDs: {list(invalid_ids)}')
                    return redirect('assign_student_papers', enrollment_id=enrollment_id)
            else:
                # If no papers selected, delete existing assignment if it exists
                StudentPaperAssignment.objects.filter(enrollment=enrollment, subject=subject).delete()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Paper assignment removed'})
                messages.success(request, 'Paper assignment removed.')
                return redirect('assign_student_papers', enrollment_id=enrollment_id)
            
            # Get or create assignment (without validation to avoid recursion)
            # We'll validate manually after papers are set
            try:
                assignment = StudentPaperAssignment.objects.get(
                    enrollment=enrollment,
                    subject=subject
                )
                created = False
            except StudentPaperAssignment.DoesNotExist:
                # Create new assignment without validation
                assignment = StudentPaperAssignment(
                    enrollment=enrollment,
                    subject=subject
                )
                # Save without validation first
                assignment.save(skip_validation=True)
                created = True
            
            # Now set the papers (many-to-many relationship)
            # Use set() but ensure assignment is fully saved first
            # Clear existing papers first
            if assignment.pk:
                # Use direct database operation to avoid triggering signals/validation
                from django.db import connection
                with connection.cursor() as cursor:
                    # Delete existing paper assignments
                    cursor.execute(
                        "DELETE FROM academics_studentpaperassignment_papers WHERE studentpaperassignment_id = %s",
                        [assignment.pk]
                    )
                    # Insert new paper assignments
                    if papers:
                        values = [(assignment.pk, paper.pk) for paper in papers]
                        cursor.executemany(
                            "INSERT INTO academics_studentpaperassignment_papers (studentpaperassignment_id, subjectpaper_id) VALUES (%s, %s)",
                            values
                        )
            else:
                # If assignment doesn't have pk yet, save it first
                assignment.save(skip_validation=True)
                # Now set papers using direct DB operation
                from django.db import connection
                with connection.cursor() as cursor:
                    if papers:
                        values = [(assignment.pk, paper.pk) for paper in papers]
                        cursor.executemany(
                            "INSERT INTO academics_studentpaperassignment_papers (studentpaperassignment_id, subjectpaper_id) VALUES (%s, %s)",
                            values
                        )
            
            if created:
                messages.success(request, f'Papers assigned to {enrollment.student.get_full_name()} for {subject.name} successfully!')
            else:
                messages.success(request, f'Paper assignment updated successfully!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Get paper names directly (no need to refresh, papers are already set)
                paper_names = [p.name for p in papers]
                return JsonResponse({
                    'success': True,
                    'message': 'Assignment saved successfully',
                    'assignment': {
                        'id': assignment.id,
                        'subject': subject.name,
                        'papers': paper_names
                    }
                })
            
            return redirect('assign_student_papers', enrollment_id=enrollment_id)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            # Log error to console for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in assign_student_papers POST: {str(e)}")
            logger.error(error_trace)
            print(f"Error in assign_student_papers: {str(e)}")
            print(error_trace)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                error_response = {
                    'success': False,
                    'error': f'Error saving papers: {str(e)}'
                }
                # Include traceback for superusers for debugging
                if request.user.is_superadmin():
                    error_response['traceback'] = error_trace
                return JsonResponse(error_response, status=500)
            messages.error(request, f'Error saving papers: {str(e)}')
            return redirect('assign_student_papers', enrollment_id=enrollment_id)
    
    # Build context with subjects and their papers
    try:
        subjects_data = []
        for subject in subjects_with_papers:
            try:
                # Get papers for this subject (as a list, not queryset)
                papers_queryset = subject.get_papers()
                papers = list(papers_queryset) if papers_queryset else []
                
                # Only include subjects that actually have papers
                if not papers:
                    print(f"Subject {subject.name} has no papers, skipping")
                    continue
                
                existing_assignment = existing_assignments.filter(subject=subject).first()
                assigned_paper_ids = []
                if existing_assignment:
                    try:
                        assigned_paper_ids = list(existing_assignment.papers.values_list('id', flat=True))
                    except Exception as e:
                        print(f"Error getting assigned papers for subject {subject.id}: {str(e)}")
                        assigned_paper_ids = []
                
                subjects_data.append({
                    'subject': subject,
                    'papers': papers,
                    'assigned_paper_ids': assigned_paper_ids,
                    'assignment_id': existing_assignment.id if existing_assignment else None
                })
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"Error processing subject {subject.id if hasattr(subject, 'id') else 'unknown'}: {str(e)}")
                print(error_trace)
                # Skip this subject and continue
                continue
        
        # If AJAX request, return partial HTML for modal
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                # Ensure we have the required context
                context = {
                    'enrollment': enrollment,
                    'student': enrollment.student,
                    'subjects_data': subjects_data
                }
                
                html = render_to_string('academics/assign_student_papers_modal.html', context, request=request)
                response = HttpResponse(html)
                response['Content-Type'] = 'text/html; charset=utf-8'
                return response
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                error_msg = f'Error rendering template: {str(e)}'
                print(error_msg)
                print(error_trace)
                # Return JSON error response
                error_response = {
                    'success': False,
                    'error': error_msg
                }
                # Include traceback for superusers
                if request.user.is_superadmin():
                    error_response['traceback'] = error_trace
                return JsonResponse(error_response, status=500)
        
        return render(request, 'academics/assign_student_papers.html', {
            'enrollment': enrollment,
            'student': enrollment.student,
            'subjects_data': subjects_data,
            'title': f'Assign Papers - {enrollment.student.get_full_name()}'
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error building context: {str(e)}")
        print(error_trace)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            error_response = {
                'success': False,
                'error': f'Error building context: {str(e)}'
            }
            # Include traceback for superusers
            if request.user.is_superadmin():
                error_response['traceback'] = error_trace
            return JsonResponse(error_response, status=500)
        messages.error(request, f'Error loading page: {str(e)}')
        return redirect('student_list')

@login_required
@user_passes_test(headteacher_required)
def get_student_papers(request, enrollment_id, subject_id):
    """Get papers for a student's subject (AJAX endpoint)"""
    from django.http import JsonResponse
    from students.models import Enrollment
    from academics.models import StudentPaperAssignment
    
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    subject = get_object_or_404(Subject, pk=subject_id, has_papers=True)
    
    # Get existing assignment
    assignment = StudentPaperAssignment.objects.filter(
        enrollment=enrollment,
        subject=subject
    ).first()
    
    assigned_paper_ids = list(assignment.papers.values_list('id', flat=True)) if assignment else []
    
    # Get all papers for this subject
    papers = subject.get_papers()
    papers_data = []
    for paper in papers:
        papers_data.append({
            'id': paper.id,
            'name': paper.name,
            'paper_number': paper.paper_number or 0,
            'code': paper.code or '',
            'description': paper.description or '',
            'is_assigned': paper.id in assigned_paper_ids
        })
    
    return JsonResponse({
        'papers': papers_data,
        'subject_name': subject.name,
        'assigned_paper_ids': assigned_paper_ids
    })

# Mark Entry Views
@login_required
@user_passes_test(teacher_required)
def mark_entry_list(request):
    """Mark entry page - shows filters for term, grade, subject, exam"""
    from core.models import Term, AcademicYear
    from students.models import Enrollment
    from academics.models import TeacherSubject
    
    school = None if request.user.is_superadmin() else getattr(request.user, 'school', None)
    
    # Get terms for the school
    terms = Term.objects.all()
    if school:
        terms = terms.filter(academic_year__school=school)
    terms = terms.select_related('academic_year').order_by('-academic_year__start_date', 'start_date')
    
    # Get current term (if any) - use date-based filtering
    from datetime import date
    today = date.today()
    current_term = terms.filter(start_date__lte=today, end_date__gte=today).first()
    
    # Get selected filters from request
    selected_term_id = request.GET.get('term')
    selected_grade_id = request.GET.get('grade')
    selected_subject_id = request.GET.get('subject')
    selected_exam_id = request.GET.get('exam')
    
    # Get grades where teacher teaches
    grades = Grade.objects.none()
    if request.user.is_teacher() and not request.user.is_superadmin():
        # Get grades from teacher's subject assignments
        teacher_subjects = TeacherSubject.objects.filter(teacher=request.user)
        if school:
            teacher_subjects = teacher_subjects.filter(teacher__school=school)
        # Get grade IDs from teacher's subject assignments
        grade_ids_from_subjects = list(teacher_subjects.values_list('grade_id', flat=True).distinct())
        # Get grade IDs where teacher is class teacher
        grade_ids_from_class_teacher = []
        if school:
            grade_ids_from_class_teacher = list(Grade.objects.filter(school=school, class_teacher=request.user).values_list('id', flat=True))
        # Combine and get unique grades
        all_grade_ids = list(set(grade_ids_from_subjects + grade_ids_from_class_teacher))
        if all_grade_ids:
            grades = Grade.objects.filter(id__in=all_grade_ids).distinct()
        else:
            grades = Grade.objects.none()
    elif request.user.is_headteacher() or request.user.is_superadmin():
        # Headteachers and superadmins see all grades
        if school:
            grades = Grade.objects.filter(school=school)
        else:
            grades = Grade.objects.all()
    
    grades = grades.order_by('level', 'name')
    
    # Get subjects where teacher teaches (filtered by teacher's assignments)
    subjects = Subject.objects.none()
    if request.user.is_teacher() and not request.user.is_superadmin():
        # Get subjects from teacher's assignments
        teacher_subjects = TeacherSubject.objects.filter(teacher=request.user)
        if selected_grade_id:
            # Filter by selected grade if provided
            teacher_subjects = teacher_subjects.filter(
                Q(grade_id=selected_grade_id) | Q(grade__isnull=True)
            )
        subject_ids = teacher_subjects.values_list('subject_id', flat=True).distinct()
        subjects = Subject.objects.filter(id__in=subject_ids).order_by('name')
    elif request.user.is_headteacher() or request.user.is_superadmin():
        # Headteachers and superadmins see all subjects
        subjects = Subject.objects.all().order_by('name')
        if selected_grade_id:
            # Filter by grade level if grade is selected
            try:
                grade = Grade.objects.get(pk=selected_grade_id)
                subjects = subjects.filter(level=grade.level)
            except Grade.DoesNotExist:
                pass
    
    # Get exams for selected term
    exams = Exam.objects.none()
    term_for_exams = None
    exam_count = 0
    
    # Determine which term to use for loading exams
    # Priority: 1) selected_term_id from URL, 2) current_term, 3) None
    term_to_use = None
    
    if selected_term_id:
        try:
            term_to_use = Term.objects.get(pk=selected_term_id)
        except (Term.DoesNotExist, ValueError, TypeError):
            # Invalid term ID, try current_term as fallback
            term_to_use = current_term
    elif current_term:
        # No term in URL, but we have a current_term - use it
        term_to_use = current_term
        # Set selected_term_id to current_term for consistency in template
        selected_term_id = str(current_term.id)
    
    # Set term_for_exams for template
    term_for_exams = term_to_use
    
    # Now load exams if we have a term
    if term_to_use:
        try:
            # First, try to get active exams only (for mark entry)
            # But if no active exams found, show all exams as fallback
            exams_query = Exam.objects.filter(term=term_to_use)
            
            # Filter by school if applicable
            # Exam model has BOTH a direct 'school' field AND a 'term' field
            # Check both to ensure we get all exams for this school
            if school:
                from django.db.models import Q
                # Combine both queries to check direct school field OR term's academic_year's school
                exams_query = exams_query.filter(
                    Q(school=school) | Q(term__academic_year__school=school)
                ).distinct()
            
            # Try active exams first
            active_exams = exams_query.filter(is_active=True)
            exam_count = active_exams.count()
            
            if exam_count > 0:
                # Use active exams
                exams = active_exams
            else:
                # No active exams - show all exams as fallback (with warning)
                all_exams = exams_query
                exam_count = all_exams.count()
                if exam_count > 0:
                    exams = all_exams
                    print(f"Warning: No active exams found for term {term_to_use.name}, showing all {exam_count} exams (including inactive)")
            
            # Order by order field, then by name
            exams = exams.order_by('order', 'name')
            
            # Debug: Print exam details
            print(f"Term: {term_to_use.name} (ID: {term_to_use.id})")
            print(f"School: {school.name if school else 'All'}")
            print(f"Found {exam_count} exam(s) for term {term_to_use.name}")
            if exam_count > 0:
                exam_names = [e.name for e in exams[:5]]
                print(f"Exam names: {', '.join(exam_names)}")
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error loading exams for term {term_to_use.id if term_to_use else 'None'}: {str(e)}")
            print(error_trace)
            exam_count = 0
    
    # Determine the selected term ID for template comparison
    template_selected_term = None
    if term_for_exams:
        template_selected_term = term_for_exams.id
    elif selected_term_id:
        try:
            template_selected_term = int(selected_term_id)
        except (ValueError, TypeError):
            if current_term:
                template_selected_term = current_term.id
    elif current_term:
        template_selected_term = current_term.id
    
    return render(request, 'academics/mark_entry.html', {
        'terms': terms,
        'current_term': current_term,
        'grades': grades,
        'subjects': subjects,
        'exams': exams,
        'exam_count': exam_count,
        'term_for_exams': term_for_exams,  # Term object for template checks
        'selected_term': template_selected_term,  # Integer ID for template comparison
        'selected_grade': int(selected_grade_id) if selected_grade_id else None,
        'selected_subject': int(selected_subject_id) if selected_subject_id else None,
        'selected_exam': int(selected_exam_id) if selected_exam_id else None,
        'title': 'Mark Entry'
    })

@login_required
@user_passes_test(teacher_required)
def get_students_for_subject(request):
    """Get students for a subject/grade/exam (AJAX endpoint)"""
    from django.http import JsonResponse
    from students.models import Enrollment, EnrollmentSubject
    from academics.models import StudentPaperAssignment, TeacherSubject
    
    subject_id = request.GET.get('subject_id')
    grade_id = request.GET.get('grade_id')
    exam_id = request.GET.get('exam_id')
    
    if not subject_id or not grade_id or not exam_id:
        return JsonResponse({
            'success': False,
            'error': 'Subject, grade, and exam are required'
        }, status=400)
    
    try:
        subject = Subject.objects.get(pk=subject_id)
        grade = Grade.objects.get(pk=grade_id)
        exam = Exam.objects.get(pk=exam_id)
    except (Subject.DoesNotExist, Grade.DoesNotExist, Exam.DoesNotExist) as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid subject, grade, or exam: {str(e)}'
        }, status=400)
    
    # Verify teacher is assigned to this subject
    if request.user.is_teacher() and not request.user.is_headteacher() and not request.user.is_superadmin():
        teacher_subject = TeacherSubject.objects.filter(
            Q(teacher=request.user) &
            Q(subject=subject) &
            (Q(grade=grade) | Q(grade__isnull=True))
        ).first()
        
        if not teacher_subject:
            return JsonResponse({
                'success': False,
                'error': 'You are not assigned to teach this subject for this grade.'
            }, status=403)
    
    # Get enrollments for this grade that are enrolled in this subject
    enrollments = Enrollment.objects.filter(
        grade=grade,
        is_active=True
    ).filter(
        enrollment_subjects__subject=subject
    ).select_related('student', 'grade').distinct()
    
    # Get papers for this subject
    papers = []
    subject_has_papers = subject.has_papers
    
    # Get teacher's assigned papers for this subject
    teacher_papers = []
    if request.user.is_teacher() and not request.user.is_headteacher() and not request.user.is_superadmin():
        teacher_subject = TeacherSubject.objects.filter(
            Q(teacher=request.user) &
            Q(subject=subject) &
            (Q(grade=grade) | Q(grade__isnull=True))
        ).first()
        
        if teacher_subject:
            if teacher_subject.papers.exists():
                # Teacher has specific papers assigned
                teacher_papers = list(teacher_subject.papers.values_list('id', flat=True))
            else:
                # Teacher teaches all papers
                teacher_papers = list(SubjectPaper.objects.filter(subject=subject).values_list('id', flat=True))
    else:
        # Headteacher/superadmin sees all papers
        teacher_papers = list(SubjectPaper.objects.filter(subject=subject).values_list('id', flat=True))
    
    if subject_has_papers:
        papers = SubjectPaper.objects.filter(subject=subject, id__in=teacher_papers).order_by('paper_number', 'name')
        papers_data = [{
            'id': p.id,
            'name': p.name,
            'code': p.code or '',
            'paper_number': p.paper_number or 0
        } for p in papers]
    else:
        papers_data = []
    
    # Get students with their marks
    students_data = []
    for enrollment in enrollments:
        student = enrollment.student
        
        # Get student's assigned papers for this subject (if subject has papers)
        assigned_paper_ids = []
        if subject_has_papers:
            assignment = StudentPaperAssignment.objects.filter(
                enrollment=enrollment,
                subject=subject
            ).first()
            if assignment:
                assigned_paper_ids = list(assignment.papers.values_list('id', flat=True))
        
        # Get existing marks for this student
        marks_dict = {}
        if subject_has_papers:
            # Get marks for each paper
            for paper in papers:
                mark = MarkEntry.objects.filter(
                    enrollment=enrollment,
                    subject=subject,
                    subject_paper=paper,
                    exam=exam
                ).first()
                
                if mark:
                    marks_dict[str(paper.id)] = {
                        'score': float(mark.score),
                        'grade': mark.grade,
                        'points': float(mark.points) if mark.points else None,
                        'comments': mark.comments or ''
                    }
        else:
            # Subject doesn't have papers - get mark without paper
            mark = MarkEntry.objects.filter(
                enrollment=enrollment,
                subject=subject,
                subject_paper__isnull=True,
                exam=exam
            ).first()
            
            if mark:
                marks_dict['default'] = {
                    'score': float(mark.score),
                    'grade': mark.grade,
                    'points': float(mark.points) if mark.points else None,
                    'comments': mark.comments or ''
                }
        
        students_data.append({
            'id': enrollment.id,
            'name': student.get_full_name(),
            'admission_number': student.admission_number or '',
            'marks': marks_dict,
            'assigned_paper_ids': assigned_paper_ids
        })
    
    return JsonResponse({
        'success': True,
        'students': students_data,
        'papers': papers_data,
        'subject_has_papers': subject_has_papers
    })

@login_required
@user_passes_test(teacher_required)
def mark_entry_create(request):
    """Create/update mark entries (AJAX endpoint)"""
    from django.http import JsonResponse
    from students.models import Enrollment
    from academics.models import TeacherSubject
    from decimal import Decimal
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    exam_id = request.POST.get('exam')
    subject_id = request.POST.get('subject')
    grade_id = request.POST.get('grade')
    
    if not exam_id or not subject_id or not grade_id:
        return JsonResponse({
            'success': False,
            'error': 'Exam, subject, and grade are required'
        }, status=400)
    
    try:
        exam = Exam.objects.get(pk=exam_id)
        subject = Subject.objects.get(pk=subject_id)
        grade = Grade.objects.get(pk=grade_id)
    except (Exam.DoesNotExist, Subject.DoesNotExist, Grade.DoesNotExist) as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid exam, subject, or grade: {str(e)}'
        }, status=400)
    
    # Verify teacher is assigned to this subject
    if request.user.is_teacher() and not request.user.is_headteacher() and not request.user.is_superadmin():
        teacher_subject = TeacherSubject.objects.filter(
            Q(teacher=request.user) &
            Q(subject=subject) &
            (Q(grade=grade) | Q(grade__isnull=True))
        ).first()
        
        if not teacher_subject:
            return JsonResponse({
                'success': False,
                'error': 'You are not assigned to teach this subject for this grade.'
            }, status=403)
    
    # Process marks for each student
    created_count = 0
    updated_count = 0
    errors = []
    
    # Get all enrollment IDs from POST data
    enrollment_ids = set()
    for key in request.POST.keys():
        if key.startswith('score_'):
            enrollment_id = key.replace('score_', '')
            try:
                enrollment_ids.add(int(enrollment_id))
            except ValueError:
                continue
    
    for enrollment_id in enrollment_ids:
        try:
            enrollment = Enrollment.objects.get(pk=enrollment_id, grade=grade, is_active=True)
        except Enrollment.DoesNotExist:
            errors.append(f'Enrollment {enrollment_id} not found')
            continue
        
        # Get score, paper, and comments
        score_str = request.POST.get(f'score_{enrollment_id}', '').strip()
        if not score_str:
            continue  # Skip if no score provided
        
        try:
            score = Decimal(score_str)
            if score < 0 or score > 100:
                errors.append(f'Score for {enrollment.student.get_full_name()} must be between 0 and 100')
                continue
        except (ValueError, InvalidOperation):
            errors.append(f'Invalid score for {enrollment.student.get_full_name()}')
            continue
        
        # Get paper if subject has papers
        subject_paper = None
        if subject.has_papers:
            paper_id = request.POST.get(f'paper_{enrollment_id}', '').strip()
            if not paper_id:
                errors.append(f'Paper required for {enrollment.student.get_full_name()}')
                continue
            
            try:
                subject_paper = SubjectPaper.objects.get(pk=paper_id, subject=subject)
            except SubjectPaper.DoesNotExist:
                errors.append(f'Invalid paper for {enrollment.student.get_full_name()}')
                continue
            
            # Verify teacher is assigned to this paper
            if request.user.is_teacher() and not request.user.is_headteacher() and not request.user.is_superadmin():
                teacher_subject = TeacherSubject.objects.filter(
                    Q(teacher=request.user) &
                    Q(subject=subject) &
                    (Q(grade=grade) | Q(grade__isnull=True))
                ).first()
                
                if teacher_subject and teacher_subject.papers.exists():
                    if subject_paper not in teacher_subject.papers.all():
                        errors.append(f'You are not assigned to teach {subject_paper.name} for {enrollment.student.get_full_name()}')
                        continue
        
        comments = request.POST.get(f'comments_{enrollment_id}', '').strip()
        
        # Get or create mark entry
        mark_entry, created = MarkEntry.objects.get_or_create(
            enrollment=enrollment,
            subject=subject,
            subject_paper=subject_paper,
            exam=exam,
            defaults={
                'teacher': request.user,
                'score': score,
                'comments': comments
            }
        )
        
        if not created:
            # Update existing mark
            mark_entry.score = score
            mark_entry.comments = comments
            mark_entry.teacher = request.user
            updated_count += 1
        else:
            created_count += 1
        
        # Save will trigger grade and points calculation
        mark_entry.save()
    
    if errors:
        return JsonResponse({
            'success': False,
            'error': 'Some marks could not be saved',
            'errors': errors,
            'created': created_count,
            'updated': updated_count
        }, status=400)
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully saved {created_count + updated_count} mark(s) ({created_count} created, {updated_count} updated)',
        'created': created_count,
        'updated': updated_count
    })

@login_required
def subject_search_suggestions(request):
    """AJAX endpoint for subject search autocomplete"""
    query = request.GET.get('q', '').strip()
    if len(query) < 1:
        return JsonResponse({'suggestions': []})
    
    # Get subjects matching the query
    subjects = Subject.objects.filter(
        Q(name__icontains=query) |
        Q(code__icontains=query)
    )[:10]  # Limit to 10 suggestions
    
    suggestions = []
    for subject in subjects:
        suggestions.append({
            'value': subject.name,
            'label': f"{subject.name} ({subject.code or 'No Code'}) - {subject.get_level_display()}",
            'code': subject.code or '',
            'level': subject.get_level_display()
        })
    
    return JsonResponse({'suggestions': suggestions})
