import os
import io
import pytz
from datetime import datetime 

import numpy as np
from netCDF4 import Dataset
from sricdms.settings import ECMWF_HRES_NC

from django.shortcuts import render
from django.views import View
from django.conf import settings
from django.http.response import FileResponse, JsonResponse

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
        data['data'] = get_netcdf_info('ECMWF_HRES_NC')

        return render(request, 'forecast_view.html', data)


class get_netcdf_subset_ecmwf_hres(View):

    state_name = "ECMWF_HRES_NC"

    def get(self, request):
        param_list = request.GET.getlist('variables')
        left_lon, right_lon = float(request.GET.get('left-lon')), float(request.GET.get('right-lon'))
        top_lat, bottom_lat = float(request.GET.get('top-lat')), float(request.GET.get('bottom-lat'))
        if not param_list:
            return JsonResponse({'error': 'query missing'})

        return get_subset_netcdf(
            param_list,
            top_lat,
            bottom_lat,
            right_lon,
            left_lon,
            self.state_name,
            ECMWF_HRES_NC
        )


def get_netcdf_info(state_name):
    data = dict()
    params = dict()
    data['sys_state'] = system_state.objects.get(state_name=state_name)
    data['nc_date'] = (
        datetime.strptime(data['sys_state'].init_time, '%Y%m%d_%H')
    ).strftime('%d-%m-%Y')
    info = system_state.objects.get(state_name=state_name).info
    for var in info['variables']:
        if (var['name'] == 'latitude' or
                var['name'] == 'longitude' or
                var['name'] == 'time'):
            continue

        params[var['name']] = var['fullname']

    data['nc_params'] = params

    data['state_name'] = state_name
    data['lat_bounds'] = info['lat_bounds']
    data['lon_bounds'] = info['lon_bounds']
    if state_name == 'ECMWF_SEAS_NC':
        data['state_is_recent'] = (
            data['sys_state'].updated_at.month == today_start().month
        )
    else:
        data['state_is_recent'] = (
            data['sys_state'].updated_at > today_start()
        )

    return data

def today_start():
    today = datetime.today()
    today_start = datetime(today.year, today.month, today.day)
    project_tz = pytz.timezone(settings.TIME_ZONE)
    
    return project_tz.localize(today_start)


def get_subset_netcdf(
        sel_params,
        top_lat,
        bottom_lat,
        right_lon,
        left_lon,
        state_name,
        ECMWF_NC,
        req_date=None
):
    if req_date:
        update = req_date
    else:
        update = system_state.objects.get(state_name=state_name).init_time

    nc_origin_path = (
        datetime.strptime(update, '%Y%m%d_%H')
    ).strftime(ECMWF_NC)

    try:
        nc_origin = Dataset(nc_origin_path)
    except FileNotFoundError:
        data = {}
        data['error'] = 'No file error'
        data['message'] = 'Requested file does not exist'
        return JsonResponse(data)

    # memory is essentially gets ignored if the file format is NETCDF4
    nc_subset = Dataset('subset.nc', 'w', format="NETCDF4", memory=0)

    lats = nc_origin.variables['latitude'][:]
    lons = nc_origin.variables['longitude'][:]
    times = nc_origin.variables['time'][:]

    lat_indices, lon_indices = np.where((lats >= bottom_lat) & (lats <= top_lat)), np.where((lons >= left_lon) & (lons <= right_lon))
    lat_crop, lon_crop = lats[lat_indices], lons[lon_indices]
    try:
        latli, latui = lat_indices[0][0], lat_indices[0][-1]
        lonli, lonui = lon_indices[0][0], lon_indices[0][-1]
    except IndexError:
        return JsonResponse(
            {
                'error': 'Out of scope',
                'message': 'Selected region not available'
            }
        )

    # dimensions of the subset
    nc_subset.createDimension('latitude', len(lat_crop))
    nc_subset.createDimension('longitude', len(lon_crop))
    nc_subset.createDimension('time', len(times))

    # set values for subset's variables which are in dimensions \
    # -> lat,lon and time
    for var_name in nc_subset.dimensions:

        var_subset = nc_subset.createVariable(
                var_name, nc_origin.variables[var_name].datatype,
                nc_origin.variables[var_name].dimensions
        )
        var_subset.setncatts(
            {
                k: nc_origin[var_name].getncattr(k)
                for k in nc_origin[var_name].ncattrs()
            }
        )

        if var_name == 'time':
            var_subset[:] = times

        if var_name == 'latitude':
            var_subset[:] = lat_crop

        if var_name == 'longitude':
            var_subset[:] = lon_crop

    # set values for the params requested by the user
    for v_name in sel_params:
        var_subset = nc_subset.createVariable(
                v_name, nc_origin.variables[v_name].datatype,
                nc_origin.variables[v_name].dimensions
            )
        var_subset.setncatts(
            {
                k: nc_origin[v_name].getncattr(k)
                for k in nc_origin[v_name].ncattrs()
            }
        )
        var_subset[:] = nc_origin[v_name][:, latli:latui+1, lonli:lonui+1]

    nc_origin.close()
    nc_subset.generated_by = 'Data Exchange Portal, RIMES'
    nc_subset.source = 'European Center for Medium Range Weather Forecast'
    nc_subset.generation_time = datetime.today().strftime('%Y %b %m %H:%M:%S')

    mem_view_subset = nc_subset.close()
    nc_subset_bytes = io.BytesIO(mem_view_subset)
    filename = (
            f'{state_name}_{top_lat}N_\
            {bottom_lat}S_{right_lon}E_{left_lon}W.nc'
    )
    nc_subset_bytes.seek(io.SEEK_SET)
    file_response = FileResponse(
            nc_subset_bytes,
            filename=filename,
            as_attachment=True
    )
    file_response['Content-Type'] = 'application/netcdf'
    file_response['init_time'] = datetime.strptime(update, '%Y%m%d_%H')
    return file_response
