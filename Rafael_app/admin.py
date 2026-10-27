from django.contrib import admin

from .models import AdminAuditLog, MovieVerse, UserProfile


@admin.register(MovieVerse)
class MovieVerseAdmin(admin.ModelAdmin):
    list_display = ("title_name", "owner", "genre", "release_year", "rating", "date_added")
    list_filter = ("genre", "type", "status")
    search_fields = ("title_name", "genre", "owner__username")
    readonly_fields = ("date_added",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "avatar_url")
    search_fields = ("user__username", "user__email")


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "target", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "target")
    readonly_fields = ("actor", "action", "target", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
