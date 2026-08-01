from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, ProjectViewSet

router = DefaultRouter()
router.register(prefix=r"projects", viewset = ProjectViewSet)
router.register(r"tasks", TaskViewSet, basename="task")
urlpatterns = router.urls