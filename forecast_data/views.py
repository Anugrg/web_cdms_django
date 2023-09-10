import os
import io
import pytz
import json
from datetime import datetime 

import numpy as np
from netCDF4 import Dataset
from django.conf import settings

from django.shortcuts import render
from django.views import View
from django.conf import settings
from django.http.response import FileResponse, JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from forecast_data.models import system_state
from .plotter import animator, grapher, ShpGrapher, ShpAnimator
from .param_processors import (
                               ecmwf_hres_anime_processor,
                               ecmwf_hres_graph_processor,
                               graph_processors,
                               gen_fcst_times
)
from .param_plot_info import ParamInfo
from .helpers import NcFile, HRES, get_graph_params
from forecast_anls.models import user_asset


ECMWF_HRES_NC = settings.ECMWF_HRES_NC

models = {
    # 'ECMWF_SEAS_NC': SEAS,
    'ECMWF_HRES_NC': HRES,
    # 'ECMWF_ENS_NC': ENS
}


# Create your views here.

@method_decorator(login_required(login_url='user_auth.login'), name='dispatch')
class ForecastView(View):

    lead_day = 10
    daily_step = 4
    processor_class = ecmwf_hres_graph_processor

    def get(self, request):
        data = dict()

        data['state_name'] = 'ECMWF_HRES_VIS'
        data['source'] = 'ECMWF_HRES'

        nc_origin = NcFile('ECMWF_HRES_NC')
        dates = nc_origin.get_dates()
        info = nc_origin.state.info

        # need to override this with system_state only 
        data['init_time'] = system_state.objects.filter(
                                state_name=data['state_name'],
                                source__name=data['source']
                            ).values('init_time').first()['init_time']
        
        data['url_prefix'] = os.path.join(settings.FCST_JSON_URL_PREF,data['source'],data['init_time'])
        data['dates'] = gen_fcst_times(
            self.lead_day,
            self.daily_step,
            dates
        )
        data['data'] = get_netcdf_info('ECMWF_HRES_NC')
        data['params'] = get_graph_params(self.processor_class)

        return render(request, 'forecast_view.html', data)

@method_decorator(login_required(login_url='user_auth.login'), name='get')
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
    today_start_date = datetime(today.year, today.month, today.day)
    project_tz = pytz.timezone(settings.TIME_ZONE)
    
    return project_tz.localize(today_start_date)


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


@method_decorator(login_required(login_url='user_auth.login'), name='get')
class get_graph(View):

    state_name = "ECMWF_HRES_NC"
    lead_day = 10
    daily_step = 4

    def get(self, request):

        param = request.GET.get('param_name')
        fcst_time = request.GET.get('fcst_time')
        start_idx = int(request.GET.get('start_idx'))
        end_idx = int(request.GET.get('end_idx'))
        left_lon, right_lon = float(request.GET.get('left-lon')), float(request.GET.get('right-lon'))
        top_lat, bottom_lat = float(request.GET.get('top-lat')), float(request.GET.get('bottom-lat'))

        return self.generate_graph(
                param,
                left_lon, right_lon,
                top_lat, bottom_lat,
                start_idx, end_idx,
                fcst_time
        )

    def post(self, request):
        data = dict()
        data['error'] = None
        data['message'] = 'Successful'

        if request.content_type == 'application/json':
            try:
                req_payload = json.loads(request.body.decode('utf-8'))
            except:
                data['error'] = 'invalid request'
                data['message'] = 'unparsable json data'
                return JsonResponse(data)

        date_indx = req_payload.get('indx', None)
        param = req_payload.get('param', None)
        left_lon, right_lon = req_payload['domain']['left-lon'], req_payload['domain']['right-lon']
        top_lat, bottom_lat = req_payload['domain']['top-lat'], req_payload['domain']['bottom-lat']

        return self.generate_graph(
                param,
                left_lon, right_lon,
                top_lat, bottom_lat,
                date_indx=date_indx
        )

    def generate_graph(
            self, param,
            left_lon, right_lon,
            top_lat, bottom_lat,
            start_idx=None, end_idx=None,
            fcst_time=None, date_indx=None,
    ):
        nc_origin = NcFile(self.state_name)
        if not fcst_time:
            dates = nc_origin.get_dates()

            # retrieve time info for hres
            date_info = gen_fcst_times(
                self.lead_day,
                self.daily_step,
                dates
            )
            fcst_time = str(date_info[date_indx]['start_time']) + ' to ' + str(date_info[date_indx]['end_time'])
            start_idx, end_idx = date_info[date_indx]['start_idx'], date_info[date_indx]['end_idx']

        lat_indices, lon_indices = nc_origin.get_coords_indices(
            bottom_lat,
            top_lat,
            left_lon,
            right_lon
        )
        lat_crop, lon_crop = nc_origin.crop_region(lat_indices, lon_indices)
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

        graph_obj = ecmwf_hres_graph_processor(
            nc_origin.data,
            start_idx, end_idx,
            latli, latui,
            lonli, lonui
        )
        data = getattr(graph_obj, param)()
        param_info = ParamInfo(param)
        param_info.resolve_param()
        cname = param_info.cname
        levels = param_info.levels
        unit_label = param_info.unit_label
        ext = param_info.ext
        name = param

        graph = grapher(
                data, lon_crop, lat_crop,
                name, fcst_time, levels,
                ext, cname, unit_label
        )
        buf = graph.save_graph()
        filename = f'{param}_{fcst_time}.png'
        file_response = FileResponse(
            buf, filename=filename, as_attachment=True
        )
        file_response['Content-Type'] = 'image/png'
        file_response['init_time'] = datetime.strptime(
            nc_origin.update,
            '%Y%m%d_%H'
        )
        nc_origin.data.close()

        return file_response


