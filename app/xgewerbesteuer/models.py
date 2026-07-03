from django.conf import settings
from django.db import models


class SavedBescheidUpload(models.Model):
    session_key = models.CharField(max_length=80, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name="saved_bescheid_uploads",
    )
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    municipality = models.CharField(max_length=255, blank=True)
    tax_period = models.CharField(max_length=255, blank=True)
    amount_due = models.CharField(max_length=100, blank=True)
    payment_type = models.CharField(max_length=100, blank=True)
    trade_tax_assessment_amount = models.CharField(max_length=100, blank=True)
    assessment_rate = models.CharField(max_length=100, blank=True)
    due_dates = models.TextField(blank=True)
    advance_payments = models.JSONField(default=list, blank=True)
    summary_items = models.JSONField(default=list, blank=True)
    result_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return f"{self.tax_period or 'Ohne Zeitraum'} - {self.file_name}"

    def to_bescheid_dict(self):
        """Rekonstruiert die Bescheid-Struktur aus den einzelnen DB-Feldern.

        Fallback fuer aeltere gespeicherte Auswertungen, deren result_data
        noch keinen vollstaendigen current_bescheid enthaelt. Einzige Quelle
        fuer diese Rekonstruktion, damit View- und Service-Schicht nicht
        auseinanderdriften.
        """
        return {
            "file_name": self.file_name,
            "file_size": self.file_size,
            "schema_name": "",
            "message_type": None,
            "message_type_label": None,
            "message_type_category": "unknown",
            "message_type_summary": "",
            "supports_comparison": False,
            "municipality": self.municipality or None,
            "tax_period": self.tax_period or None,
            "amount_due": self.amount_due or None,
            "trade_tax_assessment_amount": (
                self.trade_tax_assessment_amount or None
            ),
            "assessment_rate": self.assessment_rate or None,
            "due_dates": self.due_dates or None,
            "advance_payments": self.advance_payments or [],
            "summary_items": self.summary_items or [],
            "calculation_explanation": self.result_data.get(
                "calculation_explanation", {}
            ),
            "payment_classification": {
                "type": self.payment_type or None,
                "message": "",
            },
        }
