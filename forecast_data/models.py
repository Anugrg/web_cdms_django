from django.db import models

# Create your models here.

class forecast_source(models.Model):

    name = models.CharField('short name of forecast source', unique=True, max_length=255)
    full_name = models.CharField('full name for forecast source', max_length=255)
    lead_time = models.IntegerField('lead time in hours')
    fcst_type = models.CharField("type of forecast eps/single",max_length=255)
    center = models.CharField('center producing forecast', max_length=255, default='')    
    
    def __str__(self):
        return f'{self.name} // {self.lead_time}'

    class Meta:
        verbose_name_plural = "Forecast Source"
        indexes = [
            models.Index(fields=['name']),
        ]
    

class system_state(models.Model):

    state_name = models.CharField("name of the state", unique=True, max_length=128)
    init_time = models.CharField(
            'date and sim utc time of forecast source format yyyymmdd_hh ', 
            max_length=32
        )
    source = models.ForeignKey(forecast_source, on_delete=models.CASCADE)
    info = models.JSONField("additional info of the state, like netcdf header", default=dict)
    updated_at = models.DateTimeField('field update time', auto_now=True)

    def __str__(self):
        return f'{self.state_name} // {self.init_time} // {self.source.name}'

    class Meta:
        verbose_name_plural = "System State"
        indexes = [
            models.Index(fields=['state_name']),
        ]
    
