
from .models import Note
from .serializers import NoteSerializer, RegisterSerializer
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model


User = get_user_model()

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

class RegisterViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]