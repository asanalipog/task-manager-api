
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import Project, Task
from .serializers import ProjectSerializer, TaskSerializer
from .filters import TaskFilter
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()

    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_at"]
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    def get_queryset(self):
        user = self.request.user
        return Project.objects.filter(owner=user).order_by("created_at")

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    # permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TaskFilter
    ordering_fields = ["due_date", "created_at"]
    def get_queryset(self):
        return Task.objects.filter(project__owner=self.request.user).select_related("project", "assignee")

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = "DONE"
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data)
