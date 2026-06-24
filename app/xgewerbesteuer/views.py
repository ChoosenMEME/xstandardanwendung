from django.shortcuts import render
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError


def get_local_name(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def clean_text(text):
    if text and text.strip():
        return " ".join(text.split())
    return None


def find_first_text(root, keywords):
    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        for keyword in keywords:
            if keyword.lower() in tag_name:
                value = clean_text(element.text)

                if value:
                    return value

    return "Nicht gefunden"


def find_multiple_texts(root, keywords):
    results = []

    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        for keyword in keywords:
            if keyword.lower() in tag_name:
                value = clean_text(element.text)

                if value and value not in results:
                    results.append(value)

    if results:
        return ", ".join(results)

    return "Nicht gefunden"


def extract_bescheid_data(root):
    element_count = sum(1 for _ in root.iter())

    return {
        "Wurzelelement": get_local_name(root.tag),
        "Anzahl XML-Elemente": element_count,
        "Gemeinde / Kommune": find_first_text(root, ["gemeinde", "kommune"]),
        "Steuerjahr / Erhebungszeitraum": find_first_text(root, ["steuerjahr", "erhebungszeitraum", "zeitraum", "jahr"]),
        "Zahlbetrag": find_first_text(root, ["zahlbetrag", "zahlung", "nachzahlung", "erstattung", "betrag"]),
        "Gewerbesteuermessbetrag": find_first_text(root, ["messbetrag"]),
        "Hebesatz": find_first_text(root, ["hebesatz"]),
        "Fälligkeiten": find_multiple_texts(root, ["faelligkeit", "fälligkeit", "faellig", "fällig", "frist"]),
    }


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
                root = ElementTree.fromstring(xml_data)
                uploaded_file.seek(0)

                context["uploaded_file_name"] = uploaded_file.name
                context["uploaded_file_size"] = uploaded_file.size
                context["validation_success"] = "Die Datei wurde erfolgreich geprüft und ist grundsätzlich XML-konform."
                context["extracted_data"] = extract_bescheid_data(root)

            except (ParseError, DefusedXmlException):
                context["upload_error"] = "Die Datei ist nicht XML-konform oder enthält unsichere XML-Inhalte und konnte nicht verarbeitet werden."

            except Exception:
                context["upload_error"] = "Die Datei konnte nicht gelesen werden."

    return render(request, "xgewerbesteuer_default.html", context)

sdfjmdf;kjghsdf;gjdnb
