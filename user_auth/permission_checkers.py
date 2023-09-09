# helpers decorators

import jwt
import json
from django.conf import settings
from obs_data.models import station
from .models import CdmsUser


# checks if user has read permission for observed data
def has_permission_obs_r(request, station_id: int):

    permission = None

    if request.method == 'GET':
        permission = request.user.permission

    elif request.method == 'POST':
        token = request.headers.get('Authorization', '')
        header_data = jwt.get_unverified_header(token)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[header_data['alg']])
        permission = CdmsUser.objects.get(pk=int(payload['sub'])).permission

    if permission is None:
        return False

    # if all country
    # if 0 in permission['obs_r']:
    #     return True
    if not permission['obs_r']:
        return False

    # country_id = station.objects.filter(id=station_id).values('country__id').first().get('country__id', None)

    # if country_id not in permission['obs_r']:
    #     return False

    return True


# checks if user has permission for observed data write
def has_permission_obs_w(request, country_id: int):

    permission = None

    if request.method == 'GET':
        permission = request.user.permission

    elif request.method == 'POST':
        token = request.headers.get('Authorization', '')
        header_data = jwt.get_unverified_header(token)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[header_data['alg']])
        permission = CdmsUser.objects.get(pk=int(payload['sub'])).permission

    if permission is None:
        return False

    if not permission['obs_w']:
        return False

    # if all country
    # if 0 in permission['obs_r']:
    #     return True
    #
    # if country_id not in permission['obs_r']:
    #     return False

    return True
