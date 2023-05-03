import json

from django.shortcuts import render
from django.views import View

from datetime import datetime as dt

from django.db.models import Min, Max

from obs_data.models import station, obs_data

# Create your views here.


class HomeView(View):

    def get(self, request):
        data = {}
        data['stations'] = list(station.objects.all().values('name', 'lat', 'lon'))
        data['num_stations'] = station.objects.all().count()
        data['obs_count'] = obs_data.objects.all().count()
        data['period'] = self.construct_time_period_str()
        return render(request, 'home.html', data)

    def construct_time_period_str(self):
        period = obs_data.objects.all().aggregate(
            Min('start_time'), Max('end_time')
        )
        start__date = self.change_to_str(period['start_time__min'])
        end_date = self.change_to_str(period['end_time__max'])
        return f'{start__date} to {end_date}'
    
    def change_to_str(self, _date):
        return dt.strftime(_date, '%Y-%m-%d')

