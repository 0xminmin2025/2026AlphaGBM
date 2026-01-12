"""
Tiger Open API Client Configuration Module
Ported from new_options_module/tiger_client.py
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
from tigeropen.common.consts import Language, Market, BarPeriod
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient

class TigerClientManager:
    """Manages Tiger Open API client configuration and provides quote services"""

    def __init__(self, props_path=None):
        self.props_path = props_path
        self.client_config = None
        self.quote_client = None

    def initialize_client(self):
        """Initialize Tiger client configuration and quote client"""
        try:
            # Use environment variables if available or fallback to local files
            # For now, we assume the user has the properties file at previous location or in refactor dir
            # We'll check standard locations
            
            # Paths to check
            candidate_paths = [
                 # Same dir as this service
                 os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tiger_openapi_config.properties'),
                 os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tiger_openapi_config.properties'),
                 os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'tiger_openapi_config.properties'),
            ]
            
            config_file_path = None
            for path in candidate_paths:
                if os.path.exists(path):
                    config_file_path = path
                    break
            
            if not config_file_path:
                 print(f"⚠️ Tiger Config not found in any candidate path")
                 return False

            self.client_config = TigerOpenClientConfig(props_path=config_file_path)
            self.client_config.language = Language.zh_CN

            print(f"✅ Client config initialized - Tiger ID: {self.client_config.tiger_id}")

            # Initialize QuoteClient
            self.quote_client = QuoteClient(self.client_config)

            print("✅ Quote Client initialized successfully")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize client: {str(e)}")
            return False

    def get_option_expirations(self, symbol, market=Market.US):
        if not self.quote_client:
            raise Exception("Quote client not initialized")
        return self.quote_client.get_option_expirations(symbols=[symbol], market=market)

    def get_option_chain(self, symbol, expiry, market=Market.US):
        if not self.quote_client:
            raise Exception("Quote client not initialized")
        
        return self.quote_client.get_option_chain(
            symbol=symbol,
            expiry=expiry,
            market=market,
            return_greek_value=True
        )

    def get_stock_quote(self, symbols):
        if not self.quote_client:
            raise Exception("Quote client not initialized")
        return self.quote_client.get_stock_briefs(symbols)
    
    def get_margin_rate(self, symbol: str, market=Market.US) -> Optional[float]:
        if not self.quote_client:
            return None
        
        try:
            stock_data = self.quote_client.get_stock_briefs([symbol])
            
            if stock_data is not None and not stock_data.empty:
                if 'margin_rate' in stock_data.columns:
                    margin_rate = stock_data['margin_rate'].iloc[0]
                    if pd.notna(margin_rate) and margin_rate > 0:
                        return float(margin_rate)
                elif 'margin_requirement' in stock_data.columns:
                    margin_req = stock_data['margin_requirement'].iloc[0]
                    if pd.notna(margin_req):
                        if margin_req > 1:
                            return float(margin_req) / 100.0
                        return float(margin_req)
            return None
            
        except Exception as e:
            print(f"⚠️ Could not fetch margin rate for {symbol}: {str(e)}")
            return None
    
    def get_stock_history(self, symbol: str, days: int = 60, market: Market = Market.US) -> Optional[List[float]]:
        if not self.quote_client:
            raise Exception("Quote client not initialized")
        
        try:
            days = max(30, days)
            end_time = int(datetime.now().timestamp() * 1000)
            limit = min(days, 200)
            
            bars = self.quote_client.get_bars(
                symbols=[symbol],
                period=BarPeriod.DAY,
                end_time=end_time,
                limit=limit,
                market=market
            )
            
            if bars is None or bars.empty:
                return None
            
            if 'close' in bars.columns and 'time' in bars.columns:
                bars_sorted = bars.sort_values('time')
                prices = bars_sorted['close'].tolist()
                prices = [p for p in prices if pd.notna(p) and p > 0]
                
                if len(prices) < 30:
                    return None
                
                return prices
            else:
                return None
        except Exception as e:
            print(f"❌ Error fetching price history for {symbol}: {str(e)}")
            return None

# Global client manager instance
client_manager = TigerClientManager()

def get_client_manager():
    return client_manager
