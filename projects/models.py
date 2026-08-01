from django.db import models

from django.conf import settings

# Create your models here.

class Status(models.TextChoices):
    TODO = "TODO", "to do"
    DONE = "DONE", "done"
    IN_PROGRESS = "IN_PROGRESS", "in_progress"
    
    

class Project(models.Model):
    name = models.CharField(max_length=20)
    description = models.CharField(max_length=50)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    title = models.CharField(max_length=20)
    description = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null = True, blank= True)
    
    def __str__(self):
        return self.title
    
