# Source - https://stackoverflow.com/q/50563326
# Posted by Rakmo, modified by community. See post 'Timeline' for change history
# Retrieved 2026-07-27, License - CC BY-SA 4.0

from .models import Task, Project
import django_filters


class TaskFilter(django_filters.FilterSet):
    project = django_filters.ModelChoiceFilter(
      queryset=lambda request: Project.objects.filter(owner=request.user))
    class Meta:
        model = Task
        fields = ['status', 'project']


    

    
