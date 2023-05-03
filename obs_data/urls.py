from django.urls import path
from .views import ObsView, InsertObs, GetObs, StationMeta, GetParameters

urlpatterns = [
    path('', ObsView.as_view(), name='obs_data.obs_view'),
    path('insert/', InsertObs.as_view(), name='obs_data.insert'),
    path('view_obs/', GetObs.as_view(), name='obs_data.get_obs'),
    path('stations/', StationMeta.as_view(), name='obs_data.get_station_meta'),
    path('parameters/', GetParameters.as_view(), name='obs_data.get_params'),
]