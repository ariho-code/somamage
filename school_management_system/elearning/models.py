"""
E-Learning Module Models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

# Import related models with string references to avoid circular imports
# These will be resolved at runtime

class Course(models.Model):
    """Online courses for students"""
    COURSE_LEVEL_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses_taught', limit_choices_to={'role__in': ['teacher', 'headteacher', 'director_of_studies']})
    school = models.ForeignKey('core.School', on_delete=models.CASCADE, related_name='courses')
    grade = models.ForeignKey('academics.Grade', on_delete=models.SET_NULL, null=True, blank=True, help_text="Target grade level")
    subject = models.ForeignKey('academics.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    level = models.CharField(max_length=20, choices=COURSE_LEVEL_CHOICES, default='beginner')
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    is_published = models.BooleanField(default=False)
    enrollment_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        # Note: unique_together removed to allow multiple courses per grade if needed
    
    def __str__(self):
        return self.title
    
    def get_enrollment_count(self):
        return self.enrollments.filter(is_active=True).count()
    
    def get_lesson_count(self):
        return self.lessons.count()


class CourseEnrollment(models.Model):
    """Student enrollments in courses"""
    # Note: Students may not have User accounts, so we use a flexible approach
    # For now, we'll allow any user to enroll, but in practice, only students should enroll
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Progress percentage")
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-enrolled_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.course.title}"
    
    def update_progress(self):
        """Calculate and update progress based on completed lessons"""
        total_lessons = self.course.lessons.count()
        if total_lessons == 0:
            self.progress = 0
        else:
            completed = self.lesson_completions.filter(completed=True).count()
            self.progress = (completed / total_lessons) * 100
        self.save()


class Lesson(models.Model):
    """Lessons within a course"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content = models.TextField(help_text="Lesson content in HTML or markdown")
    video_url = models.URLField(blank=True, null=True, help_text="YouTube or video URL")
    video_file = models.FileField(upload_to='lesson_videos/', blank=True, null=True)
    order = models.IntegerField(default=0, help_text="Order in course")
    duration_minutes = models.IntegerField(default=0, help_text="Estimated duration in minutes")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ('course', 'order')
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class LessonCompletion(models.Model):
    """Track lesson completion by students"""
    enrollment = models.ForeignKey(CourseEnrollment, on_delete=models.CASCADE, related_name='lesson_completions')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='completions')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('enrollment', 'lesson')
    
    def __str__(self):
        return f"{self.enrollment.student.get_full_name()} - {self.lesson.title}"


class Assignment(models.Model):
    """Assignments/Quizzes for courses"""
    ASSIGNMENT_TYPE_CHOICES = (
        ('quiz', 'Quiz'),
        ('exam', 'Exam'),
        ('assignment', 'Assignment'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField()
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE_CHOICES, default='assignment')
    due_date = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True, help_text="Start time for timed quizzes/exams")
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="Duration in minutes for timed quizzes/exams")
    total_points = models.DecimalField(max_digits=6, decimal_places=2, default=100.00)
    is_published = models.BooleanField(default=True)
    # For exams
    exam_pdf = models.FileField(upload_to='exam_pdfs/', blank=True, null=True, help_text="PDF file for exam")
    allow_attachments = models.BooleanField(default=True, help_text="Allow students to attach files with submission")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    def is_quiz(self):
        return self.assignment_type == 'quiz'
    
    def is_exam(self):
        return self.assignment_type == 'exam'


class QuizQuestion(models.Model):
    """Questions for objective quizzes"""
    QUESTION_TYPE_CHOICES = (
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
    )
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='questions', limit_choices_to={'assignment_type': 'quiz'})
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='multiple_choice')
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.assignment.title} - Q{self.order + 1}"


class QuizOption(models.Model):
    """Answer options for quiz questions"""
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.question.question_text[:50]} - {self.option_text[:30]}"


class QuizAnswer(models.Model):
    """Student answers to quiz questions"""
    submission = models.ForeignKey('AssignmentSubmission', on_delete=models.CASCADE, related_name='quiz_answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(QuizOption, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(blank=True, help_text="For short answer questions")
    is_correct = models.BooleanField(default=False)
    points_earned = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    class Meta:
        unique_together = ('submission', 'question')
    
    def __str__(self):
        return f"{self.submission.student.get_full_name()} - {self.question.question_text[:50]}"


class AssignmentSubmission(models.Model):
    """Student submissions for assignments"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    submission_text = models.TextField(blank=True, help_text="Text answer for exams/assignments")
    submission_file = models.FileField(upload_to='assignment_submissions/', blank=True, null=True, help_text="Uploaded answer sheet")
    submitted_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True, help_text="When student started the quiz/exam")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When student completed/submitted")
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    total_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Total possible score")
    feedback = models.TextField(blank=True)
    is_graded = models.BooleanField(default=False)
    is_auto_graded = models.BooleanField(default=False, help_text="True if quiz was auto-graded")
    
    class Meta:
        unique_together = ('assignment', 'student')
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.assignment.title}"
    
    def get_percentage(self):
        """Get score as percentage"""
        if self.total_score and self.total_score > 0:
            return (self.score / self.total_score * 100) if self.score else 0
        return 0


class SubmissionAttachment(models.Model):
    """Attachments for exam/assignment submissions"""
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='submission_attachments/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.submission.student.get_full_name()} - {self.file.name}"


class CourseMaterial(models.Model):
    """Additional materials for courses (PDFs, documents, videos, images, etc.)"""
    MATERIAL_TYPE_CHOICES = (
        ('pdf', 'PDF Document'),
        ('doc', 'Word Document'),
        ('ppt', 'PowerPoint'),
        ('video', 'Video File'),
        ('image', 'Image'),
        ('link', 'External Link'),
        ('other', 'Other'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=255)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES, default='pdf')
    file = models.FileField(upload_to='course_materials/', blank=True, null=True, help_text="Upload PDF, video, image, or document")
    external_url = models.URLField(blank=True, null=True, help_text="External link (YouTube, etc.)")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

