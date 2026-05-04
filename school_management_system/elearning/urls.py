from django.urls import path
from . import views, views_teacher, views_student, views_quiz

urlpatterns = [
    # General E-Learning
    path("", views.course_list, name="elearning_home"),
    path("courses/", views.course_list, name="course_list"),
    path("courses/<int:course_id>/", views.course_detail, name="course_detail"),
    path("courses/<int:course_id>/enroll/", views.enroll_course, name="enroll_course"),
    path("courses/<int:course_id>/lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("my-courses/", views.my_courses, name="my_courses"),
    path("assignments/<int:assignment_id>/", views.assignment_detail, name="assignment_detail"),
    path("assignments/<int:assignment_id>/submit/", views.submit_assignment, name="submit_assignment"),
    
    # Teacher E-Learning
    path("teacher/classes/", views_teacher.teacher_classes, name="teacher_classes"),
    path("teacher/classes/<int:grade_id>/", views_teacher.teacher_class_detail, name="teacher_class_detail"),
    path("teacher/courses/<int:course_id>/materials/add/", views_teacher.add_material, name="add_material"),
    path("teacher/courses/<int:course_id>/assignments/add/", views_teacher.add_quiz_exam, name="add_quiz_exam"),
    path("teacher/materials/<int:material_id>/delete/", views_teacher.delete_material, name="delete_material"),
    path("teacher/assignments/<int:assignment_id>/delete/", views_teacher.delete_assignment, name="delete_assignment"),
    
    # Quiz Management
    path("teacher/assignments/<int:assignment_id>/questions/", views_quiz.add_quiz_questions, name="add_quiz_questions"),
    path("teacher/questions/<int:question_id>/edit/", views_quiz.edit_quiz_question, name="edit_quiz_question"),
    
    # Student E-Learning
    path("student/classes/", views_student.student_classes, name="student_classes"),
    path("student/classes/<int:course_id>/", views_student.student_class_detail, name="student_class_detail"),
    path("student/materials/<int:material_id>/", views_student.view_material, name="view_material"),
]

