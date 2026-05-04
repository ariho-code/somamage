"""
E-Learning Views for Students
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Course, CourseEnrollment, Lesson, Assignment, CourseMaterial, AssignmentSubmission
from students.models import Enrollment, Student
from academics.models import Grade
from django.utils import timezone

@login_required
def student_classes(request):
    """List all classes/subjects the student is enrolled in"""
    if not request.user.is_student():
        messages.error(request, 'Only students can access this page.')
        return redirect('home')
    
    # Get student profile
    student = getattr(request.user, 'student_profile', None)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    # Get active enrollments
    enrollments = Enrollment.objects.filter(student=student, is_active=True).select_related('grade')
    
    # Get courses for each grade
    classes_list = []
    for enrollment in enrollments:
        grade = enrollment.grade
        # Get courses for this grade
        courses = Course.objects.filter(
            grade=grade,
            is_published=True
        ).select_related('instructor')
        
        if courses.exists():
            classes_list.append({
                'grade': grade,
                'courses': courses,
                'enrollment': enrollment
            })
    
    context = {
        'classes_list': classes_list,
        'title': 'My Classes - E-Learning'
    }
    
    return render(request, 'elearning/student_classes.html', context)


@login_required
def student_class_detail(request, course_id):
    """Student's view of a specific class - view materials, quizzes, exams"""
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check if student is enrolled in this grade
    student = getattr(request.user, 'student_profile', None)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('student_classes')
    
    enrollment = Enrollment.objects.filter(
        student=student,
        grade=course.grade,
        is_active=True
    ).first()
    
    if not enrollment:
        messages.error(request, 'You are not enrolled in this class.')
        return redirect('student_classes')
    
    # Check or create course enrollment
    course_enrollment, created = CourseEnrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'is_active': True}
    )
    
    # Get all materials, lessons, assignments
    materials = course.materials.all()
    lessons = course.lessons.all().order_by('order')
    assignments = course.assignments.filter(is_published=True)
    quizzes = assignments.filter(assignment_type='quiz')
    exams = assignments.filter(assignment_type='exam')
    regular_assignments = assignments.filter(assignment_type='assignment')
    
    # Get student's submissions
    submissions = AssignmentSubmission.objects.filter(
        student=request.user,
        assignment__in=assignments
    )
    
    context = {
        'course': course,
        'grade': course.grade,
        'materials': materials,
        'lessons': lessons,
        'assignments': regular_assignments,
        'quizzes': quizzes,
        'exams': exams,
        'submissions': submissions,
        'enrollment': course_enrollment,
        'title': f'{course.title} - E-Learning'
    }
    
    return render(request, 'elearning/student_class_detail.html', context)


@login_required
def view_material(request, material_id):
    """View/download a material"""
    material = get_object_or_404(CourseMaterial, id=material_id)
    course = material.course
    
    # Check enrollment
    student = getattr(request.user, 'student_profile', None)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('student_classes')
    
    enrollment = Enrollment.objects.filter(
        student=student,
        grade=course.grade,
        is_active=True
    ).exists()
    
    if not enrollment:
        messages.error(request, 'You are not enrolled in this class.')
        return redirect('student_classes')
    
    context = {
        'material': material,
        'course': course,
        'title': material.title
    }
    
    return render(request, 'elearning/view_material.html', context)

