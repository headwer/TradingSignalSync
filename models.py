from app import db
from datetime import datetime
from sqlalchemy import Enum
import enum

class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class OrderSide(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, default="ETHUSDC")
    side = db.Column(Enum(OrderSide), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float)
    order_id = db.Column(db.String(50))
    status = db.Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    signal_data = db.Column(db.Text)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, default="ETHUSDC")
    side = db.Column(Enum(OrderSide), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float)
    current_price = db.Column(db.Float)
    pnl = db.Column(db.Float, default=0.0)
    is_open = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BotSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(255))
    api_secret = db.Column(db.String(255))
    testnet = db.Column(db.Boolean, default=True)
    default_quantity = db.Column(db.Float, default=0.01)
    max_position_size = db.Column(db.Float, default=0.1)
    risk_percentage = db.Column(db.Float, default=1.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
