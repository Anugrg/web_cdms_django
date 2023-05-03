from django.shortcuts import render
from django.views import View
# Create your views here.


class BufrView(View):

    def get(self, request):
        return render(request, 'bufr_view.html')
