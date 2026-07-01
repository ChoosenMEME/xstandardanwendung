"""Datei-, XML- und XSD-Validierung fuer XGewerbesteuer-Bescheide."""

from dataclasses import asdict, dataclass
from pathlib import Path

from lxml import etree


SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

XSD_SCHEMA_FILES = [
    "xunternehmen-gewerbesteuer.xsd",
    "gewerbesteuer.xsd",
]

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class UploadValidationIssue:
    """Strukturierter, nutzersicherer Validierungsfehler fuer Uploads."""

    code: str
    group: str
    message: str
    next_action: str
    detail: str = ""

    def as_dict(self):
        return asdict(self)


def build_validation_issue(code, detail=""):
    issue_definitions = {
        "invalid_file_type": {
            "group": "Falscher Dateityp",
            "message": "Die hochgeladene Datei muss eine XML-Datei sein.",
            "next_action": "Bitte wählen Sie eine XML-Datei mit der Endung .xml aus.",
        },
        "file_too_large": {
            "group": "Datei zu groß",
            "message": "Die hochgeladene Datei ist zu groß.",
            "next_action": (
                "Bitte laden Sie eine kleinere XML-Datei hoch oder exportieren "
                "Sie den Bescheid erneut ohne Anhänge."
            ),
        },
        "malformed_xml": {
            "group": "Nicht wohlgeformtes XML",
            "message": "Die XML-Datei ist nicht wohlgeformt.",
            "next_action": (
                "Bitte exportieren Sie die Datei erneut aus dem Fachverfahren "
                "oder prüfen Sie, ob die Datei vollständig übertragen wurde."
            ),
        },
        "unsafe_xml": {
            "group": "Unsichere XML-Inhalte",
            "message": (
                "Die XML-Datei enthält aus Sicherheitsgründen nicht erlaubte "
                "XML-Inhalte."
            ),
            "next_action": (
                "Bitte verwenden Sie eine XGewerbesteuer-Datei ohne DOCTYPE- "
                "oder Entity-Deklarationen."
            ),
        },
        "xsd_validation_error": {
            "group": "XSD-Validierungsfehler",
            "message": (
                "Die Datei entspricht nicht dem erwarteten XGewerbesteuer-1.4-Schema."
            ),
            "next_action": (
                "Bitte prüfen Sie, ob es sich um eine XGewerbesteuer-1.4-Datei "
                "handelt, oder exportieren Sie den Bescheid erneut."
            ),
        },
        "unsupported_message_type": {
            "group": "Nicht unterstützter Nachrichtentyp",
            "message": "Der Nachrichtentyp der XML-Datei wird derzeit nicht unterstuetzt.",
            "next_action": (
                "Bitte laden Sie einen unterstützten XGewerbesteuer-Bescheid hoch."
            ),
        },
        "read_error": {
            "group": "Unerwarteter Lesefehler",
            "message": "Die Datei konnte nicht verarbeitet werden.",
            "next_action": "Bitte prüfen Sie die Datei und versuchen Sie es erneut.",
        },
    }
    definition = issue_definitions[code]

    return UploadValidationIssue(
        code=code,
        group=definition["group"],
        message=definition["message"],
        next_action=definition["next_action"],
        detail=detail,
    )


def get_upload_issue(uploaded_file):
    if not uploaded_file.name.lower().endswith(".xml"):
        return build_validation_issue("invalid_file_type")

    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        return build_validation_issue(
            "file_too_large",
            detail=f"Maximal erlaubt sind {MAX_UPLOAD_SIZE_BYTES // 1024 // 1024} MB.",
        )

    return None


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


def get_upload_error(uploaded_file):
    issue = get_upload_issue(uploaded_file)

    return issue.message if issue else None
