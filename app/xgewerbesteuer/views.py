"""View-Funktionen fuer die XGewerbesteuer-App."""

from pathlib import Path

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from .calculations import build_plausibility_check
from .ratelimit import rate_limit
from .comparisons import (
    build_change_comparison,
    build_historical_development,
    build_message_type_comparison_notice,
    build_multi_bescheid_comparison,
    build_period_comparison_notice,
    sort_bescheid_records_chronologically,
)
from .constants import RESULT_SESSION_KEY
from .forms import SignupForm
from .models import SavedBescheidUpload
from .services.bescheid import (
    build_due_date_calendar,
    build_liquidity_impact,
    build_notice_area,
    build_status_indicator,
    build_unexpected_import_error_result,
    create_saved_upload,
    get_saved_uploads_for_request,
    prepare_download_sessions,
    process_uploaded_bescheid,
)
from .services.assistant import (
    ASSISTANT_UNAVAILABLE_MESSAGE,
    AssistantInputError,
    answer_assistant_question,
    build_assistant_ui_context,
    get_assistant_mode,
    get_assistant_mode_label,
)
from .services.assistant_providers import AssistantProviderError
from .services.export import (
    CSV_EXPORT_SESSION_KEY,
    ICS_EXPORT_SESSION_KEY,
    PDF_REPORT_SESSION_KEY,
    create_csv_export,
    create_ics_export,
    create_pdf_report,
)
from .services.privacy import anonymize_result_context

# Die Demo-Dateien liegen bewusst ausserhalb von tests/, weil das
# Test-Verzeichnis per .dockerignore nicht ins Release-Image gelangt.
DEMO_FIXTURE_DIR = Path(__file__).resolve().parent / "demo_data"
DEMO_FIXTURE_FILES = [
    (
        "GEWST-0010-12345678-1234567890000-2022-01-15_"
        "00000000-0000-0000-0000-000000000102.xml"
    ),
    (
        "GEWST-0010-12345678-1234567890000-2023-01-15_"
        "00000000-0000-0000-0000-000000000103.xml"
    ),
]


def xgewerbesteuer_dashboard(request):
    saved_uploads = get_saved_uploads_for_request(request)
    return render(request, "xgewerbesteuer/dashboard.html", {
        "saved_uploads": saved_uploads,
    })


def _build_result_session_data(results, upload_errors=None, is_demo=False, demo_notice=None):
    # Gemeinsame Sortierregel mit der Mehrjahrestabelle (siehe comparisons):
    # unbekannte Zeitraeume vorn, letzter Eintrag = aktuellster Bescheid.
    sorted_bescheide = sort_bescheid_records_chronologically(results)
    current_bescheid = sorted_bescheide[-1]

    session_data = {
        "current_bescheid": current_bescheid,
        "all_bescheide_count": len(sorted_bescheide),
        "previous_bescheid": None,
        "period_comparison_notice": None,
        "change_comparison_items": None,
        "comparison_errors": upload_errors or [],
        "multi_bescheid_comparison": None,
        "historical_development": None,
        "saved_upload_success": None,
        "saved_upload_error": None,
        "is_demo": is_demo,
        "demo_notice": demo_notice,
    }

    if len(sorted_bescheide) >= 2:
        previous_bescheid = sorted_bescheide[-2]
        session_data["previous_bescheid"] = previous_bescheid
        message_type_comparison_notice = build_message_type_comparison_notice(
            current_bescheid,
            previous_bescheid,
        )
        period_comparison_notice = build_period_comparison_notice(
            current_bescheid["tax_period"],
            previous_bescheid["tax_period"],
        )
        session_data["period_comparison_notice"] = (
            message_type_comparison_notice or period_comparison_notice
        )
        session_data["change_comparison_items"] = build_change_comparison(
            current_bescheid,
            previous_bescheid,
        )

        multi_bescheid_comparison = build_multi_bescheid_comparison(sorted_bescheide)

        if multi_bescheid_comparison:
            session_data["multi_bescheid_comparison"] = multi_bescheid_comparison
            session_data["historical_development"] = build_historical_development(
                multi_bescheid_comparison["records"]
            )

    return session_data


def _process_uploaded_files(uploaded_files):
    """Verarbeitet Uploads zu (gueltige Bescheide, Fehlerliste).

    Gemeinsame Fehlerbehandlung fuer Upload- und Demo-View: Auch unerwartete
    Fehler werden als kontrollierte Fehlerantwort mit Fehler-ID gemeldet.
    """
    results = []
    upload_errors = []

    for uploaded_file in uploaded_files:
        try:
            result = process_uploaded_bescheid(uploaded_file)
        except Exception as error:
            result = build_unexpected_import_error_result(error)

        if result["is_valid"]:
            results.append(result["bescheid"])
        else:
            upload_errors.append({
                "file_name": uploaded_file.name,
                "message": result["message"],
                "error_id": result.get("error_id"),
                "details": result.get("details", []),
            })

    return results, upload_errors


