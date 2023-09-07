from django.urls import path

from forecast_anls.views import *

urlpatterns = [
    path(
        '',
        forecast_by_region_ecmwf_hres.as_view(),
        name='forecast_anls.forecast_region_ecmwf_hres'
    ),
    path(
        'get_ecmwf_hres_region_data/',
        get_ecmwf_hres_region_data.as_view(),
        name='forecast_anls.get_ecmwf_hres_region_data'
    ),

    path(
        'get_asset_info/',
        get_asset_info.as_view(),
        name='forecast_anls.get_asset_info'
    ),
    path(
        'get_user_fcst_assets/',
        get_user_fcst_assets.as_view(),
        name='forecast_anls.get_user_fcst_assets'
    )

]