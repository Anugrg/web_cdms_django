from datetime import datetime 

from netCDF4 import Dataset, num2date

from django.core.management.base import BaseCommand, CommandError
from forecast_data.models import *
from sricdms.settings import ECMWF_HRES_NC


class Command(BaseCommand):

    help = 'Update state of ECMWF_HRES_NC'
    state_name = "ECMWF_HRES_NC"
    source = "ECMWF_HRES"
    source_obj = forecast_source.objects.get(name=source)

    def add_arguments(self, parser):
        parser.add_argument('date', type=str, help="forecast date in yyyymmdd format")

    def handle(self, *args, **options):
        dateobj = datetime.strptime(options['date'], '%Y%m%d')
        self.update_state(dateobj)


    def update_state(self, dateobj):
        ncfile_path = dateobj.strftime(ECMWF_HRES_NC)
        print(ncfile_path)
        ncfile = Dataset(ncfile_path,'r')
        var_list = []
        var = {}
        info = {}
        lat_bounds = {}
        lon_bounds = {}

        for val, val1 in ncfile.variables.items():
            if val1.name == 'latitude' or val1.name == 'longitude' or val1.name == 'time':
                print(val1.name)
                continue
            var["name"] = val1.name    
            var["fullname"] = val1.long_name
            var["unit"] = val1.units
            var_list.append(var)
            var = {}

        info["variables"] = var_list 

        lat_min = ncfile.variables['latitude'][:][-1]    
        lat_max = ncfile.variables['latitude'][:][0]

        lon_min = ncfile.variables['longitude'][:][0]
        lon_max = ncfile.variables['longitude'][:][-1]

        lat_bounds["lat_min"] = str(lat_min)
        lat_bounds["lat_max"] = str(lat_max)
        lon_bounds["lon_max"] = str(lon_max)
        lon_bounds["lon_min"] = str(lon_min)

        info["lat_bounds"] = lat_bounds
        info["lon_bounds"] = lon_bounds 

        date = num2date(ncfile.variables['time'][:].min(), ncfile.variables['time'].units).strftime('%Y%m%d_%H') # using min() to find init date
        ncfile.close()

        if system_state.objects.filter(state_name=self.state_name, source=self.source_obj).exists():
            print('updating existing record...')
            state = system_state.objects.get(state_name=self.state_name, source=self.source_obj)
            state.init_time= date
            state.info = info
            state.save()
        else:
            print("Creating new record...")
            system_state(state_name=self.state_name, init_time=date, source=self.source_obj, info=info).save()
            
            
        


                




        
