"""
Fee APR Estimator

Estimates fee earnings APR based on historical trading volume
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class FeeEstimator:
    """Estimate fee APR for LP positions"""

    def estimate_apr(
        self,
        volume_window: float,
        tvl_avg: float,
        fee_tier: float,
        window_hours: int,
    ) -> Dict[str, Any]:
        """
        Calculate estimated APR from fees

        Formula:
        fees = volume × fee_tier
        APR = (fees / TVL) × (365 × 24 / window_hours) × 100

        Args:
            volume_window: Trading volume in the window (USD)
            tvl_avg: Average TVL in the window (USD)
            fee_tier: Fee percentage (e.g., 0.003 for 0.3%)
            window_hours: Historical window size in hours

        Returns:
            Dict with fee_apr_est and breakdown
        """
        try:
            if tvl_avg <= 0:
                logger.warning("TVL is zero or negative, cannot calculate APR")
                return {
                    "fee_apr_est": 0.0,
                    "fees_earned": 0.0,
                    "volume_window": volume_window,
                    "tvl_avg": tvl_avg,
                    "annualized": False,
                }

            # Calculate fees earned in window
            fees_earned = volume_window * fee_tier

            # Calculate return over window
            return_window = fees_earned / tvl_avg

            # Annualize the return
            hours_per_year = 365 * 24
            periods_per_year = hours_per_year / window_hours
            apr = return_window * periods_per_year * 100

            return {
                "fee_apr_est": apr,
                "fees_earned": fees_earned,
                "volume_window": volume_window,
                "tvl_avg": tvl_avg,
                "fee_tier": fee_tier,
                "window_hours": window_hours,
                "annualized": True,
            }

        except Exception as e:
            logger.error(f"Fee APR calculation error: {e}")
            return {
                "fee_apr_est": 0.0,
                "fees_earned": 0.0,
                "volume_window": volume_window,
                "tvl_avg": tvl_avg,
                "annualized": False,
                "error": str(e),
            }

    def estimate_daily_fees(
        self,
        volume_24h: float,
        fee_tier: float,
    ) -> float:
        """
        Calculate daily fee earnings

        Args:
            volume_24h: 24-hour trading volume (USD)
            fee_tier: Fee percentage

        Returns:
            Daily fees in USD
        """
        return volume_24h * fee_tier

    def estimate_annual_fees(
        self,
        volume_24h: float,
        fee_tier: float,
    ) -> float:
        """
        Estimate annual fee earnings assuming constant volume

        Args:
            volume_24h: 24-hour trading volume (USD)
            fee_tier: Fee percentage

        Returns:
            Estimated annual fees in USD
        """
        daily_fees = self.estimate_daily_fees(volume_24h, fee_tier)
        return daily_fees * 365

    def calculate_fee_velocity(
        self,
        volume_window: float,
        tvl_avg: float,
        window_hours: int,
    ) -> float:
        """
        Calculate fee velocity (volume/TVL ratio)

        Higher velocity means more trading activity relative to liquidity

        Args:
            volume_window: Trading volume in window
            tvl_avg: Average TVL
            window_hours: Window size

        Returns:
            Annualized velocity ratio
        """
        if tvl_avg <= 0:
            return 0.0

        velocity_window = volume_window / tvl_avg

        # Annualize
        hours_per_year = 365 * 24
        periods_per_year = hours_per_year / window_hours
        annual_velocity = velocity_window * periods_per_year

        return annual_velocity

    def estimate_position_earnings(
        self,
        position_size_usd: float,
        volume_window: float,
        tvl_avg: float,
        fee_tier: float,
        window_hours: int,
    ) -> Dict[str, Any]:
        """
        Estimate earnings for a specific position size

        Args:
            position_size_usd: Size of LP position in USD
            volume_window: Trading volume in window
            tvl_avg: Average TVL
            fee_tier: Fee percentage
            window_hours: Window size

        Returns:
            Dict with earnings breakdown
        """
        try:
            if tvl_avg <= 0:
                return {
                    "position_size_usd": position_size_usd,
                    "earnings_window": 0.0,
                    "earnings_daily": 0.0,
                    "earnings_annual": 0.0,
                    "apr_percent": 0.0,
                }

            # Calculate share of pool
            pool_share = position_size_usd / tvl_avg

            # Total fees in window
            total_fees = volume_window * fee_tier

            # Position's share of fees in window
            earnings_window = total_fees * pool_share

            # Annualize
            hours_per_year = 365 * 24
            periods_per_year = hours_per_year / window_hours
            earnings_annual = earnings_window * periods_per_year

            # Daily earnings
            earnings_daily = earnings_annual / 365

            # APR
            apr_percent = (earnings_annual / position_size_usd) * 100 if position_size_usd > 0 else 0.0

            return {
                "position_size_usd": position_size_usd,
                "pool_share_percent": pool_share * 100,
                "earnings_window": earnings_window,
                "earnings_daily": earnings_daily,
                "earnings_annual": earnings_annual,
                "apr_percent": apr_percent,
            }

        except Exception as e:
            logger.error(f"Position earnings calculation error: {e}")
            return {
                "position_size_usd": position_size_usd,
                "earnings_window": 0.0,
                "earnings_daily": 0.0,
                "earnings_annual": 0.0,
                "apr_percent": 0.0,
                "error": str(e),
            }

    def compare_fee_tiers(
        self,
        volume_window: float,
        tvl_avg: float,
        window_hours: int,
    ) -> Dict[str, float]:
        """
        Compare APR across different fee tiers

        Args:
            volume_window: Trading volume
            tvl_avg: Average TVL
            window_hours: Window size

        Returns:
            Dict mapping fee tier to APR
        """
        fee_tiers = {
            "0.05%": 0.0005,
            "0.3%": 0.003,
            "1.0%": 0.01,
        }

        results = {}
        for tier_name, tier_value in fee_tiers.items():
            apr_result = self.estimate_apr(volume_window, tvl_avg, tier_value, window_hours)
            results[tier_name] = apr_result["fee_apr_est"]

        return results

    def calculate_breakeven_volume(
        self,
        tvl_avg: float,
        fee_tier: float,
        target_apr: float,
        window_hours: int = 24,
    ) -> float:
        """
        Calculate required volume to achieve target APR

        Args:
            tvl_avg: Average TVL
            fee_tier: Fee percentage
            target_apr: Target APR percentage
            window_hours: Window size

        Returns:
            Required trading volume
        """
        if tvl_avg <= 0 or fee_tier <= 0:
            return 0.0

        # Reverse the APR calculation
        hours_per_year = 365 * 24
        periods_per_year = hours_per_year / window_hours

        # target_apr = (volume * fee_tier / tvl) * periods_per_year * 100
        # volume = (target_apr / 100 * tvl) / (fee_tier * periods_per_year)

        required_volume = (target_apr / 100 * tvl_avg) / (fee_tier * periods_per_year)

        return required_volume
