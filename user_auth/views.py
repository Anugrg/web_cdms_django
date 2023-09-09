
import os
import json
import jwt
from datetime import datetime as dt, timedelta as td

from django.shortcuts import render, redirect, reverse
from django.contrib.auth import hashers
from django.views import View
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

from forecast_anls.utils import get_asset_info
from forecast_anls.models import user_asset
from user_auth.models import CdmsUser
from user_auth.decorators import *
# Create your views here.


class UserLogin(View):

    template_name = 'sign-in.html'

    def get(self, request, invalid_uname_pass=0):
        data = dict()
        data['next'] = request.GET.get('next', '')
        if invalid_uname_pass == 1:
            data['message'] = "Incorrect Username or Password"

        return render(request, self.template_name, data)

    def post(self, request):

        _next = request.POST.get('next', '')
        _user = request.POST.get('username', '_')
        _pass = request.POST.get('password', '__')

        user = authenticate(request, username=_user, password=_pass)
        if user is not None:

            login(request, user)

            if _next != "":
                return redirect(_next)

            return redirect(reverse('home.home_view'))

        return redirect(reverse('user_auth.login'), invalid_uname_pass=1)


def logout_user(request):
    logout(request)
    return render(request, 'sign-in.html')

@method_decorator(login_required(login_url='user_auth.login'), name='dispatch')
class UserProfile(View):

    def get(self, request):
        data = dict()
        data['assests'] = user_asset.objects.filter(user_id=request.user.id)
        data['user_name'] = request.user.name
        data['email'] = request.user.email
        return render(request, 'user_profile.html', data)


class asset_manager(View):

    template_name = 'user_profile.html'

    def get(self, request):

        data = dict()
        data['assests'] = user_asset.objects.filter(user_id=request.user.id)
        for row in data['assests']:
            print('>>', row.info)

        return render(request, self.template_name, data)

    def post(self, request):

        data = {
            'error': None,
            'message': None
        }

        uploaded_file = request.FILES.get('asset', None)

        if uploaded_file is None:
            data['message'] = ['No file data provided.']
            return JsonResponse({})

        file_data = uploaded_file.read()

        ok, err_msg, asset_info = get_asset_info(file_data.decode('utf-8'))

        if ok:
            try:
                new_asset = user_asset()

                new_asset.file = uploaded_file

                new_asset.user = request.user

                new_asset.info = asset_info
                new_asset.save()
            except Exception as e:
                data['error'] = 'EDB-001'
                data['message'] = str(e)

        else:
            data['error'] = 'E-001'
            data['message'] = err_msg

        return JsonResponse(data)


def delete_asset(request):
    data = {
        'error': None,
        'message': None
    }

    if request.method == 'POST':
        data['error'] = 'POST not allowed'
        data['message'] = 'Http POST is prohibited'
        return JsonResponse(data)

    asset_id = request.GET.get('asset_id')
    asset = user_asset.objects.get(identifier=f'{asset_id}')
    if asset:
        asset.delete()
    else:
        data['error'] = 'Asset not found'
        data['message'] = 'Asset does not exist'
        return JsonResponse(data)

    return JsonResponse(data)


def download_asset(request):
    data = {
        'error': None,
        'message': None
    }

    if request.method == 'POST':
        data['error'] = 'Post not allowed'
        data['message'] = 'Http POST is prohibited'
        return JsonResponse(data)

    asset_id = request.GET.get('asset_id')
    asset = user_asset.objects.filter(identifier=f'{asset_id}').values('file')
    if asset:
        file = asset[0].get('file')
        with open(os.path.join(settings.MEDIA_ROOT, file), "r") as asset_file:
            data['asset_file'] = json.load(asset_file)

    else:
        data['error'] = 'Asset not found'
        data['message'] = 'Asset does not exist'
        return JsonResponse(data)

    return JsonResponse(data)


class get_token(View):

    def gen_jwt(self, user_id: int, user_perm: dict) -> str:

        payload = {
            'sub': user_id,
            'iat': dt.utcnow(),
            'exp': dt.utcnow() + td(minutes=settings.TOKEN_TIMEOUT_MIN),
            #'iss': ''
        }

        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.TOKEN_ALTORITHM
        )
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return token

    def get(self, request):

        data = dict()
        data['error'] = None
        data['message'] = 'generated JSON web token'

        data['token'] = self.gen_jwt(request.user.id, request.user.permission)

        return JsonResponse(data)

    # this should not require login + csrf exempt
    def post(self, request):

        data = dict()
        data['error'] = None

        _user = request.POST.get('username', None)
        _pass = request.POST.get('password', None)

        user = authenticate(username=_user, password=_pass)

        if user is not None:
            data['message'] = 'User authentication successful'
            data['token'] = self.gen_jwt(user.id, user.permission)
            return JsonResponse(data)
        data['error'] = 'AUTH-001'
        data['message'] = 'Invalid login credentials'
        return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(token_required, name='post')
class check_token(View):

    def post(self, request):
        token = request.headers.get('Authorization', '')
        header_data = jwt.get_unverified_header(token)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[header_data['alg']])
        exp = dt.fromtimestamp(payload['exp'])
        if dt.utcnow() > exp:  # + delt(hours=5):
            return JsonResponse({
                'error': 'AUTH-002 ',
                'message': 'token is expired',
            })

        # print(json.dumps(payload))
        return JsonResponse({
            'error': None,
            'message': 'token is valid',
            # 'data': json.dumps(payload, separators=(',', ':'))
        })


class UserRegister(View):

    template_name = 'sign-up.html'

    def get(self, request):
        data = dict()
        '''code = request.GET.get('code')
        pk = request.GET.get('id')
        if not user_invitation.objects.filter(invitation_code=code, pk=pk).exists():
            return render(request, 'page-expired.html')        
        data['email'] = user_invitation.objects.get(invitation_code=code).email
        data['code'] = code
        data['pk'] = pk'''

        return render(request, self.template_name)

    def post(self, request):
        name = request.POST.get('name')
        email = request.POST.get('email')
        # pk = request.POST.get('pk')
        # code = request.POST.get('code')
        password = hashers.make_password(request.POST.get('password'))
        try:
            user = CdmsUser(name=name, email=email, password=password)
            user.save()
        except:
            return JsonResponse({'message': 'Unable to proceed'})

        # delete user invite
        # if user_invitation.objects.filter(invitation_code=code, pk=pk).exists():
        #     permission = user_invitation.objects.get(pk=pk).permission
        #     dataex_user.objects.create(name=name, email=email,
        #                                password=password, permission=permission,
        #                                organization_id=org_id)
        #     invite = user_invitation.objects.get(pk=pk)
        #     invite.delete()
        # else:
        #     return render(request, 'page-404.html')

        return redirect(reverse('user_auth.login'))
