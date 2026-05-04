from rest_framework.routers import DefaultRouter
from .api_views import (
    CombinationViewSet, ExamViewSet, GradeViewSet,
    MarkEntryViewSet, ReportCardViewSet, StreamViewSet,
    SubjectViewSet, TeacherSubjectViewSet,
)

app_name = "academics_api"

router = DefaultRouter()
router.register("grades", GradeViewSet, basename="grade")
router.register("subjects", SubjectViewSet, basename="subject")
router.register("combinations", CombinationViewSet, basename="combination")
router.register("streams", StreamViewSet, basename="stream")
router.register("exams", ExamViewSet, basename="exam")
router.register("marks", MarkEntryViewSet, basename="mark")
router.register("report-cards", ReportCardViewSet, basename="report-card")
router.register("teacher-subjects", TeacherSubjectViewSet, basename="teacher-subject")

urlpatterns = router.urls
