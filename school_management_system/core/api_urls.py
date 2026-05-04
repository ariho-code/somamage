from rest_framework.routers import DefaultRouter
from .api.views import (
    AcademicYearViewSet,
    NotificationViewSet,
    SchoolViewSet,
    TermViewSet,
    UserViewSet,
)

app_name = "core-api"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"schools", SchoolViewSet, basename="school")
router.register(r"academic-years", AcademicYearViewSet, basename="academic-year")
router.register(r"terms", TermViewSet, basename="term")
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = router.urls
