from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('platform_owner', 'Platform Owner'),
        ('superadmin', 'Super Admin'),
        ('school_admin', 'School Admin'),
        ('headteacher', 'Headteacher'),
        ('director_of_studies', 'Director of Studies'),
        ('teacher', 'Teacher'),
        ('bursar', 'Bursar'),
        ('parent', 'Parent'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='parent')
    school = models.ForeignKey('School', null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    must_change_password = models.BooleanField(default=False, help_text="Force password change on next login")
    
    # Additional profile fields
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    qualifications = models.TextField(blank=True, help_text="Educational qualifications")
    bio = models.TextField(blank=True, help_text="Brief biography")
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True, help_text="User profile picture")
    
    def get_profile_picture_url(self):
        """Get profile picture URL or default avatar"""
        if self.profile_picture:
            return self.profile_picture.url
        # Return default avatar based on initials
        return f"https://ui-avatars.com/api/?name={self.get_full_name() or self.username}&background=667eea&color=fff&size=128"
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None

    def is_superadmin(self):
        return self.role == 'superadmin'

    def is_headteacher(self):
        return self.role == 'headteacher'

    def is_director_of_studies(self):
        return self.role == 'director_of_studies'

    def is_teacher(self):
        return self.role == 'teacher'

    def is_bursar(self):
        return self.role == 'bursar'

    def is_parent(self):
        return self.role == 'parent'

    def is_student(self):
        return self.role == 'student'

class School(models.Model):
    SCHOOL_TYPE_CHOICES = (
        ('primary', 'Primary School'),
        ('high', 'High School'),
    )
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    school_type = models.CharField(max_length=20, choices=SCHOOL_TYPE_CHOICES, default='primary', help_text="Primary school for P1-P7, High school for S1-S6")
    address = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True, help_text="School badge/logo for watermark")
    seal = models.ImageField(upload_to='school_seals/', blank=True, null=True, help_text="Unique school seal/stamp (hard to duplicate)")
    motto = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name
    
    def is_primary(self):
        """Check if this is a primary school"""
        return self.school_type == 'primary'
    
    def is_high_school(self):
        """Check if this is a high school"""
        return self.school_type == 'high'

class AcademicYear(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='academic_years')
    name = models.CharField(max_length=255, default="", blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.school.name})"

    class Meta:
        unique_together = ('school', 'name')

class Term(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.academic_year.name})"
    
    @classmethod
    def get_current_term(cls):
        """Get the current term based on today's date"""
        from datetime import date
        today = date.today()
        return cls.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).first()
    
    @classmethod
    def get_current_term_for_school(cls, school):
        """Get the current term for a specific school based on today's date"""
        from django.utils import timezone
        today = timezone.now().date()
        # Use direct query to avoid related name issues - academic_year__school uses the FK relationship
        return cls.objects.filter(
            academic_year__school=school,
            academic_year__is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).first()

    class Meta:
        unique_together = ('academic_year', 'name')


class Notification(models.Model):
    """User notifications"""
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('academic', 'Academic'),
        ('fee', 'Fee'),
        ('attendance', 'Attendance'),
        ('system', 'System'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.URLField(blank=True, null=True, help_text="Optional link to related page")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


class LoginHistory(models.Model):
    """Track user login history with device and IP information"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device = models.CharField(max_length=255, blank=True)
    browser = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_successful = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-login_time']
        verbose_name_plural = 'Login Histories'
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time} - {self.ip_address}"


class AIConversation(models.Model):
    """Store AI assistant conversation history for learning"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_conversations')
    message = models.TextField()
    response = models.TextField()
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'AI Conversations'

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"


class PlatformLead(models.Model):
    """Inbound school applications / demo requests from the public marketing site."""

    PLAN_CHOICES = (
        ('starter',    'Starter'),
        ('pro',        'Pro'),
        ('enterprise', 'Enterprise'),
        ('unsure',     'Not sure yet'),
    )
    SCHOOL_TYPE_CHOICES = (
        ('primary',   'Primary (P1-P7)'),
        ('olevel',    'Secondary O-Level (S1-S4)'),
        ('alevel',    'Secondary A-Level (S5-S6)'),
        ('combined',  'Combined (Primary + Secondary)'),
        ('other',     'Other'),
    )
    STATUS_CHOICES = (
        ('new',         'New'),
        ('contacted',   'Contacted'),
        ('qualified',   'Qualified'),
        ('onboarded',   'Onboarded'),
        ('rejected',    'Rejected'),
    )

    school_name    = models.CharField(max_length=255)
    contact_name   = models.CharField(max_length=150)
    email          = models.EmailField()
    phone          = models.CharField(max_length=32)
    district       = models.CharField(max_length=100, blank=True)
    school_type    = models.CharField(max_length=20, choices=SCHOOL_TYPE_CHOICES, default='primary')
    student_count  = models.PositiveIntegerField(null=True, blank=True)
    plan_interest  = models.CharField(max_length=20, choices=PLAN_CHOICES, default='unsure')
    message        = models.TextField(blank=True)

    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    source_ip      = models.GenericIPAddressField(null=True, blank=True)
    user_agent     = models.CharField(max_length=255, blank=True)
    referrer       = models.URLField(blank=True)

    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Platform Lead'
        verbose_name_plural = 'Platform Leads'

    def __str__(self):
        return f"{self.school_name} <{self.email}>"