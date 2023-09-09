import json
from datetime import datetime as dt, timedelta as td

from django.shortcuts import render
from django.http import JsonResponse
from django.db import IntegrityError
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Min, Max, Count

from obs_data.models import *

# Create your views here.


class ObsView(View):

    def get(self, request):
        data = {}
        data['stations'] = station.objects.all().values('id', 'name')
        return render(request, 'obs_view.html', data)


class GetParameters(View):
    def get(self, request):
        data = {}
        stn_id = request.GET.get('station_id', None)
        params = []
        parameter_ids = obs_data.objects.values_list(
                'parameter__id', flat=True
            ).filter(
                station_id=stn_id
            ).distinct()

        if parameter_ids.exists():
            params.extend(
                list(
                    parameter.objects.filter(id__in=list(parameter_ids)).values('name', 'id')
                )
            )
        data['errors'] = None
        data['message'] = 'List of parameters'
        data['parameters'] = params
        return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
class InsertObs(View):

    def get(self, request):

        return JsonResponse(
            {'error': 'invalid request', 'message': 'restricted access'}
        )


    def date_ok(self,start_date:str, end_date:str)->True:

        date_ok = True
        try:
            start_date_obj = dt.strptime(start_date, '%Y-%m-%d %H:%MZ')
            end_date_obj = dt.strptime(end_date, '%Y-%m-%d %H:%MZ')

        except:
            return False

        if start_date_obj > end_date_obj:
            date_ok = False

        return date_ok

    def rec_ok(self,rec)->bool:
        msg = ''

        # check if the formatting is okay field
        fmt_ok =  ( rec.get('station_id',None) != None and type(rec['station_id'])==int ) \
                & ( rec.get('parameter_id',None) != None and type(rec['parameter_id'])==int ) \
                & ( rec.get('level_id',None) != None and type(rec['level_id'])==int ) \
                & ( rec.get('start_time',None) != None ) \
                & ( rec.get('end_time',None) != None ) \
                & ( rec.get('value',None) != None and ( type(rec['value'])==int or type(rec['value'])==float ) )

        #  check for valid datetime
        date_ok =  self.date_ok(rec['start_time'], rec['end_time'])

        # check if station is within country
        stn_ok = rec['station_id'] in self.stations

        if not fmt_ok:
            msg += "data format is not okay :: "

        if not date_ok:
            msg += "date format is not okay :: "

        if not stn_ok:
            msg += "station id does not exist :: "

        return fmt_ok and date_ok and stn_ok, msg

    # req_payload = pre parsed parsed by decorator etc.
    def post(self, request):

        data = dict()
        data['error'] = None
        data['message'] = 'insert was successful'
        print(request.content_type)

        if request.content_type != 'application/json':
            data['error'] = 'invalid request'
            data['message'] = 'unsupported content type'
            return JsonResponse(data)

        # parse json data from request body
        try:
            req_payload = request.body.decode('utf-8')
            print(req_payload)
            try:
                req_payload = json.loads(req_payload)
            except:
                data['error'] = 'invalid request'
                data['message'] = 'Unparsable Json data'
                return JsonResponse(data)
        except:
            data['error'] = 'Max data size limit'
            data['message'] = f'Request data size is more than 2.5 mb'
            return JsonResponse(data)

        # get and check if country id is provided
        # req_country_id = req_payload.get('country_id',None)

        # if req_country_id == None or type(req_country_id)!=int:
        #     data['error'] = 'invalid json format'
        #     data['message'] = 'country_id is not valid'
        #     return JsonResponse(data)

        # if not has_permission_obs_w(request, req_country_id):
        #     data['error'] = 'error-perm-001'
        #     data['message'] = 'user dosent have permission'
        #     return JsonResponse(data)

        # get and check if data is provided
        req_data = req_payload.get('data', None)
        print(req_data)

        if req_data is None or type(req_data) != list or len(req_data) == 0:
            data['error'] = 'invalid json format'
            data['message'] = 'data is not provided or formatted properly'

        # get station_id list
        self.stations = set(
                            station.objects.all()
                            .values_list('id', flat=True)
                        )

        obs_data_obj_queue = []
        for i, rec in enumerate(req_data):

            # check if record is okay
            print(rec)
            _ok, msg = self.rec_ok(rec)
            if not _ok:
                data['error'] = 'invalid data'
                data['message'] = f'error in data in record {i}, {msg}'
                return JsonResponse(data)

            obs_data_obj_queue.append(
                obs_data(
                    start_time=rec['start_time'],
                    end_time=rec['end_time'],
                    duration=dt.strptime(rec['end_time'], '%Y-%m-%d %H:%MZ') - dt.strptime(rec['start_time'], '%Y-%m-%d %H:%MZ'),
                    value=rec['value'],
                    parameter_id=rec['parameter_id'],
                    level_id=rec['level_id'],
                    station_id=rec['station_id']
                )
            )

        try:
            obs_data.objects.bulk_create(obs_data_obj_queue)
        except IntegrityError as e:
            data['error'] = 'invalid data'
            data['message'] = f'{e}'
            return JsonResponse(data)

        return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
