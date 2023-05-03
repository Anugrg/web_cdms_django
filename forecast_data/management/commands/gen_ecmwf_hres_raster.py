#!/usr/bin/env python3
'''
Generate JSON data for ECMWF HERS forecast

- Temporal Reduction : Daily 
- Stream Name        : R1Dxxx
- Lead Time          : 10 Day

Author: Nazmul Ahasan
email: nazmul@rimes.int / nzahasan@gmail.com

'''
import os
import json
import numpy as np
from django.conf import settings
from forecast_data.models import *  
from netCDF4 import Dataset as nco, num2date as n2d
from django.core.management.base  import BaseCommand, CommandError
from datetime import datetime as dt
from  yaspin import yaspin


class Command(BaseCommand):

    help="generate raster of ecmwf hres forecast"

    source = 'ECMWF_HRES'
    sys_state = 'ECMWF_HRES_VIS'
    source_obj = forecast_source.objects.get(name=source)
    daily_step = 4
    lead_day = 10
    sim_time = 0 # simulation utc time
    root_path = os.path.join(settings.FCST_JSONOUT,source)
    
    temp_cinf = {
        'name':'plasma',
        'stops': 100,
        'extend_min': True,
        'extend_max': True,
        'reversed': False,
        'range':[-10,45]
    }

    rh_cinf = {
        'name': 'summer',
        'stops': 100,
        'extend_min': True,
        'extend_max': True,
        'reversed': True,
        'range':[5,95]
    }

    rf_cinf = {
        'name': 'Spectral',
        'stops': 100,
        'extend_min': False,
        'extend_max': True,
        'reversed': True,
        'range':[1,250]
    }

    ws_cinf = {
        'name': 'YlGnBu',
        'stops': 100,
        'extend_min': True,
        'extend_max': True,
        'reversed': False,
        'range':[1,110]
    }

    finfo = {
        'time':[],
        'params':{
            'rf': {
                'fullname':'Rainfall',
                'unit':'mm',
                'cinf': rf_cinf,
                'fa_icon':'fal fa-raindrops',
            },
            'tmin': { 
                'fullname':'Temperature Min',
                'unit':'°C',
                'cinf': temp_cinf,
                'fa_icon':'fal fa-thermometer-quarter',
            },
            'tmax': {
                'fullname':'Temperature Max',
                'unit':'°C',
                'cinf': temp_cinf,
                'fa_icon':'fal fa-thermometer-three-quarters',
            },
            'wsavg': {
                'fullname':'Wind Speed Avg',
                'unit':'kmph',
                'cinf': ws_cinf,
                'fa_icon':'fal fa-wind',
            },

            'rhavg': {
                'fullname':'Relative Humidity Avg',
                'unit':'%',
                'cinf': rh_cinf,
                'fa_icon':'fal fa-humidity',
            },
        },
        
        'file_suffix' :[]
    }

    def add_arguments(self, parser):
        parser.add_argument('date', type=str, help="forecast date in yyyymmdd format")


    def handle(self,*args,**kwargs):

        try:        
            date_obj = dt.strptime(kwargs['date'],'%Y%m%d')
            with yaspin() as ysp:
                ysp.text = "Processing ECMWF_HRES_VIS. "
                self.gen_hres_raster_json(date_obj)
        except Exception as e:
            print(e)

    def update_state(self,forecast_date):
        # update system state

        if system_state.objects.filter(state_name=self.sys_state,source=self.source_obj).count():
            print('State exists. updating..')
            state = system_state.objects.get(state_name=self.sys_state,source=self.source_obj)
            state.init_time = forecast_date
            state.save()
        else:
            print('State dosent exists. Creating..')
            system_state(state_name=self.sys_state,source=self.source_obj,init_time=forecast_date).save()			



    def save_ufgrid(self, lats:np.ndarray, lons:np.ndarray, 
                    arr2d:np.ndarray, nodata_val:float, lat_desc:bool, 
                    scale_factor:float, out_file:str,force_min=None):

        data = dict()

        data['nx'] = lons.shape[0]
        data['ny'] = lats.shape[0]
        
        data['dx'] = np.abs(np.diff(lons,n=1).mean()).item()
        data['dy'] = np.abs(np.diff(lats,n=1).mean()).item()

        data['xll_center'] = lons[0].item()
        data['yll_center'] = lats[-1].item()

        data['nodata'] = nodata_val

        data['min'] = arr2d.min().item() if force_min==None else force_min
        data['max'] = arr2d.max().item()

        data['sf'] = scale_factor

        data['data'] = (arr2d.flatten()*scale_factor).astype(int).tolist(fill_value=-9999*scale_factor)

        with open(os.path.join(self.outpath,out_file),'w') as wf:
            json.dump(data,wf,separators=(',', ':'))
            return True 

        return False



    def calc_rh(self, temp:np.ndarray, dewtemp:np.ndarray)->np.ndarray:

        ''' 
        Using, August–Roche–Magnus approximation
        RH = 100*( EXP( (17.625*TD) / (243.04+TD) ) / EXP( (17.625*T) / (243.04+T) ) )

        a = 17.625
        b = 243.04

        ** 6.1094 ommited cause will calucate fraction later
        es_td = (a*TD)/(b+TD)
        es_t  = (a*T) /(b+T)

        RH = 100*( exp(es_td) / exp(es_t) ) 
        '''
        a = 17.625
        b = 243.04

        es_td = (a * dewtemp) / (b + dewtemp)
        es_t  = (a * temp)    / (b + temp)

        return 100 * ( np.exp(es_td) / np.exp(es_t) )
        
        
    def gen_hres_raster_json(self,date_obj:dt):
        
        
        nc_filename = date_obj.strftime(settings.ECMWF_HRES_NC)

        nf = nco(nc_filename,'r')

        nclats = nf.variables['latitude'][:]
        nclons = nf.variables['longitude'][:]
        
        bottom_lat, top_lat, left_lon, right_lon = 5.725, 10.16, 79.23, 82.35
        lat_indices, lon_indices = np.where((nclats >= bottom_lat) & (nclats <= top_lat)), np.where((nclons >= left_lon) & (nclons <= right_lon))
        lats, lons = nclats[lat_indices], nclons[lon_indices]
        
        times = n2d(nf.variables['time'][:],nf.variables['time'].units)

        adate  = times[0].strftime('%Y%m%d_%H')
        
        self.outpath = os.path.join(self.root_path,adate)

        # create path if not exists
        if not os.path.exists(self.outpath): os.makedirs(self.outpath)
        
        # check if if grid is regular
        if np.diff(lats,n=2).all() != 0 or np.diff(lons,n=2).all() != 0:
            print('warning: non regular grid')

        lat_desc = True 

        if lats[1]-lats[0] > 0:
            lat_desc = False

        rf = (nf.variables['lsp'][:] + nf.variables['cp'][:])*1000 # m2mm : *1000
        
        temp = nf.variables['t2m'][:] - 273.15 # k2dc : -273.15
        
        ws = np.sqrt( np.square(nf.variables['u10'][:]) + np.square(nf.variables['v10'][:]) ) * 3.6

        dewtemp = nf.variables['d2m'][:] - 273.15
        
        rh = self.calc_rh(temp, dewtemp)


        for iday in range(self.lead_day):
            
            start_idx = iday * self.daily_step
            end_idx = start_idx + self.daily_step

            if iday==0:
                rf_day = rf[end_idx,:,:]
            else:
                rf_day = rf[end_idx,:,:] - rf[start_idx,:,:]
            tmin_day = np.amin(temp[start_idx:end_idx+1,:,:], axis=0)
            tmax_day = np.amax(temp[start_idx:end_idx+1,:,:], axis=0)
            wsavg_day = np.average(ws[start_idx:end_idx+1,:,:], axis=0)
            rhavg_day = np.average(rh[start_idx:end_idx+1,:,:], axis=0)

            # print(rf_day.sum())
            # return
            file_suffix = f'{adate}.d{iday:02d}.json'

            # save parameter
            
            self.save_ufgrid(lats, lons, tmin_day, -9999, True, 100, f'tmin.{file_suffix}')
            self.save_ufgrid(lats, lons, tmax_day, -9999, True, 100, f'tmax.{file_suffix}')
            self.save_ufgrid(lats, lons, rf_day, -9999, True, 100, f'rf.{file_suffix}')
            self.save_ufgrid(lats, lons, wsavg_day, -9999, True, 100, f'wsavg.{file_suffix}')
            self.save_ufgrid(lats, lons, rhavg_day, -9999, True, 100, f'rhavg.{file_suffix}')

            # finfo
            self.finfo['time'].append({
                'start_time': times[start_idx].strftime('%d-%b_%H'),
                'end_time': times[end_idx].strftime('%d-%b_%H'),
            }) 

            self.finfo['file_suffix'].append(file_suffix) 


            # print(FileNotFoundError())

        with open(os.path.join(self.outpath,'finfo.json'),'w') as wf:
            json.dump(self.finfo, wf)

        # update state
        
        self.update_state(adate)


