/**
 * Formula Tester - Main Application JavaScript
 * Interactive calculators for stock and options analysis formulas
 */

// API Configuration
const API_BASE = 'http://localhost:8100/api';

// Global state
let currentSymbol = '';
let stockData = null;
let optionsData = null;
let priceChart = null;
let useMockMode = false;

// ============================================
// Mock Data for Testing Without Backend
// ============================================

const MOCK_STOCK_DATA = {
    success: true,
    symbol: 'MOCK',
    fetched_at: new Date().toISOString(),
    data_source: 'mock',
    price_data: {
        current_price: 150.25,
        prev_close: 148.50,
        change: 1.75,
        change_percent: 1.18,
        high_52w: 180.50,
        low_52w: 120.30,
        volume: 45000000,
        avg_volume_20d: 52000000
    },
    technical_levels: {
        resistance_1: 155.00,
        resistance_2: 162.50,
        support_1: 145.00,
        support_2: 138.50,
        ma_5: 149.80,
        ma_20: 147.50,
        ma_50: 145.20,
        ma_200: 140.00
    },
    volatility: {
        daily_volatility: 1.85,
        annualized_volatility: 29.35,
        beta: 1.15
    },
    fundamentals: {
        pe_ratio: 28.5,
        forward_pe: 24.2,
        peg_ratio: 1.8,
        pb_ratio: 8.5,
        dividend_yield: 0.65,
        market_cap: 2500000000000,
        debt_to_equity: 45.2,
        roe: 35.5,
        gross_margin: 42.8,
        revenue_growth: 12.5,
        earnings_growth: 18.3
    },
    history: {
        dates: generateMockDates(60),
        open: generateMockPrices(60, 145, 155),
        high: generateMockPrices(60, 148, 158),
        low: generateMockPrices(60, 142, 152),
        close: generateMockPrices(60, 145, 155),
        volume: generateMockVolumes(60)
    }
};

const MOCK_OPTIONS_DATA = {
    success: true,
    symbol: 'MOCK',
    fetched_at: new Date().toISOString(),
    current_price: 150.25,
    expiration: generateFutureDate(30),
    days_to_expiry: 30,
    available_expirations: [
        generateFutureDate(7),
        generateFutureDate(14),
        generateFutureDate(21),
        generateFutureDate(30),
        generateFutureDate(45),
        generateFutureDate(60)
    ],
    weighted_iv: 32.5,
    atm_iv: 30.8,
    calls: generateMockOptions('call', 150.25, 10),
    puts: generateMockOptions('put', 150.25, 10),
    summary: {
        total_calls: 10,
        total_puts: 10,
        call_volume: 15000,
        put_volume: 12000,
        call_oi: 85000,
        put_oi: 72000
    }
};

// Mock data helper functions
function generateMockDates(count) {
    const dates = [];
    const today = new Date();
    for (let i = count - 1; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        // Skip weekends
        if (date.getDay() === 0) date.setDate(date.getDate() - 2);
        if (date.getDay() === 6) date.setDate(date.getDate() - 1);
        dates.push(date.toISOString().split('T')[0]);
    }
    return dates;
}

function generateMockPrices(count, min, max) {
    const prices = [];
    let price = (min + max) / 2;
    for (let i = 0; i < count; i++) {
        price += (Math.random() - 0.5) * 3;
        price = Math.max(min, Math.min(max, price));
        prices.push(parseFloat(price.toFixed(2)));
    }
    return prices;
}

function generateMockVolumes(count) {
    const volumes = [];
    for (let i = 0; i < count; i++) {
        volumes.push(Math.floor(30000000 + Math.random() * 40000000));
    }
    return volumes;
}

function generateFutureDate(days) {
    const date = new Date();
    date.setDate(date.getDate() + days);
    return date.toISOString().split('T')[0];
}

function generateMockOptions(type, currentPrice, count) {
    const options = [];
    const baseStrike = Math.round(currentPrice / 5) * 5;

    for (let i = -count/2; i < count/2; i++) {
        const strike = baseStrike + (i * 5);
        const isITM = type === 'call' ? strike < currentPrice : strike > currentPrice;
        const distanceFromATM = Math.abs(strike - currentPrice) / currentPrice;
        const baseIV = 28 + distanceFromATM * 50;
        const premium = type === 'call'
            ? Math.max(0.1, currentPrice - strike + (baseIV / 100) * currentPrice * 0.1)
            : Math.max(0.1, strike - currentPrice + (baseIV / 100) * currentPrice * 0.1);

        options.push({
            strike: strike,
            bid: parseFloat((premium * 0.98).toFixed(2)),
            ask: parseFloat((premium * 1.02).toFixed(2)),
            last: parseFloat(premium.toFixed(2)),
            volume: Math.floor(100 + Math.random() * 2000),
            open_interest: Math.floor(500 + Math.random() * 10000),
            implied_volatility: parseFloat(baseIV.toFixed(2)),
            delta: type === 'call'
                ? parseFloat((0.5 + (currentPrice - strike) / currentPrice).toFixed(2))
                : parseFloat((-0.5 + (currentPrice - strike) / currentPrice).toFixed(2)),
            gamma: parseFloat((0.01 + Math.random() * 0.05).toFixed(4)),
            theta: parseFloat((-0.05 - Math.random() * 0.1).toFixed(4)),
            vega: parseFloat((0.1 + Math.random() * 0.2).toFixed(4)),
            in_the_money: isITM
        });
    }
    return options;
}

