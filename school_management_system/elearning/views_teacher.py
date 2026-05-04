"""
E-Learning Views for Teachers
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import Course, CourseEnrollment, Lesson, Assignment, CourseMaterial
from academics.models import TeacherSubject, Grade
from django.utils import timezone
from django import forms

@login_required
def teacher_classes(request):
    """List all classes/subjects the teacher teaches"""
    if not (request.user.is_teacher() or request.user.is_headteacher() or request.user.is_director_of_studies()):
        messages.error(request, 'Only teachers can access this page.')
        return redirect('home')
    
    # Get classes where teacher is class teacher
    classes_taught = Grade.objects.filter(class_teacher=request.user)
    
    # Get subjects teacher teaches (via TeacherSubject)
    subjects_taught = TeacherSubject.objects.filter(teacher=request.user).select_related('subject', 'grade')
    
    # Group subjects by grade
    classes_dict = {}
    for ts in subjects_taught:
        grade = ts.grade
        if grade:
            if grade.id not in classes_dict:
                classes_dict[grade.id] = {
                    'grade': grade,
                    'subjects': [],
                    'is_class_teacher': grade.class_teacher == request.user
                }
            classes_dict[grade.id]['subjects'].append(ts.subject)
    
    # Add classes where teacher is class teacher but may not have subjects assigned
    for grade in classes_taught:
        if grade.id not in classes_dict:
            classes_dict[grade.id] = {
                'grade': grade,
                'subjects': [],
                'is_class_teacher': True
            }
    
    context = {
        'classes_dict': classes_dict.values(),
        'title': 'My Classes - E-Learning'
    }
    
    return render(request, 'elearning/teacher_classes.html', context)


@login_required
def teacher_class_detail(request, grade_id):
    """Teacher's view of a specific class - manage materials, quizzes, exams"""
    grade = get_object_or_404(Grade, id=grade_id)
    
    # Check if teacher teaches this class
    is_class_teacher = grade.class_teacher == request.user
    teaches_subject = TeacherSubject.objects.filter(teacher=request.user, grade=grade).exists()
    
    if not (is_class_teacher or teaches_subject or request.user.is_headteacher()):
        messages.error(request, 'You do not teach this class.')
        return redirect('teacher_classes')
    
    # Get or create course for this grade/subject combination
    # For now, we'll create a course per grade (can be extended to per subject)
    school = request.user.school or grade.school
    if not school:
        messages.error(request, 'School not found.')
        return redirect('teacher_classes')
    
    # Try to get existing course, or create new one
    course = Course.objects.filter(grade=grade, school=school).first()
    if not course:
        course = Course.objects.create(
            grade=grade,
            school=school,
            title=f"{grade.name} - E-Learning",
            description=f"E-Learning materials for {grade.name}",
            instructor=request.user,
            is_published=True
        )
    
    # Get all materials, lessons, assignments
    materials = course.materials.all()
    lessons = course.lessons.all().order_by('order')
    assignments = course.assignments.all()
    quizzes = assignments.filter(assignment_type='quiz')
    exams = assignments.filter(assignment_type='exam')
    
    context = {
        'grade': grade,
        'course': course,
        'materials': materials,
        'lessons': lessons,
        'assignments': assignments,
        'quizzes': quizzes,
        'exams': exams,
        'is_class_teacher': is_class_teacher,
        'title': f'{grade.name} - E-Learning Management'
    }
    
    return render(request, 'elearning/teacher_class_detail.html', context)


