# TradingView Binance Webhook Bot

## Overview

This is a Flask-based trading bot that receives webhook signals from TradingView and executes trades on Binance. The application provides a web dashboard for monitoring trades, positions, and bot settings, with real-time integration to the Binance API.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM
- **Database**: SQLite by default (configurable via DATABASE_URL environment variable)
- **API Integration**: Binance API client for trade execution
- **Webhook Processing**: RESTful endpoint for TradingView signals

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme
- **Styling**: Custom CSS with Font Awesome icons
- **JavaScript**: Vanilla JS for real-time updates and dashboard interactions
- **Responsive Design**: Bootstrap-based responsive layout

### Database Schema
- **Trade**: Records trade execution history with status tracking
- **Position**: Tracks open/closed positions with P&L calculations
- **BotSettings**: Stores API credentials and bot configuration

## Key Components

### Core Application (app.py)
- Flask application factory with SQLAlchemy integration
- Database initialization and model registration
- Environment-based configuration for database and secrets
- ProxyFix middleware for deployment compatibility

### Trading Bot (trading_bot.py)
- Binance API client wrapper with error handling
- Database-driven configuration management
- Trade execution logic with position management
- Webhook signal processing capabilities

### Data Models (models.py)
- **Trade**: Comprehensive trade tracking with enums for status and side
- **Position**: Position management with P&L calculations
- **BotSettings**: Centralized bot configuration storage
- Timestamp tracking for audit trails

### Web Interface (routes.py)
- Dashboard with trade history and position overview
- Webhook endpoint for TradingView integration
- Settings management interface
- Real-time balance and status monitoring

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