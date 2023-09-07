from datetime import datetime as dt
from typing import Type, Callable
from dataclasses import dataclass

from netCDF4 import Dataset, num2date
import numpy as np

from django.conf import settings

from .models import system_state

from .param_processors import *


nc_paths = {
    "ECMWF_HRES_NC": settings.ECMWF_HRES_NC,
}


class NcFile:

    def __init__(self, state_name):
        self.state = system_state.objects.get(state_name=state_name)
        self.update = self.state.init_time
        self._path = (
            dt.strptime(self.update, '%Y%m%d_%H')
        ).strftime(nc_paths[state_name])
        self.data = Dataset(self._path)
        self.lats = self.data.variables['latitude'][:]
        self.lons = self.data.variables['longitude'][:]

    def crop_region(self, lat_indices, lon_indices):
        lat_crop, lon_crop = self.lats[lat_indices], self.lons[lon_indices]
        return lat_crop, lon_crop

    def get_coords_indices(
        self,
        bottom_lat,
        top_lat,
        left_lon,
        right_lon
    ):
        lat_indices = np.where((self.lats >= bottom_lat) & (self.lats <= top_lat))
        lon_indices = np.where((self.lons >= left_lon) & (self.lons <= right_lon))
        return lat_indices, lon_indices

    def get_dates(self):
        dates = num2date(
            self.data.variables['time'][:],
            self.data.variables['time'].units
        )
        return dates


def get_graph_params(processor_class):
    params = [
        {
            'name': r,
        }
        for r in dir(processor_class)
        if not r.startswith('_')
    ]
    return params


@dataclass
class EcModel:
    state_name: str
    gen_date: Callable
    graph: Type[graph_processor]
    animation: Type[anime_processor]
    lead_day: int = None
    daily_step: int = None
    lead_month: int = None


HRES = EcModel(
    state_name='ECMWF_HRES_NC',
    graph=ecmwf_hres_graph_processor,
    animation=ecmwf_hres_anime_processor,
    gen_date=gen_fcst_times,
    lead_day=10,
    daily_step=4
)
