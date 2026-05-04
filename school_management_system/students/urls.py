from django.urls import path
from . import views

urlpatterns = [
    path("staff/add/", views.add_staff, name="add_staff"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/<int:teacher_id>/", views.teacher_detail, name="teacher_detail"),
    path("staff/<int:teacher_id>/edit/", views.teacher_edit, name="teacher_edit"),
    path("staff/<int:teacher_id>/delete/", views.teacher_delete, name="teacher_delete"),
    path("staff/<int:teacher_id>/assign-subjects/", views.assign_subject, name="assign_subject"),
    path("students/add/", views.add_student, name="add_student"),
    path("students/bulk-upload/", views.bulk_upload_students, name="bulk_upload_students"),
    path("students/", views.student_list, name="student_list"),
    path("students/<int:student_id>/", views.student_detail, name="student_detail"),
    path("students/<int:student_id>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:student_id>/delete/", views.student_delete, name="student_delete"),
    path("students/<int:student_id>/select-optional-subjects/", views.student_select_optional_subjects, name="student_select_optional_subjects"),
    path("students/<int:student_id>/assign-optional-subjects/", views.student_assign_optional_subjects, name="student_assign_optional_subjects"),
    path("students/<int:student_id>/assign-combination/", views.student_assign_combination, name="student_assign_combination"),
    path("students/<int:student_id>/edit-combination/", views.student_edit_combination, name="student_edit_combination"),
    path("students/subject-teacher/", views.subject_teacher_students, name="subject_teacher_students"),
    path("students/report/", views.student_report, name="student_report"),
    path("students/assign-compulsory-subjects/", views.assign_compulsory_subjects_to_existing_olevel_students, name="assign_compulsory_subjects"),
    path("parent/teachers/", views.parent_teachers, name="parent_teachers"),
    path("streams/get/", views.get_streams_for_grade, name="get_streams_for_grade"),
    # Search autocomplete endpoints
    path("students/search-suggestions/", views.student_search_suggestions, name="student_search_suggestions"),
    path("staff/search-suggestions/", views.teacher_search_suggestions, name="teacher_search_suggestions"),
]
