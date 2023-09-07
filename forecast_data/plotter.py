import io

import numpy as np
import matplotlib.animation as animation
from matplotlib import pyplot as plt
from matplotlib import use as plot_backend
import cartopy.io.shapereader as shpreader
from cartopy.feature import ShapelyFeature
from cartopy import crs as ccrs
from cartopy import feature as cfeature


from django.conf import settings

'''
set backend and rc_params for
consistent machine to machine
plot generation
'''

plot_backend('Agg')
plt.style.use('fast')
plt.rcParams['figure.dpi'] = settings.PLOT_DPI
plt.rcParams['savefig.dpi'] = 'figure'
plt.rcParams['savefig.bbox'] = 'tight'
# setting inconsolata as default font for plotting
plt.rcParams['font.family'] = \
    plt.rcParams['font.sans-serif'] = \
    plt.rcParams['font.monospace'] = 'Inconsolata'


class animator:
    """
    Create an animated graph of a parameter
    comprising all forecast dates
    """

    def __init__(
        self, data, name,
        date_info, unit_label,
        max_val, min_val, ext,
        cmap, levels, lat_crop,
        lon_crop, frames, quantile=None
    ):
        self.lat = lat_crop
        self.lon = lon_crop
        self.data = data
        self.name = name
        self.quantile = quantile
        self.max_val = max_val
        self.date_info = date_info
        self.min_val = min_val
        self.extend = ext
        self.levels = levels
        self.unit_label = unit_label
        self.cmap = cmap
        self.fig = plt.figure(figsize=(12, 8))
        self.ax = self.fig.subplots(
            subplot_kw={'projection': ccrs.PlateCarree()}
        )
        self.states = cfeature.NaturalEarthFeature(
            category='cultural',
            name='admin_1_states_provinces_lines',
            scale='10m',
            facecolor='none'
        )
        self.ax.add_feature(cfeature.COASTLINE, linewidth=1)
        self.ax.add_feature(
            self.states, edgecolor='black', linewidth=0.3
        )
        self.ax.add_feature(cfeature.BORDERS, linewidth=1)
        self.ax.patch.set_edgecolor('black')
        self.ax.patch.set_linewidth('1')
        self.xticks = np.arange(lon_crop[0]+2, lon_crop[-1], 5, dtype=int)
        self.yticks = np.arange(lat_crop[-1]+2, lat_crop[0], 5, dtype=int)
        self.gl = self.ax.gridlines(
            color="black", linestyle="dotted",
            draw_labels=True, xlocs=self.xticks,
            ylocs=self.yticks
        )
        self.gl.top_labels = self.gl.right_labels = False
        self.ani = animation.FuncAnimation(self.fig, self.animate,
                                           frames, interval=1000, blit=False,
                                           init_func=self.init_animation,
                                           repeat=False)

    def draw(self, frame, add_colorbar):

        grid = self.data[frame]
        plt.rcParams["font.family"] = "Ubuntu Mono"
        plt.rcParams['font.size'] = '11'
        if frame != 0:
            self.ax.cla()
            self.set_axes_props()

        contour = self.ax.contourf(
            self.lon, self.lat, grid,
            vmin=self.min_val, vmax=self.max_val,
            levels=self.levels, cmap=self.cmap,
            extend=self.extend
        )
        time = (str(self.date_info[frame]['start_time'])
                + " to " + str(self.date_info[frame]['end_time']))
        title = ""
        if self.quantile:
            title = f'{self.name}_{self.quantile}, {time}'
        else:
            title = f'{self.name}, {time}'

        if add_colorbar:
            cbar = plt.colorbar(contour, ax=self.ax, orientation='vertical',
                                pad=0.15, aspect=16,
                                shrink=1.0, drawedges=True)
            cbar.set_label(f'{self.unit_label}')

        self.ax.set_title(title)
        return contour

    def init_animation(self):
        """
        Initialize the first frame of the video
        """
        return self.draw(0, add_colorbar=True)

    def animate(self, frame):
        return self.draw(frame, add_colorbar=False)

    def convert_to_html_vid(self):
        video_data = self.ani.to_html5_video()
        data = video_data.replace("width=\"1200\"", "width=\"1100\"")
        return data

    def set_axes_props(self):
        self.ax.add_feature(cfeature.COASTLINE, linewidth=1)
        self.ax.add_feature(
                self.states, edgecolor='black', linewidth=0.3
        )
        self.ax.add_feature(cfeature.BORDERS, linewidth=1)
        self.ax.patch.set_edgecolor('black')
        self.ax.patch.set_linewidth('1')
        self.xticks = np.arange(self.lon[0]+2, self.lon[-1], 5, dtype=int)
        self.yticks = np.arange(self.lat[-1]+2, self.lat[0], 5, dtype=int)
        self.gl = self.ax.gridlines(
            color="black", linestyle="dotted",
            draw_labels=True, xlocs=self.xticks,
            ylocs=self.yticks
        )
        self.gl.top_labels = self.gl.right_labels = False

    def __del__(self):
        plt.close()