function loadMockData() {
    const symbolInput = document.getElementById('symbolInput');
    const symbol = symbolInput.value.trim().toUpperCase() || 'MOCK';

    currentSymbol = symbol;
    useMockMode = true;

    // Clone mock data and update symbol
    stockData = JSON.parse(JSON.stringify(MOCK_STOCK_DATA));
    stockData.symbol = symbol;
    stockData.fetched_at = new Date().toISOString();

    optionsData = JSON.parse(JSON.stringify(MOCK_OPTIONS_DATA));
    optionsData.symbol = symbol;
    optionsData.fetched_at = new Date().toISOString();

    // Update UI
    populateStockInputs();
    populateOptionsInputs();
    updateRawDataDisplay('stock');
    updateRawDataDisplay('options');
    renderPriceChart();

    document.getElementById('statusIndicator').textContent = `Mock: ${symbol}`;
    document.getElementById('statusIndicator').classList.remove('text-yellow-400', 'text-red-400');
    document.getElementById('statusIndicator').classList.add('text-purple-400');

    console.log('Mock data loaded for', symbol);
}

// ============================================
// Navigation & UI Utilities
// ============================================

function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.add('hidden');
    });

    // Show selected section
    const section = document.getElementById(`section-${sectionId}`);
    if (section) {
        section.classList.remove('hidden');
    }

    // Update nav buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('border-blue-500', 'text-blue-400');
        btn.classList.add('border-transparent', 'text-gray-400');
    });

    const activeBtn = document.getElementById(`tab-${sectionId}`);
    if (activeBtn) {
        activeBtn.classList.remove('border-transparent', 'text-gray-400');
        activeBtn.classList.add('border-blue-500', 'text-blue-400');
    }
}

function toggleFormula(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.toggle('hidden');
    }
}

function syncInput(targetId, value) {
    const el = document.getElementById(targetId);
    if (el) {
        el.value = value;
    }
}

function showLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = '<div class="text-gray-400">Calculating...</div>';
    }
}

function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = `<div class="text-red-400">${message}</div>`;
    }
}

function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return 'N/A';
    return parseFloat(num).toFixed(decimals);
}

function formatPercent(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return 'N/A';
    return parseFloat(num).toFixed(decimals) + '%';
}

function formatCurrency(num) {
    if (num === null || num === undefined || isNaN(num)) return 'N/A';
    return '$' + parseFloat(num).toFixed(2);
}

function getScoreColor(score) {
    if (score >= 75) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    if (score >= 25) return 'text-orange-400';
    return 'text-red-400';
}

function getScoreLabel(score) {
    if (score >= 75) return 'Excellent';
    if (score >= 50) return 'Good';
    if (score >= 25) return 'Fair';
    return 'Poor';
}

// ============================================
// Data Fetching
// ============================================

async function fetchSymbolData() {
    const symbolInput = document.getElementById('symbolInput');
    const symbol = symbolInput.value.trim().toUpperCase();

    if (!symbol) {
        alert('Please enter a stock symbol');
        return;
    }

    currentSymbol = symbol;
    document.getElementById('statusIndicator').textContent = 'Fetching...';
    document.getElementById('statusIndicator').classList.add('text-yellow-400');

    try {
        // Fetch both stock and options data in parallel
        const [stockResponse, optionsResponse] = await Promise.all([
            fetch(`${API_BASE}/stock/${symbol}`).catch(() => null),
            fetch(`${API_BASE}/options/${symbol}`).catch(() => null)
        ]);

        if (stockResponse && stockResponse.ok) {
            stockData = await stockResponse.json();
            populateStockInputs();
            updateRawDataDisplay('stock');
            renderPriceChart();
            document.getElementById('statusIndicator').textContent = `Loaded: ${symbol}`;
            document.getElementById('statusIndicator').classList.remove('text-yellow-400');
            document.getElementById('statusIndicator').classList.add('text-green-400');
        } else {
            const errorData = stockResponse ? await stockResponse.json() : {detail: 'Connection failed'};
            document.getElementById('statusIndicator').textContent = `Error: ${errorData.detail || 'Failed'}`;
            document.getElementById('statusIndicator').classList.remove('text-yellow-400');
            document.getElementById('statusIndicator').classList.add('text-red-400');
            stockData = null;
        }

        if (optionsResponse && optionsResponse.ok) {
            optionsData = await optionsResponse.json();
            populateOptionsInputs();
            updateRawDataDisplay('options');
        } else {
            optionsData = null;
        }

    } catch (error) {
        console.error('Error fetching data:', error);
        document.getElementById('statusIndicator').textContent = 'API Error';
        document.getElementById('statusIndicator').classList.add('text-red-400');
    }
}

