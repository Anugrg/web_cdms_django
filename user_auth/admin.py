from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.db.models import query
from django.db.models.fields import CharField
from django.forms import fields, models
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from user_auth.models import CdmsUser
from django.contrib.auth.forms import ReadOnlyPasswordHashField
import json

# Register your models here.


def generate_perm(
        obs_r: bool,
        obs_w: bool,
        fcst_graph: bool,
        fcst_analysis: bool,
        fcst_subset: bool
) -> dict:
    permission = {
        'obs_r': bool(obs_r),
        'obs_w': bool(obs_w),
        'fcst_graph': bool(fcst_graph),
        'fcst_analysis': bool(fcst_analysis),
        'fcst_subset': bool(fcst_subset)
    }
    return permission


class cdms_user_create_form(forms.ModelForm):
    class Meta:
        model = CdmsUser
        fields = '__all__'

    password1 = forms.CharField(label='Password1', widget=forms.PasswordInput)

    obs_r = fields.MultipleChoiceField(
        label="Allow Observed Data Read",
        widget=forms.SelectMultiple(attrs={'style': 'width:350px'}),
        required=True
    )

    obs_w = fields.MultipleChoiceField(
        label="Allow Observed Data Write",
        widget=forms.SelectMultiple(attrs={'style': 'width:350px'}),
        required=True
    )

    fcst_graph = fields.BooleanField(label="Allow Graphics Engine", required=False)
    fcst_analysis = fields.BooleanField(label="Allow Analysis Engine", required=False)
    fcst_subset = fields.BooleanField(label="Allow Subsetting Engine", required=False)

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

    def clean(self):
        try:
            obs_r, obs_w, fcst_graph, fcst_analysis, fcst_subset = self.cleaned_data['obs_r'], self.cleaned_data[
                'obs_w'], self.cleaned_data['fcst_graph'], self.cleaned_data['fcst_analysis'], self.cleaned_data[
                'fcst_subset']
        except KeyError as err:
            raise ValidationError((f'select a choice in {str(err)}'))

        permission = generate_perm(fcst_graph, fcst_analysis, fcst_subset)

        self.cleaned_data['permission'] = permission

    def save(self, commit=True):

        user = super(cdms_user_create_form, self).save(commit=False)

        user.set_password(self.cleaned_data['password1'])

        user.permission = self.cleaned_data['permission']

        if commit:
            user.save()

        return user


class cdms_user_change_form(forms.ModelForm):
    class Meta:
        model = CdmsUser
        fields = '__all__'

    password = ReadOnlyPasswordHashField(label=("Password"),
                                         help_text=("Raw passwords are not stored, so there is no way to see "
                                                    "this user's password, but you can change the password "
                                                    "using <a href=\"../password/\">this form</a>."))

    obs_r = fields.BooleanField(
        label="Allow Observed Data Read",
        required=True
    )

    obs_w = fields.BooleanField(
        label="Allow Observed Data Write",
        required=True
    )

    fcst_graph = fields.BooleanField(label="Allow Graphics Engine", required=False)
    fcst_analysis = fields.BooleanField(label="Allow Analysis Engine", required=False)
    fcst_subset = fields.BooleanField(label="Allow Subsetting Engine", required=False)

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields['obs_r'].initial = self.instance.permission['obs_r']
            self.fields['obs_w'].initial = self.instance.permission['obs_w']

            self.fields['fcst_graph'].initial = self.instance.permission['fcst_graph']
            self.fields['fcst_analysis'].initial = self.instance.permission['fcst_analysis']
            self.fields['fcst_subset'].initial = self.instance.permission['fcst_subset']

    def clean_password(self):
        return self.initial["password"]

    def clean(self):

        obs_r = self.cleaned_data['obs_r']
        obs_w = self.cleaned_data['obs_w']
        fcst_graph, fcst_analysis, fcst_subset = self.cleaned_data['fcst_graph'], self.cleaned_data['fcst_analysis'], \
            self.cleaned_data['fcst_subset']

        permission = generate_perm(obs_r, obs_w, fcst_graph, fcst_analysis, fcst_subset)

        self.cleaned_data['permission'] = permission

    def save(self, commit=True):

        user = super(cdms_user_change_form, self).save(commit=False)

        user.permission = self.cleaned_data['permission']

        if commit:
            user.save()

        return user

class cdms_user_admin(UserAdmin):

    form = cdms_user_change_form
    add_form = cdms_user_create_form

    list_display = ('name', 'email', 'date_joined', 'last_login', 'is_admin',)
    list_filter = ('name', 'email', 'is_admin')
    search_fields = ('email',)
    ordering = ('name',)
    filter_horizontal = ()

    # for updating user
    fieldsets = (
        ('User Information', {'fields': ('name', 'password', 'is_admin', 'is_superuser', 'is_staff')}),
        ('User Permission', {'fields': ('obs_r', 'obs_w', 'fcst_graph', 'fcst_analysis', 'fcst_subset')}),

    )

    # for creating new user
    add_fieldsets = (
        ('User Information',
         {'fields': ('name', 'email', 'password1', 'is_admin', 'is_superuser', 'is_staff')}),
        ('User Permission', {'fields': ('obs_r', 'obs_w', 'fcst_graph', 'fcst_analysis', 'fcst_subset')}),
    )

admin.site.register(CdmsUser, cdms_user_admin)

