from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    LogoutView,
    ProfileView,
    PublicProfileView,
)

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Profile
    path('profile/', ProfileView.as_view(), name='auth-profile'),
    path('users/<str:username>/', PublicProfileView.as_view(), name='public-profile'),
]
