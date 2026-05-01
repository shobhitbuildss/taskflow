from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.MeView.as_view(), name='me'),

    # Users
    path('users/', views.UserListView.as_view(), name='user-list'),

    # Projects
    path('projects/', views.ProjectListCreateView.as_view(), name='project-list'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('projects/<int:project_id>/members/', views.ProjectMemberListView.as_view(), name='project-members'),
    path('projects/<int:project_id>/members/<int:pk>/', views.ProjectMemberDetailView.as_view(), name='project-member-detail'),

    # Tasks
    path('tasks/', views.TaskListCreateView.as_view(), name='task-list'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),

    # Comments
    path('tasks/<int:task_id>/comments/', views.CommentListCreateView.as_view(), name='comment-list'),
    path('tasks/<int:task_id>/comments/<int:pk>/', views.CommentDetailView.as_view(), name='comment-detail'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
]
