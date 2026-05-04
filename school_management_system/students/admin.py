from django.contrib import admin
from .models import Guardian, Student, Enrollment, EnrollmentSubject

class EnrollmentSubjectInline(admin.TabularInline):
    """Inline admin for Enrollment Subjects"""
    model = EnrollmentSubject
    extra = 0
    fields = ('subject', 'is_compulsory', 'assigned_date')
    readonly_fields = ('assigned_date',)

@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email")

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("admission_number", "user", "gender")
    search_fields = ("admission_number", "user__username", "user__first_name", "user__last_name")

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "grade", "combination", "academic_year", "is_active")
    list_filter = ("academic_year", "grade", "combination", "is_active")
    inlines = [EnrollmentSubjectInline]

@admin.register(EnrollmentSubject)
class EnrollmentSubjectAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "subject", "is_compulsory", "assigned_date")
    list_filter = ("is_compulsory", "subject", "enrollment__grade")
    search_fields = ("enrollment__student__admission_number", "subject__name")
