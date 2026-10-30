from django.contrib import admin
from django.urls import path
from election import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('polling-unit/', views.polling_unit_results, name='polling_unit_results'),
    path('lga-results/', views.lga_results, name='lga_results'),
    path('enter-results/', views.enter_results, name='enter_results'),
]
