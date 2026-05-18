from .models import UserProfile


def user_role_flags(request):
    user = request.user
    is_site_admin_user = False

    if user.is_authenticated:
        is_site_admin_user = user.is_staff or user.is_superuser
        if not is_site_admin_user:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            is_site_admin_user = profile.role == UserProfile.Role.ADMIN

    return {
        'is_site_admin_user': is_site_admin_user,
        'is_customer_user': user.is_authenticated and not is_site_admin_user,
    }
