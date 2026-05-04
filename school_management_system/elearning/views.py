"""
E-Learning Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Avg
from .models import Course, CourseEnrollment, Lesson, LessonCompletion, Assignment, AssignmentSubmission, CourseMaterial, QuizQuestion, QuizOption, QuizAnswer, SubmissionAttachment
from academics.models import TeacherSubject, Grade, Subject
from students.models import Enrollment
from django.utils import timezone
from django.forms import modelform_factory
from django import forms

@login_required
def course_list(request):
    """List all available courses"""
    courses = Course.objects.filter(is_published=True)
    
    # Filter by school if user has one
    if request.user.school:
        courses = courses.filter(school=request.user.school)
    
    # Filter by grade if student or parent viewing for student
    if request.user.is_student() or request.user.is_parent():
        # Get student's current grade (for students with user accounts or parents viewing)
        from students.models import Enrollment, Student
        if request.user.is_student():
            student = getattr(request.user, 'student_profile', None)
        else:
            # For parents, get their child's enrollment
            student = Student.objects.filter(guardian__phone=request.user.username).first()
        
        if student:
            enrollment = Enrollment.objects.filter(
                student=student,
                is_active=True
            ).first()
            if enrollment:
                courses = courses.filter(
                    Q(grade=enrollment.grade) | Q(grade__isnull=True)
                )
    
    # Get enrollment status for each course
    enrolled_course_ids = []
    if request.user.is_student() or request.user.is_parent():
        enrolled_course_ids = CourseEnrollment.objects.filter(
            student=request.user,
            is_active=True
        ).values_list('course_id', flat=True)
    
    context = {
        'courses': courses,
        'enrolled_course_ids': list(enrolled_course_ids),
        'title': 'E-Learning Courses'
    }
    
    return render(request, 'elearning/course_list.html', context)


@login_required
def course_detail(request, course_id):
    """Course detail page"""
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check enrollment
    is_enrolled = False
    enrollment = None
    enrollment = CourseEnrollment.objects.filter(
        student=request.user,
        course=course,
        is_active=True
    ).first()
    is_enrolled = enrollment is not None
    
    # Get lessons
    lessons = course.lessons.filter(is_published=True).order_by('order')
    
    # Get assignments
    assignments = course.assignments.filter(is_published=True)
    
    # Get materials
    materials = course.materials.all()
    
    context = {
        'course': course,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment,
        'lessons': lessons,
        'assignments': assignments,
        'materials': materials,
        'title': course.title
    }
    
    return render(request, 'elearning/course_detail.html', context)


@login_required
def enroll_course(request, course_id):
    """Enroll in a course"""
    # Allow any authenticated user to enroll (students, parents viewing for children, etc.)
    # In practice, you may want to restrict this further
    
    course = get_object_or_404(Course, id=course_id, is_published=True, enrollment_open=True)
    
    # Check if already enrolled
    enrollment, created = CourseEnrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'is_active': True}
    )
    
    if created:
        messages.success(request, f'Successfully enrolled in {course.title}!')
    else:
        if not enrollment.is_active:
            enrollment.is_active = True
            enrollment.save()
            messages.success(request, f'Re-enrolled in {course.title}!')
        else:
            messages.info(request, 'You are already enrolled in this course.')
    
    return redirect('course_detail', course_id=course_id)


@login_required
def lesson_detail(request, course_id, lesson_id):
    """Lesson detail page"""
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course, is_published=True)
    
    # Check enrollment
    enrollment = CourseEnrollment.objects.filter(
        student=request.user,
        course=course,
        is_active=True
    ).first()
    
    if not enrollment:
        messages.error(request, 'You must enroll in this course first.')
        return redirect('course_detail', course_id=course_id)
    
    # Update last accessed
    enrollment.last_accessed = timezone.now()
    enrollment.save()
    
    # Get or create lesson completion
    completion, _ = LessonCompletion.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )
    completion.last_accessed = timezone.now()
    completion.save()
    
    # Get all lessons for navigation
    all_lessons = course.lessons.filter(is_published=True).order_by('order')
    current_index = list(all_lessons).index(lesson)
    previous_lesson = all_lessons[current_index - 1] if current_index > 0 else None
    next_lesson = all_lessons[current_index + 1] if current_index < len(all_lessons) - 1 else None
    
    context = {
        'course': course,
        'lesson': lesson,
        'previous_lesson': previous_lesson,
        'next_lesson': next_lesson,
        'all_lessons': all_lessons,
        'title': lesson.title
    }
    
    return render(request, 'elearning/lesson_detail.html', context)


@login_required
def my_courses(request):
    """User's enrolled courses"""
    # Allow any user to view their enrolled courses
    
    enrollments = CourseEnrollment.objects.filter(
        student=request.user,
        is_active=True
    ).select_related('course').order_by('-enrolled_at')
    
    context = {
        'enrollments': enrollments,
        'title': 'My Courses'
    }
    
    return render(request, 'elearning/my_courses.html', context)


@login_required
def assignment_detail(request, assignment_id):
    """Assignment detail page"""
    assignment = get_object_or_404(Assignment, id=assignment_id, is_published=True)
    
    # Check if user is enrolled
    is_enrolled = False
    submission = None
    is_enrolled = CourseEnrollment.objects.filter(
        student=request.user,
        course=assignment.course,
        is_active=True
    ).exists()
    
    if is_enrolled:
        submission = AssignmentSubmission.objects.filter(
            student=request.user,
            assignment=assignment
        ).first()
    
    context = {
        'assignment': assignment,
        'is_enrolled': is_enrolled,
        'submission': submission,
        'title': assignment.title
    }
    
    return render(request, 'elearning/assignment_detail.html', context)