function populateStockInputs() {
    if (!stockData || !stockData.success) return;

    const pd = stockData.price_data;
    const tl = stockData.technical_levels;
    const v = stockData.volatility;
    const f = stockData.fundamentals;

    // Risk Score inputs
    if (v && v.annualized_volatility) {
        document.getElementById('risk-volatility').value = v.annualized_volatility;
        document.getElementById('risk-volatility-slider').value = Math.min(v.annualized_volatility, 200);
    }
    if (f) {
        if (f.pe_ratio) document.getElementById('risk-pe').value = f.pe_ratio;
        if (f.debt_to_equity) document.getElementById('risk-de').value = f.debt_to_equity;
        if (f.market_cap) document.getElementById('risk-mcap').value = (f.market_cap / 1e9).toFixed(1);
    }

    // Target Price inputs
    if (pd && pd.current_price) {
        document.getElementById('target-price').value = pd.current_price;
    }
    if (f) {
        if (f.pe_ratio) document.getElementById('target-pe').value = f.pe_ratio;
        if (f.peg_ratio) document.getElementById('target-peg').value = f.peg_ratio;
        if (f.revenue_growth) document.getElementById('target-rev-growth').value = f.revenue_growth;
        if (f.earnings_growth) document.getElementById('target-earn-growth').value = f.earnings_growth;
    }

    // Style inputs
    if (f) {
        if (f.revenue_growth) document.getElementById('style-rev').value = f.revenue_growth;
        if (f.earnings_growth) document.getElementById('style-earn').value = f.earnings_growth;
        if (f.peg_ratio) document.getElementById('style-peg').value = f.peg_ratio;
        if (f.pe_ratio) document.getElementById('style-pe').value = f.pe_ratio;
        if (f.pb_ratio) document.getElementById('style-pb').value = f.pb_ratio;
        if (f.dividend_yield) document.getElementById('style-div').value = f.dividend_yield;
        if (f.roe) document.getElementById('style-roe').value = f.roe;
        if (f.gross_margin) document.getElementById('style-margin').value = f.gross_margin;
        if (f.debt_to_equity) document.getElementById('style-de').value = f.debt_to_equity;
    }

    // Sell Put inputs
    if (pd) {
        document.getElementById('sp-price').value = pd.current_price;
        document.getElementById('sp-strike').value = (pd.current_price * 0.95).toFixed(2);
    }
    if (tl) {
        if (tl.support_1) document.getElementById('sp-s1').value = tl.support_1;
        if (tl.support_2) document.getElementById('sp-s2').value = tl.support_2;
        if (tl.ma_50) document.getElementById('sp-ma50').value = tl.ma_50;
    }

    // Sell Call inputs
    if (pd) {
        document.getElementById('sc-price').value = pd.current_price;
        document.getElementById('sc-strike').value = (pd.current_price * 1.05).toFixed(2);
    }
    if (tl && tl.resistance_1) document.getElementById('sc-r1').value = tl.resistance_1;
    if (pd && pd.high_52w) document.getElementById('sc-high52').value = pd.high_52w;

    // ATR Stop Loss
    if (pd && pd.current_price) {
        document.getElementById('sl-price').value = pd.current_price;
    }

    // ATR Safety
    if (pd) {
        document.getElementById('atrs-price').value = pd.current_price;
        document.getElementById('atrs-strike').value = (pd.current_price * 0.95).toFixed(2);
    }

    // Risk Return Profile
    if (pd && pd.current_price) {
        document.getElementById('rrp-price').value = pd.current_price;
        document.getElementById('rrp-strike').value = (pd.current_price * 0.95).toFixed(2);
    }
}

function populateOptionsInputs() {
    if (!optionsData || !optionsData.success) return;

    // VRP inputs
    if (optionsData.atm_iv) {
        document.getElementById('vrp-iv').value = optionsData.atm_iv;
        document.getElementById('vrp-iv-slider').value = Math.min(optionsData.atm_iv, 100);
        document.getElementById('vrp-atm').value = optionsData.atm_iv;
    }

    // Use HV from stock data if available
    if (stockData && stockData.volatility && stockData.volatility.annualized_volatility) {
        document.getElementById('vrp-hv').value = stockData.volatility.annualized_volatility;
        document.getElementById('vrp-hv-slider').value = Math.min(stockData.volatility.annualized_volatility, 100);
    }

    // Options scoring inputs
    if (optionsData.days_to_expiry) {
        document.getElementById('sp-dte').value = optionsData.days_to_expiry;
        document.getElementById('sc-dte').value = optionsData.days_to_expiry;
        document.getElementById('rrp-dte').value = optionsData.days_to_expiry;
    }

    // Find a representative put option for Sell Put
    if (optionsData.puts && optionsData.puts.length > 0) {
        const otmPuts = optionsData.puts.filter(p => !p.in_the_money);
        if (otmPuts.length > 0) {
            const put = otmPuts[Math.floor(otmPuts.length / 3)]; // Pick one near the money
            document.getElementById('sp-strike').value = put.strike;
            document.getElementById('sp-bid').value = put.bid;
            document.getElementById('sp-ask').value = put.ask;
            document.getElementById('sp-iv').value = put.implied_volatility;
            document.getElementById('sp-volume').value = put.volume;
            document.getElementById('sp-oi').value = put.open_interest;
        }
    }

    // Find a representative call option for Sell Call
    if (optionsData.calls && optionsData.calls.length > 0) {
        const otmCalls = optionsData.calls.filter(c => !c.in_the_money);
        if (otmCalls.length > 0) {
            const call = otmCalls[Math.floor(otmCalls.length / 3)];
            document.getElementById('sc-strike').value = call.strike;
            document.getElementById('sc-bid').value = call.bid;
            document.getElementById('sc-ask').value = call.ask;
            document.getElementById('sc-iv').value = call.implied_volatility;
            document.getElementById('sc-volume').value = call.volume;
            document.getElementById('sc-oi').value = call.open_interest;
        }
    }
}

function populateSellPutFromData() {
    if (!stockData || !optionsData) {
        alert('Please fetch symbol data first');
        return;
    }
    populateStockInputs();
    populateOptionsInputs();
}

function updateRawDataDisplay(type) {
    if (type === 'stock' && stockData) {
        document.getElementById('stock-raw-data').textContent = JSON.stringify(stockData, null, 2);
    }
    if (type === 'options' && optionsData) {
        document.getElementById('options-raw-data').textContent = JSON.stringify(optionsData, null, 2);
    }
}

