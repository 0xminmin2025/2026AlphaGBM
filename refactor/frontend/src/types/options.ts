
export interface OptionScores {
    sprv?: number;
    scrv?: number;
    bcrv?: number;
    bprv?: number;
    liquidity_factor?: number;
    iv_rank?: number;
    iv_percentile?: number;
    days_to_expiry?: number;
    assignment_probability?: number;
    premium_income?: number;
    margin_requirement?: number;
    annualized_return?: number;
}

export interface OptionData {
    identifier: string;
    symbol: string;
    strike: number;
    put_call: 'CALL' | 'PUT';
    expiry_date: string;
    bid_price?: number;
    ask_price?: number;
    latest_price?: number;
    volume?: number;
    open_interest?: number;
    implied_vol?: number;
    delta?: number;
    gamma?: number;
    theta?: number;
    vega?: number;
    rho?: number;
    scores?: OptionScores;
    premium?: number;
    spread_percentage?: number;
}

export interface OptionChainResponse {
    symbol: string;
    expiry_date: string;
    calls: OptionData[];
    puts: OptionData[];
    data_source?: string;
    real_stock_price?: number;
}

export interface ExpirationDate {
    date: string;
    timestamp: number;
    period_tag: string;
}

export interface ExpirationResponse {
    symbol: string;
    expirations: ExpirationDate[];
}

export interface VRPResult {
    vrp: number;
    iv: number;
    rv_forecast: number;
    iv_rank: number;
    iv_percentile: number;
    recommendation: string;
}

export interface EnhancedAnalysisResponse {
    symbol: string;
    option_identifier: string;
    vrp_result?: VRPResult;
    available: boolean;
}
