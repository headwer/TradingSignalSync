// TradingView Binance Webhook Bot JavaScript

// Global variables
let refreshInterval = null;
let isRefreshing = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    startAutoRefresh();
});

// Initialize application
function initializeApp() {
    console.log('TradingView Binance Webhook Bot initialized');
    
    // Initialize tooltips
    initializeTooltips();
    
    // Check connection status
    checkConnectionStatus();
}

// Setup event listeners
function setupEventListeners() {
    // Refresh buttons
    const refreshButtons = document.querySelectorAll('[onclick*="refresh"]');
    refreshButtons.forEach(button => {
        button.addEventListener('click', function() {
            const functionName = this.getAttribute('onclick').match(/(\w+)\(/)[1];
            if (functionName === 'refreshTrades') {
                refreshTrades();
            } else if (functionName === 'refreshPositions') {
                refreshPositions();
            }
        });
    });
    
    // Copy webhook URL button
    const copyButton = document.querySelector('[onclick="copyWebhookUrl()"]');
    if (copyButton) {
        copyButton.addEventListener('click', copyWebhookUrl);
    }
    
    // Settings form
    const settingsForm = document.querySelector('form[action*="settings"]');
    if (settingsForm) {
        settingsForm.addEventListener('submit', handleSettingsSubmit);
    }
    
    // Test connection button
    const testConnectionButton = document.querySelector('[onclick="testConnection()"]');
    if (testConnectionButton) {
        testConnectionButton.addEventListener('click', testConnection);
    }
}

// Initialize tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Copy webhook URL to clipboard
function copyWebhookUrl() {
    const webhookInput = document.getElementById('webhookUrl');
    if (webhookInput) {
        webhookInput.select();
        webhookInput.setSelectionRange(0, 99999); // For mobile devices
        
        try {
            document.execCommand('copy');
            showNotification('Webhook URL copied to clipboard!', 'success');
        } catch (err) {
            console.error('Failed to copy URL:', err);
            showNotification('Failed to copy URL', 'error');
        }
    }
}

// Refresh trades table
function refreshTrades() {
    if (isRefreshing) return;
    
    isRefreshing = true;
    const tradesTable = document.getElementById('tradesTable');
    
    if (tradesTable) {
        tradesTable.classList.add('loading');
        
        fetch('/api/trades')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                updateTradesTable(data);
            })
            .catch(error => {
                console.error('Error refreshing trades:', error);
                showNotification('Failed to refresh trades: ' + error.message, 'error');
            })
            .finally(() => {
                tradesTable.classList.remove('loading');
                isRefreshing = false;
            });
    }
}

// Refresh positions table
function refreshPositions() {
    if (isRefreshing) return;
    
    isRefreshing = true;
    const positionsTable = document.getElementById('positionsTable');
    
    if (positionsTable) {
        positionsTable.classList.add('loading');
        
        fetch('/api/positions')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                updatePositionsTable(data);
            })
            .catch(error => {
                console.error('Error refreshing positions:', error);
                showNotification('Failed to refresh positions: ' + error.message, 'error');
            })
            .finally(() => {
                positionsTable.classList.remove('loading');
                isRefreshing = false;
            });
    }
}

// Update trades table
function updateTradesTable(trades) {
    const tradesTable = document.getElementById('tradesTable');
    if (!tradesTable) return;
    
    if (trades.length === 0) {
        tradesTable.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-history fa-3x text-muted mb-3"></i>
                <p class="text-muted">No trades yet</p>
            </div>
        `;
        return;
    }
    
    let tableHTML = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Error</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    trades.forEach(trade => {
        const sideClass = trade.side === 'BUY' ? 'bg-success' : 'bg-danger';
        const statusClass = trade.status === 'FILLED' ? 'bg-success' : 
                           trade.status === 'FAILED' ? 'bg-danger' : 'bg-warning';
        const price = trade.price ? `$${parseFloat(trade.price).toFixed(2)}` : 'N/A';
        const createdAt = new Date(trade.created_at).toLocaleString();
        const errorButton = trade.error_message ? 
            `<button class="btn btn-sm btn-outline-danger" data-bs-toggle="tooltip" title="${trade.error_message}">
                <i class="fas fa-exclamation-triangle"></i>
            </button>` : '-';
        
        tableHTML += `
            <tr>
                <td>${trade.symbol}</td>
                <td><span class="badge ${sideClass}">${trade.side}</span></td>
                <td>${parseFloat(trade.quantity).toFixed(6)}</td>
                <td>${price}</td>
                <td><span class="badge ${statusClass}">${trade.status}</span></td>
                <td>${createdAt}</td>
                <td>${errorButton}</td>
            </tr>
        `;
    });
    
    tableHTML += '</tbody></table></div>';
    tradesTable.innerHTML = tableHTML;
    
    // Reinitialize tooltips
    initializeTooltips();
}

// Update positions table
function updatePositionsTable(data) {
    const positionsTable = document.getElementById('positionsTable');
    if (!positionsTable) return;
    
    const positions = data.database_positions || [];
    const livePositions = data.live_positions || [];
    
    if (positions.length === 0 && livePositions.length === 0) {
        positionsTable.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-chart-line fa-3x text-muted mb-3"></i>
                <p class="text-muted">No open positions</p>
            </div>
        `;
        return;
    }
    
    let tableHTML = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>Quantity</th>
                        <th>Entry Price</th>
                        <th>Current Price</th>
                        <th>PNL</th>
                        <th>Source</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // Add database positions
    positions.forEach(position => {
        const sideClass = position.side === 'BUY' ? 'bg-success' : 'bg-danger';
        const pnlClass = position.pnl >= 0 ? 'text-success' : 'text-danger';
        const entryPrice = position.entry_price ? `$${parseFloat(position.entry_price).toFixed(2)}` : 'N/A';
        const currentPrice = position.current_price ? `$${parseFloat(position.current_price).toFixed(2)}` : 'N/A';
        const createdAt = new Date(position.created_at).toLocaleString();
        
        tableHTML += `
            <tr>
                <td>${position.symbol}</td>
                <td><span class="badge ${sideClass}">${position.side}</span></td>
                <td>${parseFloat(position.quantity).toFixed(6)}</td>
                <td>${entryPrice}</td>
                <td>${currentPrice}</td>
                <td class="${pnlClass}">$${parseFloat(position.pnl).toFixed(2)}</td>
                <td><span class="badge bg-secondary">Database</span></td>
                <td>${createdAt}</td>
            </tr>
        `;
    });
    
    // Add live positions
    livePositions.forEach(position => {
        const sideClass = position.side === 'LONG' ? 'bg-success' : 'bg-danger';
        const pnlClass = position.pnl >= 0 ? 'text-success' : 'text-danger';
        
        tableHTML += `
            <tr>
                <td>${position.symbol}</td>
                <td><span class="badge ${sideClass}">${position.side}</span></td>
                <td>${parseFloat(position.size).toFixed(6)}</td>
                <td>$${parseFloat(position.entry_price).toFixed(2)}</td>
                <td>$${parseFloat(position.mark_price).toFixed(2)}</td>
                <td class="${pnlClass}">$${parseFloat(position.pnl).toFixed(2)} (${parseFloat(position.percentage).toFixed(2)}%)</td>
                <td><span class="badge bg-primary">Live</span></td>
                <td>-</td>
            </tr>
        `;
    });
    
    tableHTML += '</tbody></table></div>';
    positionsTable.innerHTML = tableHTML;
}

