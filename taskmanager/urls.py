from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, FileResponse
from django.conf import settings
import os


def health(request):
    return JsonResponse({'status': 'ok', 'message': 'TaskManager API is running'})


def frontend(request):
    index_path = os.path.join(settings.BASE_DIR, '..', 'frontend', 'index.html')
    return FileResponse(open(index_path, 'rb'), content_type='text/html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('health/', health),
    path('', frontend),
]