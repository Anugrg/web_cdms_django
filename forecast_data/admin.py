from django.contrib import admin

from .models import *
# Register your models here.

admin.site.register(system_state)
admin.site.register(forecast_source)