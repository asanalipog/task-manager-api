from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import AbstractUser





class Note(models.Model):
    title = models.CharField(max_length=50)
    body = models.TextField()
    
    def __str__(self):
        return self.title

class User(AbstractUser):
    email = models.EmailField(null=True, blank=True)
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return self.username