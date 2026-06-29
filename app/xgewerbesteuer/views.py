"""View-Funktionen fuer die XGewerbesteuer-App."""

from django.contrib import messages
from django.db import DatabaseError
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .calculations import build_plausibility_check
from .comparisons import (
    build_change_comparison,
    build_historical_development,
    build_multi_bescheid_comparison,
    build_period_comparison_notice,
    extract_sort_year,
)
from .services.bescheid import (
    build_due_date_calendar,
    build_liquidity_impact,
    build_notice_area,
    build_status_indicator,
    create_saved_upload,
    get_saved_uploads_for_request,
    prepare_download_sessions,
    process_uploaded_bescheid,
)
from .services.export import (
    CSV_EXPORT_SESSION_KEY,
    ICS_EXPORT_SESSION_KEY,
    PDF_REPORT_SESSION_KEY,
    create_csv_export,
    create_ics_export,
    create_pdf_report,
)

RESULT_SESSION_KEY = "xgewerbesteuer_result"


def xgewerbesteuer_dashboard(request):
    saved_uploads = get_saved_uploads_for_request(request)
    return render(request, "xgewerbesteuer/dashboard.html", {
        "saved_uploads": saved_uploads,
    })


def _sort_bescheide_chronologically(bescheide):
    def sort_key(bescheid):
        tax_period = bescheid.get("tax_period", "")
        sort_year = extract_sort_year(tax_period)

        # Unknown periods come first so the last entry remains the newest
        # reliably dated Bescheid selected for summaries and exports.
        return (
            sort_year != 9999,
            sort_year,
            tax_period,
            bescheid.get("file_name", ""),
        )

    return sorted(
        bescheide,
        key=sort_key,
    )


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

    results = []
    upload_errors = []

    for uploaded_file in uploaded_files:
        result = process_uploaded_bescheid(uploaded_file)
        if result["is_valid"]:
            results.append(result["bescheid"])
        else:
            upload_errors.append({
                "file_name": uploaded_file.name,
                "message": result["message"],
            })

    if not results:
        return render(request, "xgewerbesteuer/upload.html", {
            "upload_error": "Keine der hochgeladenen Dateien konnte verarbeitet werden.",
            "upload_errors": upload_errors,
        })

    sorted_bescheide = _sort_bescheide_chronologically(results)
    current_bescheid = sorted_bescheide[-1]

    session_data = {
        "current_bescheid": current_bescheid,
        "all_bescheide_count": len(sorted_bescheide),
        "previous_bescheid": None,
        "period_comparison_notice": None,
        "change_comparison_items": None,
        "comparison_errors": upload_errors,
        "multi_bescheid_comparison": None,
        "historical_development": None,
        "saved_upload_success": None,
        "saved_upload_error": None,
    }

    if len(sorted_bescheide) >= 2:
        previous_bescheid = sorted_bescheide[-2]
        session_data["previous_bescheid"] = previous_bescheid
        session_data["period_comparison_notice"] = build_period_comparison_notice(
            current_bescheid["tax_period"],
            previous_bescheid["tax_period"],
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

    if should_save_upload:
        context_for_save = _build_result_context(session_data)
        try:
            create_saved_upload(request, current_bescheid, context_for_save)
            session_data["saved_upload_success"] = (
                "Die Auswertung wurde gespeichert und kann in dieser "
                "Browser-Session erneut geöffnet werden."
            )
        except DatabaseError:
            session_data["saved_upload_error"] = (
                "Die Auswertung konnte nicht gespeichert werden. "
                "Bitte versuchen Sie es später erneut."
            )

    request.session[RESULT_SESSION_KEY] = session_data
    return redirect("xgewerbesteuer_results")


def xgewerbesteuer_results(request):
    session_data = request.session.get(RESULT_SESSION_KEY)

    if not session_data:
        return redirect("xgewerbesteuer_upload")

    context = _build_result_context(session_data)
    prepare_download_sessions(request, context)

    return render(request, "xgewerbesteuer/results.html", context)


def _build_result_context(session_data):
    current_bescheid = session_data["current_bescheid"]
    change_comparison_items = session_data.get("change_comparison_items")

    context = {
        "current_bescheid": current_bescheid,
        "uploaded_file_name": current_bescheid["file_name"],
        "uploaded_file_size": current_bescheid["file_size"],
        "all_bescheide_count": session_data.get("all_bescheide_count", 1),
        "summary_items": current_bescheid["summary_items"],
        "calculation_explanation": current_bescheid["calculation_explanation"],
        "advance_payments": current_bescheid["advance_payments"],
        "payment_classification": current_bescheid["payment_classification"],
        "due_date_calendar": build_due_date_calendar(current_bescheid),
        "plausibility_check": build_plausibility_check(current_bescheid),
        "liquidity_impact": build_liquidity_impact(current_bescheid),
        "validation_success": (
            "Die Datei wurde erfolgreich geprüft und entspricht dem erwarteten "
            f"XGewerbesteuer-Schema. Verwendetes Schema: {current_bescheid['schema_name']}"
        ),
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


def xgewerbesteuer_load_saved(request):
    if request.method != "POST":
        return redirect("xgewerbesteuer_dashboard")

    session_key = request.session.session_key
    saved_upload_id = request.POST.get("saved_upload_id")

    if not session_key or not saved_upload_id:
        messages.error(
            request,
            "Die gespeicherte Auswertung konnte nicht gefunden werden.",
        )
        return redirect("xgewerbesteuer_dashboard")

    from .models import SavedBescheidUpload

    saved_upload = SavedBescheidUpload.objects.filter(
        id=saved_upload_id,
        session_key=session_key,
    ).first()

    if saved_upload is None:
        messages.error(
            request,
            "Die gespeicherte Auswertung konnte nicht gefunden werden.",
        )
        return redirect("xgewerbesteuer_dashboard")

    current_bescheid = saved_upload.result_data.get("current_bescheid") or {
        "file_name": saved_upload.file_name,
        "file_size": saved_upload.file_size,
        "schema_name": "",
        "municipality": saved_upload.municipality or "Nicht gefunden",
        "tax_period": saved_upload.tax_period or "Nicht gefunden",
        "amount_due": saved_upload.amount_due or "Nicht gefunden",
        "trade_tax_assessment_amount": (
            saved_upload.trade_tax_assessment_amount or "Nicht gefunden"
        ),
        "assessment_rate": saved_upload.assessment_rate or "Nicht gefunden",
        "due_dates": saved_upload.due_dates or "Nicht gefunden",
        "advance_payments": saved_upload.advance_payments or [],
        "summary_items": saved_upload.summary_items or [],
        "calculation_explanation": saved_upload.result_data.get("calculation_explanation", {}),
        "payment_classification": {
            "type": saved_upload.payment_type or "Nicht gefunden",
            "message": "",
        },
    }

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


def xgewerbesteuer_delete_saved(request):
    if request.method != "POST":
        return redirect("xgewerbesteuer_dashboard")

    session_key = request.session.session_key
    saved_upload_id = request.POST.get("saved_upload_id")

    if not session_key or not saved_upload_id:
        messages.error(
            request,
            "Die gespeicherte Auswertung konnte nicht gefunden werden.",
        )
        return redirect("xgewerbesteuer_dashboard")

    from .models import SavedBescheidUpload

    deleted_count, _ = SavedBescheidUpload.objects.filter(
        id=saved_upload_id,
        session_key=session_key,
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
