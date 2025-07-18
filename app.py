import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///trading_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    
    # Create default trading pairs if they don't exist
    from models import TradingPair
    if not TradingPair.query.first():
        default_pairs = [
            TradingPair(
                symbol='ETHUSDC',
                base_asset='ETH',
                quote_asset='USDC',
                min_qty=0.001,
                max_qty=1000.0,
                step_size=0.001,
                tick_size=0.01,
                is_active=True
            ),
            TradingPair(
                symbol='BTCUSDC',
                base_asset='BTC',
                quote_asset='USDC',
                min_qty=0.00001,
                max_qty=100.0,
                step_size=0.00001,
                tick_size=0.01,
                is_active=True
            ),
            TradingPair(
                symbol='ADAUSDC',
                base_asset='ADA',
                quote_asset='USDC',
                min_qty=1.0,
                max_qty=100000.0,
                step_size=1.0,
                tick_size=0.0001,
                is_active=True
            ),
            TradingPair(
                symbol='SOLUSDC',
                base_asset='SOL',
                quote_asset='USDC',
                min_qty=0.01,
                max_qty=10000.0,
                step_size=0.01,
                tick_size=0.001,
                is_active=True
            )
        ]
        
        for pair in default_pairs:
            db.session.add(pair)
        
        db.session.commit()

# Import routes
import routes
