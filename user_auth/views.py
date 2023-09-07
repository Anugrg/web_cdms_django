
import os
import json

from django.shortcuts import render, redirect, reverse
from django.views import View
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout

from forecast_anls.utils import get_asset_info
from forecast_anls.models import user_asset
from user_auth.models import CdmsUser
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
        print(user)

        if user is not None:

            login(request, user)

            if _next != "":
                return redirect(_next)

            return redirect(reverse('home.home_view'))

        return redirect(reverse('user_auth.login'), invalid_uname_pass=1)


class UserRegister(View):

    def get(self, request):
        email = request.get.GET('email')
        user_name = request.get.GET('name')
        password = request.get.GET('pass')

        return render(request, 'sign-in.html')


def logout_user(request):
    logout(request)
    return render(request, 'sign-in.html')


class UserProfile(View):

    def get(self, request):
        data = dict()
        data['assests'] = user_asset.objects.filter(user_id=request.user.id)
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

