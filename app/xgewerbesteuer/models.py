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