// ============================================
// Stock Analysis Calculators
// ============================================

async function calculateRiskScore() {
    const params = {
        volatility: parseFloat(document.getElementById('risk-volatility').value) / 100,
        pe_ratio: parseFloat(document.getElementById('risk-pe').value) || null,
        debt_to_equity: parseFloat(document.getElementById('risk-de').value) || null,
        market_cap: parseFloat(document.getElementById('risk-mcap').value) * 1e9 || null,
        risk_premium: parseFloat(document.getElementById('risk-premium').value) || null,
        sector: document.getElementById('risk-sector').value
    };

    showLoading('risk-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/risk-score`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('risk-result', result.detail || 'Calculation failed');
            return;
        }

        const resultDiv = document.getElementById('risk-result');
        resultDiv.innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold ${getScoreColor(100 - result.risk_score)}">${formatNumber(result.risk_score)}</div>
                    <div class="text-sm text-gray-400">Risk Score</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold text-blue-400">${result.risk_level || 'N/A'}</div>
                    <div class="text-sm text-gray-400">Risk Level</div>
                </div>
            </div>
            <div class="mt-4 text-sm">
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Position Size Rec.</span>
                    <span class="text-white">${formatPercent(result.position_size_pct || 3)}</span>
                </div>
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Risk Adjustment Factor</span>
                    <span class="text-white">${formatNumber(result.risk_adjustment_factor || 1)}</span>
                </div>
            </div>
        `;

    } catch (error) {
        showError('risk-result', 'API error: ' + error.message);
    }
}

async function calculateTargetPrice() {
    const params = {
        current_price: parseFloat(document.getElementById('target-price').value),
        pe_ratio: parseFloat(document.getElementById('target-pe').value) || null,
        peg_ratio: parseFloat(document.getElementById('target-peg').value) || null,
        book_value: parseFloat(document.getElementById('target-book').value) || null,
        revenue_growth: (parseFloat(document.getElementById('target-rev-growth').value) || 0) / 100,
        earnings_growth: (parseFloat(document.getElementById('target-earn-growth').value) || 0) / 100,
        risk_score: parseFloat(document.getElementById('target-risk').value),
        style: document.getElementById('target-style').value
    };

    showLoading('target-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/target-price`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('target-result', result.detail || 'Calculation failed');
            return;
        }

        const upside = result.upside_potential || ((result.target_price - params.current_price) / params.current_price * 100);
        const upsideColor = upside >= 0 ? 'text-green-400' : 'text-red-400';

        document.getElementById('target-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold text-green-400">${formatCurrency(result.target_price)}</div>
                    <div class="text-sm text-gray-400">Target Price</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold ${upsideColor}">${upside >= 0 ? '+' : ''}${formatPercent(upside)}</div>
                    <div class="text-sm text-gray-400">Upside Potential</div>
                </div>
            </div>
            <div class="mt-4 text-sm">
                ${result.methods ? `
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Methods Used</span>
                    <span class="text-white">${result.methods.length}</span>
                </div>
                ` : ''}
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Risk Adjustment</span>
                    <span class="text-white">${formatNumber(result.risk_adjustment || 1)}</span>
                </div>
            </div>
        `;

    } catch (error) {
        showError('target-result', 'API error: ' + error.message);
    }
}

async function calculateSentiment() {
    if (!stockData || !stockData.history) {
        showError('sentiment-result', 'Please fetch stock data first');
        return;
    }

    const params = {
        prices: stockData.history.close,
        volumes: stockData.history.volume.map(v => parseFloat(v))
    };

    showLoading('sentiment-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/sentiment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('sentiment-result', result.detail || 'Calculation failed');
            return;
        }

        const sentimentColor = result.total_score > 10 ? 'text-green-400' :
                              result.total_score < -10 ? 'text-red-400' : 'text-yellow-400';

        document.getElementById('sentiment-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold ${sentimentColor}">${formatNumber(result.total_score)}</div>
                    <div class="text-sm text-gray-400">Sentiment Score</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold ${sentimentColor}">${result.sentiment || 'Neutral'}</div>
                    <div class="text-sm text-gray-400">Overall Sentiment</div>
                </div>
            </div>
            <div class="mt-4 text-sm">
                ${result.components ? `
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Price Momentum</span>
                    <span class="text-white">${formatNumber(result.components.price_momentum || 0)}</span>
                </div>
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Volume Trend</span>
                    <span class="text-white">${formatNumber(result.components.volume_trend || 0)}</span>
                </div>
                ` : ''}
            </div>
        `;

    } catch (error) {
        showError('sentiment-result', 'API error: ' + error.message);
    }
}

