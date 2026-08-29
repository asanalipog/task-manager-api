from django.db import models

from django.conf import settings
from rest_framework.exceptions import ValidationError
from django.db.models import CheckConstraint, Q, F
from django.db.models.functions import TruncDate
# Create your models here.

class Status(models.TextChoices):
    TODO = "TODO", "to do"
    DONE = "DONE", "done"
    IN_PROGRESS = "IN_PROGRESS", "in_progress"
    
    

class Project(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["id"]
    def __str__(self):
        return self.name


class Task(models.Model):
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=1000)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks", )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null = True, blank= True)


    class Meta:
        indexes = [models.Index(fields=["due_date"])]
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                check = Q(due_date__isnull=True) | Q(due_date__gte = TruncDate('created_at')),
                name = "date_checker"
            ),
            models.CheckConstraint(
                check = Q(status__in = Status.values),
                name = "status_checker"
            )
        ]
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
            models.CheckConstraint(
                check = Q(role__in=Role.values),
                name = "role_checker"
            ),
            models.UniqueConstraint(
                fields=["user", "project"],
                name="unique_user_project"
            )
        ]
    def __str__(self):
            return self.role