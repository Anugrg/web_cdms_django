from django.db import models
from datetime import timedelta

# Create your models here.


class parameter(models.Model):

    INST, ACCM, MIN, MAX, AVG = "INST", "ACCM", "MIN", "MAX", "AVG"
    
    # value, view  
    PARAM_TYPES = (
        (INST, "Instant"),
        (ACCM, "Accumulated"),
        (MIN,  "Minimum"),
        (MAX,  "Maximum"),
        (AVG,  "Average"),
    )

    name = models.CharField('Parameter short Name', unique=True, max_length=512)
    full_name = models.CharField('Parameter full name', max_length=512)
    unit = models.CharField('Parameter unit', max_length=32)
    parameter_type = models.CharField(choices=PARAM_TYPES, max_length=512) 

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "parameter"
        indexes = [
            models.Index(fields=['name'])
        ]


class level(models.Model):

    name = models.CharField('Level short name', max_length=32)
    full_name = models.CharField('Full name of level', max_length=128)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "level"
        indexes = [
            models.Index(fields=['name'])
        ]


class station(models.Model):

    # an agromet station is a meteorological station
    METEOROLOGICAL, HYDROLOGICAL, AGROMETEOROLOGICAL = 'MET', 'HYDRO', 'AGRO'
    AUTO, MAN = 'AUTOMATIC', 'MANUAL'

    station_category = (
        (METEOROLOGICAL,'Meteorological Station'),
        (HYDROLOGICAL,'Hydrological Station'),
        (AGROMETEOROLOGICAL,'Agrometeorological Station'),
    )

    station_type = (
        (AUTO, 'AUTOMATIC STATION'),
        (MAN, 'MANUAL STATION')
    )

    name = models.CharField('Station name', max_length=512)
    full_name = models.CharField('Station full name', max_length=512)
    station_id = models.CharField('Local Station id', max_length=512, default='', blank=True)
    wmo_id = models.CharField('WMO Station id', max_length=512, default='', blank=True)
    
    lat = models.FloatField('Station latitude')
    lon = models.FloatField('Station longitude')
    elevation = models.FloatField('Station elevation',null=True, default=None)
    
    station_category = models.CharField(choices=station_category, max_length=50)
    station_type = models.CharField(choices=station_type, max_length=50)

    def __str__(self):
        return f'{self.full_name}'

    class Meta:
        verbose_name_plural = "station"
        unique_together = ('name', 'wmo_id','station_id')

        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['station_id']),
            models.Index(fields=['wmo_id']),
        ]


class obs_data(models.Model):

    start_time = models.DateTimeField('observation start time')
    end_time = models.DateTimeField('observation end time')

    value = models.FloatField('value of data')

    parameter = models.ForeignKey(parameter, on_delete=models.CASCADE)
    level = models.ForeignKey(level, default=1, on_delete=models.CASCADE)
    station = models.ForeignKey(station, on_delete=models.CASCADE)
    duration = models.DurationField(default=timedelta(seconds=86400))

    # calculate time delta of a record
    def delt(self):
        return self.end_time - self.start_time

    def __str__(self):
        return f'{self.station.name} - {self.parameter.name} - {self.level.name} - {self.value}'
    
    class Meta:
        verbose_name_plural = "observation_data"
        # to prevent multiple insert
        unique_together = ('start_time', 'end_time', 'parameter', 'level', 'station')
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['end_time']),
            models.Index(fields=['parameter']),
            models.Index(fields=['level']),
            models.Index(fields=['station']),
        ]

    def save(self, *args, **kwargs):
        if not self.duration:
            self.duration = self.delt
        
        super(obs_data, self).save(*args, **kwargs)