// Test connection to Binance
function testConnection() {
    const button = document.querySelector('[onclick="testConnection()"]');
    if (button) {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
    }
    
    fetch('/api/test-connection')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            const mode = data.testnet ? 'Testnet' : 'Live';
            showNotification(`Connection successful! Connected to Binance ${mode}`, 'success');
            
            // Update connection status
            updateConnectionStatus(true, mode);
        })
        .catch(error => {
            console.error('Connection test failed:', error);
            showNotification('Connection failed: ' + error.message, 'error');
            updateConnectionStatus(false);
        })
        .finally(() => {
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-plug"></i> Test Connection';
            }
        });
}

// Check connection status
function checkConnectionStatus() {
    fetch('/api/test-connection')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                updateConnectionStatus(false);
            } else {
                const mode = data.testnet ? 'Testnet' : 'Live';
                updateConnectionStatus(true, mode);
            }
        })
        .catch(error => {
            console.error('Connection check failed:', error);
            updateConnectionStatus(false);
        });
}

// Update connection status display
function updateConnectionStatus(connected, mode = '') {
    const statusElements = document.querySelectorAll('.connection-status');
    statusElements.forEach(element => {
        if (connected) {
            element.className = 'connection-status connected';
            element.innerHTML = `<i class="fas fa-check-circle"></i> Connected ${mode}`;
        } else {
            element.className = 'connection-status disconnected';
            element.innerHTML = '<i class="fas fa-times-circle"></i> Disconnected';
        }
    });
}

// Handle settings form submission
function handleSettingsSubmit(event) {
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        
        // Re-enable button after form submission
        setTimeout(() => {
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="fas fa-save"></i> Save Settings';
        }, 2000);
    }
}

// Show notification
function showNotification(message, type = 'info') {
    const alertClass = type === 'success' ? 'alert-success' : 
                      type === 'error' ? 'alert-danger' : 'alert-info';
    
    const alertHTML = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert at the top of the main content
    const mainContent = document.querySelector('main .container');
    if (mainContent) {
        mainContent.insertAdjacentHTML('afterbegin', alertHTML);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = mainContent.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }
}

// Start auto-refresh
function startAutoRefresh() {
    // Refresh every 30 seconds
    refreshInterval = setInterval(() => {
        if (!isRefreshing) {
            refreshTrades();
            refreshPositions();
        }
    }, 30000);
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        startAutoRefresh();
        // Refresh immediately when page becomes visible
        refreshTrades();
        refreshPositions();
    }
});

// Utility functions
function formatPrice(price) {
    return price ? `$${parseFloat(price).toFixed(2)}` : 'N/A';
}

function formatQuantity(quantity) {
    return parseFloat(quantity).toFixed(6);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString();
}

function getBadgeClass(side) {
    return side === 'BUY' || side === 'LONG' ? 'bg-success' : 'bg-danger';
}

function getStatusBadgeClass(status) {
    switch (status) {
        case 'FILLED':
            return 'bg-success';
        case 'FAILED':
            return 'bg-danger';
        case 'CANCELLED':
            return 'bg-secondary';
        default:
            return 'bg-warning';
    }
}

function getPnlClass(pnl) {
    return parseFloat(pnl) >= 0 ? 'text-success' : 'text-danger';
}

// Export functions for global access
window.copyWebhookUrl = copyWebhookUrl;
window.refreshTrades = refreshTrades;
window.refreshPositions = refreshPositions;
window.testConnection = testConnection;
