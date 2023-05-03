from django.urls import path
from .views import ForecastView, NetcdfView


urlpatterns = [
    path('', ForecastView.as_view(), name='forecast.forecast_view'),
    path('netcdf/', NetcdfView.as_view(), name='forecast.forecast_netcdf')
]