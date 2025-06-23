from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta, date
from django.db.models import Q

from .models import Event, EventDate, Category, UserFavorite
from .serializers import (
    EventSerializer, EventListSerializer, EventDateSerializer,
    CategorySerializer, MapEventSerializer, UserFavoriteSerializer
)
from authentication.models import EventPlanner
from rest_framework.exceptions import ValidationError
import logging

# Set up logging
logger = logging.getLogger(__name__)



class IsEventPlannerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow event planners to edit their own events.
    """
    def has_permission(self, request, view):
        # Allow read access to anyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if user is authenticated and is an approved event planner
        if request.user.is_authenticated:
            try:
                planner = request.user.planner_profile
                return planner.status == 'approved'
            except EventPlanner.DoesNotExist:
                return False
        return False

    def has_object_permission(self, request, view, obj):
        # Allow read access to anyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if this event belongs to the requesting planner
        try:
            return obj.planner == request.user.planner_profile
        except:
            return False

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    permission_classes = [IsEventPlannerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['location', 'price']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['price', 'created_at']



    def create(self, request, *args, **kwargs):
        try:
            # Log the incoming request data
            logger.info(f"Attempting to create event with data: {request.data}")
            
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                # Log validation errors in detail
                logger.error(f"Validation error: {serializer.errors}")
                return Response(
                    {
                        "status": "error",
                        "detail": "Invalid event data",
                        "errors": serializer.errors
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED, 
                headers=headers
            )
        except ValidationError as ve:
            # Handle validation errors
            logger.error(f"Validation error: {str(ve)}")
            return Response(
                {"status": "error", "detail": str(ve)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Catch and log unexpected errors
            logger.error(f"Unexpected error creating event: {str(e)}", exc_info=True)
            return Response(
                {"status": "error", "detail": "An unexpected error occurred"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        try:
            # Log the incoming update request
            logger.info(f"Attempting to update event {kwargs.get('pk')} with data: {request.data}")
            
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
            
            if not serializer.is_valid():
                # Log validation errors in detail
                logger.error(f"Validation error: {serializer.errors}")
                return Response(
                    {
                        "status": "error",
                        "detail": "Invalid event data",
                        "errors": serializer.errors
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            self.perform_update(serializer)
            return Response(serializer.data)
        except ValidationError as ve:
            # Handle validation errors
            logger.error(f"Validation error: {str(ve)}")
            return Response(
                {"status": "error", "detail": str(ve)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Catch and log unexpected errors
            logger.error(f"Unexpected error updating event: {str(e)}", exc_info=True)
            return Response(
                {"status": "error", "detail": "An unexpected error occurred"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    def get_serializer_class(self):
        if self.action == 'list':
            return EventListSerializer
        elif self.action == 'map_events':
            return MapEventSerializer
        return EventSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def perform_create(self, serializer):
        serializer.save(planner=self.request.user.planner_profile)

    def list(self, request, *args, **kwargs):
        # Filter by category
        category = request.query_params.get('category', 'All')
        queryset = self.filter_queryset(self.get_queryset())
        
        if category != 'All':
            queryset = queryset.filter(categories__name=category)
        
        # Date filtering
        date_filter = request.query_params.get('dateFilter', 'All')
        today = date.today()
        
        if date_filter == 'Today':
            queryset = queryset.filter(dates__date=today)
        elif date_filter == 'Tomorrow':
            tomorrow = today + timedelta(days=1)
            queryset = queryset.filter(dates__date=tomorrow)
        elif date_filter == 'This Weekend':
            # Get next Saturday and Sunday
            days_until_weekend = (5 - today.weekday()) % 7
            saturday = today + timedelta(days=days_until_weekend)
            sunday = saturday + timedelta(days=1)
            queryset = queryset.filter(Q(dates__date=saturday) | Q(dates__date=sunday))
        elif date_filter == 'This Week':
            # Get dates for the next 7 days
            next_week = today + timedelta(days=7)
            queryset = queryset.filter(dates__date__range=[today, next_week])
        elif date_filter == 'This Month':
            # Get dates for the current month
            next_month = today.replace(day=1)
            if today.month == 12:
                next_month = next_month.replace(year=today.year + 1, month=1)
            else:
                next_month = next_month.replace(month=today.month + 1)
            queryset = queryset.filter(dates__date__range=[today, next_month - timedelta(days=1)])
        
        # Sorting
        sort_by = request.query_params.get('sortBy', 'Recommended')
        if sort_by == 'Date':
            queryset = queryset.order_by('dates__date')
        elif sort_by == 'Price: Low to High':
            queryset = queryset.order_by('price')
        elif sort_by == 'Price: High to Low':
            queryset = queryset.order_by('-price')
        elif sort_by == 'Distance':
            # Would need user location for actual implementation
            pass  # For now, no special sorting
        
        # Remove duplicates
        queryset = queryset.distinct()
        
        # For event planners, show only their events if requested
        planner_only = request.query_params.get('plannerOnly', 'false').lower() == 'true'
        if planner_only and request.user.is_authenticated:
            try:
                planner = request.user.planner_profile
                if planner.status == 'approved':
                    queryset = queryset.filter(planner=planner)
            except EventPlanner.DoesNotExist:
                pass

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_date(self, request, pk=None):
        event = self.get_object()
        serializer = EventDateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(event=event)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['get'])
    def map_events(self, request):
        """Return events with geolocation for map view"""
        category = request.query_params.get('category', 'All')
        date_filter = request.query_params.get('dateFilter', 'All')
        
        # Start with events that have lat/long coordinates
        queryset = Event.objects.filter(
            latitude__isnull=False, 
            longitude__isnull=False
        )
        
        # Apply category filter
        if category != 'All':
            queryset = queryset.filter(categories__name=category)
        
        # Apply date filter (same logic as in list method)
        today = date.today()
        
        if date_filter == 'Today':
            queryset = queryset.filter(dates__date=today)
        elif date_filter == 'Tomorrow':
            tomorrow = today + timedelta(days=1)
            queryset = queryset.filter(dates__date=tomorrow)
        elif date_filter == 'This Weekend':
            days_until_weekend = (5 - today.weekday()) % 7
            saturday = today + timedelta(days=days_until_weekend)
            sunday = saturday + timedelta(days=1)
            queryset = queryset.filter(Q(dates__date=saturday) | Q(dates__date=sunday))
        elif date_filter == 'This Week':
            next_week = today + timedelta(days=7)
            queryset = queryset.filter(dates__date__range=[today, next_week])
        elif date_filter == 'This Month':
            next_month = today.replace(day=1)
            if today.month == 12:
                next_month = next_month.replace(year=today.year + 1, month=1)
            else:
                next_month = next_month.replace(month=today.month + 1)
            queryset = queryset.filter(dates__date__range=[today, next_month - timedelta(days=1)])
        
        # Remove duplicates
        queryset = queryset.distinct()
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """Toggle an event as favorite for the current user"""
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        event = self.get_object()
        favorite, created = UserFavorite.objects.get_or_create(
            user=request.user,
            event=event
        )
        
        if not created:
            # User already had this as favorite, so remove it
            favorite.delete()
            return Response({"status": "removed from favorites"})
            
        return Response({"status": "added to favorites"})
        
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
