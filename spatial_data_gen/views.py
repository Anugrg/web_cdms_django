from django.shortcuts import render
from django.views import View
# Create your views here.


class SpatialView(View):

    def get(self, request):
        return render(request, 'spat_data_gen.html')