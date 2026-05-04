from rest_framework.routers import DefaultRouter
from .views import CampusViewSet, PlatformViewSet, SchoolViewSet

app_name = "tenants"

router = DefaultRouter()
router.register("platform", PlatformViewSet, basename="platform")
router.register("schools", SchoolViewSet, basename="school")
router.register("campuses", CampusViewSet, basename="campus")

urlpatterns = router.urls
