from rest_framework.routers import DefaultRouter
from .api_views import (
    AssignmentSubmissionViewSet,
    AssignmentViewSet,
    CourseEnrollmentViewSet,
    CourseViewSet,
    LessonViewSet,
)

app_name = "elearning-api"

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"lessons", LessonViewSet, basename="lesson")
router.register(r"assignments", AssignmentViewSet, basename="assignment")
router.register(r"submissions", AssignmentSubmissionViewSet, basename="submission")
router.register(r"enrollments", CourseEnrollmentViewSet, basename="enrollment")

urlpatterns = router.urls
