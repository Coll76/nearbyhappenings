from django.contrib import admin
from django.db.models import Count
from .models import Event, EventDate, Category, UserFavorite

class EventDateInline(admin.TabularInline):
    model = EventDate
    extra = 1
    fields = ('date', 'time', 'availability', 'price', 'capacity', 'tickets_sold')
    readonly_fields = ('availability',)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'planner', 'location', 'price', 'currency', 'is_featured', 'get_categories', 'get_dates_count')
    list_filter = ('is_featured', 'categories', 'created_at')
    search_fields = ('title', 'description', 'location', 'planner__user__username')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [EventDateInline]
    filter_horizontal = ('categories',)
    
    def get_categories(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])
    get_categories.short_description = 'Categories'
    
    def get_dates_count(self, obj):
        return obj.dates.count()
    get_dates_count.short_description = 'Number of Dates'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('categories', 'dates')

@admin.register(EventDate)
class EventDateAdmin(admin.ModelAdmin):
    list_display = ('event', 'date', 'time', 'availability', 'price', 'capacity', 'tickets_sold')
    list_filter = ('availability', 'date')
    search_fields = ('event__title',)
    readonly_fields = ('availability',)
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('event')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_events_count')
    search_fields = ('name',)
    
    def get_events_count(self, obj):
        return obj.events.count()
    get_events_count.short_description = 'Number of Events'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(events_count=Count('events'))

@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'event__title')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'event')
