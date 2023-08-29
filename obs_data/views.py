import json
from datetime import datetime as dt

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


class GetObs(View):

    def get(self, request):
        data = {}
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        station_id = request.GET.get('station_id', None)
        param_id = request.GET.get('param_id', None)

        sdate = dt.strptime(start_date, '%Y-%m-%d')
        edate = dt.strptime(end_date, '%Y-%m-%d')

        data['obs'] = list(
            obs_data.objects.filter(
                station_id=station_id,
                parameter_id=param_id,
                start_time__gte=sdate.strftime('%Y-%m-%d 00:00:00Z'),
                end_time__lte=edate.strftime('%Y-%m-%d 00:00:00Z')
            ).values('end_time', 'value'))

        return JsonResponse(data)


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
