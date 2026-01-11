"""
Tiger Open API Client Configuration Module
Handles client setup and provides quote services for the option API
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
from tigeropen.common.consts import Language, Market, BarPeriod
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.util.signature_utils import read_private_key

class TigerClientManager:
    """
    Manages Tiger Open API client configuration and provides quote services
    """

    def __init__(self, props_path='/Users/lewis/space/trading/tiger'):
        """
        Initialize Tiger client manager

        Args:
            props_path: Path to the properties files directory
        """
        self.props_path = props_path
        self.client_config = None
        self.quote_client = None

    def initialize_client(self):
        """
        Initialize Tiger client configuration and quote client

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Use local configuration file relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_file_path = os.path.join(current_dir, 'tiger_openapi_config.properties')
            
            if not os.path.exists(config_file_path):
                 print(f"⚠️ Config not found at {config_file_path}, trying default path...")
                 config_file_path = '/Users/lewis/space/trading/tiger/tiger_openapi_config.properties'
            self.client_config = TigerOpenClientConfig(props_path=config_file_path)
            self.client_config.language = Language.zh_CN

            print(f"✅ Client config initialized - Tiger ID: {self.client_config.tiger_id}")
            print(f"   License: {self.client_config.license}")

            # Initialize QuoteClient
            self.quote_client = QuoteClient(self.client_config)

            print("✅ Quote Client initialized successfully")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize client: {str(e)}")
            return False

    def test_permissions(self):
        """
        Test quote permissions (optional step)

        Returns:
            list: Permission details if successful, None otherwise
        """
        if not self.quote_client:
            print("❌ Quote client not initialized")
            return None

        try:
            permissions = self.quote_client.get_quote_permission()
            print(f"✅ Found {len(permissions)} permissions:")
            for permission in permissions:
                print(f"   - {permission['name']}")
            return permissions

        except Exception as e:
            print(f"⚠️ Permission check failed: {str(e)}")
            # This is not critical for quote operations
            return None

    def get_option_expirations(self, symbol, market=Market.US):
        """
        Get option expiration dates for a symbol

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            market: Market (Market.US or Market.HK)

        Returns:
            pandas.DataFrame: Expiration dates data
        """
        if not self.quote_client:
            raise Exception("Quote client not initialized")

        return self.quote_client.get_option_expirations(symbols=[symbol], market=market)

    def get_option_chain(self, symbol, expiry, market=Market.US):
        """
        Get option chain for a symbol and expiry date with Greeks

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            expiry: Expiry date (string like '2024-01-19' or timestamp)
            market: Market (Market.US or Market.HK)

        Returns:
            pandas.DataFrame: Option chain data with Greeks
        """
        if not self.quote_client:
            raise Exception("Quote client not initialized")

        print(f"📊 Requesting option chain: {symbol} {expiry} {market}")

        # Get option chain with Greek values enabled
        option_chain = self.quote_client.get_option_chain(
            symbol=symbol,
            expiry=expiry,
            market=market,
            return_greek_value=True  # Enable Greeks (delta, gamma, theta, vega, rho)
        )

        print(f"📈 Received option chain with {len(option_chain)} contracts")

        return option_chain

    def get_stock_quote(self, symbols):
        """
        Get basic stock quote data

        Args:
            symbols: List of stock symbols

        Returns:
            pandas.DataFrame: Stock quote data
        """
        if not self.quote_client:
            raise Exception("Quote client not initialized")

        return self.quote_client.get_stock_briefs(symbols)
    
    def get_margin_rate(self, symbol: str, market=Market.US) -> Optional[float]:
        """
        Get margin rate for a stock (for options trading)
        
        Note: Tiger API may not directly provide margin rates.
        This method attempts to fetch margin rate from stock briefs,
        or returns None to use standard Reg-T rules.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            market: Market (Market.US or Market.HK)
        
        Returns:
            float: Margin rate (e.g., 0.20 for 20%), or None if not available
        """
        if not self.quote_client:
            return None
        
        try:
            # Try to get stock briefs and check for margin rate field
            stock_data = self.quote_client.get_stock_briefs([symbol])
            
            if stock_data is not None and not stock_data.empty:
                # Check if margin_rate or similar field exists
                # Common field names: 'margin_rate', 'margin_requirement', 'margin_pct'
                if 'margin_rate' in stock_data.columns:
                    margin_rate = stock_data['margin_rate'].iloc[0]
                    if pd.notna(margin_rate) and margin_rate > 0:
                        return float(margin_rate)
                elif 'margin_requirement' in stock_data.columns:
                    # If margin_requirement is a percentage (0-1), return it
                    margin_req = stock_data['margin_requirement'].iloc[0]
                    if pd.notna(margin_req):
                        # If it's already a rate (0-1), return as is
                        # If it's a percentage (0-100), convert to rate
                        if margin_req > 1:
                            return float(margin_req) / 100.0
                        return float(margin_req)
            
            # If no margin rate found, return None to use standard rules
            return None
            
        except Exception as e:
            print(f"⚠️ Could not fetch margin rate for {symbol}: {str(e)}")
            return None
    
    def get_stock_history(self, symbol: str, days: int = 60, market: Market = Market.US) -> Optional[List[float]]:
        """
        Get historical stock price data for VRP calculation
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            days: Number of days of history to fetch (default 60, minimum 30)
            market: Market (Market.US or Market.HK)
        
        Returns:
            List[float]: List of closing prices (from oldest to newest), or None if failed
        """
        if not self.quote_client:
            raise Exception("Quote client not initialized")
        
        try:
            # Ensure minimum 30 days for VRP calculation
            days = max(30, days)
            
            # Calculate end time (now) and limit
            end_time = int(datetime.now().timestamp() * 1000)
            limit = min(days, 200)  # API limit is typically 200
            
            print(f"📊 Fetching {days} days of price history for {symbol}...")
            
            # Get historical bars
            bars = self.quote_client.get_bars(
                symbols=[symbol],
                period=BarPeriod.DAY,
                end_time=end_time,
                limit=limit,
                market=market
            )
            
            if bars is None or bars.empty:
                print(f"⚠️ No historical data returned for {symbol}")
                return None
            
            # Extract closing prices and sort by time (oldest first)
            if 'close' in bars.columns and 'time' in bars.columns:
                # Sort by time ascending (oldest first)
                bars_sorted = bars.sort_values('time')
                prices = bars_sorted['close'].tolist()
                
                # Filter out invalid prices
                prices = [p for p in prices if pd.notna(p) and p > 0]
                
                if len(prices) < 30:
                    print(f"⚠️ Insufficient historical data: {len(prices)} points (need at least 30)")
                    return None
                
                print(f"✅ Retrieved {len(prices)} days of price history for {symbol}")
                return prices
            else:
                print(f"⚠️ Historical data missing 'close' or 'time' columns")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching price history for {symbol}: {str(e)}")
            return None

# Global client manager instance
client_manager = TigerClientManager()

def get_client_manager():
    """
    Get the global client manager instance

    Returns:
        TigerClientManager: The client manager instance
    """
    return client_manager