from django.urls import path
from .views import xgewerbesteuer_default 

urlpatterns = [
    path("", xgewerbesteuer_default, name="xgewerbesteuer_default"),
]
