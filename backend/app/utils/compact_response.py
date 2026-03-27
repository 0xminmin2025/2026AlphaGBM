"""
Compact response utilities for AI Agent consumption.
Reduces large analysis results to agent-friendly sizes (~500-1000 tokens).
Used when ?compact=true is passed to sync endpoints.
"""


def compact_stock_result(full_result: dict) -> dict:
    """
    Compress full stock analysis result for agent consumption.

    Input: full result from get_stock_analysis_data() with keys: success, data, risk, report
    Output: ~15 key fields, AI summary truncated to 500 chars
    """
    if 'error' in full_result:
        return full_result

    data = full_result.get('data', {})
    risk = full_result.get('risk', {})
    report = full_result.get('report', '')
    ev = data.get('ev_model', {})
    recommendation = ev.get('recommendation', {})

    # Truncate AI report
    ai_summary = ''
    if isinstance(report, str):
        # Strip markdown headers for cleaner agent output
        lines = [l for l in report.split('\n') if l.strip() and not l.strip().startswith('#')]
        ai_summary = '\n'.join(lines)[:500]

    return {
        'success': True,
        'ticker': data.get('symbol') or data.get('name', ''),
        'price': data.get('price'),
        'currency': data.get('currency_symbol', '$'),
        'target_price': data.get('target_price'),
        'stop_loss_price': data.get('stop_loss_price'),
        'recommendation': recommendation.get('action', 'HOLD'),
        'recommendation_confidence': recommendation.get('confidence'),
        'risk_score': risk.get('score'),
        'risk_level': risk.get('level'),
        'suggested_position_pct': risk.get('suggested_position'),
        'ev_score': ev.get('ev_score'),
        'market_sentiment': data.get('market_sentiment'),
        'key_metrics': {
            'pe': data.get('pe'),
            'forward_pe': data.get('forward_pe'),
            'market_cap': data.get('marketCap'),
            'revenue_growth': data.get('growth'),
            'profit_margin': data.get('margin'),
            'beta': data.get('beta'),
            '52w_high': data.get('week52_high'),
            '52w_low': data.get('week52_low'),
        },
        'ai_summary': ai_summary,
    }


def compact_chain_result(full_result: dict) -> dict:
    """
    Compress full options chain result for agent consumption.

    Filters to top 5 scored calls and puts (instead of all strikes).
    Extracts chain-level IV metrics.
    """
    if 'error' in full_result:
        return full_result

    # Extract top-level fields
    symbol = full_result.get('symbol', '')
    underlying_price = full_result.get('real_stock_price') or full_result.get('underlying_price')
    expiry = full_result.get('expiry_date') or full_result.get('expiry', '')

    # IV metrics (from chain-level data)
    iv_rank = full_result.get('iv_rank_30d')
    iv_percentile = full_result.get('iv_percentile_30d')
    hv_30d = full_result.get('historical_volatility')

    # Extract VRP if available
    vrp_analysis = full_result.get('vrp_analysis', {})
    vrp = vrp_analysis.get('vrp') if isinstance(vrp_analysis, dict) else None

    # Get strategy summary
    summary = full_result.get('summary', {})
    best_strategies = summary.get('best_strategies', [])
    overall = summary.get('overall_recommendation', {})

    # Top scored options from calls/puts
    def extract_top_options(options_list, n=5):
        if not options_list:
            return []
        # Sort by score descending
        scored = [o for o in options_list if isinstance(o, dict) and o.get('score') is not None]
        scored.sort(key=lambda x: x.get('score', 0), reverse=True)
        return [
            {
                'strike': o.get('strike'),
                'score': o.get('score'),
                'bid': o.get('bid'),
                'ask': o.get('ask'),
                'iv': o.get('impliedVolatility') or o.get('iv'),
                'volume': o.get('volume'),
                'open_interest': o.get('openInterest') or o.get('open_interest'),
                'delta': o.get('delta'),
            }
            for o in scored[:n]
        ]

    calls = full_result.get('calls', [])
    puts = full_result.get('puts', [])

    return {
        'success': True,
        'symbol': symbol,
        'underlying_price': underlying_price,
        'expiry': expiry,
        'iv_rank': iv_rank,
        'iv_percentile': iv_percentile,
        'hv_30d': hv_30d,
        'vrp': vrp,
        'overall_recommendation': {
            'action': overall.get('action'),
            'strategy': overall.get('strategy'),
            'score': overall.get('score'),
            'reason': overall.get('reason'),
        } if overall else None,
        'best_strategies': [
            {
                'strategy': s.get('strategy'),
                'score': s.get('score'),
                'style_label': s.get('style_label'),
                'summary': s.get('summary'),
            }
            for s in best_strategies[:3]
        ],
        'top_calls': extract_top_options(calls),
        'top_puts': extract_top_options(puts),
        'total_calls': len(calls),
        'total_puts': len(puts),
    }


def compact_enhanced_result(full_result: dict) -> dict:
    """
    Compress enhanced single-option analysis for agent consumption.

    Extracts: VRP verdict, key Greeks, risk level.
    """
    if 'error' in full_result:
        return full_result

    vrp = full_result.get('vrp_analysis', {})
    risk = full_result.get('risk_analysis', {})
    greeks = risk.get('greeks', {}) if isinstance(risk, dict) else {}

    return {
        'success': True,
        'symbol': full_result.get('symbol', ''),
        'option_identifier': full_result.get('option_identifier', ''),
        'vrp': {
            'implied_volatility': vrp.get('implied_volatility') or vrp.get('iv'),
            'historical_volatility': vrp.get('historical_volatility'),
            'vrp': vrp.get('vrp'),
            'vrp_level': vrp.get('vrp_level'),
            'iv_rank': vrp.get('iv_rank'),
            'iv_percentile': vrp.get('iv_percentile'),
            'assessment': vrp.get('assessment'),
        },
        'greeks': {
            'delta': greeks.get('delta'),
            'gamma': greeks.get('gamma'),
            'theta': greeks.get('theta'),
            'vega': greeks.get('vega'),
        },
        'risk_level': risk.get('overall_risk') if isinstance(risk, dict) else None,
    }
