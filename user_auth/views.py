from django.shortcuts import render
from django.views import View
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


class UserProfile(View):

    def get(self, request):
        return render(request, 'user_profile.html')
