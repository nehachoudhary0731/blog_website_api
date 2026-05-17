import django_filters
from .models import Post


class PostFilter(django_filters.FilterSet):

    category = django_filters.NumberFilter(field_name='category__id')
    category_slug = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    tags = django_filters.BaseInFilter(field_name='tags__id', lookup_expr='in')
    tag_slug = django_filters.CharFilter(field_name='tags__slug', lookup_expr='exact')
    author = django_filters.NumberFilter(field_name='author__id')
    author_username = django_filters.CharFilter(field_name='author__username', lookup_expr='exact')
    status = django_filters.ChoiceFilter(choices=Post.Status.choices)
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Post
        fields = ['status', 'category', 'category_slug', 'tags', 'tag_slug', 'author', 'author_username']
