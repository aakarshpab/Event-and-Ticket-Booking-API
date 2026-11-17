from django.contrib import admin

from .models import Event, TicketType, Venue


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    extra = 0


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "capacity")
    search_fields = ("name", "city")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "venue", "start_time", "organizer", "is_published")
    list_filter = ("category", "is_published")
    inlines = [TicketTypeInline]


admin.site.register(TicketType)
