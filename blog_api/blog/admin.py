from django.contrib import admin
from .models import Post, Comment, Category, Tag, Like, Bookmark


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'category', 'views_count', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'content', 'author__username']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['author']
    filter_horizontal = ['tags']
    readonly_fields = ['views_count', 'created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'parent', 'is_deleted', 'created_at']
    list_filter = ['is_deleted', 'created_at']
    search_fields = ['content', 'author__username']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
