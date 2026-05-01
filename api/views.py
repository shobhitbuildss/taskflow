from django.utils import timezone
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q

from .models import User, Project, ProjectMember, Task, Comment
from .serializers import (
    UserSerializer, LoginSerializer, ProjectSerializer, ProjectCreateSerializer,
    ProjectMemberSerializer, TaskSerializer, TaskListSerializer,
    CommentSerializer, DashboardSerializer, UserPublicSerializer
)
from .permissions import IsProjectAdminOrOwner, IsProjectMember, IsTaskProjectMember


# ─── Auth ───────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data['refresh'])
            token.blacklist()
        except Exception:
            pass
        return Response({'message': 'Logged out successfully.'})


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


# ─── Users ──────────────────────────────────────────────────────────────────

class UserListView(generics.ListAPIView):
    serializer_class = UserPublicSerializer
    queryset = User.objects.filter(is_active=True)
    filter_backends = [filters.SearchFilter]
    search_fields = ['email', 'username', 'first_name', 'last_name']


# ─── Projects ───────────────────────────────────────────────────────────────

class ProjectListCreateView(generics.ListCreateAPIView):

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectSerializer

    def get_queryset(self):
        user = self.request.user
        member_projects = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
        # FIX: Also include projects where the user has assigned tasks
        assigned_task_projects = Task.objects.filter(assignee=user).values_list('project_id', flat=True)
        qs = Project.objects.filter(
            Q(owner=user) | Q(id__in=member_projects) | Q(id__in=assigned_task_projects)
        ).distinct().prefetch_related('members__user', 'tasks')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        # Owner is automatically a member with admin role
        ProjectMember.objects.create(project=project, user=self.request.user, role='admin')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        project = Project.objects.prefetch_related('members__user', 'tasks').get(id=serializer.instance.id)
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        user = self.request.user
        member_projects = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
        # FIX: Also include projects where the user has assigned tasks
        assigned_task_projects = Task.objects.filter(assignee=user).values_list('project_id', flat=True)
        return Project.objects.filter(
            Q(owner=user) | Q(id__in=member_projects) | Q(id__in=assigned_task_projects)
        ).distinct()

    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if project.owner != request.user:
            try:
                m = ProjectMember.objects.get(project=project, user=request.user)
                if m.role != 'admin':
                    return Response({'error': 'Only admins can edit projects.'}, status=403)
            except ProjectMember.DoesNotExist:
                return Response({'error': 'Not a member.'}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        # FIX: Check ProjectMember role instead of request.user.role (which doesn't exist)
        if project.owner != request.user:
            try:
                m = ProjectMember.objects.get(project=project, user=request.user)
                if m.role != 'admin':
                    return Response({'error': 'Only the project owner or admin can delete this project.'}, status=403)
            except ProjectMember.DoesNotExist:
                return Response({'error': 'Not a member.'}, status=403)
        return super().destroy(request, *args, **kwargs)


# ─── Project Members ─────────────────────────────────────────────────────────

class ProjectMemberListView(generics.ListCreateAPIView):
    serializer_class = ProjectMemberSerializer

    def get_queryset(self):
        return ProjectMember.objects.filter(
            project_id=self.kwargs['project_id']
        ).select_related('user')

    def perform_create(self, serializer):
        project = Project.objects.get(id=self.kwargs['project_id'])
        if project.owner != self.request.user:
            try:
                m = ProjectMember.objects.get(project=project, user=self.request.user)
                if m.role != 'admin':
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('Only admins can add members.')
            except ProjectMember.DoesNotExist:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Not a member of this project.')
        serializer.save(project=project)


class ProjectMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectMemberSerializer

    def get_queryset(self):
        return ProjectMember.objects.filter(project_id=self.kwargs['project_id'])


# ─── Tasks ───────────────────────────────────────────────────────────────────

class TaskListCreateView(generics.ListCreateAPIView):

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TaskListSerializer
        return TaskSerializer

    def get_queryset(self):
        user = self.request.user
        member_projects = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
        accessible_projects = Project.objects.filter(
            Q(owner=user) | Q(id__in=member_projects)
        ).values_list('id', flat=True)

        qs = Task.objects.filter(
            Q(project_id__in=accessible_projects) | Q(assignee=user)
        ).select_related('assignee', 'project', 'created_by').distinct()

        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        priority = self.request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=priority)

        assignee = self.request.query_params.get('assignee')
        if assignee == 'me':
            qs = qs.filter(assignee=user)
        elif assignee:
            qs = qs.filter(assignee_id=assignee)

        overdue = self.request.query_params.get('overdue')
        if overdue == 'true':
            qs = qs.filter(due_date__lt=timezone.now().date()).exclude(status='done')

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        user = self.request.user
        member_projects = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
        accessible_projects = Project.objects.filter(
            Q(owner=user) | Q(id__in=member_projects)
        ).values_list('id', flat=True)
        return Task.objects.filter(
            Q(project_id__in=accessible_projects) | Q(assignee=user)
        ).select_related('assignee', 'project', 'created_by').prefetch_related(
            'comments__author'
        ).distinct()

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        if task.created_by != request.user and task.project.owner != request.user:
            try:
                m = ProjectMember.objects.get(project=task.project, user=request.user)
                if m.role not in ('admin',):
                    return Response({'error': 'Only task creator or project admin can delete tasks.'}, status=403)
            except ProjectMember.DoesNotExist:
                return Response({'error': 'Not a member.'}, status=403)
        return super().destroy(request, *args, **kwargs)


# ─── Comments ────────────────────────────────────────────────────────────────

class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(task_id=self.kwargs['task_id']).select_related('author')

    def perform_create(self, serializer):
        serializer.save(
            task_id=self.kwargs['task_id'],
            author=self.request.user
        )


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(task_id=self.kwargs['task_id'])

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user:
            try:
                m = ProjectMember.objects.get(project=comment.task.project, user=request.user)
                if m.role != 'admin':
                    return Response({'error': 'You can only delete your own comments.'}, status=403)
            except ProjectMember.DoesNotExist:
                return Response({'error': 'You can only delete your own comments.'}, status=403)
        return super().destroy(request, *args, **kwargs)


# ─── Dashboard ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    user = request.user
    member_projects = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
    assigned_project_ids = Task.objects.filter(assignee=user).values_list('project_id', flat=True)
    accessible_projects = Project.objects.filter(
        Q(owner=user) | Q(id__in=member_projects) | Q(id__in=assigned_project_ids)
    ).distinct()

    accessible_project_ids = accessible_projects.values_list('id', flat=True)
    all_tasks = Task.objects.filter(project_id__in=accessible_project_ids)
    today = timezone.now().date()

    my_tasks = Task.objects.filter(
        Q(project_id__in=accessible_project_ids) | Q(assignee=user),
        assignee=user,
    ).exclude(status='done').select_related('assignee', 'project').distinct()[:10]

    recent_projects = accessible_projects.prefetch_related(
        'members__user', 'tasks'
    ).order_by('-updated_at')[:5]

    data = {
        'total_projects': accessible_projects.count(),
        'total_tasks': all_tasks.count(),
        'completed_tasks': all_tasks.filter(status='done').count(),
        'overdue_tasks': all_tasks.filter(due_date__lt=today).exclude(status='done').count(),
        'in_progress_tasks': all_tasks.filter(status='in_progress').count(),
        'my_tasks': my_tasks,
        'recent_projects': recent_projects,
    }

    serializer = DashboardSerializer(data)
    return Response(serializer.data)