class grapher:
    """
    Create a single day plot of a parameter
    values using matplotlib
    """

    def __init__(
        self, data,
        lon_crop, lat_crop,
        name, fcst_time,
        levels, ext, cname,
        unit_label, quantile=None
    ):
        self.fig = plt.figure(figsize=(8, 5))
        self.ax = self.fig.subplots(
            subplot_kw={'projection': ccrs.PlateCarree()}
        )
        self.unit_label = unit_label
        states = cfeature.NaturalEarthFeature(
            category='cultural',
            name='admin_1_states_provinces_lines',
            scale='10m',
            facecolor='none'
        )
        self.cfp = plt.contourf(lon_crop, lat_crop,
                                data, cmap=cname,
                                levels=levels, extend=ext)
        if quantile:
            plt.title(f'{name}_{quantile}, {fcst_time}', pad=8.8)
        else:
            plt.title(f'{name}, {fcst_time}', pad=8.8)

        self.ax.add_feature(states, edgecolor='black', linewidth=0.3)
        self.ax.add_feature(cfeature.BORDERS, linewidth=1)
        self.ax.add_feature(cfeature.COASTLINE, linewidth=1)
        xticks = np.arange(lon_crop[0]+2, lon_crop[-1], 5, dtype=int)
        yticks = np.arange(lat_crop[-1]+2, lat_crop[0], 5, dtype=int)
        self.gl = self.ax.gridlines(
            color="black", linestyle="dotted",
            draw_labels=True, xlocs=xticks, ylocs=yticks
        )
        self.gl.top_labels = self.gl.right_labels = False
        self.setup_color_bar()

    def save_graph(self):
        buf = io.BytesIO()
        self.fig.savefig(buf, format='png')
        buf.seek(0)
        return buf

    def setup_color_bar(self):
        cax = self.fig.add_axes(
            [
                self.ax.get_position().x1+0.01,
                self.ax.get_position().y0,
                0.02,
                self.ax.get_position().height
            ]
        )
        cbar = plt.colorbar(self.cfp, cax=cax)


        cbar.set_label(self.unit_label, labelpad=0)

    def __del__(self):
        plt.close(self.fig)



# Refactor future: will merge shpgrapher and shpanimator with above classes

