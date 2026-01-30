from django.contrib import admin
from django.urls import path
from users import views

app_name = 'user'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing, name='landing'),
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout, name='logout'),
    path('add/', views.add_to_list, name='add_to_list'),
    path('my-books/', views.profile, name='my_books'),
]
