
from datetime import datetime as dt
import json

import fiona
import pytz
from shapely.geometry import shape

from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from forecast_data.models import system_state
from forecast_anls.models import user_asset
from forecast_anls.reducers import ecmwf_hres_region_reducers
from user_auth.models import CdmsUser
from forecast_anls.utils import get_asset_info

# Create your views here.


class get_asset_info(View):

    def asset_info(self, asset_identifier):

        data = dict()
        data['error'] = None
        data['message'] = None

        if asset_identifier is None:
            data['error'] = 'query-001'
            data['message'] = 'insufficient query parameter'
            return data

        try:
            asset = user_asset.objects.get(identifier=asset_identifier)

            data['data'] = asset.info

        except Exception as e:
            data['error'] = 'query-002'
            data['message'] = str(e)

        return data

    def get(self, request):
        asset_identifier = request.GET.get('asset_identifier', None)

        return JsonResponse(self.asset_info(asset_identifier))


def today_start():
    today = dt.today()
    today_start_date = dt(today.year, today.month, today.day)
    project_tz = pytz.timezone(settings.TIME_ZONE)

    return project_tz.localize(today_start_date)


@method_decorator(login_required(login_url='user_auth.login'), name='get')
class get_user_fcst_assets(View):

    def get(self, request):
        data = dict()
        user_id = request.user.id
        data['user_assets'] = self.get_assets(user_id)
        return JsonResponse(data)

    def post(self, request):
        data = dict()
        if request.content_type == "application/json":
            try:
                req_payload = json.loads(request.body.decode('utf-8'))
            except:
                data['error'] = 'invalid request'
                data['message'] = 'unparsable json data'
                return JsonResponse(data)

        user_id = CdmsUser.objects.get(email=req_payload.get('username')).id
        data['user_assets'] = self.get_assets(user_id)

        data['error'] = None
        data['message'] = 'Successful'

        return JsonResponse(data)

    def get_assets(self, user_id):
        assets = list(
            user_asset.objects.filter(
                user_id=user_id
            ).values('file', 'identifier', 'info')
        )
        return assets


@method_decorator(login_required(login_url='user_auth.login'), name='get')
class forecast_by_region_ecmwf_hres(View):

    reducer_class = ecmwf_hres_region_reducers

    def get(self, request):
        data = {}
        data['usr_assests'] = user_asset.objects.filter(user_id=request.user.id)
        print(data)
        hres_state = system_state.objects.get(state_name='ECMWF_HRES_VIS')
        data['sys_state'] = hres_state
        data['state_is_recent'] = data['sys_state'].updated_at > today_start()

        data['reducers'] = [
                    {
                        'name': r,
                        'doc': getattr(self.reducer_class, r).__doc__
                    }
                    for r in dir(self.reducer_class)
                    if not r.startswith('_')
        ]

        return render(request, 'forecast_by_region_ecwmf_hres.html', data)


@method_decorator(login_required(login_url='user_auth.login'), name='get')
class get_ecmwf_hres_region_data(View):

    ecmwf_hres_state = "ECMWF_HRES_NC"
    reducer_class = ecmwf_hres_region_reducers

    def get_reduced_data(self, asset_identifier, reducer_name, unique_field) -> JsonResponse:

        data = dict()
        data['error'] = None
        data['message'] = None

        if asset_identifier is None or reducer_name is None or unique_field is None:
            data['error'] = 'query-001'
            data['message'] = 'insufficient query parameter'
            return JsonResponse(data)

        # check if reducer is valid
        if reducer_name not in dir(self.reducer_class):
            data['error'] = 'query-002'
            data['message'] = 'Invalid reducer'

        try:
            asset_obj = user_asset.objects.get(identifier=asset_identifier)
        except Exception as e:
            data['error'] = 'query-004'
            data['message'] = str(e)
            return JsonResponse(data)

        if unique_field not in asset_obj.info['unique_fields']:
             data['error'] = 'query-003'
             data['message'] = 'invalid unique field'

        _asset_path = asset_obj.file.path
        print(_asset_path)

        # get init_time and netcdf path
        state_update = system_state.objects.get(state_name=self.ecmwf_hres_state).init_time
        fcst_init = dt.strptime(state_update, '%Y%m%d_%H')

        # get netcdf full path
        _ecmwf_hres_nc = fcst_init.strftime(settings.ECMWF_HRES_NC)

        # instance of reducer object
        reducer_obj = self.reducer_class(fcst_init, _ecmwf_hres_nc, _asset_path)

        # get function of class > execute >> assign returned data
        data['data'] = getattr(reducer_obj, reducer_name)(unique_field)

        return JsonResponse(data)

    def get(self, request):

        asset_identifier = request.GET.get('asset_identifier', None)
        reducer_name = request.GET.get('reducer', None)
        unique_field = request.GET.get('unique_field', None)

        return self.get_reduced_data(asset_identifier, reducer_name, unique_field)


def extract_asset_info(file: str) -> tuple:
        info = dict()
        print(file)

        try:
            sf = fiona.open(file, 'r')
        except Exception as e:
            return False, str(e), info

        sf_schema_prop = sf.schema['properties']

        # only allow string and int header
        allowed_header_types = ['int', 'str']
        allowed_headers = []
        header_values = dict()

        for header in sf_schema_prop:
            if sf_schema_prop[header].split(':')[0] in allowed_header_types:
                allowed_headers.append(header)
                header_values[header] = set()

        rec_count = 0

        for i, rec in enumerate(sf):

            try:
                if rec['geometry']['type'] not in ['MultiPolygon', 'Polygon']:
                    raise ValueError('File contains non polygon record')

                shp = shape(rec['geometry'])

                if not shp.is_valid:
                    raise ValueError(f'File contains invalid geometry at record no {i}')

            except Exception as e:

                return (False, str(e), info)

            for _header in allowed_headers:
                header_values[_header].add(rec['properties'][_header])

            rec_count = i + 1

        unique_headers = []

        for _header in allowed_headers:

            if len(header_values[_header]) == rec_count:
                unique_headers.append(_header)

        info['rec_count'] = rec_count
        info['unique_fields'] = unique_headers

        return True, None, info