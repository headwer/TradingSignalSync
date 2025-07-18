from app import db
from datetime import datetime
from sqlalchemy import Enum
import enum

class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"

class OrderSide(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"

class PositionStatus(enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, default="ETHUSDC")
    side = db.Column(Enum(OrderSide), nullable=False)
    order_type = db.Column(Enum(OrderType), nullable=False, default=OrderType.MARKET)
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float)
    stop_price = db.Column(db.Float)
    filled_quantity = db.Column(db.Float, default=0.0)
    avg_price = db.Column(db.Float)
    order_id = db.Column(db.String(50))
    client_order_id = db.Column(db.String(50))
    status = db.Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    signal_data = db.Column(db.Text)
    error_message = db.Column(db.Text)
    commission = db.Column(db.Float, default=0.0)
    commission_asset = db.Column(db.String(10))
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
    unrealized_pnl = db.Column(db.Float, default=0.0)
    realized_pnl = db.Column(db.Float, default=0.0)
    stop_loss_price = db.Column(db.Float)
    take_profit_price = db.Column(db.Float)
    stop_loss_order_id = db.Column(db.String(50))
    take_profit_order_id = db.Column(db.String(50))
    status = db.Column(Enum(PositionStatus), nullable=False, default=PositionStatus.OPEN)
    close_price = db.Column(db.Float)
    closed_at = db.Column(db.DateTime)
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
    stop_loss_percentage = db.Column(db.Float, default=2.0)
    take_profit_percentage = db.Column(db.Float, default=4.0)
    enable_stop_loss = db.Column(db.Boolean, default=True)
    enable_take_profit = db.Column(db.Boolean, default=True)
    allowed_symbols = db.Column(db.Text, default="ETHUSDC,BTCUSDC,ADAUSDC,SOLUSDC")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TradingPair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, unique=True)
    base_asset = db.Column(db.String(10), nullable=False)
    quote_asset = db.Column(db.String(10), nullable=False)
    min_qty = db.Column(db.Float, default=0.001)
    max_qty = db.Column(db.Float, default=1000.0)
    step_size = db.Column(db.Float, default=0.001)
    tick_size = db.Column(db.Float, default=0.01)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TradingAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    losing_trades = db.Column(db.Integer, default=0)
    total_volume = db.Column(db.Float, default=0.0)
    total_pnl = db.Column(db.Float, default=0.0)
    max_drawdown = db.Column(db.Float, default=0.0)
    win_rate = db.Column(db.Float, default=0.0)
    avg_win = db.Column(db.Float, default=0.0)
    avg_loss = db.Column(db.Float, default=0.0)
    profit_factor = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
