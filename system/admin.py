from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Fields to display in the list view
    list_display = ('email', 'full_name', 'phone_number', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')

    # Fields for the add/edit user forms in admin
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone_number')}),
        ('Roles & Permissions', {'fields': ('role', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fields for the user creation form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'full_name',
                'phone_number',
                'role',
                'password1',
                'password2',
                'is_staff',
                'is_superuser',
                'is_active'
            ),
        }),
    )

    search_fields = ('username', 'email', 'full_name', 'phone_number')
    ordering = ('email',)