def xgewerbesteuer_upload(request):
    if request.method != "POST":
        return render(request, "xgewerbesteuer/upload.html")

    for session_key in (
        PDF_REPORT_SESSION_KEY,
        CSV_EXPORT_SESSION_KEY,
        ICS_EXPORT_SESSION_KEY,
    ):
        request.session.pop(session_key, None)

    uploaded_files = request.FILES.getlist("bescheide")
    should_save_upload = request.POST.get("save_upload") == "on"

    if not uploaded_files:
        return render(request, "xgewerbesteuer/upload.html", {
            "upload_error": "Bitte wählen Sie mindestens eine XML-Datei aus.",
        })

    results, upload_errors = _process_uploaded_files(uploaded_files)

    if not results:
        return render(request, "xgewerbesteuer/upload.html", {
            "upload_error": "Keine der hochgeladenen Dateien konnte verarbeitet werden.",
            "upload_errors": upload_errors,
        })

    session_data = _build_result_session_data(results, upload_errors)
    current_bescheid = session_data["current_bescheid"]

    if should_save_upload and not request.user.is_authenticated:
        session_data["saved_upload_error"] = (
            "Bitte melden Sie sich an, um Auswertungen zu speichern."
        )
    elif should_save_upload:
        context_for_save = _build_result_context(session_data)
        try:
            create_saved_upload(request, current_bescheid, context_for_save)
            session_data["saved_upload_success"] = (
                "Die Auswertung wurde gespeichert und kann in Ihrem "
                "Benutzerkonto erneut geöffnet werden."
            )
        except DatabaseError:
            session_data["saved_upload_error"] = (
                "Die Auswertung konnte nicht gespeichert werden. "
                "Bitte versuchen Sie es später erneut."
            )

    request.session[RESULT_SESSION_KEY] = session_data
    return redirect("xgewerbesteuer_results")


def xgewerbesteuer_demo(request):
    uploaded_files = []
    upload_errors = []

    for fixture_name in DEMO_FIXTURE_FILES:
        fixture_path = DEMO_FIXTURE_DIR / fixture_name

        try:
            fixture_content = fixture_path.read_bytes()
        except OSError:
            upload_errors.append({
                "file_name": fixture_name,
                "message": "Die Demo-Datei konnte nicht gelesen werden.",
                "details": [],
            })
            continue

        uploaded_files.append(
            SimpleUploadedFile(
                fixture_name,
                fixture_content,
                content_type="application/xml",
            )
        )

    results, processing_errors = _process_uploaded_files(uploaded_files)
    upload_errors.extend(processing_errors)

    if not results:
        return render(request, "xgewerbesteuer/upload.html", {
            "upload_error": (
                "Demo-Beispielfall konnte nicht geladen werden. "
                "Bitte versuchen Sie es später erneut oder laden Sie eine eigene XML-Datei hoch."
            ),
            "upload_errors": upload_errors,
        })

    request.session[RESULT_SESSION_KEY] = _build_result_session_data(
        results,
        upload_errors,
        is_demo=True,
        demo_notice=(
            "Demo-Beispielfall mit fiktiven, anonymisierten Testdaten. "
            "Es wurden keine echten Bescheiddaten verarbeitet."
        ),
    )

    return redirect("xgewerbesteuer_results")


def xgewerbesteuer_results(request):
    session_data = request.session.get(RESULT_SESSION_KEY)

    if not session_data:
        return redirect("xgewerbesteuer_upload")

    context = _build_display_context(session_data)

    prepare_download_sessions(request, context)

    return render(request, "xgewerbesteuer/results.html", context)


def xgewerbesteuer_toggle_privacy(request):
    """Schaltet den Datenschutzmodus um — bewusst nur per POST.

    Ein GET-Parameter waere weder CSRF-geschuetzt noch frei von
    Seiteneffekten (Prefetching/Link-Vorschau koennte den Modus umschalten),
    deshalb aendert diese View den Session-Zustand nur auf POST und leitet
    danach per Post/Redirect/Get zurueck auf die Ergebnisseite.
    """
    if request.method != "POST":
        return redirect("xgewerbesteuer_results")

    session_data = request.session.get(RESULT_SESSION_KEY)

    if not session_data:
        return redirect("xgewerbesteuer_upload")

    session_data["privacy_mode_enabled"] = request.POST.get("privacy") == "1"
    request.session[RESULT_SESSION_KEY] = session_data

    # Export-Daten sofort neu aufbauen, damit Downloads nicht bis zum
    # naechsten Aufruf der Ergebnisseite den alten Maskierungszustand behalten.
    prepare_download_sessions(request, _build_display_context(session_data))

    return redirect("xgewerbesteuer_results")


