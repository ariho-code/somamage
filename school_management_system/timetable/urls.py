from django.urls import path
from academics import views as academics_views

urlpatterns = [
    # Timetable views are in academics app
    path("", academics_views.timetable_list, name="timetable_list"),
    path("create/", academics_views.timetable_create, name="timetable_create"),
]

