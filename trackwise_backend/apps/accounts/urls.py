from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    path('register/',         views.RegisterView.as_view(),          name='register'),
    path('login/',            views.LoginView.as_view(),             name='login'),
    path('verify-otp/',       views.VerifyOTPView.as_view(),         name='verify-otp'),
    path('resend-otp/',       views.ResendOTPView.as_view(),         name='resend-otp'),
    path('logout/',           views.LogoutView.as_view(),            name='logout'),
    path('token/refresh/',    views.CustomTokenRefreshView.as_view(),name='token-refresh'),
    path('me/',               views.MeView.as_view(),                name='me'),
    path('profile/',          views.ProfileView.as_view(),           name='profile'),
    path('change-password/',  views.ChangePasswordView.as_view(),    name='change-password'),
    path('forgot-password/',  views.ForgotPasswordView.as_view(),    name='forgot-password'),
    path('reset-password/',   views.ResetPasswordView.as_view(),     name='reset-password'),
    path('verify-email/',     views.VerifyEmailView.as_view(),       name='verify-email'),
    path('account/',          views.DeleteAccountView.as_view(),     name='delete-account'),
]
