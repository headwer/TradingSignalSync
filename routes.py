from flask import render_template, request, jsonify, flash, redirect, url_for
from app import app, db
from models import Trade, Position, BotSettings, TradingPair, TradingAnalytics, OrderStatus, OrderSide, OrderType, PositionStatus
from trading_bot import trading_bot
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get recent trades
        recent_trades = Trade.query.order_by(Trade.created_at.desc()).limit(10).all()
        
        # Get open positions
        open_positions = Position.query.filter_by(status=PositionStatus.OPEN).all()
        
        # Get account balance
        balance = trading_bot.get_account_balance()
        
        # Get bot settings
        settings = BotSettings.query.first()
        
        return render_template('index.html',
                             trades=recent_trades,
                             positions=open_positions,
                             balance=balance,
                             settings=settings)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template('index.html', 
                             trades=[], 
                             positions=[], 
                             balance=None, 
                             settings=None)

@app.route('/webhook', methods=['POST'])
def webhook():
    """TradingView webhook endpoint"""
    try:
        # Get JSON data from request
        signal_data = request.get_json()
        
        if not signal_data:
            return jsonify({'error': 'No data received'}), 400
        
        logger.info(f"Received webhook signal: {signal_data}")
        
        # Process the signal
        result = trading_bot.process_webhook_signal(signal_data)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trades')
