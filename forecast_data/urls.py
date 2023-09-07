from django.urls import path
from .views import *


urlpatterns = [
    path('', ForecastView.as_view(), name='forecast.forecast_view'),
    path('get_netcdf_subset_hres/', get_netcdf_subset_ecmwf_hres.as_view(), name='forecast.get_netcdf_subset_hres'),
    path(
        'get_graph/',
        get_graph.as_view(),
        name='forecast_graph.get_graph'
    ),
    path(
        'get_animation/',
        get_animated_graph.as_view(),
        name='forecast_graph.get_animation'
    ),
    path(
        'view_shp_asset/',
        ShpFileView.as_view(),
        name='forecast_graph.view_shp_asset'
    ),
    path(
        'plot_shp_asset_graph/',
        ShpFilePlotGraph.as_view(),
        name='forecast_graph.shp_plot'
    ),
    path(
        'plot_shp_asset_animation/',
        ShpFilePlotAnimation.as_view(),
        name='forecast_graph.shp_animation'
    )
]