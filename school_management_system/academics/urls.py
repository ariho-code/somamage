from django.urls import path
from academics import views

urlpatterns = [
    # Grades and Subjects
    path("grades/", views.grade_list, name="grade_list"),
    path("grades/create/", views.grade_create, name="grade_create"),
    path("grades/<int:pk>/edit/", views.grade_edit, name="grade_edit"),
    path("grades/<int:pk>/delete/", views.grade_delete, name="grade_delete"),
    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/create/", views.subject_create, name="subject_create"),
    path("subjects/<int:subject_id>/edit/", views.subject_edit, name="subject_edit"),
    path("subjects/<int:subject_id>/delete/", views.subject_delete, name="subject_delete"),
    path("subjects/cleanup-compulsory/", views.cleanup_compulsory_subjects, name="cleanup_compulsory_subjects"),
    path("subjects/<int:subject_id>/papers/", views.subject_paper_list, name="subject_paper_list"),
    path("subject-papers/create/", views.subject_paper_create, name="subject_paper_create"),
    path("subject-papers/<int:paper_id>/edit/", views.subject_paper_edit, name="subject_paper_edit"),
    path("subject-papers/<int:paper_id>/delete/", views.subject_paper_delete, name="subject_paper_delete"),
    # A-Level Combinations
    path("combinations/", views.combination_manage, name="combination_manage"),
    path("combinations/create/", views.combination_create, name="combination_create"),
    path("combinations/<int:combination_id>/edit/", views.combination_edit, name="combination_edit"),
    path("combinations/<int:combination_id>/delete/", views.combination_delete, name="combination_delete"),
    path("combinations/by-grade/<int:grade_id>/", views.get_combinations_by_grade, name="get_combinations_by_grade"),
    
    # Timetable
    path("timetable/", views.timetable_list, name="timetable_list"),
    path("timetable/create/", views.timetable_create, name="timetable_create"),
    path("timetable/<int:slot_id>/edit/", views.timetable_edit, name="timetable_edit"),
    path("timetable/<int:slot_id>/delete/", views.timetable_delete, name="timetable_delete"),
    
    # Teacher Subject Assignment
    path("assign-teacher-subject/", views.assign_teacher_subject, name="assign_teacher_subject"),
    path("assign-teacher-subject/<int:assignment_id>/delete/", views.teacher_subject_delete, name="teacher_subject_delete"),
    path("get-subjects-for-teacher/", views.get_subjects_for_teacher, name="get_subjects_for_teacher"),
    path("get-grades-for-teacher/", views.get_grades_for_teacher, name="get_grades_for_teacher"),
    
    # Student Paper Assignment
    path("students/<int:enrollment_id>/assign-papers/", views.assign_student_papers, name="assign_student_papers"),
    path("students/<int:enrollment_id>/papers/<int:subject_id>/", views.get_student_papers, name="get_student_papers"),
    
    # Mark Entry
    path("marks/", views.mark_entry_list, name="mark_entry_list"),
    path("marks/add/", views.mark_entry_create, name="mark_entry_create"),
    path("marks/get-students/", views.get_students_for_subject, name="get_students_for_subject"),
    path("marks/teacher-context/", views.get_teacher_entry_context, name="get_teacher_entry_context"),
    
    # Report Cards
    path("report-cards/", views.report_card_list, name="report_card_list"),
    path("report-cards/<int:report_card_id>/", views.report_card_detail, name="report_card_detail"),
    path("report-cards/<int:report_card_id>/export/", views.report_card_export_pdf, name="report_card_export_pdf"),
    path("report-cards/<int:report_card_id>/add-comment/", views.report_card_add_comment, name="report_card_add_comment"),
    path("report-cards/<int:report_card_id>/add-headteacher-comment/", views.report_card_add_headteacher_comment, name="report_card_add_headteacher_comment"),
    path("report-cards/generate/", views.generate_report_cards, name="generate_report_cards"),
    path("report-cards/export-all/", views.report_cards_export_all, name="report_cards_export_all"),
    # Class/Grade Stream Management
    path("grades/<int:grade_id>/streams/", views.manage_streams, name="manage_streams"),
    path("grades/<int:grade_id>/streams/add/", views.add_stream, name="add_stream"),
    path("streams/<int:stream_id>/edit/", views.edit_stream, name="edit_stream"),
    path("streams/<int:stream_id>/delete/", views.delete_stream, name="delete_stream"),
    
    # A-Level Combination Management (additional views from stream_views)
    path("grades/<int:grade_id>/combinations/add/", views.add_combination, name="add_combination"),
    path("combinations/<int:combination_id>/streams/add/", views.add_stream_to_combination, name="add_stream_to_combination"),
    
    # Mark Sheet
    path("marksheet/", views.marksheet_view, name="marksheet"),

    # Headteacher management
    path("grading-settings/", views.grading_settings, name="grading_settings"),
    path("streams/", views.stream_list, name="stream_list"),
    path("teachers/<int:teacher_id>/assign-role/", views.assign_teacher_role, name="assign_teacher_role"),
    path("grading-systems/<int:grading_system_id>/scales/", views.grading_scales, name="grading_scales"),
    
    # Exam Management
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/create/", views.exam_create, name="exam_create"),
    path("exams/<int:exam_id>/edit/", views.exam_edit, name="exam_edit"),
    path("exams/<int:exam_id>/delete/", views.exam_delete, name="exam_delete"),
    
    # UACE Grading Configuration
    path("uace-grading-config/", views.uace_grading_config, name="uace_grading_config"),
    
    # Search autocomplete endpoints
    path("subjects/search-suggestions/", views.subject_search_suggestions, name="subject_search_suggestions"),
    
    # Get teachers for school (for grade form)
    path("get-teachers-for-school/<int:school_id>/", views.get_teachers_for_school, name="get_teachers_for_school"),
]
