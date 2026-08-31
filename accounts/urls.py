from rest_framework.routers import DefaultRouter
from .views import RegisterViewSet
from django.urls import path
router = DefaultRouter()
router.register(prefix=r"register", viewset=RegisterViewSet, basename="register")
urlpatterns = router.urls
