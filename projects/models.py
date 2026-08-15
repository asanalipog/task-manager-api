from django.db import models

from django.conf import settings
from rest_framework.exceptions import ValidationError

# Create your models here.

class Status(models.TextChoices):
    TODO = "TODO", "to do"
    DONE = "DONE", "done"
    IN_PROGRESS = "IN_PROGRESS", "in_progress"
    
    

class Project(models.Model):
    name = models.CharField(max_length=20)
    description = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["id"]
    def __str__(self):
        return self.name


class Task(models.Model):
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    title = models.CharField(max_length=20)
    description = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks", )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null = True, blank= True)

    def clean(self):
        if not Project.objects.filter(pk=self.project_id).exists():
            raise ValidationError({
                "project": "This project does not exist."
            })

    class Meta:
        ordering = ["id"]
    def __str__(self):
        return self.title

class Role(models.TextChoices):
    OWNER = "OWNER", "owner"
    ADMIN = "ADMIN", "admin"
    MEMBER = "MEMBER", "member"
    VIEWER = "VIEWER", "viewer"    

class Membership(models.Model):
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.CASCADE, related_name= "memberships")
    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"],
                name="unique_user_project"
            )
        ]
    def __str__(self):
            return self.role