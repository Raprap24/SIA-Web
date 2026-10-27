from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="movieverse_profile",
    )
    bio = models.CharField(max_length=280, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class MovieVerse(models.Model):
    title_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movie_posts",
    )
    title_name = models.CharField(max_length=100)
    type = models.CharField(max_length=50)
    genre = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    rating = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    release_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1888), MaxValueValidator(2100)],
    )
    description = models.TextField(blank=True)
    poster_url = models.URLField(max_length=500, blank=True)
    trailer_url = models.URLField(max_length=500, blank=True)
    date_added = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-date_added", "-title_id"]

    def __str__(self):
        return self.title_name


class AdminAuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="movieverse_admin_actions",
    )
    action = models.CharField(max_length=40)
    target = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action}: {self.target}"
