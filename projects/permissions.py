from rest_framework import permissions
from .models import Membership, Project, Task
from rest_framework.response import Response
from rest_framework import status


#   VIEWER  →  read only
#   MEMBER  →  read + create/edit/complete TASKS, can be an assignee
#   ADMIN   →  MEMBER + manage MEMBERSHIPS (add/remove/change non-owner roles)
#   OWNER   →  ADMIN + delete the PROJECT, manage admins/ownership
#   ANONYM    →  no access
#   Cumulative ladder; each role adds one power. Note the role set differs by 
#   resource: task-editing = MEMBER+, membership-managing = ADMIN+, project-delete = OWNER only.



class IsProjectEditorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False

        return Membership.objects.filter(
            user = request.user,
            project_id = obj.id,
            role__in = ["OWNER", ]
        ).exists()


    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        
        return True


    
class IsTaskEditorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        task = obj

        value =  Membership.objects.filter(
            user = request.user,
            project = task.project,
            role__in = ["OWNER", "ADMIN", "MEMBER"]
        ).exists()

        return value


    def has_permission(self, request, view):

        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method == "POST":
            project_id = request.data.get('project')
            try:
                project_id = int(project_id)
            except (TypeError, ValueError):
                return True

            if Project.objects.filter(id = project_id).exists() == False:
                return True
            
            if not project_id:
                if view.action != "complete":
                    return False
                return True
            
            membership =  Membership.objects.filter(
                            user = request.user,
                            project_id = project_id,
                            role__in = ["OWNER", "ADMIN", "MEMBER"]
                        )
            return membership.exists()
        
        return True




class IsMembershipEditor(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        if not request.user.is_authenticated:
            return False
        
        if request.method in ["POST"]:
            if view.action == "leave":
                return True
            
            project_id = request.data.get('project')
            if not project_id:
                return False
            return Membership.objects.filter(
                        user=request.user,
                        project_id=project_id,
                        role__in=["OWNER", "ADMIN", ]
                    ).exists()

        return True
        

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            if obj.user == request.user:
                return True
        
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method == 'DELETE':
            if obj.user == request.user:
                return obj.role != "OWNER"
            
            obj_membership = Membership.objects.filter(
                user = obj.user,
                project = obj.project
            ).first()
            req_membership = Membership.objects.filter(
                user = request.user,
                project = obj.project
            ).first()

            if req_membership.role == "ADMIN":
                if obj_membership.role == "OWNER" or obj_membership.role == "ADMIN":
                    return False
                else: 
                    return True
            if obj_membership.role == "OWNER": # this means that owner can not clean itself, 1 OWNER at least
                return obj_membership.role != "OWNER"

            return False


        if request.method == "PATCH":
            if obj.user == request.user:
                return obj.role != "OWNER"
            
            obj_membership = Membership.objects.filter(
                user = obj.user,
                project = obj.project
            ).first()
            req_membership = Membership.objects.filter(
                user = request.user,
                project = obj.project
            ).first()

            if req_membership.role == "ADMIN":
                if obj_membership.role == "OWNER" or obj_membership.role == "ADMIN":
                    return False
                return True
            
            if req_membership.role == "OWNER":
                return obj_membership.role != "OWNER"

            return False

        if view.action == "leave":

            if obj.user == request.user:
                return True
            return False               
            


            
        return Membership.objects.filter(
            user=request.user,
            project=obj.project,
            role__in=["OWNER", "ADMIN", ]
        ).exists()


    