@login_required
def add_material(request, course_id):
    """Add study material to a course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permission
    if not course.grade:
        messages.error(request, 'Course grade not found.')
        return redirect('teacher_classes')
    
    if course.instructor != request.user and not (request.user.is_headteacher() or request.user.is_director_of_studies()):
        messages.error(request, 'You do not have permission to add materials to this course.')
        return redirect('teacher_class_detail', grade_id=course.grade.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        material_type = request.POST.get('material_type', 'pdf')
        file = request.FILES.get('file')
        external_url = request.POST.get('external_url', '')
        
        if not title:
            messages.error(request, 'Title is required.')
            return redirect('teacher_class_detail', grade_id=course.grade.id)
        
        material = CourseMaterial.objects.create(
            course=course,
            title=title,
            description=description,
            material_type=material_type,
            file=file,
            external_url=external_url if external_url else None
        )
        
        messages.success(request, f'Material "{title}" added successfully!')
        return redirect('teacher_class_detail', grade_id=course.grade.id)
    
    return redirect('teacher_class_detail', grade_id=course.grade.id)


@login_required
def add_quiz_exam(request, course_id):
    """Add quiz or exam to a course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permission
    if not course.grade:
        messages.error(request, 'Course grade not found.')
        return redirect('teacher_classes')
    
    if course.instructor != request.user and not (request.user.is_headteacher() or request.user.is_director_of_studies()):
        messages.error(request, 'You do not have permission to add quizzes/exams to this course.')
        return redirect('teacher_class_detail', grade_id=course.grade.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        assignment_type = request.POST.get('assignment_type', 'quiz')
        due_date_str = request.POST.get('due_date')
        start_time_str = request.POST.get('start_time')
        duration_minutes = request.POST.get('duration_minutes')
        total_points = request.POST.get('total_points', 100)
        
        if not title:
            messages.error(request, 'Title is required.')
            return redirect('teacher_class_detail', grade_id=course.grade.id)
        
        due_date = None
        if due_date_str:
            try:
                due_date = timezone.datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
                due_date = timezone.make_aware(due_date)
            except:
                pass
        
        start_time = None
        if start_time_str:
            try:
                start_time = timezone.datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
                start_time = timezone.make_aware(start_time)
            except:
                pass
        
        exam_pdf = None
        if assignment_type == 'exam':
            exam_pdf = request.FILES.get('exam_pdf')
        
        assignment = Assignment.objects.create(
            course=course,
            title=title,
            description=description,
            assignment_type=assignment_type,
            due_date=due_date,
            start_time=start_time,
            duration_minutes=int(duration_minutes) if duration_minutes else None,
            total_points=float(total_points),
            exam_pdf=exam_pdf,
            allow_attachments=request.POST.get('allow_attachments') == 'on'
        )
        
        messages.success(request, f'{assignment_type.title()} "{title}" added successfully!')
        
        # For quizzes, redirect to add questions page
        if assignment_type == 'quiz':
            return redirect('add_quiz_questions', assignment_id=assignment.id)
        
        return redirect('teacher_class_detail', grade_id=course.grade.id)
    
    return redirect('teacher_class_detail', grade_id=course.grade.id)


@login_required
def delete_material(request, material_id):
    """Delete a material"""
    material = get_object_or_404(CourseMaterial, id=material_id)
    course = material.course
    
    if not course.grade:
        messages.error(request, 'Course grade not found.')
        return redirect('teacher_classes')
    
    if course.instructor != request.user and not (request.user.is_headteacher() or request.user.is_director_of_studies()):
        messages.error(request, 'You do not have permission to delete this material.')
        return redirect('teacher_class_detail', grade_id=course.grade.id)
    
    material.delete()
    messages.success(request, 'Material deleted successfully!')
    return redirect('teacher_class_detail', grade_id=course.grade.id)


@login_required
def delete_assignment(request, assignment_id):
    """Delete an assignment/quiz/exam"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    course = assignment.course
    
    if not course.grade:
        messages.error(request, 'Course grade not found.')
        return redirect('teacher_classes')
    
    if course.instructor != request.user and not (request.user.is_headteacher() or request.user.is_director_of_studies()):
        messages.error(request, 'You do not have permission to delete this assignment.')
        return redirect('teacher_class_detail', grade_id=course.grade.id)
    
    assignment.delete()
    messages.success(request, 'Assignment deleted successfully!')
    return redirect('teacher_class_detail', grade_id=course.grade.id)

