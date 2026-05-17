from rest_framework import serializers
from django.utils import timezone

from .models import Post, Comment, Category, Tag, Like, Bookmark
from users.serializers import PublicUserSerializer


#Category & Tag
class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'post_count']
        read_only_fields = ['slug']


class TagSerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'post_count']
        read_only_fields = ['slug']


#Comments
class RecursiveCommentSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = CommentSerializer(value, context=self.context)
        return serializer.data


class CommentSerializer(serializers.ModelSerializer):
    author = PublicUserSerializer(read_only=True)
    replies = RecursiveCommentSerializer(many=True, read_only=True)
    is_reply = serializers.BooleanField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'author', 'parent', 'content', 'is_reply', 'replies', 'created_at', 'updated_at', 'is_deleted']
        read_only_fields = ['id', 'author', 'is_reply', 'replies', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data['content'] = '[This comment has been deleted]'
            data['author'] = None
        return data


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'post', 'parent', 'content']

    def validate(self, attrs):
        parent = attrs.get('parent')
        post = attrs.get('post')
        if parent and parent.post != post:
            raise serializers.ValidationError({'parent': 'Parent comment must belong to the same post.'})
        return attrs


#Posts 
class PostListSerializer(serializers.ModelSerializer):
    author = PublicUserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author', 'category', 'tags',
            'excerpt', 'content', 'cover_image', 'status',
            'likes_count', 'comments_count', 'views_count',
            'is_liked', 'is_bookmarked',
            'created_at', 'published_at',
        ]

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.filter(is_deleted=False).count()

    def _get_user(self):
        request = self.context.get('request')
        return request.user if request and request.user.is_authenticated else None

    def get_is_liked(self, obj):
        user = self._get_user()
        return obj.likes.filter(user=user).exists() if user else False

    def get_is_bookmarked(self, obj):
        user = self._get_user()
        return obj.bookmarks.filter(user=user).exists() if user else False


class PostDetailSerializer(PostListSerializer):
    top_level_comments = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ['content', 'top_level_comments', 'updated_at']

    def get_top_level_comments(self, obj):
        qs = obj.comments.filter(parent=None).select_related('author')
        return CommentSerializer(qs, many=True, context=self.context).data


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, write_only=True,
        source='tags', required=False
    )

    tag_names = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )

    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True,
        source='category', required=False, allow_null=True
    )

    class Meta:
        model = Post
        fields = ['title', 'excerpt', 'content', 'cover_image', 'status', 'category_id', 'tag_ids', 'tag_names']

    def validate_status(self, value):
        # Only allow valid status values
        if value not in [Post.Status.DRAFT, Post.Status.PUBLISHED]:
            raise serializers.ValidationError(f"Invalid status. Choose from: draft, published")
        return value

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        tag_names = validated_data.pop('tag_names', [])

        if validated_data.get('status') == Post.Status.PUBLISHED:
            validated_data['published_at'] = timezone.now()

        post = Post.objects.create(**validated_data)

        post.tags.set(tags)

        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            post.tags.add(tag)

        return post

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        # Set published_at when transitioning to published
        if (validated_data.get('status') == Post.Status.PUBLISHED
                and instance.status == Post.Status.DRAFT
                and not instance.published_at):
            validated_data['published_at'] = timezone.now()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance
