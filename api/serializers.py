from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Project, ProjectMember, Task, Comment


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name',
                  'full_name', 'role', 'avatar', 'password', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserPublicSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'full_name', 'role', 'avatar']


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')
        return {'user': user}


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserPublicSerializer(read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    task_count = serializers.ReadOnlyField()
    completed_task_count = serializers.ReadOnlyField()
    progress = serializers.ReadOnlyField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'status', 'owner', 'members',
                  'created_at', 'updated_at', 'due_date', 'color',
                  'task_count', 'completed_task_count', 'progress']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'status', 'due_date', 'color']
        read_only_fields = ['id']


class CommentSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'author', 'content', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']


class TaskSerializer(serializers.ModelSerializer):
    assignee = UserPublicSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assignee',
        write_only=True, allow_null=True, required=False
    )
    created_by = UserPublicSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    is_overdue = serializers.ReadOnlyField()
    tag_list = serializers.ReadOnlyField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'project', 'assignee', 'assignee_id',
                  'created_by', 'priority', 'status', 'due_date', 'created_at',
                  'updated_at', 'tags', 'tag_list', 'comments', 'comment_count', 'is_overdue']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_comment_count(self, obj):
        return obj.comments.count()


class TaskListSerializer(serializers.ModelSerializer):
    assignee = UserPublicSerializer(read_only=True)
    is_overdue = serializers.ReadOnlyField()
    tag_list = serializers.ReadOnlyField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'project', 'assignee', 'priority', 'status',
                  'due_date', 'created_at', 'tag_list', 'comment_count', 'is_overdue']

    def get_comment_count(self, obj):
        return obj.comments.count()


class DashboardSerializer(serializers.Serializer):
    total_projects = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    in_progress_tasks = serializers.IntegerField()
    my_tasks = TaskListSerializer(many=True)
    recent_projects = ProjectSerializer(many=True)
