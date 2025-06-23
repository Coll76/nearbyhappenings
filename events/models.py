from django.db import models
from authentication.models import User, EventPlanner
from django.utils.text import slugify
import uuid
from datetime import date

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    planner = models.ForeignKey(EventPlanner, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    location = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    is_featured = models.BooleanField(default=False)
    highlights = models.JSONField(default=list, blank=True)
    categories = models.ManyToManyField(Category, related_name='events')
    review_count = models.PositiveIntegerField(default=0)
    is_favorite = models.BooleanField(default=False)  # This will be used differently per user
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Generate a unique slug
            base_slug = slugify(self.title)
            unique_id = str(uuid.uuid4())[:8]
            self.slug = f"{base_slug}-{unique_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    def get_date_range(self):
        """Return date range as a string (e.g., 'Mar 21 - May 03')"""
        dates = self.dates.all().order_by('date')
        if not dates:
            return ""
        
        first_date = dates.first().date
        last_date = dates.last().date
        
        # Format dates
        first_str = first_date.strftime("%b %d")
        
        if first_date == last_date:
            return first_str
        
        last_str = last_date.strftime("%b %d")
        return f"{first_str} - {last_str}"

class EventDate(models.Model):
    AVAILABILITY_CHOICES = (
        ('Available', 'Available'),
        ('Limited', 'Limited'),
        ('Sold Out', 'Sold Out'),
    )

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='dates')
    date = models.DateField()
    time = models.TimeField()
    availability = models.CharField(max_length=10, choices=AVAILABILITY_CHOICES, default='Available')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capacity = models.PositiveIntegerField(default=100)
    tickets_sold = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['date', 'time']
        unique_together = ('event', 'date', 'time')

    def __str__(self):
        return f"{self.event.title} - {self.date} {self.time}"

    def save(self, *args, **kwargs):
        if self.tickets_sold >= self.capacity:
            self.availability = 'Sold Out'
        elif self.tickets_sold >= (self.capacity * 0.8):
            self.availability = 'Limited'
        else:
            self.availability = 'Available'
        super().save(*args, **kwargs)

class UserFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
        
    def __str__(self):
        return f"{self.user.username} - {self.event.title}"
