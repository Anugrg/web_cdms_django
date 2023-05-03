from django.urls import path
from .views import BufrView

urlpatterns = [
    path('', BufrView.as_view(), name='bufr_data.bufr_view'),
]