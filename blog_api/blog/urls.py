from django.urls import path
from .views import (
    PostListCreateView, PostDetailView, MyPostsView,
    CommentListCreateView, CommentDetailView,
    LikeToggleView, BookmarkToggleView, MyBookmarksView,
    CategoryListCreateView, CategoryDetailView,
    TagListCreateView,
)

urlpatterns = [
    # Posts
    path('posts/', PostListCreateView.as_view(), name='post-list-create'),
    path('posts/mine/', MyPostsView.as_view(), name='my-posts'),
    path('posts/<slug:slug>/', PostDetailView.as_view(), name='post-detail'),

    # Like & Bookmark
    path('posts/<slug:slug>/like/', LikeToggleView.as_view(), name='post-like'),
    path('posts/<slug:slug>/bookmark/', BookmarkToggleView.as_view(), name='post-bookmark'),

    # Comments (nested under posts)
    path('posts/<slug:post_slug>/comments/', CommentListCreateView.as_view(), name='comment-list-create'),
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),

    # Categories & Tags
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    path('tags/', TagListCreateView.as_view(), name='tag-list'),

    # Bookmarks
    path('bookmarks/', MyBookmarksView.as_view(), name='my-bookmarks'),
]
