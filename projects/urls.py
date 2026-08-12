from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, ProjectViewSet, MembershipViewSet

router = DefaultRouter()
router.register(prefix=r"projects", viewset = ProjectViewSet)
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"memberships", MembershipViewSet, )
urlpatterns = router.urls