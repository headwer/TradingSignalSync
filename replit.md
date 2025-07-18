# TradingView Binance Webhook Bot

## Overview

This is a Flask-based trading bot that receives webhook signals from TradingView and executes trades on Binance. The application provides a web dashboard for monitoring trades, positions, and bot settings, with real-time integration to the Binance API.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM
- **Database**: SQLite by default (configurable via DATABASE_URL environment variable)
- **API Integration**: Binance Futures API client for trade execution
- **Webhook Processing**: RESTful endpoint for TradingView signals
- **Advanced Features**: Stop-loss/take-profit automation, multiple trading pairs, analytics

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme
- **Styling**: Custom CSS with Font Awesome icons
- **JavaScript**: Vanilla JS for real-time updates and dashboard interactions
- **Responsive Design**: Bootstrap-based responsive layout
- **New Pages**: Analytics dashboard, trading pairs management

### Database Schema
- **Trade**: Records trade execution history with advanced order types and status tracking
- **Position**: Tracks open/closed positions with P&L calculations and stop-loss/take-profit prices
- **BotSettings**: Stores API credentials, bot configuration, and risk management settings
- **TradingPair**: Manages multiple trading pairs with their specifications
- **TradingAnalytics**: Stores performance metrics and trading statistics

## Key Components

### Core Application (app.py)
- Flask application factory with SQLAlchemy integration
- Database initialization and model registration
- Environment-based configuration for database and secrets
- ProxyFix middleware for deployment compatibility

### Trading Bot (trading_bot.py)
- Binance Futures API client wrapper with error handling
- Database-driven configuration management
- Advanced trade execution logic with multiple order types
- Automatic stop-loss and take-profit order placement
- Position management with P&L calculations
- Real-time analytics and performance tracking
- Webhook signal processing capabilities

### Data Models (models.py)
- **Trade**: Comprehensive trade tracking with advanced order types and status enums
- **Position**: Position management with P&L calculations and stop-loss/take-profit tracking
- **BotSettings**: Centralized bot configuration with risk management settings
- **TradingPair**: Multiple trading pairs support with specifications
- **TradingAnalytics**: Performance metrics and trading statistics storage
- Timestamp tracking for audit trails

### Web Interface (routes.py)
- Dashboard with trade history and position overview
- Analytics page with performance metrics and charts
- Trading pairs management interface
- Advanced settings with stop-loss/take-profit configuration
- Webhook endpoint for TradingView integration
- Real-time balance and status monitoring
- RESTful API endpoints for data management

## Data Flow

1. **Webhook Reception**: TradingView sends POST request to /webhook endpoint
2. **Signal Processing**: Trading bot validates and processes the signal
3. **Trade Execution**: Bot places order via Binance API
4. **Database Update**: Trade record created/updated with execution status
5. **Position Management**: Open positions tracked and updated
6. **Dashboard Display**: Real-time updates shown in web interface

## External Dependencies

### Required APIs
- **Binance API**: For trade execution and account management
- **TradingView**: Webhook signal source

### Python Packages
- **Flask**: Web framework and routing
- **Flask-SQLAlchemy**: Database ORM
- **python-binance**: Binance API client
- **Werkzeug**: WSGI utilities and middleware

### Frontend Dependencies
- **Bootstrap 5**: UI framework with dark theme
- **Font Awesome**: Icon library
- **Vanilla JavaScript**: Client-side functionality

## Deployment Strategy

### Environment Configuration
- **DATABASE_URL**: Database connection string (defaults to SQLite)
- **SESSION_SECRET**: Flask session security key
- **BINANCE_API_KEY/SECRET**: API credentials for Binance
- **BINANCE_TESTNET**: Toggle for testnet vs mainnet

### Database Management
- Automatic table creation on application startup
- SQLAlchemy migrations for schema changes
- Connection pooling with health checks

### Security Considerations
- API credentials stored in database (encrypted recommended)
- Session management with secure keys
- ProxyFix for proper header handling in production
- Testnet mode for safe development and testing

### Scalability Features
- Connection pooling for database efficiency
- Configurable position sizing and risk management
- Modular architecture for easy feature additions
- Logging infrastructure for monitoring and debugging