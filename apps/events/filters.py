import django_filters

from .models import Event


class EventFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category", lookup_expr="iexact")
    city = django_filters.CharFilter(field_name="venue__city", lookup_expr="iexact")
    date_from = django_filters.DateFilter(field_name="start_time", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="start_time", lookup_expr="date__lte")
    min_price = django_filters.NumberFilter(
        field_name="ticket_types__price", lookup_expr="gte", distinct=True
    )
    max_price = django_filters.NumberFilter(
        field_name="ticket_types__price", lookup_expr="lte", distinct=True
    )

    class Meta:
        model = Event
        fields = ["category", "city", "date_from", "date_to", "min_price", "max_price"]
