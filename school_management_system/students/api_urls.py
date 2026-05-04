from rest_framework.routers import DefaultRouter
from .api_views import EnrollmentViewSet, GuardianViewSet, StudentViewSet

app_name = "students_api"

router = DefaultRouter()
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("students", StudentViewSet, basename="student")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")

urlpatterns = router.urls