class GetObs(View):

    def get_obs_data(self, request, start_date, end_date, station_id, param_id) -> JsonResponse:
        data = dict()
        try:
            start_date_obj = dt.strptime(start_date, '%Y-%m-%d')
            end_date_obj = dt.strptime(end_date, '%Y-%m-%d')
            date_delta = (end_date_obj - start_date_obj).days

        except:
            data['error'] = 'query-001'
            data['message'] = 'provide a valid date format'

            return JsonResponse(data)

        query_parameter_okay = False

        if (station_id is not None) and (param_id is not None):
            query_parameter_okay = (start_date is not None) \
                                   or (end_date is not None) \
                                   or (param_id is not None) \
                                   or (station_id is not None) \
                                   or (station_id.isdigit() != True) \
                                   or (param_id.isdigit() != True)

        if not query_parameter_okay:
            data['error'] = 'error-query-002'
            data[
                'message'] = 'provide station_id, param_id, & start_date, end_date in yyyy-mm-dd format. max 180 day interval'

            return JsonResponse(data)

        # check for mermission
        # if not has_permission_obs_r(request, int(station_id)):
        #     data['error'] = 'EP-001'
        #     data['message'] = 'User does not have enough permission'
        #     return JsonResponse(data)

        if date_delta > 180:
            data['error'] = None
            data['message'] = 'date range is more than 180 days, showing only for 180 days'

            # override end date
            end_date_obj = start_date_obj + td(days=180)

        # if query_parameter_okay:
        try:
            _param = parameter.objects.get(pk=int(param_id))
        except ValueError:
            data['error'] = 'No data'
            data['message'] = 'Station has no observations to show!'
            return JsonResponse(data)

        _stn = station.objects.get(pk=int(station_id))

        data['parameter'] = f'{_param.full_name}'
        data['unit'] = _param.unit
        data['type'] = _param.parameter_type
        data['station_name'] = _stn.name
        data['wmo_id'] = _stn.wmo_id

        data_query = obs_data.objects.filter(
            start_time__gte=start_date_obj.strftime('%Y-%m-%d 00:00:00Z'),
            end_time__lte=end_date_obj.strftime('%Y-%m-%d 00:00:00Z'),
            parameter__id=param_id,
            station=station_id
        ).values('start_time', 'end_time', 'value')
        data['data'] = list(data_query)

        return JsonResponse(data)

    def get(self, request):

        # get query parameters
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        station_id = request.GET.get('station_id', None)
        param_id = request.GET.get('param_id', None)

        return self.get_obs_data(request, start_date, end_date, station_id, param_id)

    def post(self, request):

        data = dict()

        if request.content_type == "application/json":
            try:
                req_payload = json.loads(request.body.decode('utf-8'))
            except:
                data['error'] = 'invalid request'
                data['message'] = 'unparsable json data'
                return JsonResponse(data)
        else:
            data['error'] = 'e-004'
            data['message'] = 'invalid content type must be application/json'
            return JsonResponse(data)

        start_date = req_payload.get('start_date', None)
        end_date = req_payload.get('end_date', None)
        station_id = req_payload.get('station_id', None)
        param_id = req_payload.get('param_id', None)

        return self.get_obs_data(request, start_date, end_date, station_id, param_id)


class StationMeta(View):

    def get(self, request):
        stn_meta_fields = dict()
        station_id = request.GET.get('station_id', None)

        stn_info_fields = [
            'id', 'name', 'full_name',
            'station_id', 'wmo_id',
            'lat', 'lon', 'station_type'
        ]

        if station_id:

            station_info = station.objects.filter(id=station_id).values(*stn_info_fields).first()
            params_ids = list(obs_data.objects.filter(station__id=station_id).values_list('parameter__id', flat=True).distinct())
            param_names = list(parameter.objects.filter(id__in=params_ids).values('id', 'name', 'full_name'))

            rec_info = obs_data.objects.filter(station__id=station_id).aggregate(Min('start_time'), Max('end_time'), Count('pk'))
            rec_start = rec_info['start_time__min'].strftime('%Y-%m-%d') if rec_info['start_time__min'] else None
            rec_end = rec_info['end_time__max'].strftime('%Y-%m-%d') if rec_info['end_time__max'] else None
            rec_count = rec_info['pk__count'] if rec_info['pk__count'] else 0
            missing = obs_data.objects.filter(value=-9999, station__id=station_id).count()

            stn_meta_fields['info'] = station_info
            stn_meta_fields['params'] = param_names
            stn_meta_fields['rec_start'] = rec_start
            stn_meta_fields['rec_end'] = rec_end
            stn_meta_fields['rec_count'] = rec_count
            stn_meta_fields['missing_count'] = missing
        else:
            station_info = station.objects.all().values(*stn_info_fields)
            stn_meta_fields['info'] = list(station_info)

        return JsonResponse(stn_meta_fields)
