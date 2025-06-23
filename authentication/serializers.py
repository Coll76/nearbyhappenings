from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import EventPlanner, Notification
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar']
        read_only_fields = ['id']

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'avatar',
                  'is_staff', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'password_confirm']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class EventPlannerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = EventPlanner
        fields = ['id', 'user', 'phone', 'national_id', 'company_name', 
                  'address', 'event_types', 'status', 'created_at']
        read_only_fields = ['id', 'user', 'status', 'created_at']


class EventPlannerRegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(required=True)
    national_id = serializers.CharField(required=True)
    company_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    business_details = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    event_types = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    terms_accepted = serializers.BooleanField(required=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "User with this email already exists."})

        # Validate terms acceptance
        if not attrs.get('terms_accepted'):
            raise serializers.ValidationError({"terms_accepted": "You must accept the terms and conditions."})

        return attrs


    def create(self, validated_data):
        # Add logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Creating event planner with email: {validated_data.get('email')}")
    
        # Remove fields not needed for user creation
        validated_data.pop('password_confirm')
        terms_accepted = validated_data.pop('terms_accepted', None)
        business_details = validated_data.pop('business_details', None)
        
        # Extract user data - Store email in a variable first
        email = validated_data.pop('email')
        user_data = {
            'email': email,      
            'username': email.split('@')[0],  # Create username from email
            'password': validated_data.pop('password'),
        }
    
        # Handle name splitting for first_name and last_name
        full_name = validated_data.pop('name')
        name_parts = full_name.split(' ')
        user_data['first_name'] = name_parts[0]
        user_data['last_name'] = ' '.join(name_parts[1:]) if len(name_parts) > 1 else '' 
        try:
            # Create user
            user = User.objects.create_user(**user_data)
            logger.info(f"Created user with id: {user.id}")
            
            # Create planner profile
            planner_data = {
                'user': user,
                'phone': validated_data.pop('phone'),
                'national_id': validated_data.pop('national_id'),
                'company_name': validated_data.pop('company_name', None),
                'address': validated_data.pop('address', None),
                'event_types': validated_data.pop('event_types', []),
            }
            
            event_planner = EventPlanner.objects.create(**planner_data)
            logger.info(f"Created event planner with id: {event_planner.id}")
            
            return event_planner
        except Exception as e:
            logger.error(f"Error creating event planner: {str(e)}")
            raise serializers.ValidationError(f"Failed to create event planner: {str(e)}")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type', 'message', 'data', 'read', 'created_at']
        read_only_fields = ['id', 'created_at']
