from .models import Project, Task, Membership
from django.db import transaction
from rest_framework import serializers
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from .tasks import send_task_created_email, send_assignee_email
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "created_at"]
        read_only_fields = ["created_at"]

    def create(self, validated_data):
        user = self.context['request'].user
        
        with transaction.atomic():
            project = Project.objects.create(**validated_data)
            
            Membership.objects.create(
                project=project,
                user=user,
                role="OWNER"
            )
            
        return project


class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_username = serializers.CharField(source='assignee.username', read_only=True)

    class Meta:
        model = Task
        fields = ["id", "status", "title", "description", "created_at", "project", "due_date", "assignee", "project_name", "assignee_username"]
        read_only_fields = ["created_at", ]

    def create(self, validated_data):
        user = self.context['request'].user
        with transaction.atomic():
            task = Task.objects.create(**validated_data)
            
            transaction.on_commit(lambda: send_task_created_email.delay(user.email, user.username))

            if task.assignee:
                transaction.on_commit(lambda: send_assignee_email.delay(task.id))

        return task

    def validate_due_date(self, value):
        if value:
            if value < timezone.localdate():
                raise serializers.ValidationError(
                    {"due_date": "Due date cannot be in the past."}
                )
        return value


    def validate(self, attrs):
        project = attrs.get("project", self.instance.project if self.instance else None)
        assignee = attrs.get("assignee", self.instance.assignee if self.instance else None)
        role = Membership.objects.filter(user = self.context["request"].user , project = project).values_list("role", flat = True).first()
        assignee_role = Membership.objects.filter(user = assignee, project = project).values_list("role", flat = True).first()
        if assignee_role not in ["OWNER", "ADMIN", "MEMBER"] and assignee:
            raise serializers.ValidationError({
                "assignee": "Assignee must be the connected with project."
            })
        if role not in ["OWNER", "ADMIN", "MEMBER"]:
            raise PermissionDenied("You don't have permission to modify this project.")
        return attrs


class MembershipSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    user_name = serializers.CharField(source = "user.username", read_only = True)
    class Meta:
        model = Membership
        fields = ["id", "role", "project", "user", "project_name", "user_name"]

#     def validate_role(self, value):
#         request = self.context.get("request")
#         if not request or not request.user:
#             return value
        
#         user = request.user

#         project = (
#             self.instance.project
#             if self.instance
#             else self.initial_data.get("project")
# )

#         requester_membership = Membership.objects.filter(
#             user = user,
#             project = project
#         ).first()

#         if not requester_membership:
#             raise PermissionDenied("You are not a member of this project.")
        
#         if value == "OWNER":
#             raise PermissionDenied("There should be no more than 1 owner of a project")
        
#         if requester_membership.role == "ADMIN" and value == "ADMIN":
#             raise PermissionDenied("Admin can not assign new admins or owners")
        
#         return value

    def validate(self, attrs):
        project = attrs.get("project", self.instance.project if self.instance else None)
        user = attrs.get("user", self.instance.user if self.instance else None)
        role = attrs.get("role", self.instance.role if self.instance else None)

        requester = self.context["request"].user
        role_requester = Membership.objects.filter(user = self.context["request"].user , project = project).values_list("role", flat = True).first()

        if not role_requester:
            raise PermissionDenied("You are not a member of this project.")

        if role == "OWNER":
            raise PermissionDenied("Owner can not be changed.")

        if role_requester == "ADMIN":
            if attrs["role"] == "OWNER" or attrs["role"] == "ADMIN":
                raise PermissionDenied("You dont have access to do that.")
            if role == "ADMIN":
                raise PermissionDenied("Same level of access.")

        return attrs


        
