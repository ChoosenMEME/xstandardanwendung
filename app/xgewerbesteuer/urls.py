from django.urls import path

from .views import (
    xgewerbesteuer_assistant,
    xgewerbesteuer_csv_export,
    xgewerbesteuer_dashboard,
    xgewerbesteuer_delete_saved,
    xgewerbesteuer_help,
    xgewerbesteuer_ics_export,
    xgewerbesteuer_load_saved,
    xgewerbesteuer_pdf_report,
    xgewerbesteuer_results,
    xgewerbesteuer_upload,
)

urlpatterns = [
    path("", xgewerbesteuer_dashboard, name="xgewerbesteuer_dashboard"),
    path("upload/", xgewerbesteuer_upload, name="xgewerbesteuer_upload"),
    path("ergebnis/", xgewerbesteuer_results, name="xgewerbesteuer_results"),
    path("ki-assistent/", xgewerbesteuer_assistant, name="xgewerbesteuer_assistant"),
    path("hilfe/", xgewerbesteuer_help, name="xgewerbesteuer_help"),
    path("gespeichert/laden/", xgewerbesteuer_load_saved, name="xgewerbesteuer_load_saved"),
    path("gespeichert/loeschen/", xgewerbesteuer_delete_saved, name="xgewerbesteuer_delete_saved"),
    path("csv-export/", xgewerbesteuer_csv_export, name="xgewerbesteuer_csv_export"),
    path("fristdatei.ics", xgewerbesteuer_ics_export, name="xgewerbesteuer_ics_export"),
    path("pdf-bericht/", xgewerbesteuer_pdf_report, name="xgewerbesteuer_pdf_report"),
]