@method_decorator(login_required(login_url='user_auth.login'), name='get')
class get_animated_graph(View):

    state_name = "ECMWF_HRES_NC"
    lead_day = 10
    daily_step = 4
    processor_class = ecmwf_hres_anime_processor

    def get(self, request):
        param = request.GET.get('param_name')
        left_lon, right_lon = float(request.GET.get('left-lon')), float(request.GET.get('right-lon'))
        top_lat, bottom_lat = float(request.GET.get('top-lat')), float(request.GET.get('bottom-lat'))

        return HttpResponse(
            self.generate_animation(
                param, left_lon, right_lon,
                top_lat, bottom_lat
            )
        )

    def post(self, request):
        data = dict()
        if request.content_type == "application/json":
            try:
                req_payload = json.loads(request.body.decode('utf-8'))
            except:
                data['error'] = 'invalid request'
                data['message'] = 'unparsable json data'
                return JsonResponse(data)

        param = req_payload.get('param')
        left_lon, right_lon = req_payload['domain']['left-lon'], req_payload['domain']['right-lon']
        top_lat, bottom_lat = req_payload['domain']['top-lat'], req_payload['domain']['bottom-lat']

        return HttpResponse(
                self.generate_animation(
                    param,
                    left_lon, right_lon,
                    top_lat, bottom_lat
                )
        )

    def generate_animation(
            self, param,
            left_lon, right_lon,
            top_lat, bottom_lat
    ):
        nc_origin = NcFile(self.state_name)
        times = nc_origin.get_dates()
        data = []
        date_info = gen_fcst_times(self.lead_day, self.daily_step, times)
        lat_indices, lon_indices = nc_origin.get_coords_indices(
            bottom_lat,
            top_lat,
            left_lon,
            right_lon
        )
        lat_crop, lon_crop = nc_origin.crop_region(lat_indices, lon_indices)
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

        anime_obj = ecmwf_hres_anime_processor(
            nc_origin.data, date_info,
            latli, latui,
            lonli, lonui
        )

        data = getattr(anime_obj, param)()
        param_info = ParamInfo(param)
        param_info.resolve_param()
        cname = param_info.cname
        levels = param_info.levels
        unit_label = param_info.unit_label
        ext = param_info.ext
        min_val = param_info.min_val
        max_val = param_info.max_val
        frames = len(data)
        name = param

        anime = animator(data, name,
                         date_info, unit_label,
                         max_val, min_val,
                         ext, cname, levels,
                         lat_crop, lon_crop, frames)

        data = anime.convert_to_html_vid()
        nc_origin.data.close()

        return data


class get_fcst_graph_params(View):

    def post(self, request):
        data = dict()
        data['error'] = None
        data['message'] = 'Successful'

        if request.content_type == "application/json":
            try:
                req_payload = json.loads(request.body.decode('utf-8'))
            except:
                data['error'] = 'invalid request'
                data['message'] = 'unparsable json data'
                return JsonResponse(data)

        model_type = req_payload.get('model_type', None)

        if model_type == 'ecmwf_hres':
            model = HRES
        elif model_type == 'ecmwf_ens':
            model = ENS
        elif model_type == 'ecmwf_seas':
            model = SEAS

        data['params'] = get_graph_params(model.graph)
        return JsonResponse(data)



@method_decorator(login_required(login_url='user_auth.login'), name='get')
class ShpFileView(View):

    def get(self, request):
        data = {}
        asset_id = request.GET.get('asset_id', None)
        try:
            asset_obj = user_asset.objects.get(identifier=asset_id)
        except Exception as e:
            data['error'] = 'query-004'
            data['message'] = str(e)
            return JsonResponse(data)

        asset_file_loc = asset_obj.file.path
        with open(asset_file_loc, 'r') as f:
            shp = json.load(f)

        return JsonResponse(shp)


