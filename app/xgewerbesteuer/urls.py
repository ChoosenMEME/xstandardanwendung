from django.urls import path
from .views import xgewerbesteuer_default, xgewerbesteuer_pdf_report

urlpatterns = [
    path("", xgewerbesteuer_default, name="xgewerbesteuer_default"),
    path("pdf-bericht/", xgewerbesteuer_pdf_report, name="xgewerbesteuer_pdf_report"),
]