async function calculateStyleScores() {
    showLoading('style-result');

    try {
        // Calculate Growth Score
        const growthParams = {
            revenue_growth: (parseFloat(document.getElementById('style-rev').value) || 0) / 100,
            earnings_growth: (parseFloat(document.getElementById('style-earn').value) || 0) / 100,
            peg_ratio: parseFloat(document.getElementById('style-peg').value) || null
        };

        // Calculate Value Score
        const valueParams = {
            pe_ratio: parseFloat(document.getElementById('style-pe').value) || null,
            pb_ratio: parseFloat(document.getElementById('style-pb').value) || null,
            dividend_yield: (parseFloat(document.getElementById('style-div').value) || 0) / 100
        };

        // Calculate Quality Score
        const qualityParams = {
            roe: (parseFloat(document.getElementById('style-roe').value) || 0) / 100,
            gross_margin: (parseFloat(document.getElementById('style-margin').value) || 0) / 100,
            debt_to_equity: (parseFloat(document.getElementById('style-de').value) || 0) / 100
        };

        const [growthRes, valueRes, qualityRes] = await Promise.all([
            fetch(`${API_BASE}/calculate/growth-score`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(growthParams)
            }),
            fetch(`${API_BASE}/calculate/value-score`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(valueParams)
            }),
            fetch(`${API_BASE}/calculate/quality-score`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(qualityParams)
            })
        ]);

        const growth = await growthRes.json();
        const value = await valueRes.json();
        const quality = await qualityRes.json();

        document.getElementById('style-result').innerHTML = `
            <div class="grid grid-cols-3 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-2xl font-bold text-blue-400">${formatNumber(growth.growth_score || 0)}</div>
                    <div class="text-sm text-gray-400">Growth Score</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-2xl font-bold text-green-400">${formatNumber(value.value_score || 0)}</div>
                    <div class="text-sm text-gray-400">Value Score</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-2xl font-bold text-purple-400">${formatNumber(quality.quality_score || 0)}</div>
                    <div class="text-sm text-gray-400">Quality Score</div>
                </div>
            </div>
        `;

    } catch (error) {
        showError('style-result', 'API error: ' + error.message);
    }
}

// ============================================
// Options Calculators
// ============================================

async function calculateVRP() {
    const params = {
        implied_volatility: parseFloat(document.getElementById('vrp-iv').value) / 100,
        historical_volatility: parseFloat(document.getElementById('vrp-hv').value) / 100,
        atm_iv: (parseFloat(document.getElementById('vrp-atm').value) || null) ? parseFloat(document.getElementById('vrp-atm').value) / 100 : null
    };

    showLoading('vrp-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/vrp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('vrp-result', result.detail || 'Calculation failed');
            return;
        }

        const vrpColor = result.vrp_relative > 5 ? 'text-green-400' :
                        result.vrp_relative < -5 ? 'text-red-400' : 'text-yellow-400';

        document.getElementById('vrp-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold ${vrpColor}">${formatPercent(result.vrp_relative || result.vrp_absolute * 100)}</div>
                    <div class="text-sm text-gray-400">VRP (Relative)</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold text-blue-400">${result.level || 'Normal'}</div>
                    <div class="text-sm text-gray-400">VRP Level</div>
                </div>
            </div>
            <div class="mt-4 text-sm">
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">IV/HV Ratio</span>
                    <span class="text-white">${formatNumber(result.iv_hv_ratio || (params.implied_volatility / params.historical_volatility))}</span>
                </div>
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">VRP Absolute</span>
                    <span class="text-white">${formatPercent((result.vrp_absolute || 0) * 100)}</span>
                </div>
                <div class="flex justify-between py-1">
                    <span class="text-gray-400">Signal</span>
                    <span class="${vrpColor}">${result.vrp_relative > 5 ? 'Favor Sellers' : result.vrp_relative < -5 ? 'Favor Buyers' : 'Neutral'}</span>
                </div>
            </div>
        `;

    } catch (error) {
        showError('vrp-result', 'API error: ' + error.message);
    }
}

async function calculateTrendAlignment() {
    const params = {
        strategy: document.getElementById('trend-strategy').value,
        trend: document.getElementById('trend-direction').value,
        trend_strength: parseFloat(document.getElementById('trend-strength').value)
    };

    showLoading('trend-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/trend-alignment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('trend-result', result.detail || 'Calculation failed');
            return;
        }

        document.getElementById('trend-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold ${getScoreColor(result.alignment_score)}">${formatNumber(result.alignment_score)}</div>
                    <div class="text-sm text-gray-400">Alignment Score</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold text-blue-400">${getScoreLabel(result.alignment_score)}</div>
                    <div class="text-sm text-gray-400">Rating</div>
                </div>
            </div>
            <div class="mt-4 text-sm">
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Base Score</span>
                    <span class="text-white">${formatNumber(result.base_score || 50)}</span>
                </div>
                <div class="flex justify-between py-1">
                    <span class="text-gray-400">Adjustment</span>
                    <span class="text-white">${result.adjustment || 'None'}</span>
                </div>
            </div>
        `;

    } catch (error) {
        showError('trend-result', 'API error: ' + error.message);
    }
}

