from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('catalog/<slug:slug>/', views.product_detail, name='product_detail'),
    path('catalog/<slug:slug>/order/', views.order_create, name='order_create'),
    path('search/', views.search, name='search'),
    path('requests/new/', views.request_create, name='request_create'),
    path('documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<int:pk>/download/', views.document_download, name='document_download'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/login/', auth_views.LoginView.as_view(authentication_form=LoginForm), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/profile/', views.profile_edit, name='profile_edit'),
    path('dashboard/orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('site-admin/', views.site_admin_dashboard, name='site_admin_dashboard'),
    path('site-admin/users/', views.site_admin_users, name='site_admin_users'),
    path('site-admin/users/<int:pk>/update/', views.site_admin_user_update, name='site_admin_user_update'),
    path('site-admin/catalog/', views.site_admin_catalog, name='site_admin_catalog'),
    path('site-admin/catalog/products/new/', views.site_admin_product_create, name='site_admin_product_create'),
    path('site-admin/catalog/products/<int:pk>/edit/', views.site_admin_product_update, name='site_admin_product_update'),
    path('site-admin/catalog/categories/new/', views.site_admin_category_create, name='site_admin_category_create'),
    path('site-admin/requests/', views.site_admin_requests, name='site_admin_requests'),
    path('site-admin/requests/<int:pk>/update/', views.site_admin_request_update, name='site_admin_request_update'),
    path('site-admin/orders/', views.site_admin_orders, name='site_admin_orders'),
    path('site-admin/orders/<int:pk>/', views.site_admin_order_detail, name='site_admin_order_detail'),
    path('site-admin/orders/<int:pk>/update/', views.site_admin_order_update, name='site_admin_order_update'),
    path('site-admin/documents/', views.site_admin_documents, name='site_admin_documents'),
]
