
from .serializers import  RegisterSerializer
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model


User = get_user_model()

class RegisterViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]