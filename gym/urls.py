from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('', RedirectView.as_view(pattern_name='home'), name='root'),
    path('home/', views.home, name='home'),
    path('section/<str:section_key>/', views.section, name='section'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('analytics/', views.analytics, name='analytics'),
    path('member/<int:pk>/', views.member_profile, name='member_profile'),
    
    # AJAX endpoints for CRUD operations
    path('ajax/create/<str:entity_key>/', views.ajax_create, name='ajax_create'),
    path('ajax/update/<str:entity_key>/<int:pk>/', views.ajax_update, name='ajax_update'),
    path('ajax/delete/<str:entity_key>/<int:pk>/', views.ajax_delete, name='ajax_delete'),
]