async function calculateSellPutScore() {
    const params = {
        current_price: parseFloat(document.getElementById('sp-price').value),
        strike: parseFloat(document.getElementById('sp-strike').value),
        bid: parseFloat(document.getElementById('sp-bid').value),
        ask: parseFloat(document.getElementById('sp-ask').value),
        days_to_expiry: parseInt(document.getElementById('sp-dte').value),
        implied_volatility: parseFloat(document.getElementById('sp-iv').value) / 100,
        volume: parseInt(document.getElementById('sp-volume').value),
        open_interest: parseInt(document.getElementById('sp-oi').value),
        atr: parseFloat(document.getElementById('sp-atr').value) || null,
        support_1: parseFloat(document.getElementById('sp-s1').value) || null,
        support_2: parseFloat(document.getElementById('sp-s2').value) || null,
        ma_50: parseFloat(document.getElementById('sp-ma50').value) || null,
        trend: 'sideways',
        trend_strength: 0.5
    };

    showLoading('sellput-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/sell-put-score`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('sellput-result', result.detail || 'Calculation failed');
            return;
        }

        const scoreComponents = result.components || {};

        document.getElementById('sellput-result').innerHTML = `
            <div class="grid grid-cols-3 gap-4 mb-4">
                <div class="text-center p-4 bg-gray-800 rounded col-span-1">
                    <div class="text-4xl font-bold ${getScoreColor(result.total_score)}">${formatNumber(result.total_score)}</div>
                    <div class="text-sm text-gray-400">Total Score</div>
                </div>
                <div class="col-span-2 p-4 bg-gray-800 rounded">
                    <div class="text-lg font-semibold mb-2">${getScoreLabel(result.total_score)} Trade</div>
                    <div class="text-sm text-gray-400">
                        Premium Yield: ${formatPercent(result.premium_yield_annual || 0)} annualized
                    </div>
                    <div class="text-sm text-gray-400">
                        Safety Margin: ${formatPercent(result.safety_margin_pct || 0)}
                    </div>
                </div>
            </div>
            <div class="text-sm">
                <div class="font-medium mb-2">Score Breakdown (weights):</div>
                <div class="grid grid-cols-2 gap-2">
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Premium Yield (20%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.premium_yield || 0)}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Support (20%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.support_strength || 0)}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Safety (15%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.safety_margin || 0)}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Trend (15%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.trend_alignment || 0)}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Prob. Profit (15%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.probability_profit || 0)}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Liquidity (10%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.liquidity || 0)}</span>
                    </div>
                </div>
            </div>
        `;

    } catch (error) {
        showError('sellput-result', 'API error: ' + error.message);
    }
}

async function calculateSellCallScore() {
    const params = {
        current_price: parseFloat(document.getElementById('sc-price').value),
        strike: parseFloat(document.getElementById('sc-strike').value),
        bid: parseFloat(document.getElementById('sc-bid').value),
        ask: parseFloat(document.getElementById('sc-ask').value),
        days_to_expiry: parseInt(document.getElementById('sc-dte').value),
        implied_volatility: parseFloat(document.getElementById('sc-iv').value) / 100,
        volume: parseInt(document.getElementById('sc-volume').value),
        open_interest: parseInt(document.getElementById('sc-oi').value),
        atr: parseFloat(document.getElementById('sc-atr').value) || null,
        resistance_1: parseFloat(document.getElementById('sc-r1').value) || null,
        high_52w: parseFloat(document.getElementById('sc-high52').value) || null,
        is_covered: document.getElementById('sc-covered').checked,
        change_percent: 0,
        trend: 'sideways',
        trend_strength: 0.5
    };

    showLoading('sellcall-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/sell-call-score`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('sellcall-result', result.detail || 'Calculation failed');
            return;
        }

        const scoreComponents = result.components || {};

        document.getElementById('sellcall-result').innerHTML = `
            <div class="grid grid-cols-3 gap-4 mb-4">
                <div class="text-center p-4 bg-gray-800 rounded col-span-1">
                    <div class="text-4xl font-bold ${getScoreColor(result.total_score)}">${formatNumber(result.total_score)}</div>
                    <div class="text-sm text-gray-400">Total Score</div>
                </div>
                <div class="col-span-2 p-4 bg-gray-800 rounded">
                    <div class="text-lg font-semibold mb-2">${getScoreLabel(result.total_score)} Trade</div>
                    <div class="text-sm text-gray-400">
                        Premium Yield: ${formatPercent(result.premium_yield_annual || 0)} annualized
                    </div>
                    <div class="text-sm text-gray-400">
                        Type: ${params.is_covered ? 'Covered Call' : 'Naked Call'}
                    </div>
                </div>
            </div>
            <div class="text-sm">
                <div class="font-medium mb-2">Score Breakdown:</div>
                <div class="grid grid-cols-2 gap-2">
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Premium Yield (20%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.premium_yield || 0)}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Resistance (20%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.resistance_strength || 0)}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Safety (15%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.safety_margin || 0)}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-gray-700">
                        <span class="text-gray-400">Trend (15%)</span>
                        <span class="text-white">${formatNumber(scoreComponents.trend_alignment || 0)}</span>
                    </div>
                </div>
            </div>
        `;

    } catch (error) {
        showError('sellcall-result', 'API error: ' + error.message);
    }
}