@method_decorator(login_required(login_url='user_auth.login'), name='get')
class ShpFilePlotGraph(View):

    def get(self, request):
        data = {}
        loc = {}
        asset_id = request.GET.get('asset_id', None)
        loc['left_lon'], loc['right_lon'] = float(request.GET.get('left-lon')), float(request.GET.get('right-lon'))
        loc['top_lat'], loc['bottom_lat'] = float(request.GET.get('top-lat')), float(request.GET.get('bottom-lat'))
        start_idx = int(request.GET.get('start_idx'))
        end_idx = int(request.GET.get('end_idx'))
        param = request.GET.get('param_name')
        fcst_time = request.GET.get('fcst_time')
        state_name = request.GET.get('state_name')
        quantile = request.GET.get('quantile', None)
        try:
            asset_obj = user_asset.objects.get(identifier=asset_id)
        except Exception as e:
            data['error'] = 'query-004'
            data['message'] = str(e)
            return JsonResponse(data)

        return self.plot_shp(
            param,
            fcst_time,
            asset_obj,
            loc,
            state_name,
            start_idx,
            end_idx,
            quantile
        )

    def plot_shp(
        self,
        param,
        fcst_time,
        asset_obj,
        loc: dict,
        state_name,
        start_idx,
        end_idx,
        quantile=None
    ):
        nc_origin = NcFile(state_name)
        model = models.get(state_name)
        lat_indices, lon_indices = nc_origin.get_coords_indices(
            loc['bottom_lat'],
            loc['top_lat'],
            loc['left_lon'],
            loc['right_lon']
        )
        lat_crop, lon_crop = nc_origin.crop_region(lat_indices, lon_indices)
        latli, latui = lat_indices[0][0], lat_indices[0][-1]
        lonli, lonui = lon_indices[0][0], lon_indices[0][-1]
        if not quantile:
            graph_obj = model.graph(
                nc_origin.data,
                start_idx, end_idx,
                latli, latui,
                lonli, lonui
            )
        else:
            graph_obj = model.graph(
                nc_origin.data,
                quantile,
                start_idx, end_idx,
                latli, latui,
                lonli, lonui
            )

        data = getattr(graph_obj, param)()
        param_info = ParamInfo(param)
        param_info.resolve_param()
        cname = param_info.cname
        levels = param_info.levels
        unit_label = param_info.unit_label
        ext = param_info.ext
        name = param
        shpfile = asset_obj.file.path
        graph = ShpGrapher(
            data,
            shpfile,
            lon_crop,
            lat_crop,
            name,
            fcst_time,
            levels,
            ext,
            cname,
            unit_label,
            quantile
        )
        buf = graph.save_graph()
        filename = f'{param}_{fcst_time}.png'
        file_response = FileResponse(
            buf, filename=filename, as_attachment=True
        )
        file_response['Content-Type'] = 'image/png'
        file_response['init_time'] = datetime.strptime(
            nc_origin.update, '%Y%m%d_%H'
        )
        nc_origin.data.close()

        return file_response


@method_decorator(login_required(login_url='user_auth.login'), name='get')
class ShpFilePlotAnimation(View):

    def get(self, request):
        data = {}
        loc = {}
        param = request.GET.get('param_name')
        quantile = request.GET.get('quantile', None)
        asset_id = request.GET.get('asset_id', None)
        loc['left_lon'], loc['right_lon'] = float(request.GET.get('left-lon')), float(request.GET.get('right-lon'))
        loc['top_lat'], loc['bottom_lat'] = float(request.GET.get('top-lat')), float(request.GET.get('bottom-lat'))
        state_name = request.GET.get('state_name')
        try:
            asset_obj = user_asset.objects.get(identifier=asset_id)
        except Exception as e:
            data['error'] = 'query-004'
            data['message'] = str(e)
            return JsonResponse(data)

        return HttpResponse(
            self.generate_animation(
                param,
                loc,
                asset_obj,
                state_name,
                quantile
            )
        )

    def generate_animation(
        self,
        param,
        loc,
        asset_obj,
        state_name,
        quantile=None
    ):
        nc_origin = NcFile(state_name)
        model = models.get(state_name)
        times = nc_origin.get_dates()
        data = []
        if state_name == "ECMWF_SEAS_NC":
            date_info = model.gen_date(
                model.lead_month, nc_origin.update, times
            )
        else:
            date_info = model.gen_date(
                model.lead_day, model.daily_step, times
            )

        lat_indices, lon_indices = nc_origin.get_coords_indices(
            loc['bottom_lat'],
            loc['top_lat'],
            loc['left_lon'],
            loc['right_lon']
        )
        lat_crop, lon_crop = nc_origin.crop_region(lat_indices, lon_indices)
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
        shpfile = asset_obj.file.path
        if quantile:
            anime_obj = model.animation(
                nc_origin.data,
                quantile,
                date_info,
                latli, latui,
                lonli, lonui
            )
        else:
            anime_obj = model.animation(
                nc_origin.data,
                date_info,
                latli, latui,
                lonli, lonui
            )

        data = getattr(anime_obj, param)()
        param_info = ParamInfo(param)
        param_info.resolve_param()
        cname = param_info.cname
        levels = param_info.levels
        unit_label = param_info.unit_label
        ext = param_info.ext
        min_val = param_info.min_val
        max_val = param_info.max_val

        frames = len(data)
        name = param
        anime = ShpAnimator(
            data,
            shpfile, name,
            date_info, unit_label,
            max_val, min_val,
            ext, cname, levels,
            lat_crop, lon_crop, frames
        )

        data = anime.convert_to_html_vid()
        nc_origin.data.close()

        return data

