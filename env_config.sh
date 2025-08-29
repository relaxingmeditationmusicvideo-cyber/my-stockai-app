# .env - Environment Configuration
# Copy this to .env and update with your actual values

# Database Configuration
DATABASE_URL=postgresql://postgres:your_secure_password@localhost:5432/stockai_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stockai_db
DB_USER=postgres
DB_PASSWORD=your_secure_password

# Redis Configuration
REDIS_URL=redis://:your_redis_password@localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# JWT Configuration
JWT_SECRET=your_very_secure_jwt_secret_key_change_this_in_production_minimum_32_chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# API Keys
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
FINNHUB_API_KEY=your_finnhub_api_key_here
NEWS_API_KEY=your_news_api_key_here

# Email Configuration (for notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
EMAIL_FROM=noreply@stockaipro.com

# Application Configuration
APP_NAME=StockAI Pro
APP_VERSION=2.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,https://yourdomain.com
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
AUTH_RATE_LIMIT_PER_MINUTE=5

# File Upload
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_PATH=./uploads

# Monitoring
SENTRY_DSN=your_sentry_dsn_for_error_tracking
PROMETHEUS_ENABLED=true

# External Services
WEBHOOK_URL=https://your-webhook-url.com/notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/slack/webhook

# Cache Configuration
CACHE_TTL_STOCK_DATA=30
CACHE_TTL_MARKET_DATA=60
CACHE_TTL_NEWS_DATA=300

# Celery Configuration
CELERY_BROKER_URL=redis://:your_redis_password@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:your_redis_password@localhost:6379/2

# Production specific
SSL_CERT_PATH=/etc/ssl/certs/stockai.crt
SSL_KEY_PATH=/etc/ssl/private/stockai.key
DOMAIN_NAME=stockaipro.com

# Cloud Storage (if using)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET=stockai-pro-data
AWS_REGION=ap-south-1

# Payment Gateway (for subscriptions)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

# Analytics
GOOGLE_ANALYTICS_ID=GA_MEASUREMENT_ID
MIXPANEL_TOKEN=your_mixpanel_token