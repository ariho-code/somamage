from django.contrib import admin
from .models import User, School, AcademicYear, Term, Notification, LoginHistory, AIConversation, PlatformLead


@admin.register(PlatformLead)
class PlatformLeadAdmin(admin.ModelAdmin):
    list_display  = ('school_name', 'contact_name', 'email', 'phone', 'school_type',
                     'plan_interest', 'status', 'created_at')
    list_filter   = ('status', 'plan_interest', 'school_type', 'created_at')
    search_fields = ('school_name', 'contact_name', 'email', 'phone', 'district')
    readonly_fields = ('source_ip', 'user_agent', 'referrer', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'role', 'school', 'is_active', 'email', 'phone_number')
    list_filter = ('role', 'school', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = (
        ('Basic Information', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'role', 'school')
        }),
        ('Profile', {
            'fields': ('profile_picture', 'phone_number', 'date_of_birth', 'qualifications', 'bio')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'school_type', 'email', 'phone')
    list_filter = ('school_type',)
    search_fields = ('name', 'code')

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'start_date', 'end_date', 'is_active')
    list_filter = ('school', 'is_active')
    search_fields = ('name',)

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'start_date', 'end_date')
    list_filter = ('academic_year',)
    search_fields = ('name',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'device', 'browser', 'login_time', 'is_successful')
    list_filter = ('is_successful', 'device', 'browser', 'login_time')
    search_fields = ('user__username', 'ip_address', 'device', 'browser')
    readonly_fields = ('login_time', 'logout_time', 'ip_address', 'user_agent', 'device', 'browser')
    date_hierarchy = 'login_time'

@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_preview', 'response_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'message', 'response')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def response_preview(self, obj):
        return obj.response[:50] + '...' if len(obj.response) > 50 else obj.response
    response_preview.short_description = 'Response'