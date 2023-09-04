
import multiprocessing

import pyscissor
from netCDF4 import Dataset, num2date
import fiona
from shapely.geometry import shape
import numpy as np
from datetime import datetime as dt

from forecast_anls.mp_workers import worker_calc_weight_grd, worker_ens_pr_cp_sum
from forecast_anls.utils import calc_rh


class ecmwf_hres_region_reducers():

    _daily_step = 4
    _lead_day = 10

    # ISO date format / ECMA-262 spec
    _date_format = '%Y-%m-%dT%H:%M:%SZ'

    def __init__(self, fcst_int : dt, ecmwf_hres_nc : str, asset_path : str):

        self.fcst_init = fcst_int
        self.ncfile = Dataset(ecmwf_hres_nc, 'r')
        self.shape_file = fiona.open(asset_path, 'r')
        self.lats = self.ncfile.variables['latitude'][:]
        self.lons = self.ncfile.variables['longitude'][:]

        _time_var = self.ncfile.variables['time']
        self.times = num2date(_time_var[:], _time_var.units)


    def rainfall_daily_weighted_average_mp(self, unique_field ) -> dict:
        """
        Calculates daily accumulated rainfall and performs
        spatial weighted average operation within polygon region
        with_multiprocessing
        """

        data = {
            'fcst_init': self.fcst_init.strftime(self._date_format),
            'chart_type': 'column',
            'type': 'accumulated',
            't-reduced': 'period',
            'parameter_name': 'Rainfall',
            'unit': 'mm',
            'r_data': {}
        }
        _rf_all = (self.ncfile.variables['cp'][:] + self.ncfile['lsp'][:]) * 1000

        # spin multiprocessing pool
        mp_pool = multiprocessing.Pool(4)

        # gen args list
        args_list = list()
        for rec in self.shape_file:
            shapely_obj = shape(rec['geometry'])

            pyscissor_obj = pyscissor.scissor(shapely_obj, self.lats, self.lons)

            args_list.append((
                rec['properties'][unique_field], pyscissor_obj
            ))

        # this result can be cached
        mp_results = mp_pool.map(worker_calc_weight_grd, args_list)

        mp_pool.close()
        mp_pool.join()

        # iterate over the returned results
        for rec in mp_results:

            _shape_data = {
                'time': [],
                'value': []
            }

            _unique_name = rec['uid']

            _weight_grid = rec['wg']

            for day in range(self._lead_day):

                sid = day * self._daily_step
                eid = sid + self._daily_step

                if day == 0:
                    rf_day = _rf_all[eid].copy()

                else:
                    rf_day = (_rf_all[eid] - _rf_all[sid]).copy()

                value = np.average(rf_day, weights=_weight_grid)

                _shape_data['time'].append([
                    self.times[sid].strftime(self._date_format),
                    self.times[eid].strftime(self._date_format)
                ])

                _shape_data['value'].append(np.round(value, 2))

            data['r_data'][_unique_name] = _shape_data

        return data

    def rainfall_daily_weighted_average(self, unique_field) -> dict:
        """
        Calculates daily accumulated rainfall and performs
        spatial weighted average operation within polygon region.
        """

        data = {
            'fcst_init': self.fcst_init.strftime(self._date_format),
            'chart_type': 'column',
            'type': 'accumulated',
            't-reduced': 'period',
            'parameter_name': 'Rainfall',
            'unit': 'mm',
            'r_data': {}
        }
        _rf_all = (self.ncfile.variables['cp'][:] + self.ncfile['lsp'][:]) * 1000

        # should i trust the unique_field parameter
        for rec in self.shape_file:

            _shape_data = {
                'time': [],
                'value': []
            }

            _unique_name = rec['properties'][unique_field]

            _shapely_obj = shape(rec['geometry'])

            _pyscissor_obj = pyscissor.scissor(_shapely_obj, self.lats, self.lons)

            _weight_grid = _pyscissor_obj.get_masked_weight_recursive()

            for day in range(self._lead_day):

                sid = day * self._daily_step
                eid = sid + self._daily_step

                if day == 0:
                    rf_day = _rf_all[eid].copy()

                else:
                    rf_day = (_rf_all[eid] - _rf_all[sid]).copy()

                value = np.average(rf_day, weights=_weight_grid)

                _shape_data['time'].append([
                    self.times[sid].strftime(self._date_format),
                    self.times[eid].strftime(self._date_format)
                ])

                _shape_data['value'].append(np.round(value, 2))

            data['r_data'][_unique_name] = _shape_data

        return data

    def rainfall_step_weighted_average(self, unique_field) -> dict:
        '''
        Calculates 6 hourly accumulated rainfall and and performs
        spatial weighted average operation within polygon region.
        '''

        data = {
            'fcst_init': self.fcst_init.strftime(self._date_format),
            'chart_type': 'column',
            'type': 'accumulated',
            't-reduced': 'period',
            'parameter_name': 'Rainfall',
            'unit': 'mm',
            'r_data': {}
        }

        _rf_all = (self.ncfile.variables['cp'][:] + self.ncfile['lsp'][:]) * 1000

        for rec in self.shape_file:

            _shape_data = {
                'time': [],
                'value': []
            }

            _unique_name = rec['properties'][unique_field]

            _shapely_obj = shape(rec['geometry'])

            _pyscissor_obj = pyscissor.scissor(_shapely_obj, self.lats, self.lons)

            _weight_grid = _pyscissor_obj.get_masked_weight_recursive()

            for step in range(1, (self._daily_step * self._lead_day) + 1):

                if step == 1:
                    rf_step = _rf_all[step]
                else:
                    rf_step = _rf_all[step] - _rf_all[step - 1]

                value = np.average(rf_step, weights=_weight_grid)

                _shape_data['time'].append([
                    self.times[step - 1].strftime(self._date_format),
                    self.times[step].strftime(self._date_format)
                ])

                _shape_data['value'].append(np.round(value, 2))

            data['r_data'][_unique_name] = _shape_data

        return data

    def tmin_daily_tmin_region(self, unique_field) -> dict:

        """
        Calculates minimum temperature within a day
        and performs spatial minimum operation within polygon region
        """

        data = {
            'fcst_init': self.fcst_init.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'chart_type': 'line',
            'type': 'instant',
            't-reduced': 'period',
            'parameter_name': 'Temperature Minimum (day)',
            'unit': 'degC',
            'r_data': {}
        }

        _temp_all = self.ncfile.variables['t2m'][:] - 273.15

        for rec in self.shape_file:

            _shape_data = {
                'time': [],
                'value': []
            }

            _unique_name = rec['properties'][unique_field]

            _shapely_obj = shape(rec['geometry'])

            _pyscissor_obj = pyscissor.scissor(_shapely_obj, self.lats, self.lons)

            _weight_grid = _pyscissor_obj.get_masked_weight_recursive()

            for day in range(self._lead_day):

                sid = day * self._daily_step
                eid = sid + self._daily_step

                tmin_day = np.amin(_temp_all[sid:eid + 1, :, :], axis=0)

                if not np.ma.is_masked(tmin_day):
                    tmin_day = np.ma.masked_array(tmin_day.data, mask=_weight_grid.mask)

                tmin_day.mask = tmin_day.mask | _weight_grid.mask

                value = tmin_day.min()

                _shape_data['time'].append([
                    self.times[sid].strftime(self._date_format),
                    self.times[eid].strftime(self._date_format)
                ])

                _shape_data['value'].append(np.round(value, 2))

            data['r_data'][_unique_name] = _shape_data

        return data

    def tmax_daily_tmax_region(self, unique_field) -> dict:

        '''
        Calculates maximum temperature within a day
        and performs spatial maximum operation within polygon region
        '''

        data = {
            'fcst_init': self.fcst_init.strftime(self._date_format),
            'chart_type': 'line',
            'type': 'instant',
            't-reduced': 'period',
            'parameter_name': 'Temperature Maximum (day)',
            'unit': 'degC',
            'r_data': {}
        }

        _temp_all = self.ncfile.variables['t2m'][:] - 273.15

        for rec in self.shape_file:

            _shape_data = {
                'time': [],
                'value': []
            }

            _unique_name = rec['properties'][unique_field]

            _shapely_obj = shape(rec['geometry'])

            _pyscissor_obj = pyscissor.scissor(_shapely_obj, self.lats, self.lons)

            _weight_grid = _pyscissor_obj.get_masked_weight_recursive()

            for day in range(self._lead_day):

                sid = day * self._daily_step
                eid = sid + self._daily_step

                tmax_day = np.amax(_temp_all[sid:eid + 1, :, :], axis=0)

                if not np.ma.is_masked(tmax_day):
                    tmax_day = np.ma.masked_array(tmax_day.data, mask=_weight_grid.mask)

                tmax_day.mask = tmax_day.mask | _weight_grid.mask

                value = tmax_day.max()

                _shape_data['time'].append([
                    self.times[sid].strftime(self._date_format),
                    self.times[eid].strftime(self._date_format)
                ])

                _shape_data['value'].append(np.round(value, 2))

            data['r_data'][_unique_name] = _shape_data

        return data

    def temp_step_avg_region(self, unique_field) -> dict:
        '''
        Calculates temperature for every step averaged under a polygon region.
        '''

        data = {
            'fcst_init': self.fcst_init.strftime(self._date_format),
            'chart_type': 'line',
            'type': 'accumulated',
            't-reduced': 'step',
            'parameter_name': 'Temperature ',
            'unit': 'degC',
            'r_data': {}
        }

        _temp_all = self.ncfile.variables['t2m'][:] - 273.15

        for rec in self.shape_file:

            _shape_data = {
                'time': [],
                'value': []
            }

            _unique_name = rec['properties'][unique_field]

            _shapely_obj = shape(rec['geometry'])

            _pyscissor_obj = pyscissor.scissor(_shapely_obj, self.lats, self.lons)

            _weight_grid = _pyscissor_obj.get_masked_weight_recursive()

            for step in range((self._daily_step * self._lead_day) + 1):

                temp_step = _temp_all[step, :, :]

                if np.ma.is_masked(temp_step):
                    temp_step = np.ma.masked_array(temp_step.data, mask=_weight_grid.mask)

                temp_step.mask = temp_step.mask | _weight_grid.mask

                value = temp_step.mean()

                _shape_data['time'].append(self.times[step].strftime(self._date_format))

                _shape_data['value'].append(np.round(value, 2))

            data['r_data'][_unique_name] = _shape_data

        return data

    def ws_daily_avg_region(self, unique_field) -> dict:

        '''
        Calculates wind speed average within within a day
        and performs spatial average operation within polygon region
        '''

        data = {
            'fcst_init': self.fcst_init.strftime(self._date_format),
            'chart_type': 'line',
            'type': 'instant',
            't-reduced': 'period',
            'parameter_name': 'Wind Speed Average (day)',
            'unit': 'km/h',
            'r_data': {}
        }

        _ws_all = np.sqrt(np.square(self.ncfile.variables['u10'][:]) \
                          + np.square(self.ncfile.variables['v10'][:]) \
                          ) * 3.6

        for rec in self.shape_file:

            _shape_data = {
                'time': [],
                'value': []
            }

            _unique_name = rec['properties'][unique_field]

            _shapely_obj = shape(rec['geometry'])

            _pyscissor_obj = pyscissor.scissor(_shapely_obj, self.lats, self.lons)

            _weight_grid = _pyscissor_obj.get_masked_weight_recursive()

            for day in range(self._lead_day):

                sid = day * self._daily_step
                eid = sid + self._daily_step

                ws_day = np.average(_ws_all[sid:eid + 1, :, :], axis=0)

                if not np.ma.is_masked(ws_day):
                    ws_day = np.ma.masked_array(ws_day.data, mask=_weight_grid.mask)

                ws_day.mask = ws_day.mask | ws_day.mask

                value = ws_day.mean()

                _shape_data['time'].append([
                    self.times[sid].strftime(self._date_format),
                    self.times[eid].strftime(self._date_format)
                ])

                _shape_data['value'].append(np.round(value, 2))

            data['r_data'][_unique_name] = _shape_data

        return data

    def rh_daily_avg_region(self, unique_field) -> dict:

        '''
        Calculates relative humidity average within within a day
        and performs spatial average operation within polygon region
        '''

        data = {
            'fcst_init': self.fcst_init.strftime(self._date_format),
            'chart_type': 'line',
            'type': 'instant',
            't-reduced': 'period',
            'parameter_name': 'Relative Humidity Average (day)',
            'unit': '%',
            'r_data': {}
        }

        _temp_all = self.ncfile.variables['t2m'][:] - 273.15
        _dtemp_all = self.ncfile.variables['d2m'][:] - 273.15

        _rh_all = calc_rh(_temp_all, _dtemp_all)

        for rec in self.shape_file:

            _shape_data = {
                'time': [],
                'value': []
            }

            _unique_name = rec['properties'][unique_field]

            _shapely_obj = shape(rec['geometry'])

            _pyscissor_obj = pyscissor.scissor(_shapely_obj, self.lats, self.lons)

            _weight_grid = _pyscissor_obj.get_masked_weight_recursive()

            for day in range(self._lead_day):

                sid = day * self._daily_step
                eid = sid + self._daily_step

                rh_day = np.average(_rh_all[sid:eid + 1, :, :], axis=0)

                if not np.ma.is_masked(rh_day):
                    rh_day = np.ma.masked_array(rh_day.data, mask=_weight_grid.mask)

                rh_day.mask = rh_day.mask | rh_day.mask

                value = rh_day.mean()

                _shape_data['time'].append([
                    self.times[sid].strftime(self._date_format),
                    self.times[eid].strftime(self._date_format)
                ])

                _shape_data['value'].append(np.round(value, 2))

            data['r_data'][_unique_name] = _shape_data

        return data

