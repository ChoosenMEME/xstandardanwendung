import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_uploads_without_user(apps, schema_editor):
    """Entfernt verwaiste Alt-Eintraege ohne Nutzerkonto.

    Seit dem Nutzerkonten-Feature entstehen gespeicherte Auswertungen nur
    noch fuer angemeldete Nutzer; Eintraege ohne user stammen aus der
    session-basierten Uebergangszeit und sind ueber die UI nicht mehr
    erreichbar.
    """
    SavedBescheidUpload = apps.get_model("xgewerbesteuer", "SavedBescheidUpload")
    SavedBescheidUpload.objects.filter(user__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('xgewerbesteuer', '0002_savedbescheidupload_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(
            delete_uploads_without_user,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name='savedbescheidupload',
            name='session_key',
        ),
        migrations.AlterField(
            model_name='savedbescheidupload',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='saved_bescheid_uploads',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
