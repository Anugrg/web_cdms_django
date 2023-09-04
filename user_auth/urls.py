from django.urls import path
from .views import UserLogin, UserCreate, UserProfile, logout_user, asset_manager
from .models import CdmsUser
from django.contrib import admin
from user_auth.admin import cdms_user_admin
urlpatterns = [

    path('login/', UserLogin.as_view(), name='user_auth.login'),
    path('sign-up/', UserCreate.as_view(), name='user_auth.sign_up'),
    path('logout/', logout_user),
    path('assets/', asset_manager.as_view(), name='user_auth.user_asset'),
    path('profile/', UserProfile.as_view(), name='user_auth.profile')
]

admin.site.register(CdmsUser, cdms_user_admin)