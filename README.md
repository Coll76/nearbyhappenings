# Nearby Happenings

A comprehensive Django REST API backend for event discovery and ticket booking platform that connects users with local events and enables event planners to manage their events and ticket sales.

## 🌟 Features

### For Users
- **Event Discovery**: Browse and search local events with advanced filtering
- **Interactive Map**: View events geographically with map integration
- **Ticket Booking**: Purchase tickets with multiple payment methods (Stripe & M-Pesa)
- **Favorites**: Save and track favorite events
- **User Profiles**: Manage personal information and view booking history

### For Event Planners
- **Event Management**: Create, edit, and manage events with multiple dates
- **Ticket Management**: Track ticket sales, view analytics, and manage refunds
- **Dashboard Analytics**: Monitor event performance and revenue
- **Status Management**: Application approval workflow for planners

### For Administrators
- **Planner Approval**: Review and approve event planner applications
- **Site Settings**: Configure service fees and global application settings
- **Comprehensive Admin**: Full Django admin interface with Jazzmin styling

## 🏗️ Architecture

### Technology Stack
- **Backend**: Django 5.1.2, Django REST Framework
- **Authentication**: JWT with SimpleJWT
- **Database**: SQLite (development), easily configurable for PostgreSQL/MySQL
- **Payments**: Stripe for card payments, M-Pesa for mobile money
- **Real-time**: Django Channels for WebSocket support
- **Admin Interface**: Django Jazzmin for enhanced admin experience

### Key Components
- **Authentication System**: Custom user model with role-based access
- **Event Management**: Events with categories, dates, and geolocation
- **Payment Processing**: Factory pattern with multiple payment providers
- **Ticket System**: QR code generation and validation
- **Notification System**: User notifications with different types

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/nearby-happenings.git
   cd nearby-happenings
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install python-decouple for environment management**
   ```bash
   pip install python-decouple==3.8
   ```

5. **Environment Configuration**
   
   Create a `.env` file in the project root:
   ```env
   # Django Configuration
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1

   # Database Configuration
   DATABASE_ENGINE=django.db.backends.sqlite3
   DATABASE_NAME=db.sqlite3

   # CORS Configuration
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

   # JWT Configuration
   ACCESS_TOKEN_LIFETIME_DAYS=1
   REFRESH_TOKEN_LIFETIME_DAYS=7
   ROTATE_REFRESH_TOKENS=True
   BLACKLIST_AFTER_ROTATION=True

   # Stripe Configuration
   STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
   STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

   # M-Pesa Configuration
   MPESA_API_URL=https://sandbox.safaricom.co.ke
   MPESA_CONSUMER_KEY=your_mpesa_consumer_key
   MPESA_CONSUMER_SECRET=your_mpesa_consumer_secret
   MPESA_SHORTCODE=174379
   MPESA_PASSKEY=your_mpesa_passkey
   MPESA_CALLBACK_URL=https://your-domain.com/api/payments/mpesa/callback/

   # Channel Layers Backend
   CHANNEL_LAYERS_BACKEND=memory

   # Logging Configuration
   LOG_LEVEL=DEBUG
   LOG_FILE=debug.log
   ```

6. **Database Setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://127.0.0.1:8000/`

## 📚 API Documentation

### Base URL
```
http://127.0.0.1:8000/api/
```

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register/` | User registration |
| POST | `/auth/login/` | User login (JWT) |
| POST | `/auth/refresh/` | Refresh JWT token |
| GET | `/auth/profile/` | Get user profile |
| PUT | `/auth/profile/` | Update user profile |
| GET | `/auth/validate/` | Validate current token |

### Event Planner Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/planner/register/` | Event planner registration |
| GET | `/auth/planners/` | List planners (Admin only) |
| GET | `/auth/planners/{id}/` | Planner details (Admin only) |
| PUT | `/auth/planners/{id}/` | Update planner status (Admin only) |

### Event Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/events/` | List events with filtering |
| POST | `/events/` | Create event (Planner only) |
| GET | `/events/{id}/` | Event details |
| PUT | `/events/{id}/` | Update event (Owner only) |
| DELETE | `/events/{id}/` | Delete event (Owner only) |
| GET | `/events/map_events/` | Events for map view |
| POST | `/events/{id}/add_date/` | Add event date |
| POST | `/events/{id}/toggle_favorite/` | Toggle favorite |

