"""View-Funktionen fuer die XGewerbesteuer-App."""

from django.db import DatabaseError
from django.http import HttpResponse
from django.shortcuts import render

from .calculations import build_plausibility_check
from .comparisons import (
    build_change_comparison,
    build_historical_development,
    build_multi_bescheid_comparison,
    build_multi_bescheid_upload_errors,
    build_period_comparison_notice,
)
from .services.bescheid import (
    build_due_date_calendar,
    build_notice_area,
    build_status_indicator,
    create_saved_upload,
    get_saved_uploads_for_request,
    handle_saved_upload_action,
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


def xgewerbesteuer_pdf_report(request):
    report_data = request.session.get(PDF_REPORT_SESSION_KEY)

    if not report_data:
        return HttpResponse(
            "Es liegen keine Daten für einen PDF-Bericht vor. Bitte laden Sie zuerst einen gültigen Bescheid hoch.",
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    pdf_content = create_pdf_report(report_data)

    response = HttpResponse(pdf_content, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="gewerbesteuerbescheid-bericht.pdf"'

    return response


def xgewerbesteuer_csv_export(request):
    export_data = request.session.get(CSV_EXPORT_SESSION_KEY)

    if not export_data:
        return HttpResponse(
            "Es liegen keine Daten für einen CSV-Export vor. Bitte laden Sie zuerst einen gültigen Bescheid hoch.",
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    csv_content = create_csv_export(export_data)

    response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="gewerbesteuerbescheid-export.csv"'

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


def xgewerbesteuer_default(request):
    context = {}

    if request.method == "POST":
        handled_saved_action, saved_action_context = handle_saved_upload_action(request)

        if handled_saved_action:
            context.update(saved_action_context)
            context["saved_uploads"] = get_saved_uploads_for_request(request)

            return render(request, "xgewerbesteuer_default.html", context)

        request.session.pop(PDF_REPORT_SESSION_KEY, None)
        request.session.pop(CSV_EXPORT_SESSION_KEY, None)
        request.session.pop(ICS_EXPORT_SESSION_KEY, None)

        uploaded_file = request.FILES.get("bescheid")
        previous_uploaded_file = request.FILES.get("vorjahresbescheid")
        comparison_uploaded_files = request.FILES.getlist("vergleichsbescheide")
        should_save_upload = request.POST.get("save_upload") == "on"

        if not uploaded_file:
            context["upload_error"] = "Bitte wählen Sie eine XML-Datei aus."

        else:
            current_result = process_uploaded_bescheid(uploaded_file)

            if not current_result["is_valid"]:
                if current_result["error_type"] == "validation":
                    context["validation_error"] = current_result["message"]
                else:
                    context["upload_error"] = current_result["message"]

            else:
                current_bescheid = current_result["bescheid"]

                context["current_bescheid"] = current_bescheid
                context["uploaded_file_name"] = current_bescheid["file_name"]
                context["uploaded_file_size"] = current_bescheid["file_size"]
                context["summary_items"] = current_bescheid["summary_items"]
                context["calculation_explanation"] = current_bescheid["calculation_explanation"]
                context["advance_payments"] = current_bescheid["advance_payments"]
                context["payment_classification"] = current_bescheid["payment_classification"]
                context["due_date_calendar"] = build_due_date_calendar(current_bescheid)
                context["plausibility_check"] = build_plausibility_check(current_bescheid)
                context["validation_success"] = (
                    "Die Datei wurde erfolgreich geprüft und entspricht dem erwarteten "
                    f"XGewerbesteuer-Schema. Verwendetes Schema: {current_bescheid['schema_name']}"
                )

                if previous_uploaded_file:
                    previous_result = process_uploaded_bescheid(previous_uploaded_file)

                    if not previous_result["is_valid"]:
                        if previous_result["error_type"] == "validation":
                            context["previous_validation_error"] = (
                                f"Vorjahresbescheid: {previous_result['message']}"
                            )
                        else:
                            context["previous_upload_error"] = (
                                f"Vorjahresbescheid: {previous_result['message']}"
                            )

                    else:
                        previous_bescheid = previous_result["bescheid"]

                        context["previous_bescheid"] = previous_bescheid
                        context["period_comparison_notice"] = build_period_comparison_notice(
                            current_bescheid["tax_period"],
                            previous_bescheid["tax_period"],
                        )
                        context["change_comparison_items"] = build_change_comparison(
                            current_bescheid,
                            previous_bescheid,
                        )

                if comparison_uploaded_files:
                    comparison_results = [
                        {
                            "file_name": comparison_file.name,
                            "result": process_uploaded_bescheid(comparison_file),
                        }
                        for comparison_file in comparison_uploaded_files
                    ]
                    valid_comparison_bescheide = [
                        item["result"]["bescheid"]
                        for item in comparison_results
                        if item["result"].get("is_valid")
                    ]
                    multi_bescheid_comparison = build_multi_bescheid_comparison(
                        valid_comparison_bescheide
                    )
                    context["multi_bescheid_upload_errors"] = (
                        build_multi_bescheid_upload_errors(comparison_results)
                    )

                    if multi_bescheid_comparison:
                        context["multi_bescheid_comparison"] = multi_bescheid_comparison
                        context["historical_development"] = (
                            build_historical_development(
                                multi_bescheid_comparison["records"]
                            )
                        )

                context["notice_items"] = build_notice_area(
                    current_bescheid,
                    context.get("change_comparison_items"),
                )
                context["status_indicator"] = build_status_indicator(
                    current_bescheid,
                    context.get("notice_items"),
                    context.get("change_comparison_items"),
                )
                prepare_download_sessions(request, context)

                if should_save_upload:
                    try:
                        create_saved_upload(request, current_bescheid, context)
                        context["saved_upload_success"] = (
                            "Die Auswertung wurde gespeichert und kann in dieser "
                            "Browser-Session erneut geöffnet werden."
                        )
                    except DatabaseError:
                        context["saved_upload_error"] = (
                            "Die Auswertung konnte nicht gespeichert werden. "
                            "Bitte versuchen Sie es später erneut."
                        )

    context["saved_uploads"] = get_saved_uploads_for_request(request)
    return render(request, "xgewerbesteuer_default.html", context)
