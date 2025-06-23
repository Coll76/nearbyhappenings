from django.contrib import admin
from .models import User, EventPlanner
from django.contrib import admin
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

@admin.register(EventPlanner)
class EventPlannerAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'phone', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'company_name', 'phone')
    actions = ['approve_planners', 'reject_planners']
    
    def approve_planners(self, request, queryset):
        queryset.update(status='approved')
        for planner in queryset:
            planner.user.is_staff = True
            planner.user.save()
        self.message_user(request, f"{queryset.count()} planners were approved.")
    approve_planners.short_description = "Approve selected planners"
    
    def reject_planners(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} planners were rejected.")
    reject_planners.short_description = "Reject selected planners"



   

# Register your models here.
