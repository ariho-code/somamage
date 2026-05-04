from django.contrib import admin
from .models import (Course, CourseEnrollment, Lesson, LessonCompletion, Assignment, 
                     AssignmentSubmission, CourseMaterial, QuizQuestion, QuizOption, 
                     QuizAnswer, SubmissionAttachment)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'school', 'grade', 'is_published', 'enrollment_open', 'created_at')
    list_filter = ('is_published', 'enrollment_open', 'level', 'school')
    search_fields = ('title', 'description', 'instructor__username')
    filter_horizontal = ()

@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at', 'is_active', 'progress', 'last_accessed')
    list_filter = ('is_active', 'course', 'enrolled_at')
    search_fields = ('student__username', 'course__title')

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'duration_minutes', 'is_published', 'created_at')
    list_filter = ('is_published', 'course')
    search_fields = ('title', 'description', 'course__title')

@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'lesson', 'completed', 'completed_at', 'time_spent_minutes')
    list_filter = ('completed', 'lesson__course')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'due_date', 'total_points', 'is_published', 'created_at')
    list_filter = ('is_published', 'course')

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'submitted_at', 'score', 'is_graded')
    list_filter = ('is_graded', 'assignment__course')

@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'material_type', 'created_at')
    list_filter = ('material_type', 'course')

@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'assignment', 'question_type', 'points', 'order')
    list_filter = ('question_type', 'assignment')
    search_fields = ('question_text',)

@admin.register(QuizOption)
class QuizOptionAdmin(admin.ModelAdmin):
    list_display = ('option_text', 'question', 'is_correct', 'order')
    list_filter = ('is_correct', 'question__assignment')

@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ('submission', 'question', 'is_correct', 'points_earned')
    list_filter = ('is_correct', 'submission__assignment')

@admin.register(SubmissionAttachment)
class SubmissionAttachmentAdmin(admin.ModelAdmin):
    list_display = ('submission', 'file', 'uploaded_at')
    list_filter = ('uploaded_at',)

