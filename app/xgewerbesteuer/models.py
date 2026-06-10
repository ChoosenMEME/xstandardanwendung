from django.db import models


# Create your models here.
class xgewerbesteuer(models.Model):
    # Define your model fields here


    def __str__(self):
        return f"xgewerbesteuer {self.id}"
