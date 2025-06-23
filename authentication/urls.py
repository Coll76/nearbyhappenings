from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('auth/token/', views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/register-planner/', views.EventPlannerRegistrationView.as_view(), name='register_planner'),
    path('auth/validate-token/', views.ValidationTokenView.as_view(), name='validate_token'),
    path('auth/profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('auth/planners/', views.EventPlannerListView.as_view(), name='planner_list'),
    path('auth/planners/<int:pk>/', views.EventPlannerDetailView.as_view(), name='planner_detail'),
    # New endpoint for notifications

]
