# helpers decorators

import jwt
import json
from django.http import JsonResponse
from django.conf import settings
from obs_data.models import station

from .models import CdmsUser


def token_required(func):
    def wrapper(request, *args, **kwargs):

        try:
            token = request.headers.get('Authorization', '')
            header_data = jwt.get_unverified_header(token)
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[header_data['alg'], ])
        except Exception as e:
            # invalid token or token not provided
            return JsonResponse({'error': 'invalid token', 'message': str(e)})

        # for valid tokens: return the return value of original func
        return func(request, *args, **kwargs)

    return wrapper


# decorator for checking boolean permissions
def permission_required(permission):
    def middle(func):

        def wrapper(request, *args, **kwargs):

            if request.method == 'GET':

                if not hasattr(request.user, 'permission'):
                    return JsonResponse({
                        'error': 'AUTH-001',
                        'message': 'no user permission found, user may not be logged in'
                    })

                user_permission = request.user.permission


            elif request.method == 'POST':
                token = request.headers.get('Authorization', '')
                header_data = jwt.get_unverified_header(token)
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[header_data['alg'], ])
                user_permission = CdmsUser.objects.get(pk=int(payload['sub'])).permission

            if permission == 'fcst_analysis' and user_permission['fcst_analysis'] == False:
                return JsonResponse({
                    'error': 'dec-003',
                    'message': 'User dosent have permission to access this data'
                })

            elif permission == 'fcst_subset' and user_permission['fcst_subset'] == False:
                return JsonResponse({
                    'error': 'dec-004',
                    'message': 'User dosent have permission to access this data'
                })

            elif permission == 'fcst_graph' and user_permission['fcst_graph'] == False:
                return JsonResponse({
                    'error': 'dec-005',
                    'message': 'User dosent have permission to access graphics'
                })

            return func(request, *args, **kwargs)

        return wrapper

    return middle


'''
What is the problem if we assign permission in jwt header?

#)  user permission may change before expiration of jwt token
    in that case token with the pervious permission is still valid
    but the user permission changed in database. Thus user will be 
    able to access data while user permission is revoked.

'''