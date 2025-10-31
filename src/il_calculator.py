"""
Impermanent Loss Calculator

Calculates IL for different pool types (50/50, weighted, stable)
"""
import math
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ILCalculator:
    """Calculate impermanent loss for LP positions"""

    def calculate_il(
        self,
        price_changes: Dict[str, float],
        weights: List[float],
    ) -> Dict[str, Any]:
        """
        Calculate impermanent loss based on price changes and pool weights

        Args:
            price_changes: Dict mapping token symbols to price change ratios
            weights: List of token weights (e.g., [50, 50] or [80, 20])

        Returns:
            Dict with IL_percent and additional details
        """
        try:
            # Normalize weights to percentages
            total_weight = sum(weights)
            normalized_weights = [w / total_weight * 100 for w in weights]

            # Get price ratios (current/initial)
            tokens = list(price_changes.keys())
            price_ratios = [price_changes[token] for token in tokens]

            # Calculate IL based on pool type
            if len(weights) == 2:
                if self._is_balanced_pool(normalized_weights):
                    # 50/50 pool - use standard IL formula
                    il_percent = self._calculate_50_50_il(price_ratios[0], price_ratios[1])
                else:
                    # Weighted pool (e.g., Balancer 80/20)
                    il_percent = self._calculate_weighted_il(price_ratios, normalized_weights)
            else:
                # Multi-asset pool
                il_percent = self._calculate_multi_asset_il(price_ratios, normalized_weights)

            return {
                "IL_percent": il_percent,
                "price_ratios": {tokens[i]: price_ratios[i] for i in range(len(tokens))},
                "weights": normalized_weights,
                "pool_type": self._get_pool_type(normalized_weights),
            }

        except Exception as e:
            logger.error(f"IL calculation error: {e}")
            return {
                "IL_percent": 0.0,
                "price_ratios": {},
                "weights": weights,
                "pool_type": "unknown",
                "error": str(e),
            }

    def _is_balanced_pool(self, weights: List[float]) -> bool:
        """Check if pool is 50/50 balanced"""
        if len(weights) != 2:
            return False
        return abs(weights[0] - 50.0) < 1.0 and abs(weights[1] - 50.0) < 1.0

    def _calculate_50_50_il(self, price_ratio_0: float, price_ratio_1: float) -> float:
        """
        Calculate IL for 50/50 pool (Uniswap V2, SushiSwap)

        Formula: IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
        where price_ratio = (price_1 / price_0)
        """
        try:
            # Calculate relative price ratio
            price_ratio = price_ratio_1 / price_ratio_0

            # IL formula for 50/50 pool
            if price_ratio <= 0:
                return 0.0

            il = 2 * math.sqrt(price_ratio) / (1 + price_ratio) - 1

            # Return as percentage (negative means loss)
            return il * 100

        except Exception as e:
            logger.error(f"50/50 IL calculation error: {e}")
            return 0.0

    def _calculate_weighted_il(self, price_ratios: List[float], weights: List[float]) -> float:
        """
        Calculate IL for weighted pools (e.g., Balancer 80/20)

        Formula for 2-asset weighted pool:
        IL = (weight_0 * price_ratio_0^(weight_0/100) + weight_1 * price_ratio_1^(weight_1/100)) /
             (weight_0 * price_ratio_0 + weight_1 * price_ratio_1) - 1
        """
        try:
            if len(price_ratios) != 2 or len(weights) != 2:
                return 0.0

            w0 = weights[0] / 100  # Convert to decimal
            w1 = weights[1] / 100
            p0 = price_ratios[0]
            p1 = price_ratios[1]

            # Prevent math errors
            if p0 <= 0 or p1 <= 0:
                return 0.0

            # Weighted IL calculation
            numerator = w0 * (p0 ** w0) + w1 * (p1 ** w1)
            denominator = w0 * p0 + w1 * p1

            if denominator == 0:
                return 0.0

            il = numerator / denominator - 1

            # Return as percentage
            return il * 100

        except Exception as e:
            logger.error(f"Weighted IL calculation error: {e}")
            return 0.0

    def _calculate_multi_asset_il(self, price_ratios: List[float], weights: List[float]) -> float:
        """
        Calculate IL for multi-asset pools (>2 tokens)

        Uses generalized constant product formula
        """
        try:
            n = len(price_ratios)
            if n != len(weights):
                return 0.0

            # Convert weights to decimals
            w = [weight / 100 for weight in weights]

            # Calculate weighted geometric mean of price ratios
            product = 1.0
            for i in range(n):
                if price_ratios[i] <= 0:
                    return 0.0
                product *= price_ratios[i] ** w[i]

            # Calculate weighted arithmetic mean
            weighted_sum = sum(w[i] * price_ratios[i] for i in range(n))

            if weighted_sum == 0:
                return 0.0

            # IL as deviation from holding
            il = product / weighted_sum - 1

            # Return as percentage
            return il * 100

        except Exception as e:
            logger.error(f"Multi-asset IL calculation error: {e}")
            return 0.0

    def _get_pool_type(self, weights: List[float]) -> str:
        """Determine pool type from weights"""
        if len(weights) == 2:
            if self._is_balanced_pool(weights):
                return "50/50"
            else:
                return f"{int(weights[0])}/{int(weights[1])}"
        else:
            return "multi-asset"

    def calculate_il_from_price_change(
        self,
        initial_price: float,
        current_price: float,
        weights: List[float] = [50, 50],
    ) -> float:
        """
        Simplified IL calculation from single price change

        Args:
            initial_price: Initial token price
            current_price: Current token price
            weights: Pool weights (default 50/50)

        Returns:
            IL percentage
        """
        if initial_price <= 0 or current_price <= 0:
            return 0.0

        price_ratio = current_price / initial_price

        # For 50/50 pool
        if len(weights) == 2 and self._is_balanced_pool(weights):
            return self._calculate_50_50_il(1.0, price_ratio)

        # For weighted pools, approximate
        price_ratios = [1.0, price_ratio]
        return self._calculate_weighted_il(price_ratios, weights)

    def estimate_il_scenarios(self, weights: List[float] = [50, 50]) -> Dict[str, float]:
        """
        Generate IL estimates for common price change scenarios

        Returns:
            Dict mapping scenario to IL percentage
        """
        scenarios = {
            "2x price increase": self.calculate_il_from_price_change(1.0, 2.0, weights),
            "2x price decrease": self.calculate_il_from_price_change(1.0, 0.5, weights),
            "3x price increase": self.calculate_il_from_price_change(1.0, 3.0, weights),
            "4x price increase": self.calculate_il_from_price_change(1.0, 4.0, weights),
            "5x price increase": self.calculate_il_from_price_change(1.0, 5.0, weights),
            "10% increase": self.calculate_il_from_price_change(1.0, 1.1, weights),
            "10% decrease": self.calculate_il_from_price_change(1.0, 0.9, weights),
            "25% increase": self.calculate_il_from_price_change(1.0, 1.25, weights),
            "25% decrease": self.calculate_il_from_price_change(1.0, 0.75, weights),
        }

        return scenarios