async function calculateRiskReturnProfile() {
    const params = {
        strategy: document.getElementById('rrp-strategy').value,
        current_price: parseFloat(document.getElementById('rrp-price').value),
        strike: parseFloat(document.getElementById('rrp-strike').value),
        premium: parseFloat(document.getElementById('rrp-premium').value),
        days_to_expiry: parseInt(document.getElementById('rrp-dte').value),
        implied_volatility: parseFloat(document.getElementById('rrp-iv').value) / 100,
        vrp_level: document.getElementById('rrp-vrp').value
    };

    showLoading('rrp-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/risk-return-profile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('rrp-result', result.detail || 'Calculation failed');
            return;
        }

        const styleColor = result.style === 'conservative' ? 'text-green-400' :
                          result.style === 'moderate' ? 'text-yellow-400' : 'text-red-400';

        document.getElementById('rrp-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-2xl font-bold ${styleColor}">${(result.style || 'Unknown').charAt(0).toUpperCase() + (result.style || 'unknown').slice(1)}</div>
                    <div class="text-sm text-gray-400">Profile Style</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-2xl font-bold text-blue-400">${formatNumber(result.risk_reward_ratio || 0)}:1</div>
                    <div class="text-sm text-gray-400">Risk/Reward</div>
                </div>
            </div>
            <div class="text-sm">
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Max Profit</span>
                    <span class="text-green-400">${formatCurrency(result.max_profit || 0)}</span>
                </div>
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Max Loss</span>
                    <span class="text-red-400">${formatCurrency(result.max_loss || 0)}</span>
                </div>
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Breakeven</span>
                    <span class="text-white">${formatCurrency(result.breakeven || 0)}</span>
                </div>
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Return on Risk</span>
                    <span class="text-white">${formatPercent(result.return_on_risk || 0)}</span>
                </div>
                <div class="flex justify-between py-1">
                    <span class="text-gray-400">Annualized Return</span>
                    <span class="text-white">${formatPercent(result.annualized_return || 0)}</span>
                </div>
            </div>
        `;

    } catch (error) {
        showError('rrp-result', 'API error: ' + error.message);
    }
}

// ============================================
// Technical Indicator Calculators
// ============================================

async function calculateATR() {
    if (!stockData || !stockData.history) {
        showError('atr-result', 'Please fetch stock data first');
        return;
    }

    const params = {
        high: stockData.history.high,
        low: stockData.history.low,
        close: stockData.history.close,
        period: parseInt(document.getElementById('atr-period').value)
    };

    showLoading('atr-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/atr`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('atr-result', result.detail || 'Calculation failed');
            return;
        }

        const currentPrice = stockData.price_data.current_price;
        const atrPct = (result.atr / currentPrice) * 100;

        document.getElementById('atr-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold text-blue-400">${formatCurrency(result.atr)}</div>
                    <div class="text-sm text-gray-400">ATR (${params.period})</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold text-yellow-400">${formatPercent(atrPct)}</div>
                    <div class="text-sm text-gray-400">ATR as % of Price</div>
                </div>
            </div>
            <div class="mt-4 text-sm text-gray-400">
                ATR measures volatility. Higher ATR = more volatile stock.
            </div>
        `;

        // Also update ATR fields in other calculators
        document.getElementById('sl-atr').value = result.atr.toFixed(2);
        document.getElementById('sp-atr').value = result.atr.toFixed(2);
        document.getElementById('sc-atr').value = result.atr.toFixed(2);
        document.getElementById('atrs-atr').value = result.atr.toFixed(2);

    } catch (error) {
        showError('atr-result', 'API error: ' + error.message);
    }
}

async function calculateStopLoss() {
    const beta = document.getElementById('sl-beta').value;
    const params = {
        buy_price: parseFloat(document.getElementById('sl-price').value),
        atr: parseFloat(document.getElementById('sl-atr').value),
        atr_multiplier: parseFloat(document.getElementById('sl-mult').value),
        min_stop_loss_pct: parseFloat(document.getElementById('sl-min').value) / 100,
        beta: beta ? parseFloat(beta) : null
    };

    showLoading('sl-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/atr-stop-loss`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('sl-result', result.detail || 'Calculation failed');
            return;
        }

        const stopPct = ((params.buy_price - result.stop_loss) / params.buy_price) * 100;

        document.getElementById('sl-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold text-red-400">${formatCurrency(result.stop_loss)}</div>
                    <div class="text-sm text-gray-400">Stop Loss Price</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold text-yellow-400">${formatPercent(stopPct)}</div>
                    <div class="text-sm text-gray-400">Stop Loss %</div>
                </div>
            </div>
            <div class="mt-4 text-sm">
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">ATR Distance</span>
                    <span class="text-white">${formatCurrency(result.atr_distance || (params.atr * params.atr_multiplier))}</span>
                </div>
                <div class="flex justify-between py-1">
                    <span class="text-gray-400">Position Size Risk</span>
                    <span class="text-white">${formatCurrency(params.buy_price - result.stop_loss)} per share</span>
                </div>
            </div>
        `;

    } catch (error) {
        showError('sl-result', 'API error: ' + error.message);
    }
}

async function calculateRSI() {
    if (!stockData || !stockData.history) {
        showError('rsi-result', 'Please fetch stock data first');
        return;
    }

    const params = {
        prices: stockData.history.close,
        period: parseInt(document.getElementById('rsi-period').value)
    };

    showLoading('rsi-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/rsi`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('rsi-result', result.detail || 'Calculation failed');
            return;
        }

        const rsiColor = result.rsi > 70 ? 'text-red-400' : result.rsi < 30 ? 'text-green-400' : 'text-yellow-400';
        const signal = result.rsi > 70 ? 'Overbought' : result.rsi < 30 ? 'Oversold' : 'Neutral';

        document.getElementById('rsi-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold ${rsiColor}">${formatNumber(result.rsi)}</div>
                    <div class="text-sm text-gray-400">RSI (${params.period})</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold ${rsiColor}">${signal}</div>
                    <div class="text-sm text-gray-400">Signal</div>
                </div>
            </div>
            <div class="mt-4">
                <div class="w-full bg-gray-700 rounded h-3 relative">
                    <div class="absolute left-0 w-[30%] h-full bg-green-900 rounded-l"></div>
                    <div class="absolute left-[30%] w-[40%] h-full bg-yellow-900"></div>
                    <div class="absolute left-[70%] w-[30%] h-full bg-red-900 rounded-r"></div>
                    <div class="absolute top-0 h-full w-1 bg-white" style="left: ${result.rsi}%"></div>
                </div>
                <div class="flex justify-between text-xs text-gray-400 mt-1">
                    <span>0</span>
                    <span>30</span>
                    <span>70</span>
                    <span>100</span>
                </div>
            </div>
        `;

    } catch (error) {
        showError('rsi-result', 'API error: ' + error.message);
    }
}

async function calculateLiquidity() {
    const params = {
        volume: parseInt(document.getElementById('liq-volume').value),
        open_interest: parseInt(document.getElementById('liq-oi').value),
        bid: parseFloat(document.getElementById('liq-bid').value),
        ask: parseFloat(document.getElementById('liq-ask').value)
    };

    showLoading('liq-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/liquidity`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('liq-result', result.detail || 'Calculation failed');
            return;
        }

        const spread = params.ask - params.bid;
        const spreadPct = (spread / params.ask) * 100;

        document.getElementById('liq-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold ${getScoreColor(result.liquidity_score)}">${formatNumber(result.liquidity_score)}</div>
                    <div class="text-sm text-gray-400">Liquidity Score</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold text-blue-400">${result.level || getScoreLabel(result.liquidity_score)}</div>
                    <div class="text-sm text-gray-400">Liquidity Level</div>
                </div>
            </div>
            <div class="mt-4 text-sm">
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Bid/Ask Spread</span>
                    <span class="text-white">${formatCurrency(spread)} (${formatPercent(spreadPct)})</span>
                </div>
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Volume Score</span>
                    <span class="text-white">${formatNumber(result.volume_score || 0)}</span>
                </div>
                <div class="flex justify-between py-1">
                    <span class="text-gray-400">Spread Score</span>
                    <span class="text-white">${formatNumber(result.spread_score || 0)}</span>
                </div>
            </div>
        `;

    } catch (error) {
        showError('liq-result', 'API error: ' + error.message);
    }
}

async function calculateATRSafety() {
    const params = {
        current_price: parseFloat(document.getElementById('atrs-price').value),
        strike: parseFloat(document.getElementById('atrs-strike').value),
        atr: parseFloat(document.getElementById('atrs-atr').value),
        atr_ratio: parseFloat(document.getElementById('atrs-ratio').value)
    };

    showLoading('atrs-result');

    try {
        const response = await fetch(`${API_BASE}/calculate/atr-safety`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (!response.ok) {
            showError('atrs-result', result.detail || 'Calculation failed');
            return;
        }

        const actualBuffer = Math.abs(params.current_price - params.strike);
        const atrMultiples = actualBuffer / params.atr;
        const isSafe = result.is_safe || atrMultiples >= params.atr_ratio;
        const safeColor = isSafe ? 'text-green-400' : 'text-red-400';

        document.getElementById('atrs-result').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-3xl font-bold text-blue-400">${formatNumber(result.atr_multiples || atrMultiples)}</div>
                    <div class="text-sm text-gray-400">ATR Multiples</div>
                </div>
                <div class="text-center p-4 bg-gray-800 rounded">
                    <div class="text-xl font-semibold ${safeColor}">${isSafe ? 'SAFE' : 'RISKY'}</div>
                    <div class="text-sm text-gray-400">Safety Status</div>
                </div>
            </div>
            <div class="mt-4 text-sm">
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Actual Buffer</span>
                    <span class="text-white">${formatCurrency(actualBuffer)}</span>
                </div>
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Required Buffer</span>
                    <span class="text-white">${formatCurrency(params.atr * params.atr_ratio)}</span>
                </div>
                <div class="flex justify-between py-1 border-b border-gray-700">
                    <span class="text-gray-400">Safety Ratio</span>
                    <span class="text-white">${formatNumber(result.safety_ratio || (actualBuffer / (params.atr * params.atr_ratio)))}</span>
                </div>
                <div class="flex justify-between py-1">
                    <span class="text-gray-400">Buffer %</span>
                    <span class="text-white">${formatPercent((actualBuffer / params.current_price) * 100)}</span>
                </div>
            </div>
        `;

    } catch (error) {
        showError('atrs-result', 'API error: ' + error.message);
    }
}

