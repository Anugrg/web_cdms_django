from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.contrib.auth import logout

from forecast_anls.utils import get_asset_info
from forecast_anls.models import user_asset
from user_auth.models import CdmsUser
# Create your views here.


class UserLogin(View):

    def get(self, request):
        return render(request, 'sign-in.html')


class UserCreate(View):

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
        return render(request, 'user_profile.html')


class asset_manager(View):

    template_name = 'profile_view_assets.html'

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

                new_asset.user = CdmsUser.objects.get(id=2) #request.user

                new_asset.info = asset_info
                new_asset.save()
            except Exception as e:
                data['error'] = 'EDB-001'
                data['message'] = str(e)

        else:
            data['error'] = 'E-001'
            data['message'] = err_msg

        return JsonResponse(data)
