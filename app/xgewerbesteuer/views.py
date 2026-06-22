from django.shortcuts import render


def xgewerbesteuer_default(request):
    context = {}

    if request.method == "POST":
        uploaded_file = request.FILES.get("bescheid")

        if uploaded_file:
            context["uploaded_file_name"] = uploaded_file.name
            context["uploaded_file_size"] = uploaded_file.size
        else:
            context["upload_error"] = "Bitte wählen Sie eine XML-Datei aus."

    return render(request, "xgewerbesteuer_default.html", context)
