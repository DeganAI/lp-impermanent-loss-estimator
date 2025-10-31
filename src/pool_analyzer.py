"""
Pool Analyzer

Main orchestrator for pool data analysis and IL/fee calculations
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from src.data_sources import DataSourceManager

logger = logging.getLogger(__name__)


class PoolAnalyzer:
    """Analyzes LP pools and calculates metrics"""

    def __init__(self, rpc_url: str, chain_id: int):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.data_source = DataSourceManager(rpc_url, chain_id)
        self.is_connected = self.data_source.is_connected

    async def analyze_pool(
        self,
        pool_address: str,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Analyze pool and gather all data needed for IL and fee calculations

        Args:
            pool_address: Pool contract address
            window_hours: Historical window size

        Returns:
            Dict with all pool data including price changes, volume, TVL, etc.
        """
        try:
            logger.info(f"Analyzing pool {pool_address} over {window_hours}h window")

            # Detect pool type
            pool_type = self.data_source.detect_pool_type(pool_address)
            logger.info(f"Detected pool type: {pool_type}")

            # Get token information
            tokens = self.data_source.get_pool_tokens(pool_address)
            if not tokens:
                raise Exception("Failed to fetch pool tokens")

            token0_address = tokens["token0"]["address"]
            token1_address = tokens["token1"]["address"]
            token0_symbol = tokens["token0"]["symbol"]
            token1_symbol = tokens["token1"]["symbol"]

            logger.info(f"Pool tokens: {token0_symbol} / {token1_symbol}")

            # Get current prices
            current_price0 = self.data_source.get_token_price(token0_address)
            current_price1 = self.data_source.get_token_price(token1_address)

            if not current_price0 or not current_price1:
                raise Exception("Failed to fetch current token prices")

            logger.info(f"Current prices: {token0_symbol}=${current_price0:.2f}, {token1_symbol}=${current_price1:.2f}")

            # Get historical prices (at start of window)
            initial_price0 = self.data_source.get_historical_price(token0_address, window_hours)
            initial_price1 = self.data_source.get_historical_price(token1_address, window_hours)

            # Fallback: if historical prices unavailable, use current prices (IL will be 0)
            if not initial_price0:
                initial_price0 = current_price0
                logger.warning(f"Historical price unavailable for {token0_symbol}, using current price")

            if not initial_price1:
                initial_price1 = current_price1
                logger.warning(f"Historical price unavailable for {token1_symbol}, using current price")

            # Calculate price changes (ratio)
            price_ratio0 = current_price0 / initial_price0 if initial_price0 > 0 else 1.0
            price_ratio1 = current_price1 / initial_price1 if initial_price1 > 0 else 1.0

            logger.info(f"Price changes: {token0_symbol} {(price_ratio0-1)*100:+.2f}%, {token1_symbol} {(price_ratio1-1)*100:+.2f}%")

            # Get current TVL
            current_tvl = self.data_source.calculate_tvl(pool_address)
            if not current_tvl:
                raise Exception("Failed to calculate TVL")

            logger.info(f"Current TVL: ${current_tvl:,.2f}")

            # Estimate trading volume
            # In production, would use The Graph or other indexer
            # For now, estimate from TVL
            volume_window = self.data_source.estimate_volume_from_reserves(
                pool_address,
                window_hours,
            )

            logger.info(f"Estimated volume ({window_hours}h): ${volume_window:,.2f}")

            # Get fee tier
            fee_tier = self.data_source.get_fee_tier(pool_address, pool_type)
            logger.info(f"Fee tier: {fee_tier * 100:.2f}%")

            # Determine weights
            # For V2/V3, assume 50/50
            # For Balancer, would need to query pool
            weights = [50, 50]
            if pool_type == "balancer":
                # Would query actual weights here
                weights = [50, 50]

            # Build response
            result = {
                "pool_address": pool_address,
                "pool_type": pool_type,
                "pool_info": {
                    "type": pool_type,
                    "token0": token0_symbol,
                    "token1": token1_symbol,
                    "fee_tier_percent": fee_tier * 100,
                    "tvl_usd": current_tvl,
                },
                "price_changes": {
                    token0_symbol: price_ratio0,
                    token1_symbol: price_ratio1,
                },
                "initial_prices": {
                    token0_symbol: initial_price0,
                    token1_symbol: initial_price1,
                },
                "current_prices": {
                    token0_symbol: current_price0,
                    token1_symbol: current_price1,
                },
                "volume_window": volume_window,
                "tvl_avg": current_tvl,  # Simplified: using current TVL as average
                "fee_tier": fee_tier,
                "weights": weights,
                "window_hours": window_hours,
                "data_quality": "estimated",  # Mark as estimated since using fallbacks
            }

            return result

        except Exception as e:
            logger.error(f"Pool analysis error: {e}", exc_info=True)
            raise

    def validate_pool_address(self, pool_address: str) -> bool:
        """
        Validate that the address is a valid pool

        Args:
            pool_address: Pool address to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            tokens = self.data_source.get_pool_tokens(pool_address)
            return tokens is not None
        except:
            return False

    def get_pool_summary(self, pool_address: str) -> Dict[str, Any]:
        """
        Get quick summary of pool

        Args:
            pool_address: Pool address

        Returns:
            Dict with basic pool info
        """
        try:
            pool_type = self.data_source.detect_pool_type(pool_address)
            tokens = self.data_source.get_pool_tokens(pool_address)

            if not tokens:
                return {"error": "Invalid pool address"}

            tvl = self.data_source.calculate_tvl(pool_address)
            fee_tier = self.data_source.get_fee_tier(pool_address, pool_type)

            return {
                "pool_type": pool_type,
                "token0": tokens["token0"]["symbol"],
                "token1": tokens["token1"]["symbol"],
                "tvl_usd": tvl,
                "fee_tier_percent": fee_tier * 100,
            }

        except Exception as e:
            logger.error(f"Error getting pool summary: {e}")
            return {"error": str(e)}

    def compare_pools(
        self,
        pool_addresses: list,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Compare multiple pools

        Args:
            pool_addresses: List of pool addresses
            window_hours: Window for comparison

        Returns:
            Dict with comparison data
        """
        results = []

        for pool_address in pool_addresses:
            try:
                summary = self.get_pool_summary(pool_address)
                results.append({
                    "pool_address": pool_address,
                    **summary,
                })
            except Exception as e:
                logger.error(f"Error analyzing pool {pool_address}: {e}")
                results.append({
                    "pool_address": pool_address,
                    "error": str(e),
                })

        return {
            "pools": results,
            "window_hours": window_hours,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
