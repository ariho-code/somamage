import uuid
from django.db import models


class Platform(models.Model):
    """Singleton — represents the SomaMange platform owner."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, default="SomaMange")
    owner = models.OneToOneField(
        "core.User",
        on_delete=models.PROTECT,
        related_name="owned_platform",
        null=True,
        blank=True,
    )
    logo = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Platform"
        verbose_name_plural = "Platforms"

    def __str__(self) -> str:
        return self.name


class Campus(models.Model):
    """A physical branch of a School."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "core.School",
        on_delete=models.CASCADE,
        related_name="campuses",
    )
    name = models.CharField(max_length=200)  # e.g. "Main Campus", "Ntinda Branch"
    is_main = models.BooleanField(default=False)
    address = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    headteacher = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_campuses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Campus"
        verbose_name_plural = "Campuses"
        ordering = ["-is_main", "name"]

    def __str__(self) -> str:
        return f"{self.school.name} — {self.name}"
