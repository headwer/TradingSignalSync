import os
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
from models import Trade, Position, BotSettings, OrderStatus, OrderSide
from app import db
import json

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.client = None
        self.settings = None
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize Binance client with API keys"""
        try:
            # Get settings from database or environment
            self.settings = BotSettings.query.first()
            
            if not self.settings:
                # Create default settings from environment variables
                api_key = os.getenv("BINANCE_API_KEY", "")
                api_secret = os.getenv("BINANCE_API_SECRET", "")
                testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
                
                self.settings = BotSettings(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=testnet
                )
                db.session.add(self.settings)
                db.session.commit()
            
            if self.settings.api_key and self.settings.api_secret:
                self.client = Client(
                    api_key=self.settings.api_key,
                    api_secret=self.settings.api_secret,
                    testnet=self.settings.testnet
                )
                logger.info(f"Binance client initialized (testnet: {self.settings.testnet})")
            else:
                logger.warning("No API keys configured")
                
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {str(e)}")
    
    def process_webhook_signal(self, signal_data):
        """Process incoming TradingView webhook signal"""
        try:
            logger.info(f"Processing webhook signal: {signal_data}")
            
            if not self.client:
                raise Exception("Binance client not initialized")
            
            if not self.settings.is_active:
                raise Exception("Trading bot is deactivated")
            
            # Parse signal data
            action = signal_data.get('action', '').upper()
            symbol = signal_data.get('symbol', 'ETHUSDC').upper()
            quantity = float(signal_data.get('quantity', self.settings.default_quantity))
            
            # Validate signal
            if action not in ['BUY', 'SELL']:
                raise Exception(f"Invalid action: {action}")
            
            # Create trade record
            trade = Trade(
                symbol=symbol,
                side=OrderSide.BUY if action == 'BUY' else OrderSide.SELL,
                quantity=quantity,
                signal_data=json.dumps(signal_data),
                status=OrderStatus.PENDING
            )
            db.session.add(trade)
            db.session.commit()
            
            # Execute trade
            result = self.execute_trade(trade)
            return result
            
        except Exception as e:
            logger.error(f"Error processing webhook signal: {str(e)}")
            if 'trade' in locals():
                trade.status = OrderStatus.FAILED
                trade.error_message = str(e)
                db.session.commit()
            raise
    
    def execute_trade(self, trade):
        """Execute trade on Binance"""
        try:
            logger.info(f"Executing trade: {trade.side.value} {trade.quantity} {trade.symbol}")
            
            # Check if we need to close existing position first
            if trade.side == OrderSide.BUY:
                self.close_short_positions(trade.symbol)
            else:
                self.close_long_positions(trade.symbol)
            
            # Execute market order
            order = self.client.futures_create_order(
                symbol=trade.symbol,
                side=trade.side.value,
                type='MARKET',
                quantity=trade.quantity
            )
            
            # Update trade record
            trade.order_id = order['orderId']
            trade.status = OrderStatus.FILLED
            trade.price = float(order.get('avgPrice', 0))
            
            # Create or update position
            self.update_position(trade)
            
            db.session.commit()
            
            logger.info(f"Trade executed successfully: {order['orderId']}")
            return {
                'success': True,
                'order_id': order['orderId'],
                'message': f"Trade executed: {trade.side.value} {trade.quantity} {trade.symbol}"
            }
            
        except BinanceAPIException as e:
            error_msg = f"Binance API error: {e.message}"
            logger.error(error_msg)
            trade.status = OrderStatus.FAILED
            trade.error_message = error_msg
            db.session.commit()
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Trade execution failed: {str(e)}"
            logger.error(error_msg)
            trade.status = OrderStatus.FAILED
            trade.error_message = error_msg
            db.session.commit()
            raise Exception(error_msg)
    
    def close_long_positions(self, symbol):
        """Close all long positions for symbol"""
        try:
            positions = Position.query.filter_by(
                symbol=symbol,
                side=OrderSide.BUY,
                is_open=True
            ).all()
            
            for position in positions:
                # Create sell order to close position
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='SELL',
                    type='MARKET',
                    quantity=position.quantity
                )
                
                position.is_open = False
                db.session.commit()
                
                logger.info(f"Closed long position: {position.quantity} {symbol}")
                
        except Exception as e:
            logger.error(f"Error closing long positions: {str(e)}")
    
    def close_short_positions(self, symbol):
        """Close all short positions for symbol"""
        try:
            positions = Position.query.filter_by(
                symbol=symbol,
                side=OrderSide.SELL,
                is_open=True
            ).all()
            
            for position in positions:
                # Create buy order to close position
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    type='MARKET',
                    quantity=position.quantity
                )
                
                position.is_open = False
                db.session.commit()
                
                logger.info(f"Closed short position: {position.quantity} {symbol}")
                
        except Exception as e:
            logger.error(f"Error closing short positions: {str(e)}")
    
    def update_position(self, trade):
        """Update position after trade execution"""
        try:
            position = Position(
                symbol=trade.symbol,
                side=trade.side,
                quantity=trade.quantity,
                entry_price=trade.price,
                current_price=trade.price
            )
            
            db.session.add(position)
            db.session.commit()
            
            logger.info(f"Position updated: {trade.side.value} {trade.quantity} {trade.symbol}")
            
        except Exception as e:
            logger.error(f"Error updating position: {str(e)}")
    
    def get_account_balance(self):
        """Get account balance"""
        try:
            if not self.client:
                return None
            
            account = self.client.futures_account()
            return {
                'total_wallet_balance': float(account['totalWalletBalance']),
                'total_unrealized_pnl': float(account['totalUnrealizedProfit']),
                'available_balance': float(account['availableBalance'])
            }
            
        except Exception as e:
            logger.error(f"Error getting account balance: {str(e)}")
            return None
    
    def get_open_positions(self):
        """Get open positions"""
        try:
            if not self.client:
                return []
            
            positions = self.client.futures_position_information()
            open_positions = []
            
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    open_positions.append({
                        'symbol': pos['symbol'],
                        'side': 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT',
                        'size': abs(float(pos['positionAmt'])),
                        'entry_price': float(pos['entryPrice']),
                        'mark_price': float(pos['markPrice']),
                        'pnl': float(pos['unRealizedProfit']),
                        'percentage': float(pos['percentage'])
                    })
            
            return open_positions
            
        except Exception as e:
            logger.error(f"Error getting open positions: {str(e)}")
            return []

# Global bot instance
trading_bot = TradingBot()
