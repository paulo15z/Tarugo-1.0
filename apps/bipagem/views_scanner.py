# apps/bipagem/views_scanner.py
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin


class BipagemScannerView(LoginRequiredMixin, View):
    """
    View para servir a interface de bipagem (scanner).
    Acesso: /bipagem/scanner/
    """
    login_url = 'login'
    
    def get(self, request):
        return render(request, 'bipagem_scanner.html')
