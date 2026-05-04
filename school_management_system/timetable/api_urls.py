from rest_framework.routers import DefaultRouter
from .api_views import TimetableSlotViewSet

app_name = "timetable_api"

router = DefaultRouter()
router.register("slots", TimetableSlotViewSet, basename="timetable-slot")

urlpatterns = router.urls
