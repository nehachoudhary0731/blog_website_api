from django.db import models
from django.utils.text import slugify
from django.conf import settings
import uuid


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Post(models.Model):

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='posts'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')

    excerpt = models.TextField(max_length=500, blank=True, help_text='Short summary shown in listings')
    content = models.TextField()
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-published_at']),
            models.Index(fields=['author', 'status']),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate slug from title
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.status.upper()}] {self.title}"

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    def publish(self):
        """Transition: DRAFT → PUBLISHED"""
        from django.utils import timezone
        self.status = self.Status.PUBLISHED
        if not self.published_at:
            self.published_at = timezone.now()
        self.save(update_fields=['status', 'published_at'])

    def unpublish(self):
        """Transition: PUBLISHED → DRAFT"""
        self.status = self.Status.DRAFT
        self.save(update_fields=['status'])


class Comment(models.Model):

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='replies'
    )
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)  # Soft-delete: keep thread structure

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on '{self.post.title}'"

    @property
    def is_reply(self):
        return self.parent_id is not None


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')  # DB-level uniqueness guarantee

    def __str__(self):
        return f"{self.user.username} ❤ {self.post.title}"


class Bookmark(models.Model):
    """A user bookmarking a post. One bookmark per user per post."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} 🔖 {self.post.title}"
