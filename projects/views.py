
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import Project, Task, Membership
from .serializers import ProjectSerializer, TaskSerializer, MembershipSerializer
from .filters import TaskFilter
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .permissions import IsProjectEditorOrReadOnly, IsMembershipEditor, IsTaskEditorOrReadOnly
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()

    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsProjectEditorOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = ["id"]

    @action(detail=True, methods=["GET"])
    def memberships(self, request, pk=None):
        project = self.get_object()
        serializer = MembershipSerializer(
            Membership.objects.filter(project=project),
            many=True,
        )
        return Response(serializer.data)

    @action(detail=True, methods=["GET"])
    def tasks(self, request, pk = None):
        project = self.get_object()
        serializer = TaskSerializer(
            Task.objects.filter(
                project = project,
            ),
            many = True
        )
        return Response(serializer.data)


    def get_queryset(self):
        return Project.objects.filter(
            memberships__user=self.request.user,
            memberships__role__in=[
                "OWNER",
                "ADMIN",
                "MEMBER",
                "VIEWER",
            ],
        ).order_by("id")



class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsTaskEditorOrReadOnly]
    # permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TaskFilter
    ordering_fields = ["due_date", "created_at"]
    queryset = Task.objects.all().order_by("id")

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = "DONE"
        task.save(update_fields = ["status"])
        serializer = self.get_serializer(task)
        return Response(serializer.data)

    def get_queryset(self):
        if self.action == "list":
            return Task.objects.filter(
                project__memberships__user=self.request.user,
                project__memberships__role__in=["OWNER", "ADMIN", "MEMBER", "VIEWER"],
            ).select_related("project", "assignee")

        return Task.objects.all().order_by("id").select_related("project", "assignee")


class MembershipViewSet(viewsets.ModelViewSet):
    queryset = Membership.objects.all().order_by("project")
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsMembershipEditor]
    filter_backends = [OrderingFilter]
    ordering_fields = ["id"]

    @action(detail = True, methods=['post'])
    def leave(self, request, pk=None):
        membership = self.get_object()
        if membership.role == "OWNER":
            raise PermissionDenied("Owner should now leave the project with membership urls.")
        user = request.user
        if (user != membership.user ):
            raise PermissionDenied("You can not delete other user's role.")
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


    def get_queryset(self):
        if self.action == "list":
            return Membership.objects.filter(user=self.request.user)

        return Membership.objects.all().order_by("project")