class ShpGrapher:

    def __init__(
        self,
        data,
        shpfile,
        lon_crop,
        lat_crop,
        name,
        fcst_time,
        levels,
        ext,
        cname,
        unit_label,
        quantile=None
    ):
        self.fig = plt.figure(figsize=(8, 5))
        self.ax = self.fig.subplots(
            subplot_kw={'projection': ccrs.PlateCarree()}
        )
        self.unit_label = unit_label
        self.reader = shpreader.Reader(shpfile)
        shape_feature = ShapelyFeature(
            self.reader.geometries(),
            ccrs.PlateCarree(),
            facecolor='none',
            edgecolor='black',
            lw=1
        )
        self.ax.add_feature(shape_feature)
        self.cfp = self.ax.contourf(
                lon_crop,
                lat_crop,
                data,
                cmap=cname,
                levels=levels,
                extend=ext
            )
        if quantile:
            plt.title(f'{name}_{quantile}, {fcst_time}', pad=8.8)
        else:
            plt.title(f'{name}, {fcst_time}', pad=8.8)
        self.gl = self.ax.gridlines(
            color="black", linestyle="dotted",
            draw_labels=True  # xlocs=xticks, ylocs=yticks
        )
        self.gl.top_labels = self.gl.right_labels = False

        self.setup_color_bar()

    def setup_color_bar(self):
        cax = self.fig.add_axes(
            [
                self.ax.get_position().x1+0.01,
                self.ax.get_position().y0,
                0.02,
                self.ax.get_position().height
            ]
        )
        cbar = plt.colorbar(self.cfp, cax=cax)
        cbar.set_label(self.unit_label, labelpad=0)

    def save_graph(self):
        buf = io.BytesIO()
        self.fig.savefig(buf, format='png')
        buf.seek(0)
        return buf

    def __del__(self):
        plt.close(self.fig)


class ShpAnimator:
    """
    Create an animated graph of a parameter
    comprising of all forecast dates
    using shp file as base
    """

    def __init__(
        self,
        data,
        shpfile,
        name,
        date_info, unit_label,
        max_val, min_val, ext,
        cmap, levels, lat_crop,
        lon_crop, frames, quantile=None
    ):
        self.lat = lat_crop
        self.lon = lon_crop
        self.data = data
        self.name = name
        self.reader = shpreader.Reader(shpfile)
        self.shape_feature = ShapelyFeature(
            self.reader.geometries(),
            ccrs.PlateCarree(),
            facecolor='none',
            edgecolor='black',
            lw=1
        )
        self.quantile = quantile
        self.max_val = max_val
        self.date_info = date_info
        self.min_val = min_val
        self.extend = ext
        self.levels = levels
        self.unit_label = unit_label
        self.cmap = cmap
        self.fig = plt.figure(figsize=(12, 8))
        self.ax = self.fig.subplots(
            subplot_kw={'projection': ccrs.PlateCarree()}
        )
        self.ax.add_feature(self.shape_feature)
        self.gl = self.ax.gridlines(
            color="black",
            linestyle="dotted",
            draw_labels=True
        )
        self.gl.top_labels = self.gl.right_labels = False
        self.ani = animation.FuncAnimation(self.fig, self.animate,
                                           frames, interval=1000, blit=False,
                                           init_func=self.init_animation,
                                           repeat=False)

    def draw(self, frame, add_colorbar):
        grid = self.data[frame]
        plt.rcParams["font.family"] = "Ubuntu Mono"
        plt.rcParams['font.size'] = '11'
        if frame != 0:
            self.ax.cla()
            self.set_axes_props()

        contour = self.ax.contourf(
                self.lon, self.lat, grid,
                vmin=self.min_val, vmax=self.max_val,
                levels=self.levels, cmap=self.cmap,
                extend=self.extend
        )
        time = (str(self.date_info[frame]['start_time'])
                + " to " + str(self.date_info[frame]['end_time']))
        title = ""
        if self.quantile:
            title = f'{self.name}_{self.quantile}, {time}'
        else:
            title = f'{self.name}, {time}'

        if add_colorbar:
            cbar = plt.colorbar(contour, ax=self.ax, orientation='vertical',
                                pad=0.15, aspect=16,
                                shrink=1.0, drawedges=True)
            cbar.set_label(f'{self.unit_label}')

        self.ax.set_title(title)
        return contour

    def init_animation(self):
        """
        Initialize the first frame of the video
        """
        return self.draw(0, add_colorbar=True)

    def animate(self, frame):
        return self.draw(frame, add_colorbar=False)

    def convert_to_html_vid(self):
        video_data = self.ani.to_html5_video()
        data = video_data.replace("width=\"1200\"", "width=\"1100\"")
        return data

    def set_axes_props(self):
        self.ax.add_feature(self.shape_feature)
        self.gl = self.ax.gridlines(
            color="black",
            linestyle="dotted",
            draw_labels=True
        )
        self.gl.top_labels = self.gl.right_labels = False

    def __del__(self):
        plt.close(self.fig)