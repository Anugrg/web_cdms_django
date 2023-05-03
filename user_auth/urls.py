from django.urls import path
from .views import UserLogin, UserCreate, UserProfile

urlpatterns = [

    path('login/', UserLogin.as_view(), name='user_auth.login'),
    path('sign-up/', UserCreate.as_view(), name='user_auth.sign_up'),
    path('profile/', UserProfile.as_view(), name='user_auth.profile')
]