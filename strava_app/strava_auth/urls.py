from django.urls import path

from . import views

app_name = 'strava'

urlpatterns = [
    path('success/', views.success_auth, name='success'),
    path('forbidden/', views.auth_forbidden, name='forbidden'),
    path('canceled', views.auth_canceled, name='canceled'),
]
