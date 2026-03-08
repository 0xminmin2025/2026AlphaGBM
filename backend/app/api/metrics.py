"""
Market Data Metrics API

Provides endpoints for monitoring data provider health and performance:
- Overall statistics (success rate, cache hit rate, latency)
- Per-provider metrics
- Recent errors
- Health status dashboard
"""

from flask import Blueprint, request, jsonify, render_template_string
import logging

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')
logger = logging.getLogger(__name__)


@metrics_bp.route('/', methods=['GET'])
def get_all_metrics():
    """
    Get comprehensive metrics for all market data operations.

    Returns:
        {
            "uptime": {...},
            "totals": {
                "total_calls": 1000,
                "cache_hits": 500,
                "cache_hit_rate": 50.0,
                "failures": 10,
                "failure_rate": 1.0,
                ...
            },
            "by_provider": {
                "yfinance": {...},
                "tiger": {...},
                ...
            },
            "by_data_type": {...},
            "recent_errors": [...]
        }
    """
    try:
        from ..services.market_data import market_data_service
        stats = market_data_service.get_stats()

        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@metrics_bp.route('/providers', methods=['GET'])
def get_provider_status():
    """
    Get status of all registered data providers.

    Returns provider health, enabled status, and capabilities.
    """
    try:
        from ..services.market_data import market_data_service
        status = market_data_service.get_provider_status()

        return jsonify({
            'success': True,
            'providers': status
        })
    except Exception as e:
        logger.error(f"Error getting provider status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@metrics_bp.route('/providers/<provider_name>', methods=['GET'])
def get_provider_health(provider_name: str):
    """
    Get detailed health status for a specific provider.

    Args:
        provider_name: Name of the provider (yfinance, tiger, etc.)

    Returns:
        Health status including success rate, latency, and recent errors
    """
    try:
        from ..services.market_data import market_data_service
        health = market_data_service.get_provider_health(provider_name)

        return jsonify({
            'success': True,
            'provider': provider_name,
            'health': health
        })
    except Exception as e:
        logger.error(f"Error getting provider health: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@metrics_bp.route('/latency', methods=['GET'])
def get_latency_percentiles():
    """
    Get latency percentiles (p50, p90, p95, p99).

    Query params:
        - provider: Filter by provider (optional)
        - data_type: Filter by data type (optional)
    """
    try:
        from ..services.market_data import market_data_service
        from ..services.market_data.interfaces import DataType

        provider = request.args.get('provider')
        data_type_str = request.args.get('data_type')

        data_type = None
        if data_type_str:
            try:
                data_type = DataType(data_type_str)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid data_type: {data_type_str}'
                }), 400

        percentiles = market_data_service.get_latency_percentiles(
            provider=provider,
            data_type=data_type
        )

        return jsonify({
            'success': True,
            'percentiles': percentiles
        })
    except Exception as e:
        logger.error(f"Error getting latency percentiles: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@metrics_bp.route('/recent', methods=['GET'])
def get_recent_calls():
    """
    Get recent call records with optional filtering.

    Query params:
        - limit: Max records to return (default 100)
        - provider: Filter by provider
        - symbol: Filter by symbol
        - data_type: Filter by data type
        - errors_only: Only return errors (true/false)
    """
    try:
        from ..services.market_data import market_data_service
        from ..services.market_data.interfaces import DataType

        limit = request.args.get('limit', 100, type=int)
        limit = min(limit, 500)  # Cap at 500

        provider = request.args.get('provider')
        symbol = request.args.get('symbol')
        data_type_str = request.args.get('data_type')
        errors_only = request.args.get('errors_only', 'false').lower() == 'true'

        data_type = None
        if data_type_str:
            try:
                data_type = DataType(data_type_str)
            except ValueError:
                pass

        records = market_data_service.get_recent_calls(
            limit=limit,
            data_type=data_type,
            provider=provider,
            symbol=symbol,
            errors_only=errors_only
        )

        return jsonify({
            'success': True,
            'count': len(records),
            'records': records
        })
    except Exception as e:
        logger.error(f"Error getting recent calls: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────
# Dashboard HTML Endpoint
# ─────────────────────────────────────────────────────────────

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Data Metrics Dashboard</title>
    <style>
        :root {
            --bg: #1a1a2e;
            --card-bg: #16213e;
            --text: #eaeaea;
            --text-muted: #a0a0a0;
            --success: #00d26a;
            --warning: #ffc107;
            --danger: #ff6b6b;
            --primary: #4f8cff;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { margin-bottom: 20px; font-weight: 600; }
        h2 { font-size: 1.1rem; color: var(--text-muted); margin-bottom: 15px; }
        .grid { display: grid; gap: 20px; }
        .grid-4 { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
        .grid-2 { grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); }
        .card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
        }
        .stat-card { text-align: center; }
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .stat-label { color: var(--text-muted); font-size: 0.9rem; }
        .success { color: var(--success); }
        .warning { color: var(--warning); }
        .danger { color: var(--danger); }
        .provider-card { display: flex; justify-content: space-between; align-items: center; }
        .provider-name { font-weight: 600; font-size: 1.1rem; }
        .provider-stats { display: flex; gap: 20px; }
        .provider-stat { text-align: right; }
        .provider-stat-value { font-size: 1.2rem; font-weight: 600; }
        .provider-stat-label { font-size: 0.75rem; color: var(--text-muted); }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-success { background: rgba(0, 210, 106, 0.2); color: var(--success); }
        .badge-warning { background: rgba(255, 193, 7, 0.2); color: var(--warning); }
        .badge-danger { background: rgba(255, 107, 107, 0.2); color: var(--danger); }
        .error-list { max-height: 300px; overflow-y: auto; }
        .error-item {
            padding: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 0.85rem;
        }
        .error-item:last-child { border-bottom: none; }
        .error-time { color: var(--text-muted); }
        .error-symbol { color: var(--primary); font-weight: 600; }
        .refresh-btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        .refresh-btn:hover { opacity: 0.9; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .uptime { color: var(--text-muted); font-size: 0.9rem; }
        .loading { text-align: center; padding: 40px; color: var(--text-muted); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Market Data Metrics</h1>
                <div class="uptime" id="uptime">Loading...</div>
            </div>
            <button class="refresh-btn" onclick="loadData()">Refresh</button>
        </div>

        <div class="grid grid-4" id="summary-cards">
            <div class="card stat-card">
                <div class="stat-value" id="total-calls">-</div>
                <div class="stat-label">Total Calls</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value success" id="success-rate">-</div>
                <div class="stat-label">Success Rate</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value" id="cache-rate">-</div>
                <div class="stat-label">Cache Hit Rate</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value" id="p50-latency">-</div>
                <div class="stat-label">P50 Latency (ms)</div>
            </div>
        </div>

        <div class="grid grid-2" style="margin-top: 20px;">
            <div class="card">
                <h2>Provider Status</h2>
                <div id="providers-list" class="loading">Loading providers...</div>
            </div>
            <div class="card">
                <h2>Recent Errors</h2>
                <div id="errors-list" class="error-list loading">Loading errors...</div>
            </div>
        </div>

        <div class="card" style="margin-top: 20px;">
            <h2>Data Type Breakdown</h2>
            <div id="data-types" class="grid grid-4" style="margin-top: 15px;"></div>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                const [metricsRes, latencyRes] = await Promise.all([
                    fetch('/api/metrics/'),
                    fetch('/api/metrics/latency')
                ]);

                const metrics = await metricsRes.json();
                const latency = await latencyRes.json();

                if (metrics.success) {
                    renderMetrics(metrics.data, latency.percentiles);
                }
            } catch (e) {
                console.error('Failed to load metrics:', e);
            }
        }

        function renderMetrics(data, latency) {
            // Extract metrics from nested structure
            const metrics = data.metrics || {};
            const uptime = metrics.uptime || {};
            const totals = metrics.totals || {};
            const byProvider = metrics.by_provider || {};
            const byDataType = metrics.by_data_type || {};
            const recentErrors = metrics.recent_errors || [];

            // Uptime
            const uptimeHours = (uptime.uptime_seconds / 3600).toFixed(1);
            document.getElementById('uptime').textContent = `Uptime: ${uptimeHours}h`;

            // Summary cards
            document.getElementById('total-calls').textContent = (totals.total_calls || 0).toLocaleString();

            const successRate = 100 - (totals.failure_rate || 0);
            const successEl = document.getElementById('success-rate');
            successEl.textContent = successRate.toFixed(1) + '%';
            successEl.className = 'stat-value ' + (successRate >= 95 ? 'success' : successRate >= 80 ? 'warning' : 'danger');

            document.getElementById('cache-rate').textContent = (totals.cache_hit_rate || 0).toFixed(1) + '%';
            document.getElementById('p50-latency').textContent = (latency?.p50 || 0).toFixed(0);

            // Providers
            let providersHtml = '';
            for (const [name, stats] of Object.entries(byProvider)) {
                const rate = stats.success_rate || 0;
                const badgeClass = rate >= 95 ? 'badge-success' : rate >= 80 ? 'badge-warning' : 'badge-danger';
                providersHtml += `
                    <div class="provider-card" style="margin-bottom: 15px;">
                        <div>
                            <span class="provider-name">${name}</span>
                            <span class="badge ${badgeClass}">${rate.toFixed(0)}%</span>
                        </div>
                        <div class="provider-stats">
                            <div class="provider-stat">
                                <div class="provider-stat-value">${(stats.total_calls || 0).toLocaleString()}</div>
                                <div class="provider-stat-label">Calls</div>
                            </div>
                            <div class="provider-stat">
                                <div class="provider-stat-value">${(stats.avg_latency_ms || 0).toFixed(0)}ms</div>
                                <div class="provider-stat-label">Avg Latency</div>
                            </div>
                        </div>
                    </div>
                `;
            }
            document.getElementById('providers-list').innerHTML = providersHtml || '<div class="loading">No provider data</div>';

            // Errors
            let errorsHtml = '';
            if (recentErrors.length === 0) {
                errorsHtml = '<div style="padding: 20px; text-align: center; color: var(--success);">No recent errors</div>';
            } else {
                for (const err of recentErrors.slice(-20).reverse()) {
                    const time = new Date(err.timestamp).toLocaleTimeString();
                    errorsHtml += `
                        <div class="error-item">
                            <span class="error-time">${time}</span>
                            <span class="error-symbol">${err.symbol}</span>
                            <span>${err.data_type}</span>
                            <span class="danger">${err.error_type || 'unknown'}</span>
                        </div>
                    `;
                }
            }
            document.getElementById('errors-list').innerHTML = errorsHtml;

            // Data types
            let dtHtml = '';
            for (const [type, stats] of Object.entries(byDataType)) {
                if (stats.total_calls > 0) {
                    dtHtml += `
                        <div class="card stat-card" style="padding: 15px;">
                            <div class="stat-value" style="font-size: 1.5rem;">${stats.total_calls.toLocaleString()}</div>
                            <div class="stat-label">${type}</div>
                            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 5px;">
                                Cache: ${stats.cache_hit_rate?.toFixed(0) || 0}%
                            </div>
                        </div>
                    `;
                }
            }
            document.getElementById('data-types').innerHTML = dtHtml || '<div>No data</div>';
        }

        // Initial load
        loadData();

        // Auto refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
'''


@metrics_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """
    Render the metrics dashboard HTML page.

    Access at: /api/metrics/dashboard
    """
    return render_template_string(DASHBOARD_HTML)
