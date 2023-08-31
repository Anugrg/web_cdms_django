from django.urls import path
from .views import *


urlpatterns = [
    path('', ForecastView.as_view(), name='forecast.forecast_view'),
    path('get_netcdf_subset_hres/', get_netcdf_subset_ecmwf_hres.as_view(), name='forecast.get_netcdf_subset_hres' )
]