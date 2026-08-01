from rest_framework.routers import DefaultRouter
from .views import NoteViewSet, RegisterViewSet
from django.urls import path
router = DefaultRouter()
router.register(prefix=r"notes", viewset = NoteViewSet)
router.register(prefix=r"register", viewset=RegisterViewSet, basename="register")
urlpatterns = router.urls
