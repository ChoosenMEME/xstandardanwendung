from django.shortcuts import render
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError


def xgewerbesteuer_default(request):
    context = {}

    if request.method == "POST":
        uploaded_file = request.FILES.get("bescheid")

        if not uploaded_file:
            context["upload_error"] = "Bitte wählen Sie eine XML-Datei aus."

        elif not uploaded_file.name.lower().endswith(".xml"):
            context["upload_error"] = "Die hochgeladene Datei muss eine XML-Datei sein."

        else:
            try:
                xml_data = uploaded_file.read()
                ElementTree.fromstring(xml_data)
                uploaded_file.seek(0)

                context["uploaded_file_name"] = uploaded_file.name
                context["uploaded_file_size"] = uploaded_file.size
                context["validation_success"] = "Die Datei wurde erfolgreich geprüft und ist grundsätzlich XML-konform."

            except (ParseError, DefusedXmlException):
                context["upload_error"] = "Die Datei ist nicht XML-konform oder enthält unsichere XML-Inhalte und konnte nicht verarbeitet werden."

            except Exception:
                context["upload_error"] = "Die Datei konnte nicht gelesen werden."

    return render(request, "xgewerbesteuer_default.html", context)
