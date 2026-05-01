from rest_framework.permissions import BasePermission
from .models import ProjectMember


class IsProjectAdminOrOwner(BasePermission):
    """Allow access only to project owner or project-level admin."""

    def has_object_permission(self, request, view, obj):
        # obj is a Project
        if obj.owner == request.user:
            return True
        try:
            membership = ProjectMember.objects.get(project=obj, user=request.user)
            return membership.role == 'admin'
        except ProjectMember.DoesNotExist:
            return False


class IsProjectMember(BasePermission):
    """Allow access to any project member."""

    def has_object_permission(self, request, view, obj):
        # obj is a Project
        if obj.owner == request.user:
            return True
        return ProjectMember.objects.filter(project=obj, user=request.user).exists()


class IsGlobalAdmin(BasePermission):
    """Only global admins."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsTaskProjectMember(BasePermission):
    """Allow access to task if user is a member of the task's project."""

    def has_object_permission(self, request, view, obj):
        # obj is a Task
        project = obj.project
        if project.owner == request.user:
            return True
        return ProjectMember.objects.filter(project=project, user=request.user).exists()
