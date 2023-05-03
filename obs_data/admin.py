from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(station)
admin.site.register(obs_data)
admin.site.register(parameter)
admin.site.register(level)