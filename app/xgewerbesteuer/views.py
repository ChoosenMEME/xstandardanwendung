from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from django.shortcuts import render
from lxml import etree


SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

XSD_SCHEMA_FILES = [
    "xunternehmen-gewerbesteuer.xsd",
    "gewerbesteuer.xsd",
]


def validate_xml_against_xsd(xml_data):
    validation_errors = []

    xml_parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=False,
    )

    try:
        xml_document = etree.fromstring(xml_data, parser=xml_parser)
    except etree.XMLSyntaxError:
        return False, None, "Die XML-Datei ist nicht wohlgeformt."

    for schema_file_name in XSD_SCHEMA_FILES:
        schema_path = SCHEMA_DIR / schema_file_name

        if not schema_path.exists():
            validation_errors.append(f"{schema_file_name}: Schema-Datei wurde nicht gefunden.")
            continue

        try:
            schema_document = etree.parse(str(schema_path))
            schema = etree.XMLSchema(schema_document)
            schema.assertValid(xml_document)

            return True, schema_file_name, None

        except etree.DocumentInvalid as error:
            last_error = error.error_log.last_error

            if last_error is not None:
                validation_errors.append(f"{schema_file_name}: {last_error.message}")
            else:
                validation_errors.append(f"{schema_file_name}: XML passt nicht zum Schema.")

        except etree.XMLSchemaParseError:
            validation_errors.append(f"{schema_file_name}: Schema konnte nicht gelesen werden.")

        except OSError:
            validation_errors.append(f"{schema_file_name}: Schema-Datei konnte nicht geöffnet werden.")

    if validation_errors:
        return False, None, " | ".join(validation_errors)

    return False, None, "Es konnte keine passende XSD-Schema-Datei für die Validierung gefunden werden."


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

                is_valid, schema_name, schema_error = validate_xml_against_xsd(xml_data)

                if is_valid:
                    context["uploaded_file_name"] = uploaded_file.name
                    context["uploaded_file_size"] = uploaded_file.size
                    context["validation_success"] = (
                        "Die Datei wurde erfolgreich geprüft und entspricht dem erwarteten "
                        f"XGewerbesteuer-Schema. Verwendetes Schema: {schema_name}"
                    )
                else:
                    context["upload_error"] = (
                        "Die Datei ist zwar grundsätzlich XML-konform, entspricht aber nicht dem erwarteten "
                        "XGewerbesteuer-Schema. Bitte laden Sie einen gültigen XGewerbesteuer-Bescheid hoch."
                    )

            except (ParseError, DefusedXmlException):
                context["upload_error"] = (
                    "Die Datei ist nicht XML-konform oder enthält unsichere XML-Inhalte und konnte nicht verarbeitet werden."
                )

            except Exception:
                context["upload_error"] = "Die Datei konnte nicht gelesen werden."

    return render(request, "xgewerbesteuer_default.html", context)
