import os
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
from models import Trade, Position, BotSettings, TradingPair, TradingAnalytics, OrderStatus, OrderSide, OrderType, PositionStatus
from app import db
import json
from datetime import datetime, date
import uuid

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.client = None
        self.settings = None
        
    def initialize_client(self):
        """Initialize Binance client with API keys"""
        from app import app
        
        with app.app_context():
            self._initialize_client_internal()
    
    def _initialize_client_internal(self):
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
                
                # Initialize trading pairs
                self._initialize_trading_pairs()
            
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
    
    def _initialize_trading_pairs(self):
        """Initialize default trading pairs"""
        try:
            default_pairs = [
                ("ETHUSDC", "ETH", "USDC"),
                ("BTCUSDC", "BTC", "USDC"),
                ("ADAUSDC", "ADA", "USDC"),
                ("SOLUSDC", "SOL", "USDC"),
                ("BNBUSDC", "BNB", "USDC"),
                ("DOTUSDC", "DOT", "USDC"),
                ("LINKUSDC", "LINK", "USDC"),
                ("AVAXUSDC", "AVAX", "USDC")
            ]
            
            for symbol, base, quote in default_pairs:
                existing = TradingPair.query.filter_by(symbol=symbol).first()
                if not existing:
                    pair = TradingPair(
                        symbol=symbol,
                        base_asset=base,
                        quote_asset=quote
                    )
                    db.session.add(pair)
            
            db.session.commit()
            logger.info("Default trading pairs initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize trading pairs: {str(e)}")
    
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
            order_type = signal_data.get('order_type', 'MARKET').upper()
            quantity = float(signal_data.get('quantity', self.settings.default_quantity))
            price = signal_data.get('price')
            stop_price = signal_data.get('stop_price')
            stop_loss = signal_data.get('stop_loss')
            take_profit = signal_data.get('take_profit')
            
            # Validate signal
            if action not in ['BUY', 'SELL']:
                raise Exception(f"Invalid action: {action}")
            
            # Validate symbol
            if not self._is_symbol_allowed(symbol):
                raise Exception(f"Symbol {symbol} not allowed")
            
            # Get trading pair info
            trading_pair = self._get_trading_pair(symbol)
            if not trading_pair:
                raise Exception(f"Trading pair {symbol} not found")
            
            # Validate quantity
            quantity = self._validate_quantity(quantity, trading_pair)
            
            # Create trade record
            trade = Trade(
                symbol=symbol,
                side=OrderSide.BUY if action == 'BUY' else OrderSide.SELL,
                order_type=OrderType(order_type) if order_type in [e.value for e in OrderType] else OrderType.MARKET,
                quantity=quantity,
                price=float(price) if price else None,
                stop_price=float(stop_price) if stop_price else None,
                signal_data=json.dumps(signal_data),
                status=OrderStatus.PENDING,
                client_order_id=str(uuid.uuid4())
            )
            db.session.add(trade)
            db.session.commit()
            
            # Execute trade
            result = self.execute_trade(trade, stop_loss, take_profit)
            return result
            
        except Exception as e:
            logger.error(f"Error processing webhook signal: {str(e)}")
            if 'trade' in locals():
                trade.status = OrderStatus.FAILED
                trade.error_message = str(e)
                db.session.commit()
            raise
    
    def _is_symbol_allowed(self, symbol):
        """Check if symbol is allowed for trading"""
        if not self.settings.allowed_symbols:
            return True
        
        allowed_symbols = [s.strip() for s in self.settings.allowed_symbols.split(',')]
        return symbol in allowed_symbols
    
    def _get_trading_pair(self, symbol):
        """Get trading pair information"""
        return TradingPair.query.filter_by(symbol=symbol, is_active=True).first()
    
    def _validate_quantity(self, quantity, trading_pair):
        """Validate and adjust quantity based on trading pair rules"""
        if quantity < trading_pair.min_qty:
            quantity = trading_pair.min_qty
        elif quantity > trading_pair.max_qty:
            quantity = trading_pair.max_qty
        
        # Round to step size
        step_size = trading_pair.step_size
        quantity = round(quantity / step_size) * step_size
        
        return quantity
    
    def _calculate_stop_loss_price(self, entry_price, side, percentage=None):
        """Calculate stop loss price"""
        if percentage is None:
            percentage = self.settings.stop_loss_percentage
        
        if side == OrderSide.BUY:
            # For long positions, stop loss is below entry price
            return entry_price * (1 - percentage / 100)
        else:
            # For short positions, stop loss is above entry price
            return entry_price * (1 + percentage / 100)
    
    def _calculate_take_profit_price(self, entry_price, side, percentage=None):
        """Calculate take profit price"""
        if percentage is None:
            percentage = self.settings.take_profit_percentage
        
        if side == OrderSide.BUY:
            # For long positions, take profit is above entry price
            return entry_price * (1 + percentage / 100)
        else:
            # For short positions, take profit is below entry price
            return entry_price * (1 - percentage / 100)
    
    def execute_trade(self, trade, stop_loss=None, take_profit=None):
        """Execute trade on Binance with advanced order types"""
        try:
            logger.info(f"Executing trade: {trade.side.value} {trade.quantity} {trade.symbol} (Type: {trade.order_type.value})")
            
            # Check if we need to close existing position first
            if trade.side == OrderSide.BUY:
                self.close_short_positions(trade.symbol)
            else:
                self.close_long_positions(trade.symbol)
            
            # Calculate quantity using 1/4 of balance
            trade.quantity = self._calculate_quantity_with_balance_division(trade.symbol)
            
            # Get current market price for limit order
            ticker = self.client.futures_symbol_ticker(symbol=trade.symbol)
            current_price = float(ticker['price'])
            
            # Set limit price with small buffer (0.1% better than market)
            if trade.side == OrderSide.BUY:
                limit_price = current_price * 0.999  # Buy slightly below market
            else:
                limit_price = current_price * 1.001  # Sell slightly above market
            
            # Round price to appropriate decimals
            limit_price = round(limit_price, 2)
            trade.price = limit_price
            trade.order_type = OrderType.LIMIT  # Force all orders to be limit
            
            # Prepare order parameters - always use LIMIT orders
            order_params = {
                'symbol': trade.symbol,
                'side': trade.side.value,
                'type': 'LIMIT',
                'quantity': trade.quantity,
                'price': limit_price,
                'timeInForce': 'GTC',
                'newClientOrderId': trade.client_order_id
            }
            
            # Execute main order as LIMIT
            order = self.client.futures_create_order(**order_params)
            
            # Update trade record
            trade.order_id = order['orderId']
            trade.status = OrderStatus.FILLED if order['status'] == 'FILLED' else OrderStatus.PENDING
            trade.filled_quantity = float(order.get('executedQty', 0))
            trade.avg_price = float(order.get('avgPrice', 0)) if order.get('avgPrice') else None
            
            # Create or update position if filled
            if trade.status == OrderStatus.FILLED:
                position = self.update_position(trade)
                
                # Set up stop loss and take profit orders using limit orders
                if position and (self.settings.enable_stop_loss or self.settings.enable_take_profit):
                    self._setup_stop_loss_take_profit_limit(position, stop_loss, take_profit)
            
            db.session.commit()
            
            logger.info(f"Trade executed successfully: {order['orderId']}")
            return {
                'success': True,
                'order_id': order['orderId'],
                'status': trade.status.value,
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
                status=PositionStatus.OPEN
            ).all()
            
            for position in positions:
                # Get current market price for limit order
                ticker = self.client.futures_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                
                # Create sell limit order to close position (slightly better than market)
                close_price = current_price * 1.001  # Sell slightly above market
                close_price = round(close_price, 2)
                
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='SELL',
                    type='LIMIT',
                    quantity=position.quantity,
                    price=close_price,
                    timeInForce='GTC'
                )
                
                position.status = PositionStatus.CLOSED
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
                status=PositionStatus.OPEN
            ).all()
            
            for position in positions:
                # Get current market price for limit order
                ticker = self.client.futures_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                
                # Create buy limit order to close position (slightly better than market)
                close_price = current_price * 0.999  # Buy slightly below market
                close_price = round(close_price, 2)
                
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    type='LIMIT',
                    quantity=position.quantity,
                    price=close_price,
                    timeInForce='GTC'
                )
                
                position.status = PositionStatus.CLOSED
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
            return position
            
        except Exception as e:
            logger.error(f"Error updating position: {str(e)}")
            return None
    
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
    
    def _setup_stop_loss_take_profit(self, position, stop_loss=None, take_profit=None):
        """Set up stop loss and take profit orders for a position"""
        try:
            entry_price = position.entry_price
            
            # Set up stop loss
            if self.settings.enable_stop_loss:
                sl_price = stop_loss if stop_loss else self._calculate_stop_loss_price(entry_price, position.side)
                sl_order = self._create_stop_loss_order(position, sl_price)
                if sl_order:
                    position.stop_loss_price = sl_price
                    position.stop_loss_order_id = sl_order['orderId']
            
            # Set up take profit
            if self.settings.enable_take_profit:
                tp_price = take_profit if take_profit else self._calculate_take_profit_price(entry_price, position.side)
                tp_order = self._create_take_profit_order(position, tp_price)
                if tp_order:
                    position.take_profit_price = tp_price
                    position.take_profit_order_id = tp_order['orderId']
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to set up stop loss/take profit: {str(e)}")
    
    def _create_stop_loss_order(self, position, stop_price):
        """Create stop loss order"""
        try:
            # Opposite side for closing position
            side = 'SELL' if position.side == OrderSide.BUY else 'BUY'
            
            order = self.client.futures_create_order(
                symbol=position.symbol,
                side=side,
                type='STOP_MARKET',
                quantity=position.quantity,
                stopPrice=stop_price,
                newClientOrderId=f"SL_{position.id}_{str(uuid.uuid4())[:8]}"
            )
            
            logger.info(f"Stop loss order created: {order['orderId']} at {stop_price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to create stop loss order: {str(e)}")
            return None
    
    def _create_take_profit_order(self, position, take_profit_price):
        """Create take profit order"""
        try:
            # Opposite side for closing position
            side = 'SELL' if position.side == OrderSide.BUY else 'BUY'
            
            order = self.client.futures_create_order(
                symbol=position.symbol,
                side=side,
                type='TAKE_PROFIT_MARKET',
                quantity=position.quantity,
                stopPrice=take_profit_price,
                newClientOrderId=f"TP_{position.id}_{str(uuid.uuid4())[:8]}"
            )
            
            logger.info(f"Take profit order created: {order['orderId']} at {take_profit_price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to create take profit order: {str(e)}")
            return None
    
    def calculate_analytics(self, symbol=None, days=30):
        """Calculate trading analytics"""
        try:
            from datetime import datetime, timedelta
            
            # Get trades for analysis
            query = Trade.query.filter(Trade.status == OrderStatus.FILLED)
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            
            trades = query.filter(
                Trade.created_at >= datetime.utcnow() - timedelta(days=days)
            ).all()
            
            if not trades:
                return None
            
            # Calculate metrics
            total_trades = len(trades)
            winning_trades = 0
            losing_trades = 0
            total_pnl = 0
            total_volume = 0
            wins = []
            losses = []
            
            for trade in trades:
                # Get position for this trade
                position = Position.query.filter_by(
                    symbol=trade.symbol,
                    created_at=trade.created_at
                ).first()
                
                if position:
                    pnl = position.realized_pnl
                    total_pnl += pnl
                    total_volume += trade.quantity * (trade.avg_price or trade.price or 0)
                    
                    if pnl > 0:
                        winning_trades += 1
                        wins.append(pnl)
                    else:
                        losing_trades += 1
                        losses.append(abs(pnl))
            
            # Calculate derived metrics
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            profit_factor = (sum(wins) / sum(losses)) if losses else float('inf')
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'total_volume': total_volume,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor
            }
            
        except Exception as e:
            logger.error(f"Error calculating analytics: {str(e)}")
            return None
    
    def _calculate_stop_loss_price(self, entry_price, side):
        """Calculate stop loss price based on entry price and side"""
        try:
            percentage = self.settings.stop_loss_percentage / 100
            
            if side == OrderSide.BUY:
                # For long positions, stop loss is below entry price
                return entry_price * (1 - percentage)
            else:
                # For short positions, stop loss is above entry price
                return entry_price * (1 + percentage)
                
        except Exception as e:
            logger.error(f"Error calculating stop loss price: {str(e)}")
            return None
    
    def _calculate_take_profit_price(self, entry_price, side):
        """Calculate take profit price based on entry price and side"""
        try:
            percentage = self.settings.take_profit_percentage / 100
            
            if side == OrderSide.BUY:
                # For long positions, take profit is above entry price
                return entry_price * (1 + percentage)
            else:
                # For short positions, take profit is below entry price
                return entry_price * (1 - percentage)
                
        except Exception as e:
            logger.error(f"Error calculating take profit price: {str(e)}")
            return None
    
    def _calculate_quantity_with_balance_division(self, symbol):
        """Calculate quantity using 1/4 of available balance"""
        try:
            # Get account balance
            account = self.client.futures_account()
            available_balance = float(account['availableBalance'])
            
            # Use 1/4 of the available balance
            quarter_balance = available_balance / 4
            
            # Get current price to calculate quantity
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Calculate quantity based on quarter balance
            quantity = quarter_balance / current_price
            
            # Get trading pair to validate quantity
            trading_pair = self._get_trading_pair(symbol)
            if trading_pair:
                quantity = self._validate_quantity(quantity, trading_pair)
            else:
                # Default minimum quantity if no trading pair found
                quantity = max(quantity, 0.001)
            
            logger.info(f"Calculated quantity for {symbol}: {quantity} (using 1/4 balance: ${quarter_balance:.2f})")
            return quantity
            
        except Exception as e:
            logger.error(f"Error calculating quantity with balance division: {str(e)}")
            # Fallback to default quantity
            return self.settings.default_quantity if self.settings else 0.01
    
    def _setup_stop_loss_take_profit_limit(self, position, stop_loss=None, take_profit=None):
        """Set up stop loss and take profit orders using LIMIT orders only"""
        try:
            entry_price = position.entry_price
            
            # Set up stop loss with limit order
            if self.settings.enable_stop_loss:
                sl_price = stop_loss if stop_loss else self._calculate_stop_loss_price(entry_price, position.side)
                sl_order = self._create_stop_loss_limit_order(position, sl_price)
                if sl_order:
                    position.stop_loss_price = sl_price
                    position.stop_loss_order_id = sl_order['orderId']
            
            # Set up take profit with limit order
            if self.settings.enable_take_profit:
                tp_price = take_profit if take_profit else self._calculate_take_profit_price(entry_price, position.side)
                tp_order = self._create_take_profit_limit_order(position, tp_price)
                if tp_order:
                    position.take_profit_price = tp_price
                    position.take_profit_order_id = tp_order['orderId']
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to set up stop loss/take profit with limit orders: {str(e)}")
    
    def _create_stop_loss_limit_order(self, position, stop_price):
        """Create stop loss order using STOP_LIMIT instead of STOP_MARKET"""
        try:
            # Opposite side for closing position
            side = 'SELL' if position.side == OrderSide.BUY else 'BUY'
            
            # For limit orders, we need both stop price and limit price
            # Set limit price slightly worse than stop price to ensure execution
            if side == 'SELL':
                limit_price = stop_price * 0.999  # Sell limit slightly below stop
            else:
                limit_price = stop_price * 1.001  # Buy limit slightly above stop
            
            limit_price = round(limit_price, 2)
            stop_price = round(stop_price, 2)
            
            order = self.client.futures_create_order(
                symbol=position.symbol,
                side=side,
                type='STOP_LIMIT',
                quantity=position.quantity,
                price=limit_price,
                stopPrice=stop_price,
                timeInForce='GTC',
                newClientOrderId=f"SL_{position.id}_{str(uuid.uuid4())[:8]}"
            )
            
            logger.info(f"Stop loss LIMIT order created: {order['orderId']} at stop {stop_price}, limit {limit_price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to create stop loss limit order: {str(e)}")
            return None
    
    def _create_take_profit_limit_order(self, position, take_profit_price):
        """Create take profit order using TAKE_PROFIT_LIMIT instead of TAKE_PROFIT_MARKET"""
        try:
            # Opposite side for closing position
            side = 'SELL' if position.side == OrderSide.BUY else 'BUY'
            
            # For limit orders, we need both stop price and limit price
            # Set limit price slightly better than stop price to ensure good execution
            if side == 'SELL':
                limit_price = take_profit_price * 1.001  # Sell limit slightly above stop
            else:
                limit_price = take_profit_price * 0.999  # Buy limit slightly below stop
            
            limit_price = round(limit_price, 2)
            take_profit_price = round(take_profit_price, 2)
            
            order = self.client.futures_create_order(
                symbol=position.symbol,
                side=side,
                type='TAKE_PROFIT_LIMIT',
                quantity=position.quantity,
                price=limit_price,
                stopPrice=take_profit_price,
                timeInForce='GTC',
                newClientOrderId=f"TP_{position.id}_{str(uuid.uuid4())[:8]}"
            )
            
            logger.info(f"Take profit LIMIT order created: {order['orderId']} at stop {take_profit_price}, limit {limit_price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to create take profit limit order: {str(e)}")
            return None

# Global bot instance
trading_bot = TradingBot()
