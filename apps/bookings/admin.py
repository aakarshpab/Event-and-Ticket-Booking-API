from django.contrib import admin

from .models import Booking, BookingItem


class BookingItemInline(admin.TabularInline):
    model = BookingItem
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "attendee", "event", "status", "total_amount", "created_at")
    list_filter = ("status",)
    inlines = [BookingItemInline]
