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


def extract_municipality(root):
    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        if tag_name == "kommune":
            for child in element.iter():
                child_tag_name = get_local_name(child.tag).lower()

                if child_tag_name in ["namebehoerde", "namebehörde", "name"]:
                    value = clean_text(child.text)

                    if value:
                        return value

    return find_first_text(
        root,
        [
            "namebehoerde",
            "namebehörde",
            "behoerde",
            "behörde",
            "gemeinde",
            "kommune",
            "gemeindename",
            "gebietskörperschaft",
            "gebietskoerperschaft",
            "steuerberechtigtegemeinde",
            "hebeberechtigtegemeinde",
        ],
    )


def extract_tax_period(root):
    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        if tag_name in ["erhebungszeitraum", "zeitraum"]:
            bezugsjahr = None
            beginn = None
            ende = None
            quartal = None

            for child in element.iter():
                child_tag_name = get_local_name(child.tag).lower()
                value = clean_text(child.text)

                if not value:
                    continue

                if child_tag_name in ["bezugsjahr", "steuerjahr", "jahr"]:
                    bezugsjahr = value
                elif child_tag_name == "beginn":
                    beginn = value
                elif child_tag_name == "ende":
                    ende = value
                elif child_tag_name == "quartal":
                    quartal = value

            if bezugsjahr and quartal:
                return f"{bezugsjahr}, Quartal {quartal}"

            if beginn and ende:
                return f"{beginn} bis {ende}"

            if bezugsjahr:
                return bezugsjahr

    return find_first_text(
        root,
        [
            "steuerjahr",
            "bezugsjahr",
            "erhebungsjahr",
            "veranlagungsjahr",
            "erhebungszeitraum",
        ],
    )


def extract_trade_tax_assessment_amount(root):
    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        if tag_name in [
            "gewerbesteuermessbetrag",
            "steuermessbetrag",
            "messbetrag",
            "festgesetztergewerbesteuermessbetrag",
        ]:
            value = clean_text(element.text)

            if value:
                return value

    return find_first_text(
        root,
        [
            "gewerbesteuermessbetrag",
            "steuermessbetrag",
            "messbetrag",
            "festgesetztergewerbesteuermessbetrag",
        ],
    )


def extract_assessment_rate(root):
    for element in root.iter():
        tag_name = get_local_name(element.tag).lower()

        if tag_name in [
            "hebesatz",
            "gewerbesteuerhebesatz",
            "hebensatz",
            "kommunalerhebesatz",
        ]:
            value = clean_text(element.text)

            if value:
                return value

    return find_first_text(
        root,
        [
            "hebesatz",
            "gewerbesteuerhebesatz",
            "hebensatz",
            "kommunalerhebesatz",
        ],
    )


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

                root = ElementTree.fromstring(xml_data)

                municipality = extract_municipality(root)
                tax_period = extract_tax_period(root)
                trade_tax_assessment_amount = extract_trade_tax_assessment_amount(root)
                assessment_rate = extract_assessment_rate(root)

                is_valid, schema_name, schema_error = validate_xml_against_xsd(xml_data)

                context["uploaded_file_name"] = uploaded_file.name
                context["uploaded_file_size"] = uploaded_file.size
                context["municipality"] = municipality
                context["tax_period"] = tax_period
                context["trade_tax_assessment_amount"] = trade_tax_assessment_amount
                context["assessment_rate"] = assessment_rate

                if is_valid:
                    context["validation_success"] = (
                        "Die Datei wurde erfolgreich geprüft und entspricht dem erwarteten "
                        f"XGewerbesteuer-Schema. Verwendetes Schema: {schema_name}"
                    )
                else:
                    context["validation_success"] = (
                        "Die Datei ist grundsätzlich XML-konform. Zentrale Bescheiddaten wurden ausgelesen. "
                        "Die vollständige XSD-Validierung ist jedoch nicht erfolgreich gewesen."
                    )

            except (ParseError, DefusedXmlException):
                context["upload_error"] = (
                    "Die Datei ist nicht XML-konform oder enthält unsichere XML-Inhalte und konnte nicht verarbeitet werden."
                )

            except Exception:
                context["upload_error"] = "Die Datei konnte nicht gelesen werden."

    return render(request, "xgewerbesteuer_default.html", context)
