from django.urls import path, include
from .views import SpatialView

urlpatterns = [

    path('', SpatialView.as_view(), name='spatial_data_gen.spatial' )
]