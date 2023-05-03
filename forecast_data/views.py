import os

from django.shortcuts import render
from django.views import View
from django.conf import settings

from forecast_data.models import system_state

# Create your views here.


class ForecastView(View):

    def get(self, request):
        data = dict()

        data['state_name'] = 'ECMWF_HRES_VIS'
        data['source'] = 'ECMWF_HRES'

        # need to override this with system_state only 
        data['init_time'] = system_state.objects.filter(
                                state_name=data['state_name'],
                                source__name=data['source']
                            ).values('init_time').first()['init_time']
        
        data['url_prefix'] = os.path.join(settings.FCST_JSON_URL_PREF,data['source'],data['init_time'])

        return render(request, 'forecast_view.html', data)


class NetcdfView(View):

    def get(self, request):
        return render(request, 'netcdf_view.html')