@login_required
def submit_assignment(request, assignment_id):
    """Submit assignment - handles quizzes (auto-grade) and exams"""
    from django.http import JsonResponse
    from .models import QuizQuestion, QuizOption, QuizAnswer, SubmissionAttachment
    from django.utils import timezone
    import json
    
    assignment = get_object_or_404(Assignment, id=assignment_id, is_published=True)
    
    # Check enrollment
    enrollment = CourseEnrollment.objects.filter(
        student=request.user,
        course=assignment.course,
        is_active=True
    ).first()
    
    if not enrollment:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Not enrolled in course'}, status=403)
        messages.error(request, 'You must be enrolled in the course to submit assignments.')
        return redirect('assignment_detail', assignment_id=assignment_id)
    
    if request.method == 'POST':
        # Handle quiz submission with auto-grading
        if assignment.is_quiz():
            quiz_answers = json.loads(request.POST.get('answers', '{}'))
            started_at_str = request.POST.get('started_at')
            
            started_at = None
            if started_at_str:
                try:
                    started_at = timezone.datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                except:
                    started_at = timezone.now()
            else:
                started_at = timezone.now()
            
            # Create or get submission
            submission, created = AssignmentSubmission.objects.get_or_create(
                student=request.user,
                assignment=assignment,
                defaults={
                    'started_at': started_at,
                    'completed_at': timezone.now(),
                    'total_score': assignment.total_points
                }
            )
            
            if not created:
                submission.completed_at = timezone.now()
                submission.save()
            
            # Grade answers
            total_score = 0
            total_points = 0
            
            for question_id, answer_data in quiz_answers.items():
                try:
                    question = QuizQuestion.objects.get(id=question_id, assignment=assignment)
                    total_points += question.points
                    
                    if question.question_type == 'multiple_choice':
                        selected_option_id = answer_data.get('option_id')
                        if selected_option_id:
                            selected_option = QuizOption.objects.get(id=selected_option_id, question=question)
                            is_correct = selected_option.is_correct
                            points_earned = question.points if is_correct else 0
                            
                            quiz_answer, _ = QuizAnswer.objects.get_or_create(
                                submission=submission,
                                question=question,
                                defaults={
                                    'selected_option': selected_option,
                                    'is_correct': is_correct,
                                    'points_earned': points_earned
                                }
                            )
                            total_score += points_earned
                    elif question.question_type == 'true_false':
                        answer_bool = answer_data.get('answer') == 'true' or answer_data.get('answer') == True
                        correct_option = question.options.filter(is_correct=True).first()
                        is_correct = (correct_option and correct_option.option_text.lower() == str(answer_bool).lower())
                        points_earned = question.points if is_correct else 0
                        
                        quiz_answer, _ = QuizAnswer.objects.get_or_create(
                            submission=submission,
                            question=question,
                            defaults={
                                'is_correct': is_correct,
                                'points_earned': points_earned,
                                'text_answer': str(answer_bool)
                            }
                        )
                        total_score += points_earned
                    elif question.question_type == 'short_answer':
                        text_answer = answer_data.get('text', '')
                        # For short answer, teacher needs to grade manually
                        quiz_answer, _ = QuizAnswer.objects.get_or_create(
                            submission=submission,
                            question=question,
                            defaults={
                                'text_answer': text_answer,
                                'points_earned': 0
                            }
                        )
                except Exception as e:
                    continue
            
            submission.score = total_score
            submission.total_score = total_points
            submission.is_auto_graded = True
            submission.is_graded = True
            submission.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'score': float(total_score),
                    'total_score': float(total_points),
                    'percentage': float((total_score / total_points * 100) if total_points > 0 else 0)
                })
            
            messages.success(request, f'Quiz submitted! Your score: {total_score}/{total_points}')
            return redirect('assignment_detail', assignment_id=assignment_id)
        
        # Handle exam/assignment submission
        else:
            submission_text = request.POST.get('submission_text', '')
            submission_file = request.FILES.get('submission_file')
            attachment_files = request.FILES.getlist('attachments')
            
            if not submission_text and not submission_file:
                messages.error(request, 'Please provide either text or file submission.')
                return redirect('assignment_detail', assignment_id=assignment_id)
            
            submission, created = AssignmentSubmission.objects.get_or_create(
                student=request.user,
                assignment=assignment,
                defaults={
                    'submission_text': submission_text,
                    'submission_file': submission_file,
                    'completed_at': timezone.now(),
                    'total_score': assignment.total_points
                }
            )
            
            if not created:
                submission.submission_text = submission_text
                if submission_file:
                    submission.submission_file = submission_file
                submission.completed_at = timezone.now()
                submission.save()
            
            # Handle attachments
            for attachment_file in attachment_files:
                SubmissionAttachment.objects.create(
                    submission=submission,
                    file=attachment_file
                )
            
            messages.success(request, 'Assignment submitted successfully!')
            return redirect('assignment_detail', assignment_id=assignment_id)
    
    return redirect('assignment_detail', assignment_id=assignment_id)

