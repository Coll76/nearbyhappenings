from rest_framework import serializers
from .models import Event, EventDate, Category, UserFavorite
from django.db import transaction
from datetime import datetime, timedelta

class EventDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventDate
        fields = ['id', 'date', 'time', 'availability', 'price', 'capacity', 'tickets_sold']
        read_only_fields = ['availability', 'tickets_sold']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class EventSerializer(serializers.ModelSerializer):
    dates = EventDateSerializer(many=True, required=False)
    categories = CategorySerializer(many=True, required=False, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        write_only=True,
        queryset=Category.objects.all(),
        source='categories',
        required=False
    )
    dateRange = serializers.SerializerMethodField()
    isFavorite = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'image', 'location', 'address',
            'latitude', 'longitude', 'price', 'currency', 'is_featured', 
            'highlights', 'dates', 'categories', 'category_ids', 'dateRange',
            'review_count', 'isFavorite', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_dateRange(self, obj):
        return obj.get_date_range()
    
    def get_isFavorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserFavorite.objects.filter(user=request.user, event=obj).exists()
        return False

    """def create(self, validated_data):
        dates_data = validated_data.pop('dates', [])
        with transaction.atomic():
            event = Event.objects.create(**validated_data)
            for date_data in dates_data:
                EventDate.objects.create(event=event, **date_data)
        return event"""

    def create(self, validated_data):
        categories = validated_data.pop('categories', None)
        dates_data = validated_data.pop('dates', [])

        with transaction.atomic():
            event = Event.objects.create(**validated_data)

            # Set categories if provided
            if categories:
                event.categories.set(categories)

            # Create dates
            for date_data in dates_data:
                EventDate.objects.create(event=event, **date_data)

        return event

    """def update(self, instance, validated_data):
        dates_data = validated_data.pop('dates', [])
        # Update the event instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle dates
        if dates_data:
            instance.dates.all().delete()  # Remove existing dates
            for date_data in dates_data:
                EventDate.objects.create(event=instance, **date_data)

        return instance"""

    def update(self, instance, validated_data):
        categories = validated_data.pop('categories', None)
        dates_data = validated_data.pop('dates', [])

        # Update the event instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update categories if provided
        if categories is not None:
            instance.categories.set(categories)

        # Handle dates
        if dates_data:
            instance.dates.all().delete()  # Remove existing dates
            for date_data in dates_data:
                EventDate.objects.create(event=instance, **date_data)

        return instance

class EventListSerializer(serializers.ModelSerializer):
    dateRange = serializers.SerializerMethodField()
    isFavorite = serializers.SerializerMethodField()
    categories = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'image', 'location', 'price', 'currency', 
            'is_featured', 'dateRange', 'review_count', 'isFavorite', 'categories'
        ]
    
    def get_dateRange(self, obj):
        return obj.get_date_range()
    
    def get_isFavorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserFavorite.objects.filter(user=request.user, event=obj).exists()
        return False

class MapEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'title', 'location', 'latitude', 'longitude']

class UserFavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFavorite
        fields = ['id', 'event', 'created_at']
        read_only_fields = ['id', 'created_at']
