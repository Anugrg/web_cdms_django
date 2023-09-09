from django.urls import path

from .views import *


urlpatterns = [

    path('get_token/', get_token.as_view(), name='user_auth.get_token'),
    path('check_token/', check_token.as_view(), name='user_auth.check_token'),

    path('login/', UserLogin.as_view(), name='user_auth.login'),
    path('login/<int:invalid_uname_pass>', UserLogin.as_view(), name='user_auth.login'),
    path('signup/', UserRegister.as_view(), name='user_auth.user_register'),
    path('logout/', logout_user, name='user_auth.logout'),

    path('assets/', asset_manager.as_view(), name='user_auth.user_asset'),

    path('profile/', UserProfile.as_view(), name='user_auth.profile'),
    path('profile/assets/delete_asset', delete_asset, name='user_auth.delete_asset'),
    path('profile/assets/download_asset', download_asset, name='user_auth.download_asset')
]
