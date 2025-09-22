from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, CustomerProfile, ArtistProfile
from .forms import CustomUserCreationForm, CustomUserChangeForm

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom user admin following Django conventions."""
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = ['username', 'email', 'first_name', 'last_name', 'user_type', 'is_active']
    list_filter = ['user_type', 'is_active', 'is_staff', 'date_joined']
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('user_type', 'phone', 'email_verified')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('email', 'first_name', 'last_name', 'user_type')}),
    )
    search_fields = ['username', 'email', 'first_name', 'last_name']

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Customer profile admin following Django conventions."""
    list_display = ['user', 'parish', 'created_at']
    list_filter = ['parish', 'marketing_consent', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ArtistProfile)
class ArtistProfileAdmin(admin.ModelAdmin):
    """Artist profile admin following Django conventions."""
    list_display = ['display_name', 'user', 'is_approved', 'commission_rate', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['display_name', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_artists']
    
    def approve_artists(self, request, queryset):
        """Bulk approve artists."""
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} artist(s) approved successfully.')
    approve_artists.short_description = 'Approve selected artists'
