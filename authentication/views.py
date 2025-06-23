from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .models import EventPlanner
from .serializers import (UserSerializer, RegisterSerializer,
                          EventPlannerSerializer, EventPlannerRegistrationSerializer)
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

class EventPlannerRegistrationView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EventPlannerRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        planner = serializer.save()

        refresh = RefreshToken.for_user(planner.user)

        return Response({
            'user': {
                'id': planner.user.id,
                'name': f"{planner.user.first_name} {planner.user.last_name}",
                'email': planner.user.email,
                'avatar': planner.user.avatar.url if planner.user.avatar else None,
                'role': 'planner',
                'plannerStatus': planner.status,
                'phone': planner.phone,
                'nationalId': planner.national_id,
                'companyName': planner.company_name,
                'address': planner.address,
                'eventTypes': planner.event_types,
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class EventPlannerListView(generics.ListAPIView):
    queryset = EventPlanner.objects.all()
    serializer_class = EventPlannerSerializer
    permission_classes = [permissions.IsAdminUser]

class EventPlannerDetailView(generics.RetrieveUpdateAPIView):
    queryset = EventPlanner.objects.all()
    serializer_class = EventPlannerSerializer
    permission_classes = [permissions.IsAdminUser]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if 'status' in request.data:
            # If status changed to 'approved', update user's role
            if request.data['status'] == 'approved':
                instance.user.is_staff = True
                instance.user.save()

        return Response(serializer.data)

class ValidationTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        planner = None

        try:
            planner = user.planner_profile
            role = 'planner'
            planner_status = planner.status
        except:
            role = 'admin' if user.is_staff else 'user'
            planner_status = None

        return Response({
            'id': user.id,
            'name': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'avatar': user.avatar.url if user.avatar else None,
            'role': role,
            'plannerStatus': planner_status,
        })

# Signal to track planner status changes
@receiver(post_save, sender=EventPlanner)
def track_planner_status_change(sender, instance, created, **kwargs):
    if not created:  # Only for updates, not creation
        # This signal will be used by the frontend to update the user status
        # We don't need to implement WebSocket-specific logic here
        pass