#### Event Filtering Parameters
- `category`: Filter by category name
- `dateFilter`: `All`, `Today`, `Tomorrow`, `This Weekend`, `This Week`, `This Month`
- `sortBy`: `Recommended`, `Date`, `Price: Low to High`, `Price: High to Low`
- `location`: Filter by location
- `price`: Filter by price range
- `search`: Search in title, description, location
- `plannerOnly`: Show only planner's events (boolean)

### Ticket Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tickets/` | List user tickets |
| POST | `/tickets/purchase/` | Purchase tickets |
| GET | `/tickets/{id}/` | Ticket details |
| POST | `/tickets/{id}/cancel/` | Cancel ticket |
| POST | `/tickets/{id}/refund/` | Refund ticket |
| GET | `/tickets/{id}/payment_details/` | Payment details |
| GET | `/tickets/{id}/check_payment_status/` | Check payment status |
| GET | `/tickets/stats/` | Ticket statistics (Planner only) |

#### Ticket Filtering Parameters
- `filter`: `upcoming`, `past`
- `status`: `PENDING`, `CONFIRMED`, `CANCELLED`, `USED`
- `event`: Filter by event ID
- `payment_completed`: Boolean filter

### Category Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categories/` | List all categories |

### Site Settings (Admin Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/core/settings/` | Get site settings |
| PUT | `/core/settings/` | Update site settings |

## 💳 Payment Integration

### Stripe Setup
1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe dashboard
3. Add keys to your `.env` file
4. Configure webhooks for payment confirmations

### M-Pesa Setup
1. Register for M-Pesa API at https://developer.safaricom.co.ke
2. Get your consumer key and secret
3. Configure your shortcode and passkey
4. Set up callback URL for payment confirmations

### Payment Flow
```python
# Example ticket purchase
{
    "event_id": "uuid",
    "event_date_id": "uuid", 
    "quantity": 2,
    "payment_method": "CARD",  # or "MPESA"
    "payment_data": {
        "payment_method_id": "pm_xxx",  # For Stripe
        "phone_number": "254700000000"  # For M-Pesa
    }
}
```

## 🔐 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Permission Classes**: Role-based access control
- **CORS Configuration**: Cross-origin request handling
- **Environment Variables**: Sensitive data protection
- **Input Validation**: Comprehensive request validation
- **Payment Security**: PCI-compliant payment processing

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test events
python manage.py test tickets
python manage.py test authentication

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Test Categories
- **Unit Tests**: Model and utility function testing
- **Integration Tests**: API endpoint testing
- **Payment Tests**: Mock payment processor testing

## 📊 Monitoring & Logging

### Logging Configuration
The application uses Django's logging framework with:
- **Console Output**: Development debugging
- **File Logging**: Persistent error tracking
- **Level Control**: Configurable via `LOG_LEVEL` environment variable

### Key Metrics to Monitor
- **Payment Success Rates**: Track payment completion
- **Event Creation**: Monitor planner activity
- **User Registration**: Track platform growth
- **Error Rates**: Monitor application health

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False` in production
- [ ] Configure production database (PostgreSQL recommended)
- [ ] Set up Redis for Channel Layers
- [ ] Configure static file serving
- [ ] Set up SSL certificates
- [ ] Configure production logging
- [ ] Set up monitoring and alerting
- [ ] Configure backup procedures

### Environment Variables for Production
```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=nearby_happenings
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
CHANNEL_LAYERS_BACKEND=redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

### Docker Deployment
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "nearby.wsgi:application"]
```

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Standards
- **PEP 8**: Python code style guide
- **Django Best Practices**: Follow Django conventions
- **Documentation**: Comment complex logic
- **Testing**: Maintain test coverage above 80%

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

**Payment Processing Errors**
- Verify API keys are correctly configured
- Check webhook endpoints are accessible
- Ensure test/live mode consistency

**Authentication Issues**
- Verify JWT settings are correct
- Check token expiration settings
- Ensure CORS is properly configured

**Event Creation Problems**
- Verify event planner is approved
- Check required fields are provided
- Ensure geolocation data is valid

### Getting Help
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Email**: collins.kubu@gmail.com

## 🔮 Roadmap

### Planned Features
- [ ] Push Notifications
- [ ] Event Recommendations AI
- [ ] Social Media Integration
- [ ] Multi-language Support
- [ ] Advanced Analytics Dashboard
- [ ] Event Live Streaming Integration
- [ ] Attendee Check-in App
- [ ] Revenue Sharing System

### Version History
- **v1.0.0**: Initial release with core functionality
- **v1.1.0**: Payment integration and ticket system
- **v1.2.0**: Enhanced admin features and analytics

---

Made with ❤️ by the Nearby Happenings Team