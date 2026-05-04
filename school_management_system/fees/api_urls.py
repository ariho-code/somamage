from rest_framework.routers import DefaultRouter
from .api_views import FeeBalanceViewSet, FeePaymentViewSet, FeeStructureViewSet

app_name = "fees_api"

router = DefaultRouter()
router.register("structures", FeeStructureViewSet, basename="fee-structure")
router.register("payments", FeePaymentViewSet, basename="fee-payment")
router.register("balances", FeeBalanceViewSet, basename="fee-balance")

urlpatterns = router.urls