def _build_display_context(session_data):
    """Baut den Anzeigenkontext und wendet den Datenschutzmodus an.

    Alle Views, die Ergebnisdaten anzeigen, exportieren oder an den
    KI-Assistenten weitergeben, muessen diesen Helper verwenden, damit der
    Datenschutzmodus nicht durch einzelne Views umgangen werden kann.
    """
    context = _build_result_context(session_data)

    if session_data.get("privacy_mode_enabled"):
        context = anonymize_result_context(context)

    return context


def _build_result_context(session_data):
    current_bescheid = session_data["current_bescheid"]
    change_comparison_items = session_data.get("change_comparison_items")

    context = {
        "current_bescheid": current_bescheid,
        "uploaded_file_name": current_bescheid["file_name"],
        "uploaded_file_size": current_bescheid["file_size"],
        "message_type": current_bescheid.get("message_type"),
        "message_type_label": current_bescheid.get("message_type_label"),
        "message_type_summary": current_bescheid.get("message_type_summary"),
        "all_bescheide_count": session_data.get("all_bescheide_count", 1),
        "summary_items": current_bescheid["summary_items"],
        "calculation_explanation": current_bescheid["calculation_explanation"],
        "advance_payments": current_bescheid["advance_payments"],
        "payment_classification": current_bescheid["payment_classification"],
        "due_date_calendar": build_due_date_calendar(current_bescheid),
        "plausibility_check": build_plausibility_check(current_bescheid),
        "liquidity_impact": build_liquidity_impact(current_bescheid),
        "is_demo": session_data.get("is_demo", False),
        "demo_notice": session_data.get("demo_notice"),
        "privacy_mode_enabled": session_data.get("privacy_mode_enabled", False),
    }

    if session_data.get("previous_bescheid"):
        context["previous_bescheid"] = session_data["previous_bescheid"]

    if session_data.get("period_comparison_notice"):
        context["period_comparison_notice"] = session_data["period_comparison_notice"]

    if change_comparison_items:
        context["change_comparison_items"] = change_comparison_items

    if session_data.get("comparison_errors"):
        context["multi_bescheid_upload_errors"] = session_data["comparison_errors"]

    if session_data.get("multi_bescheid_comparison"):
        context["multi_bescheid_comparison"] = session_data["multi_bescheid_comparison"]

    if session_data.get("historical_development"):
        context["historical_development"] = session_data["historical_development"]

    context["notice_items"] = build_notice_area(
        current_bescheid,
        change_comparison_items,
    )
    context["status_indicator"] = build_status_indicator(
        current_bescheid,
        context.get("notice_items"),
        change_comparison_items,
    )

    if session_data.get("saved_upload_success"):
        context["saved_upload_success"] = session_data["saved_upload_success"]

    if session_data.get("saved_upload_error"):
        context["saved_upload_error"] = session_data["saved_upload_error"]

    return context


# Jede Assistant-Anfrage blockiert einen Worker fuer bis zu
# AI_ASSISTANT_TIMEOUT_SECONDS; ohne Limit liesse sich der Worker-Pool
# guenstig lahmlegen und der LLM-Endpunkt anonym fluten.
@rate_limit("assistant", max_requests=20, window_seconds=300)
def xgewerbesteuer_assistant(request):
    if request.method != "POST":
        return redirect("xgewerbesteuer_dashboard")

    session_data = request.session.get(RESULT_SESSION_KEY)
    question = request.POST.get("assistant_question", "")
    result_context = None
    wants_json = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
    )

    if session_data:
        result_context = _build_display_context(session_data)
        prepare_download_sessions(request, result_context)

    mode = get_assistant_mode(result_context)
    mode_label = get_assistant_mode_label(result_context)

    try:
        answer = answer_assistant_question(question, result_context)
        if wants_json:
            return JsonResponse({
                "ok": True,
                "answer": answer,
                "error": "",
                "mode": mode,
                "mode_label": mode_label,
            })

        context = result_context or {}
        context.update(
            build_assistant_ui_context(
                answer=answer,
                question=question,
                result_context=result_context,
            )
        )
    except AssistantInputError as exc:
        user_error_message = exc.args[0]
        if wants_json:
            return JsonResponse({
                "ok": False,
                "answer": "",
                "error": user_error_message,
                "mode": mode,
                "mode_label": mode_label,
            })

        context = result_context or {}
        context.update(
            build_assistant_ui_context(
                error=user_error_message,
                question=question,
                result_context=result_context,
            )
        )
    except AssistantProviderError:
        if wants_json:
            return JsonResponse({
                "ok": False,
                "answer": "",
                "error": ASSISTANT_UNAVAILABLE_MESSAGE,
                "mode": mode,
                "mode_label": mode_label,
            })

        context = result_context or {}
        context.update(
            build_assistant_ui_context(
                error=ASSISTANT_UNAVAILABLE_MESSAGE,
                question=question,
                result_context=result_context,
            )
        )

    if result_context:
        return render(request, "xgewerbesteuer/results.html", context)

    return render(request, "xgewerbesteuer/dashboard.html", context)