// ============================================
// Charts
// ============================================

function renderPriceChart() {
    if (!stockData || !stockData.history) return;

    const ctx = document.getElementById('price-chart');
    if (!ctx) return;

    if (priceChart) {
        priceChart.destroy();
    }

    const dates = stockData.history.dates;
    const closes = stockData.history.close;

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: `${stockData.symbol} Price`,
                data: closes,
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: { color: '#9ca3af' }
                }
            },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        color: '#9ca3af',
                        maxTicksLimit: 10
                    },
                    grid: { color: '#374151' }
                },
                y: {
                    display: true,
                    ticks: { color: '#9ca3af' },
                    grid: { color: '#374151' }
                }
            }
        }
    });
}

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Show stock section by default
    showSection('stock');

    // Add enter key handler for symbol input
    document.getElementById('symbolInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            fetchSymbolData();
        }
    });

    console.log('Formula Tester initialized');
});

// Export functions for HTML onclick handlers
window.showSection = showSection;
window.toggleFormula = toggleFormula;
window.syncInput = syncInput;
window.fetchSymbolData = fetchSymbolData;
window.loadMockData = loadMockData;
window.populateSellPutFromData = populateSellPutFromData;
window.calculateRiskScore = calculateRiskScore;
window.calculateTargetPrice = calculateTargetPrice;
window.calculateSentiment = calculateSentiment;
window.calculateStyleScores = calculateStyleScores;
window.calculateVRP = calculateVRP;
window.calculateTrendAlignment = calculateTrendAlignment;
window.calculateSellPutScore = calculateSellPutScore;
window.calculateSellCallScore = calculateSellCallScore;
window.calculateRiskReturnProfile = calculateRiskReturnProfile;
window.calculateATR = calculateATR;
window.calculateStopLoss = calculateStopLoss;
window.calculateRSI = calculateRSI;
window.calculateLiquidity = calculateLiquidity;
window.calculateATRSafety = calculateATRSafety;
