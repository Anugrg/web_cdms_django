
import numpy as np

from forecast_anls.utils import calc_rh


class graph_processor:

    def __init__(self):
        pass


class anime_processor:

    def __init__(self):
        pass


# HRES param processors
class ecmwf_hres_graph_processor(graph_processor):
    """
    Generate hres parameter values to plot in graph
    """

    def __init__(
        self, ncfile,
        start_idx, end_idx,
        latli, latui,
        lonli, lonui
    ):
        self.ncfile = ncfile
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.latli = latli
        self.latui = latui
        self.lonli = lonli
        self.lonui = lonui
        super().__init__()

    def temperature_min(self):
        temp = self.ncfile.variables['t2m'][:] - 273.15
        tmin_day = np.amin(
            temp[
                self.start_idx:self.end_idx+1,
                self.latli:self.latui+1,
                self.lonli:self.lonui+1
            ],
            axis=0
        )
        return tmin_day

    def temperature_max(self):
        temp = self.ncfile.variables['t2m'][:] - 273.15
        tmax_day = np.amax(
            temp[
                self.start_idx:self.end_idx+1,
                self.latli:self.latui+1,
                self.lonli:self.lonui+1
            ],
            axis=0
        )
        return tmax_day

    def total_daily_rainfall(self):
        rf = (
                self.ncfile.variables['lsp'][:]
                + self.ncfile.variables['cp'][:]
            ) * 1000  # m2mm : *1000
        if self.start_idx == 0:
            rf_day = rf[
                self.end_idx,
                self.latli:self.latui+1,
                self.lonli:self.lonui+1
            ]
        else:
            rf_start = rf[
                self.start_idx,
                self.latli:self.latui+1,
                self.lonli:self.lonui+1
            ]
            rf_end = rf[
                self.end_idx,
                self.latli:self.latui+1,
                self.lonli:self.lonui+1
            ]
            rf_day = rf_end - rf_start

        return rf_day

    def wind_speed_avg(self):
        ws = np.sqrt(
            np.square(self.ncfile.variables['u10'][:])
            + np.square(self.ncfile.variables['v10'][:])
            ) * 3.6
        wsavg_day = np.average(
            ws[
                self.start_idx:self.end_idx+1,
                self.latli:self.latui+1,
                self.lonli:self.lonui+1
            ],
            axis=0
        )
        return wsavg_day

    def relative_humidity_avg(self):
        temp = self.ncfile.variables['t2m'][:] - 273.15  # k2dc : -273.15
        dewtemp = self.ncfile.variables['d2m'][:] - 273.15
        rh = calc_rh(temp, dewtemp)
        rhavg_day = np.average(
            rh[
                self.start_idx:self.end_idx+1,
                self.latli:self.latui+1,
                self.lonli:self.lonui+1
            ],
            axis=0
        )
        return rhavg_day


class ecmwf_hres_anime_processor(anime_processor):
    """
    Generate hres parameter values to plot in
    an animated graph
    """

    def __init__(
        self, ncfile, date_info,
        latli, latui, lonli, lonui
    ):
        self.ncfile = ncfile
        self.date_info = date_info
        self.latli = latli
        self.latui = latui
        self.lonli = lonli
        self.lonui = lonui

    def temperature_min(self):
        data = []
        temp = self.ncfile.variables['t2m'][:] - 273.15
        for info in self.date_info:
            tmin_day = np.amin(
                temp[
                    info['start_idx']:info['end_idx']+1,
                    self.latli:self.latui+1,
                    self.lonli:self.lonui+1
                ],
                axis=0
            )
            data.append(tmin_day)

        return data

    def temperature_max(self):
        data = []
        temp = self.ncfile.variables['t2m'][:] - 273.15
        for info in self.date_info:
            tmin_day = np.amax(
                temp[
                    info['start_idx']:info['end_idx']+1,
                    self.latli:self.latui+1,
                    self.lonli:self.lonui+1
                ],
                axis=0
            )
            data.append(tmin_day)

        return data

    def total_daily_rainfall(self):
        data = []
        rf = (self.ncfile.variables['lsp'][:]
              + self.ncfile.variables['cp'][:]) * 1000  # m2mm : *1000
        for info in self.date_info:
            if info['start_idx'] == 0:
                rf_day = rf[
                    info['end_idx'],
                    self.latli:self.latui+1,
                    self.lonli:self.lonui+1
                ]
                data.append(rf_day)
            else:
                rf_start = rf[
                    info['start_idx'],
                    self.latli:self.latui+1,
                    self.lonli:self.lonui+1
                ]
                rf_end = rf[
                    info['end_idx'],
                    self.latli:self.latui+1,
                    self.lonli:self.lonui+1
                ]
                rf_day = rf_end - rf_start
                data.append(rf_day)

        return data

    def wind_speed_avg(self):
        data = []
        ws = np.sqrt(
            np.square(self.ncfile.variables['u10'][:])
            + np.square(self.ncfile.variables['v10'][:])
            ) * 3.6

        for info in self.date_info:
            wsavg_day = np.average(
                ws[
                    info['start_idx']:info['end_idx']+1,
                    self.latli:self.latui+1,
                    self.lonli:self.lonui+1
                ],
                axis=0
            )
            data.append(wsavg_day)

        return data

    def relative_humidity_avg(self):
        data = []
        temp = self.ncfile.variables['t2m'][:] - 273.15  # k2dc : -273.15
        dewtemp = self.ncfile.variables['d2m'][:] - 273.15
        rh = calc_rh(temp, dewtemp)
        for info in self.date_info:
            rhavg_day = np.average(
                rh[
                    info['start_idx']:info['end_idx']+1,
                    self.latli:self.latui+1,
                    self.lonli:self.lonui+1
                ],
                axis=0
            )
            data.append(rhavg_day)

        return data


def gen_fcst_times(
    lead_day,
    daily_step,
    times
):
    """
    Returns forecast times for each model
    """
    date_info = []
    for iday in range(lead_day):
        start_idx = iday * daily_step
        end_idx = start_idx + daily_step
        date_info.append({
            'start_time': times[start_idx].strftime('%d-%b'),
            'end_time': times[end_idx].strftime('%d-%b'),
            'idx': f'{start_idx},{end_idx}',
            'start_idx': start_idx,
            'end_idx': end_idx
        })

    return date_info


graph_processors = {
        'ECMWF_HRES_NC': ecmwf_hres_graph_processor,
}