def _parse_saved_upload_id(request):
    """Liest die Upload-ID aus dem POST; None bei fehlendem/ungueltigem Wert.

    Ohne diese Pruefung wuerde ein nicht-numerischer Wert im ORM-Filter einen
    ValueError und damit einen 500er ausloesen.
    """
    try:
        return int(request.POST.get("saved_upload_id", ""))
    except (TypeError, ValueError):
        return None


@login_required
def xgewerbesteuer_load_saved(request):
    if request.method != "POST":
        return redirect("xgewerbesteuer_dashboard")

    saved_upload_id = _parse_saved_upload_id(request)

    if saved_upload_id is None:
        messages.error(
            request,
            "Die gespeicherte Auswertung konnte nicht gefunden werden.",
        )
        return redirect("xgewerbesteuer_dashboard")

    saved_upload = SavedBescheidUpload.objects.filter(
        id=saved_upload_id,
        user=request.user,
    ).first()

    if saved_upload is None:
        messages.error(
            request,
            "Die gespeicherte Auswertung konnte nicht gefunden werden.",
        )
        return redirect("xgewerbesteuer_dashboard")

    current_bescheid = (
        saved_upload.result_data.get("current_bescheid")
        or saved_upload.to_bescheid_dict()
    )

    request.session[RESULT_SESSION_KEY] = {
        "current_bescheid": current_bescheid,
        "all_bescheide_count": 1,
        "previous_bescheid": None,
        "period_comparison_notice": None,
        "change_comparison_items": None,
        "comparison_bescheide": [],
        "comparison_errors": [],
        "multi_bescheid_comparison": None,
        "historical_development": None,
        "saved_upload_success": "Die gespeicherte Auswertung wurde erneut geöffnet.",
        "saved_upload_error": None,
    }

    return redirect("xgewerbesteuer_results")


@login_required
def xgewerbesteuer_delete_saved(request):
    if request.method != "POST":
        return redirect("xgewerbesteuer_dashboard")

    saved_upload_id = _parse_saved_upload_id(request)

    if saved_upload_id is None:
        messages.error(
            request,
            "Die gespeicherte Auswertung konnte nicht gefunden werden.",
        )
        return redirect("xgewerbesteuer_dashboard")

    deleted_count, _ = SavedBescheidUpload.objects.filter(
        id=saved_upload_id,
        user=request.user,
    ).delete()

    if deleted_count:
        messages.success(
            request,
            "Die gespeicherte Auswertung wurde gelöscht.",
        )
    else:
        messages.error(
            request,
            "Die gespeicherte Auswertung konnte nicht gefunden werden.",
        )

    return redirect("xgewerbesteuer_dashboard")


def xgewerbesteuer_signup(request):
    if request.user.is_authenticated:
        return redirect("xgewerbesteuer_dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(
                request,
                "Ihr Konto wurde erstellt. Sie sind jetzt angemeldet.",
            )
            return redirect("xgewerbesteuer_dashboard")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})


def xgewerbesteuer_help(request):
    return render(request, "xgewerbesteuer/help.html")


def xgewerbesteuer_pdf_report(request):
    report_data = request.session.get(PDF_REPORT_SESSION_KEY)

    if not report_data:
        return HttpResponse(
            "Es liegen keine Daten für einen PDF-Bericht vor. "
            "Bitte laden Sie zuerst einen gültigen Bescheid hoch.",
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    pdf_content = create_pdf_report(report_data)

    response = HttpResponse(pdf_content, content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="gewerbesteuerbescheid-bericht.pdf"'
    )

    return response


def xgewerbesteuer_csv_export(request):
    export_data = request.session.get(CSV_EXPORT_SESSION_KEY)

    if not export_data:
        return HttpResponse(
            "Es liegen keine Daten für einen CSV-Export vor. "
            "Bitte laden Sie zuerst einen gültigen Bescheid hoch.",
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    csv_content = create_csv_export(export_data)

    response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        'attachment; filename="gewerbesteuerbescheid-export.csv"'
    )

    return response


def xgewerbesteuer_ics_export(request):
    ics_content = request.session.get(ICS_EXPORT_SESSION_KEY)

    if not ics_content:
        return HttpResponse(
            "Es liegen keine verwertbaren Fälligkeitstermine für eine Fristdatei vor. "
            "Bitte laden Sie zuerst einen gültigen Bescheid mit Fälligkeiten hoch.",
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    response = HttpResponse(ics_content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="fristtermine.ics"'

    return response
