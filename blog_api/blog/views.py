from django.db.models import Count
from rest_framework import generics, permissions, status, filters
from django.core.cache import cache

from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Post, Comment, Category, Tag, Like, Bookmark
from .serializers import (
    PostListSerializer, PostDetailSerializer, PostCreateUpdateSerializer,
    CommentSerializer, CommentCreateSerializer,
    CategorySerializer, TagSerializer,
)
from .permissions import IsAuthorOrReadOnly
from .filters import PostFilter


# ─── Category Views ────────────────────────────────────────────────────────────

class CategoryListCreateView(generics.ListCreateAPIView):

    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Category.objects.annotate(post_count=Count('posts'))


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        return Category.objects.annotate(post_count=Count('posts'))


#Tag Views

class TagListCreateView(generics.ListCreateAPIView):
    
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        return Tag.objects.annotate(post_count=Count('posts'))


#Post Views

class PostListCreateView(generics.ListCreateAPIView):

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PostFilter
    search_fields = ['title', 'content', 'excerpt', 'tags__name', 'author__username']
    ordering_fields = ['created_at', 'published_at', 'views_count', 'title']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Post.objects.filter(status=Post.Status.PUBLISHED).select_related('author', 'category').prefetch_related('tags', 'likes', 'bookmarks', 'comments')

        from django.db.models import Q
        return Post.objects.filter(
            Q(status=Post.Status.PUBLISHED) | Q(author=user)
        ).select_related('author', 'category').prefetch_related('tags', 'likes', 'bookmarks', 'comments').distinct()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateUpdateSerializer
        return PostListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user)
        return Response(
            PostDetailSerializer(post, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    
    permission_classes = [IsAuthorOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        return Post.objects.select_related('author', 'category').prefetch_related('tags', 'likes', 'bookmarks')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PostCreateUpdateSerializer
        return PostDetailSerializer

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        return ip

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        ip = self.get_client_ip(request)

        cache_key = f"post_view_{instance.id}_{ip}"

        if request.user != instance.author:

            if not cache.get(cache_key):
                Post.objects.filter(pk=instance.pk).update(
                    views_count=instance.views_count + 1
                )

                instance.views_count += 1

                cache.set(cache_key, True, timeout=60 * 60 * 24)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = PostCreateUpdateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        post = serializer.save()
        return Response(PostDetailSerializer(post, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({'message': 'Post deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


class MyPostsView(generics.ListAPIView):
    
    serializer_class = PostListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    ordering_fields = ['created_at', 'status', 'views_count']
    ordering = ['-created_at']

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user).select_related('category').prefetch_related('tags', 'likes', 'bookmarks', 'comments')


#Comment Views
class CommentListCreateView(generics.ListCreateAPIView):
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_post(self):
        try:
            return Post.objects.get(slug=self.kwargs['post_slug'], status=Post.Status.PUBLISHED)
        except Post.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Post not found.')

    def get_queryset(self):
        post = self.get_post()
        return Comment.objects.filter(post=post, parent=None).select_related('author').prefetch_related('replies__author', 'replies__replies')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentSerializer

    def create(self, request, *args, **kwargs):
        post = self.get_post()
        data = {**request.data, 'post': post.pk}
        serializer = CommentCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(author=request.user)
        return Response(CommentSerializer(comment, context={'request': request}).data, status=status.HTTP_201_CREATED)


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    
    serializer_class = CommentSerializer
    permission_classes = [IsAuthorOrReadOnly]

    def get_queryset(self):
        return Comment.objects.select_related('author').prefetch_related('replies__author')

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        comment.is_deleted = True
        comment.content = ''
        comment.save(update_fields=['is_deleted', 'content'])
        return Response({'message': 'Comment deleted.'}, status=status.HTTP_200_OK)


#Like / Bookmark Views
class LikeToggleView(APIView):
    
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        post = generics.get_object_or_404(Post, slug=slug, status=Post.Status.PUBLISHED)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        return Response({
            'liked': liked,
            'likes_count': post.likes.count(),
        })


class BookmarkToggleView(APIView):
    
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        post = generics.get_object_or_404(Post, slug=slug)
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
        if not created:
            bookmark.delete()
            bookmarked = False
        else:
            bookmarked = True
        return Response({'bookmarked': bookmarked})


class MyBookmarksView(generics.ListAPIView):
    
    serializer_class = PostListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        bookmarked_ids = Bookmark.objects.filter(user=self.request.user).values_list('post_id', flat=True)
        return Post.objects.filter(id__in=bookmarked_ids).select_related('author', 'category').prefetch_related('tags', 'likes', 'bookmarks', 'comments')
