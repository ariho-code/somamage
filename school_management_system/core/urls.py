from django.urls import path
from . import views
from . import multi_school_views
from . import public_views
from students import views as students_views
from fees import views as fees_views
from academics import views as academics_views

urlpatterns = [
    # ── Public marketing site ────────────────────────────────────────────────
    path("",           public_views.landing,  name="landing"),
    path("apply/",     public_views.apply,    name="platform_apply"),

    # ── App (authenticated) ──────────────────────────────────────────────────
    path("dashboard/", views.dashboard,       name="home"),  # URL name preserved
    path("school/settings/", views.school_settings, name="school_settings"),
    
    # Multi-school management (superadmin only)
    path("schools/", multi_school_views.school_list, name="school_list"),
    path("schools/create/", multi_school_views.school_create, name="school_create"),
    path("schools/<int:school_id>/edit/", multi_school_views.school_edit, name="school_edit"),
    path("schools/<int:school_id>/admin/create/", multi_school_views.school_admin_create, name="school_admin_create"),
    path("schools/<int:school_id>/delete/", multi_school_views.school_delete, name="school_delete"),
    path("core/get-school-type/<int:school_id>/", views.get_school_type, name="get_school_type"),
    path("students/", students_views.student_list, name="student_list"),
    path("academics/exams/", views.exam_list, name="exam_list"),
    path("fees/", fees_views.fee_list, name="fee_list"),
    path("academics/marks/", academics_views.mark_entry_list, name="mark_entry"),
    path("attendance/", students_views.attendance_entry, name="attendance_entry"),
    path("students/report/", students_views.student_report, name="student_report"),
    path("fees/status/", students_views.fee_status, name="fee_status"),
    path("academic-year/create/", views.academic_year_create, name="academic_year_create"),
    path("academic-year/edit/<int:pk>/", views.academic_year_edit, name="academic_year_edit"),
    path("term/create/", views.term_create, name="term_create"),
    path("term/edit/<int:pk>/", views.term_edit, name="term_edit"),
    path("academic-context/select/", views.select_academic_context, name="select_academic_context"),
    
    # EduAI Assistant endpoints
    path("ai/chat/", views.ai_assistant_chat, name="ai_assistant_chat"),
    path("ai/analyze/", views.ai_assistant_analyze, name="ai_assistant_analyze"),
    path("ai/automate/", views.ai_assistant_automate, name="ai_assistant_automate"),
    path("ai/upload/", views.ai_assistant_upload, name="ai_assistant_upload"),
    
    # Notifications
    path("notifications/", views.notifications_list, name="notifications"),
    path("api/notifications/", views.notifications_api, name="notifications_api"),
    path("api/notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    
    # Profile
    path("profile/", views.profile_view, name="profile"),
    path("profile/settings/", views.profile_settings, name="profile_settings"),
    path("profile/login-history/", views.login_history_view, name="login_history"),
]