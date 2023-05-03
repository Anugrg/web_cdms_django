from django.urls import path
from .views import DataQualityControlView as dqcView

urlpatterns = [
    path('', dqcView.as_view(), name='dqc.dqc_view'),
]
