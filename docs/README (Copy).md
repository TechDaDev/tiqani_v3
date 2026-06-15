# Tiqani API

A Django REST API backend for the Tiqani platform, which facilitates freelancing and contracting services.

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Features

- User authentication and profiles
- Category management
- Payment processing with Stripe
- Real-time chat functionality
- Contract management
- Rating and review system
- Dealership management
- Notification system

## Technologies Used

- Django
- Django REST Framework
- Django Channels for WebSockets
- Django Simple JWT for authentication
- Stripe for payment processing
- SQLite database (included in repo)

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tiqani_API.git
cd tiqani_API
```

2. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Environment variables:
   - The project includes a `.env` file with necessary configuration
   - Update Stripe API keys in the `.env` file if needed

5. Run migrations:
```bash
python manage.py migrate
```

6. Start the development server:
```bash
python manage.py runserver
```

## WebSocket Server

To run the WebSocket server in development:
```bash
python run_ws_server.py
```

## API Documentation

API endpoints are organized by app functionality:
- `/api/accounts/` - User management
- `/api/category/` - Category management
- `/api/payment/` - Payment processing
- `/api/chat/` - Chat functionality
- `/api/contract/` - Contract management
- `/api/ratereview/` - Rating and review system
- `/api/dealership/` - Dealership management
- `/api/notification/` - Notification system

## Deployment Options

### Heroku Deployment

For deployment to Heroku, refer to the [Heroku deployment guide](HEROKU.md) which covers:

- One-click deployment with Heroku Button
- Manual deployment process
- Environment variable configuration
- PostgreSQL and Redis setup
- AWS S3 integration for media files
- Scaling and monitoring

### Traditional Production Deployment

For traditional server deployment (e.g., Linux with Nginx), refer to the [production guide](PRODUCTION.md) which covers:

- Server setup with Nginx, Gunicorn, Redis, and PostgreSQL
- Environment configuration
- SSL/TLS setup
- WebSocket server deployment
- Database management
- Security best practices
- Backup strategies

## Switching to Production

### For Heroku:

1. Use the Heroku Button above or follow the manual steps in [HEROKU.md](HEROKU.md)

### For traditional deployment:

1. Copy the production environment template:
```bash
cp .env.prod .env
```

2. Edit the `.env` file with production settings (ensure DEBUG=False)

3. Install production dependencies:
```bash
pip install -r requirements.txt
```

4. Follow the complete instructions in [PRODUCTION.md](PRODUCTION.md)

## Development Notes

- The SQLite database is included in the repository
- Environment variables file (.env) is included in the repository
- Debug mode is enabled by default for development
- For production deployment, update the `.env` file with appropriate settings 