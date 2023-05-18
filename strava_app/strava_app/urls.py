from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('social_django.urls', namespace='social')),
    path('strava/', include('strava_auth.urls', namespace='strava')),
    path('admin/', admin.site.urls),
]
