from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    xgewerbesteuer_assistant,
    xgewerbesteuer_csv_export,
    xgewerbesteuer_dashboard,
    xgewerbesteuer_delete_saved,
    xgewerbesteuer_demo,
    xgewerbesteuer_help,
    xgewerbesteuer_ics_export,
    xgewerbesteuer_load_saved,
    xgewerbesteuer_pdf_report,
    xgewerbesteuer_results,
    xgewerbesteuer_signup,
    xgewerbesteuer_upload,
)

urlpatterns = [
    path("", xgewerbesteuer_dashboard, name="xgewerbesteuer_dashboard"),
    path("upload/", xgewerbesteuer_upload, name="xgewerbesteuer_upload"),
    path("demo/", xgewerbesteuer_demo, name="xgewerbesteuer_demo"),
    path("ergebnis/", xgewerbesteuer_results, name="xgewerbesteuer_results"),
    path("ki-assistent/", xgewerbesteuer_assistant, name="xgewerbesteuer_assistant"),
    path("hilfe/", xgewerbesteuer_help, name="xgewerbesteuer_help"),
    path("gespeichert/laden/", xgewerbesteuer_load_saved, name="xgewerbesteuer_load_saved"),
    path("gespeichert/loeschen/", xgewerbesteuer_delete_saved, name="xgewerbesteuer_delete_saved"),
    path("csv-export/", xgewerbesteuer_csv_export, name="xgewerbesteuer_csv_export"),
    path("fristdatei.ics", xgewerbesteuer_ics_export, name="xgewerbesteuer_ics_export"),
    path("pdf-bericht/", xgewerbesteuer_pdf_report, name="xgewerbesteuer_pdf_report"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("registrieren/", xgewerbesteuer_signup, name="xgewerbesteuer_signup"),
    path(
        "passwort-vergessen/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "passwort-vergessen/gesendet/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "passwort-zuruecksetzen/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "passwort-zuruecksetzen/abgeschlossen/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]
