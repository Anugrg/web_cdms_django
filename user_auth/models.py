from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# Create your models here.


class AccountManager(BaseUserManager):

    def create_user(self, email, name, password=None):
        print(email,name)
        if not email:
            raise ValueError('email must be provided')

        user = self.model(
            self.normalize_email(email),
            name=name
        )
        user.set_password(password)
        user.save(self._db)

        return user 

    def create_superuser(self, email, name, password=None):
        
        if not email:
            raise ValueError('email must be provided')

        user = self.model(
            email=self.normalize_email(email),
            name=name
        )

        user.set_password(password)
        user.is_admin = True
        user.is_active = True 
        user.is_staff = True
        user.save(self._db)
        return user 


def initial_user_permission():
    return {
        'obs_r': [], 
        'obs_w': [],       
        'fcst_graph': False, 
        'fcst_analysis': False, 
        'fcst_subset': False
    }


class CdmsUser(AbstractBaseUser):

    name = models.CharField('name of user',max_length=255)
    email = models.EmailField('email address', unique=True)
    date_joined = models.DateTimeField('user creation date', auto_now_add=True)
    
    is_admin = models.BooleanField('is a admin', default=False)
    is_staff = models.BooleanField('is a staff', default=False)
    is_superuser = models.BooleanField('if a superuser', default=False)

    permission = models.JSONField('user permission', default = initial_user_permission)
    reset_code = models.CharField('password reset code', max_length=32, null=True, default=None, editable=False)

    objects = AccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def has_perm(self,prm,obj=None):
        return self.is_active and self.is_admin

    def has_module_perms(self,app_level):
        return self.is_active and self.is_admin

    def __str__(self):
        return f'{self.name} // {self.email}'

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=['email']),
        ]
