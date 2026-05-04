from rest_framework.routers import DefaultRouter
from .api_views import AttendanceRecordViewSet

app_name = "attendance_api"

router = DefaultRouter()
router.register("records", AttendanceRecordViewSet, basename="attendance")

urlpatterns = router.urls
