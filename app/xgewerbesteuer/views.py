from django.shortcuts import render
from .models import xgewerbesteuer

# Create your views here.

def xgewerbesteuer_default(request):
    daten = xgewerbesteuer.objects.all()
    return render(request, "xgewerbesteuer_default.html", {"daten": daten})