def api_trades():
    """API endpoint to get recent trades"""
    try:
        trades = Trade.query.order_by(Trade.created_at.desc()).limit(20).all()
        trades_data = []
        
        for trade in trades:
            trades_data.append({
                'id': trade.id,
                'symbol': trade.symbol,
                'side': trade.side.value,
                'quantity': trade.quantity,
                'price': trade.price,
                'status': trade.status.value,
                'created_at': trade.created_at.isoformat(),
                'error_message': trade.error_message
            })
        
        return jsonify(trades_data)
        
    except Exception as e:
        logger.error(f"Error getting trades: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions')
def api_positions():
    """API endpoint to get positions"""
    try:
        # Get positions from database
        db_positions = Position.query.filter_by(is_open=True).all()
        positions_data = []
        
        for pos in db_positions:
            positions_data.append({
                'id': pos.id,
                'symbol': pos.symbol,
                'side': pos.side.value,
                'quantity': pos.quantity,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'pnl': pos.pnl,
                'created_at': pos.created_at.isoformat()
            })
        
        # Get live positions from Binance
        live_positions = trading_bot.get_open_positions()
        
        return jsonify({
            'database_positions': positions_data,
            'live_positions': live_positions
        })
        
    except Exception as e:
        logger.error(f"Error getting positions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/balance')
def api_balance():
    """API endpoint to get account balance"""
    try:
        balance = trading_bot.get_account_balance()
        return jsonify(balance if balance else {'error': 'Unable to fetch balance'})
        
    except Exception as e:
        logger.error(f"Error getting balance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Bot settings page"""
    try:
        if request.method == 'POST':
            # Update settings
            settings = BotSettings.query.first()
            if not settings:
                settings = BotSettings()
                db.session.add(settings)
            
            settings.api_key = request.form.get('api_key', '')
            settings.api_secret = request.form.get('api_secret', '')
            settings.testnet = request.form.get('testnet') == 'on'
            settings.default_quantity = float(request.form.get('default_quantity', 0.01))
            settings.max_position_size = float(request.form.get('max_position_size', 0.1))
            settings.risk_percentage = float(request.form.get('risk_percentage', 1.0))
            settings.stop_loss_percentage = float(request.form.get('stop_loss_percentage', 2.0))
            settings.take_profit_percentage = float(request.form.get('take_profit_percentage', 4.0))
            settings.enable_stop_loss = request.form.get('enable_stop_loss') == 'on'
            settings.enable_take_profit = request.form.get('enable_take_profit') == 'on'
            settings.allowed_symbols = request.form.get('allowed_symbols', 'ETHUSDC,BTCUSDC,ADAUSDC,SOLUSDC')
            settings.is_active = request.form.get('is_active') == 'on'
            
            db.session.commit()
            
            # Reinitialize trading bot with new settings
            trading_bot.initialize_client()
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('settings'))
        
        # GET request - show settings form
        settings = BotSettings.query.first()
        return render_template('settings.html', settings=settings)
        
    except Exception as e:
        logger.error(f"Error in settings: {str(e)}")
        flash(f"Error updating settings: {str(e)}", 'error')
        return redirect(url_for('settings'))

@app.route('/api/test-connection')
def test_connection():
    """Test Binance API connection"""
    try:
        if not trading_bot.client:
            return jsonify({'error': 'No API connection configured'}), 400
        
        # Test connection by getting server time
        server_time = trading_bot.client.get_server_time()
        balance = trading_bot.get_account_balance()
        
        return jsonify({
            'success': True,
            'server_time': server_time,
            'balance': balance,
            'testnet': trading_bot.settings.testnet
        })
        
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/analytics')
def analytics():
    """Trading analytics page"""
    try:
        # Get available trading pairs
        trading_pairs = TradingPair.query.filter_by(is_active=True).all()
        
        # Get analytics for all pairs
        analytics_data = {}
        for pair in trading_pairs:
            analytics_data[pair.symbol] = trading_bot.calculate_analytics(pair.symbol)
        
        # Get overall analytics
        overall_analytics = trading_bot.calculate_analytics()
        
        return render_template('analytics.html',
                             trading_pairs=trading_pairs,
                             analytics_data=analytics_data,
                             overall_analytics=overall_analytics)
    except Exception as e:
        logger.error(f"Error loading analytics: {str(e)}")
        flash(f"Error loading analytics: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/trading-pairs')
def trading_pairs():
    """Trading pairs management page"""
    try:
        pairs = TradingPair.query.all()
        return render_template('trading_pairs.html', pairs=pairs)
    except Exception as e:
        logger.error(f"Error loading trading pairs: {str(e)}")
        flash(f"Error loading trading pairs: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/api/trading-pairs', methods=['GET', 'POST'])
def api_trading_pairs():
    """API endpoint for trading pairs management"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            
            # Add new trading pair
            pair = TradingPair(
                symbol=data['symbol'].upper(),
                base_asset=data['base_asset'].upper(),
                quote_asset=data['quote_asset'].upper(),
                min_qty=float(data.get('min_qty', 0.001)),
                max_qty=float(data.get('max_qty', 1000.0)),
                step_size=float(data.get('step_size', 0.001)),
                tick_size=float(data.get('tick_size', 0.01)),
                is_active=data.get('is_active', True)
            )
            
            db.session.add(pair)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Trading pair added successfully'})
        
        # GET request - return all pairs
        pairs = TradingPair.query.all()
        pairs_data = []
        
        for pair in pairs:
            pairs_data.append({
                'id': pair.id,
                'symbol': pair.symbol,
                'base_asset': pair.base_asset,
                'quote_asset': pair.quote_asset,
                'min_qty': pair.min_qty,
                'max_qty': pair.max_qty,
                'step_size': pair.step_size,
                'tick_size': pair.tick_size,
                'is_active': pair.is_active,
                'created_at': pair.created_at.isoformat()
            })
        
        return jsonify(pairs_data)
        
    except Exception as e:
        logger.error(f"Error managing trading pairs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/<symbol>')
def api_analytics(symbol=None):
    """API endpoint for trading analytics"""
    try:
        days = request.args.get('days', 30, type=int)
        analytics = trading_bot.calculate_analytics(symbol, days)
        
        if analytics:
            return jsonify(analytics)
        else:
            return jsonify({'error': 'No data available for analysis'}), 404
            
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/order-types')
def api_order_types():
    """API endpoint to get available order types"""
    try:
        order_types = [
            {'value': 'MARKET', 'label': 'Market Order'},
            {'value': 'LIMIT', 'label': 'Limit Order'},
            {'value': 'STOP_MARKET', 'label': 'Stop Market'},
            {'value': 'STOP_LIMIT', 'label': 'Stop Limit'},
            {'value': 'TAKE_PROFIT', 'label': 'Take Profit Market'},
            {'value': 'TAKE_PROFIT_LIMIT', 'label': 'Take Profit Limit'}
        ]
        return jsonify(order_types)
    except Exception as e:
        logger.error(f"Error getting order types: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
