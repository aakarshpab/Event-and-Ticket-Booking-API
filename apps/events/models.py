from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class Venue(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()

    class Meta:
        indexes = [models.Index(fields=["city"])]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name="venue_capacity_positive"),
        ]

    def __str__(self):
        return f"{self.name} ({self.city})"


class Event(models.Model):
    class Category(models.TextChoices):
        MUSIC = "music", "Music"
        TECH = "tech", "Tech"
        SPORTS = "sports", "Sports"
        ARTS = "arts", "Arts"
        FOOD = "food", "Food"
        OTHER = "other", "Other"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="events")
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["start_time"]),
            models.Index(fields=["category"]),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(end_time__gt=F("start_time")), name="event_end_after_start"),
        ]

    def __str__(self):
        return self.title


class TicketType(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_types")
    name = models.CharField(max_length=100)  # e.g. General, VIP
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity_total = models.PositiveIntegerField()
    quantity_sold = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "name"], name="unique_ticket_name_per_event"),
            models.CheckConstraint(condition=Q(price__gte=0), name="ticket_price_not_negative"),
            models.CheckConstraint(
                condition=Q(quantity_sold__lte=F("quantity_total")),
                name="ticket_sold_not_above_total",
            ),
        ]

    @property
    def available(self):
        return self.quantity_total - self.quantity_sold

    def __str__(self):
        return f"{self.event.title} - {self.name}"
