from .models import Project, Task
from rest_framework import serializers
from django.utils import timezone
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "owner", "created_at"]
        read_only_fields = ["owner", "created_at"]

class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_username = serializers.CharField(source='assignee.username', read_only=True)

    class Meta:
        model = Task
        fields = ["id", "status", "title", "description", "created_at", "project", "due_date", "assignee", "project_name", "assignee_username"]
        read_only_fields = ["created_at", ]

    def validate_project(self, value):
        if value.owner == self.context["request"].user:
            return value
        else:
            raise serializers.ValidationError("no access to the project from this user")

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

        if assignee and project and assignee != project.owner:
            raise serializers.ValidationError({
                "assignee": "Assignee must be the project owner."
            })

        return attrs
