from django.contrib import admin
from artworks.models import Artwork, ArtworkImage, Category

# Register Category
admin.site.register(Category)

# Register Artwork with approval actions
@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'price', 'status', 'created_at']
    list_filter = ['status', 'is_available']
    search_fields = ['title', 'description']
    actions = ['make_active', 'make_draft']
    
    def make_active(self, request, queryset):
        count = queryset.update(status='active')
        self.message_user(request, f'{count} artwork(s) made active (approved)!')
    make_active.short_description = "✅ Make selected artworks ACTIVE (approve)"
    
    def make_draft(self, request, queryset):
        count = queryset.update(status='draft')
        self.message_user(request, f'{count} artwork(s) set to DRAFT')
    make_draft.short_description = "📝 Set selected artworks to DRAFT"

# Register ArtworkImage
admin.site.register(ArtworkImage)

# Customize admin header
admin.site.site_header = "🎨 Jersey Artwork Admin"
admin.site.site_title = "Jersey Artwork Admin"
admin.site.index_title = "Marketplace Administration"
