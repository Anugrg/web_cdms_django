from django.urls import path

from .views import *


urlpatterns = [

    path('login/', UserLogin.as_view(), name='user_auth.login'),
    path('login/<int:invalid_uname_pass>', UserLogin.as_view(), name='user_auth.login'),
    path('sign_up', UserRegister.as_view(), name='user_auth.sign_up'),
    path('logout/', logout_user),
    path('assets/', asset_manager.as_view(), name='user_auth.user_asset'),
    path('profile/', UserProfile.as_view(), name='user_auth.profile'),
    path('profile/assets/delete_asset', delete_asset, name='user_auth.delete_asset'),
    path('profile/assets/download_asset', download_asset, name='user_auth.download_asset')
]
