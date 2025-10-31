"""
Data Sources for LP Analysis

Fetches data from on-chain sources, The Graph, and price APIs
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import requests
from web3 import Web3

logger = logging.getLogger(__name__)


# Standard ERC20 ABI (minimal)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

# Uniswap V2 Pair ABI (minimal)
UNISWAP_V2_PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "reserve0", "type": "uint112"},
            {"name": "reserve1", "type": "uint112"},
            {"name": "blockTimestampLast", "type": "uint32"},
        ],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
]

# Uniswap V3 Pool ABI (minimal)
UNISWAP_V3_POOL_ABI = [
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "fee",
        "outputs": [{"type": "uint24"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"type": "uint128"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class DataSourceManager:
    """Manages data fetching from multiple sources"""

    def __init__(self, rpc_url: str, chain_id: int):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.is_connected = self.w3.is_connected()

        # CoinGecko API (free tier)
        self.coingecko_base = "https://api.coingecko.com/api/v3"

        # Chain ID to CoinGecko platform mapping
        self.chain_platforms = {
            1: "ethereum",
            137: "polygon-pos",
            42161: "arbitrum-one",
            10: "optimistic-ethereum",
            8453: "base",
            56: "binance-smart-chain",
            43114: "avalanche",
        }

    def get_pool_tokens(self, pool_address: str) -> Optional[Dict[str, Any]]:
        """
        Fetch token addresses and info from pool contract

        Args:
            pool_address: Pool contract address

        Returns:
            Dict with token0, token1, and their info
        """
        try:
            pool_address = Web3.to_checksum_address(pool_address)

            # Try Uniswap V2 format first
            try:
                pool_contract = self.w3.eth.contract(address=pool_address, abi=UNISWAP_V2_PAIR_ABI)
                token0_address = pool_contract.functions.token0().call()
                token1_address = pool_contract.functions.token1().call()
                pool_type = "uniswap-v2"
            except:
                # Try Uniswap V3 format
                pool_contract = self.w3.eth.contract(address=pool_address, abi=UNISWAP_V3_POOL_ABI)
                token0_address = pool_contract.functions.token0().call()
                token1_address = pool_contract.functions.token1().call()
                pool_type = "uniswap-v3"

            # Get token info
            token0_info = self._get_token_info(token0_address)
            token1_info = self._get_token_info(token1_address)

            return {
                "token0": {
                    "address": token0_address,
                    "symbol": token0_info["symbol"],
                    "decimals": token0_info["decimals"],
                },
                "token1": {
                    "address": token1_address,
                    "symbol": token1_info["symbol"],
                    "decimals": token1_info["decimals"],
                },
                "pool_type": pool_type,
            }

        except Exception as e:
            logger.error(f"Error fetching pool tokens: {e}")
            return None

    def _get_token_info(self, token_address: str) -> Dict[str, Any]:
        """Fetch token symbol and decimals"""
        try:
            token_address = Web3.to_checksum_address(token_address)
            token_contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)

            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()

            return {"symbol": symbol, "decimals": decimals}

        except Exception as e:
            logger.error(f"Error fetching token info for {token_address}: {e}")
            return {"symbol": "UNKNOWN", "decimals": 18}

    def get_pool_reserves(self, pool_address: str) -> Optional[Dict[str, float]]:
        """
        Get current pool reserves

        Args:
            pool_address: Pool contract address

        Returns:
            Dict with reserve0 and reserve1
        """
        try:
            pool_address = Web3.to_checksum_address(pool_address)
            pool_contract = self.w3.eth.contract(address=pool_address, abi=UNISWAP_V2_PAIR_ABI)

            reserves = pool_contract.functions.getReserves().call()

            return {
                "reserve0": reserves[0],
                "reserve1": reserves[1],
                "timestamp": reserves[2],
            }

        except Exception as e:
            logger.error(f"Error fetching reserves: {e}")
            return None

    def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Fetch current token price from CoinGecko

        Args:
            token_address: Token contract address

        Returns:
            Token price in USD
        """
        try:
            platform = self.chain_platforms.get(self.chain_id)
            if not platform:
                logger.warning(f"No CoinGecko platform mapping for chain {self.chain_id}")
                return None

            url = f"{self.coingecko_base}/simple/token_price/{platform}"
            params = {
                "contract_addresses": token_address.lower(),
                "vs_currencies": "usd",
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            token_data = data.get(token_address.lower(), {})

            return token_data.get("usd")

        except Exception as e:
            logger.error(f"Error fetching token price from CoinGecko: {e}")
            return None

    def get_historical_price(
        self,
        token_address: str,
        hours_ago: int,
    ) -> Optional[float]:
        """
        Fetch historical token price

        Args:
            token_address: Token contract address
            hours_ago: How many hours in the past

        Returns:
            Historical token price in USD
        """
        try:
            # For simplicity, use CoinGecko market chart
            # Note: Free tier has rate limits
            platform = self.chain_platforms.get(self.chain_id)
            if not platform:
                return None

            # Get coin ID from contract
            # This is simplified - in production, need better coin ID resolution
            days_ago = max(1, hours_ago / 24)

            url = f"{self.coingecko_base}/coins/{platform}/contract/{token_address.lower()}/market_chart/"
            params = {
                "vs_currency": "usd",
                "days": days_ago,
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            prices = data.get("prices", [])

            if not prices:
                return None

            # Get price closest to hours_ago
            target_timestamp = (datetime.utcnow() - timedelta(hours=hours_ago)).timestamp() * 1000
            closest_price = min(prices, key=lambda x: abs(x[0] - target_timestamp))

            return closest_price[1]

        except Exception as e:
            logger.error(f"Error fetching historical price: {e}")
            return None

    def estimate_volume_from_reserves(
        self,
        pool_address: str,
        window_hours: int = 24,
    ) -> float:
        """
        Estimate trading volume from reserve changes

        This is a fallback when The Graph data is unavailable

        Args:
            pool_address: Pool address
            window_hours: Time window

        Returns:
            Estimated volume in USD
        """
        try:
            # Get current reserves
            reserves = self.get_pool_reserves(pool_address)
            if not reserves:
                return 0.0

            # Get token info
            tokens = self.get_pool_tokens(pool_address)
            if not tokens:
                return 0.0

            # Get token prices
            price0 = self.get_token_price(tokens["token0"]["address"])
            price1 = self.get_token_price(tokens["token1"]["address"])

            if not price0 or not price1:
                return 0.0

            # Calculate TVL
            reserve0_normalized = reserves["reserve0"] / (10 ** tokens["token0"]["decimals"])
            reserve1_normalized = reserves["reserve1"] / (10 ** tokens["token1"]["decimals"])

            tvl = (reserve0_normalized * price0) + (reserve1_normalized * price1)

            # Estimate volume as multiple of TVL
            # This is a rough heuristic: daily volume ~= 0.5x to 2x TVL for active pools
            # Use 1x as default estimate
            volume_multiplier = 1.0

            # Adjust for window
            estimated_volume = tvl * volume_multiplier * (window_hours / 24)

            logger.info(f"Estimated volume for {pool_address}: ${estimated_volume:,.2f}")

            return estimated_volume

        except Exception as e:
            logger.error(f"Error estimating volume: {e}")
            return 0.0

    def calculate_tvl(self, pool_address: str) -> Optional[float]:
        """
        Calculate current TVL from reserves and prices

        Args:
            pool_address: Pool address

        Returns:
            TVL in USD
        """
        try:
            # Get reserves
            reserves = self.get_pool_reserves(pool_address)
            if not reserves:
                return None

            # Get tokens
            tokens = self.get_pool_tokens(pool_address)
            if not tokens:
                return None

            # Get prices
            price0 = self.get_token_price(tokens["token0"]["address"])
            price1 = self.get_token_price(tokens["token1"]["address"])

            if not price0 or not price1:
                return None

            # Calculate TVL
            reserve0_normalized = reserves["reserve0"] / (10 ** tokens["token0"]["decimals"])
            reserve1_normalized = reserves["reserve1"] / (10 ** tokens["token1"]["decimals"])

            tvl = (reserve0_normalized * price0) + (reserve1_normalized * price1)

            return tvl

        except Exception as e:
            logger.error(f"Error calculating TVL: {e}")
            return None

    def detect_pool_type(self, pool_address: str) -> str:
        """
        Detect pool type (Uniswap V2, V3, Balancer, Curve, etc.)

        Args:
            pool_address: Pool address

        Returns:
            Pool type string
        """
        try:
            pool_address = Web3.to_checksum_address(pool_address)

            # Try V2
            try:
                pool_contract = self.w3.eth.contract(address=pool_address, abi=UNISWAP_V2_PAIR_ABI)
                pool_contract.functions.getReserves().call()
                return "uniswap-v2"
            except:
                pass

            # Try V3
            try:
                pool_contract = self.w3.eth.contract(address=pool_address, abi=UNISWAP_V3_POOL_ABI)
                pool_contract.functions.liquidity().call()
                return "uniswap-v3"
            except:
                pass

            return "unknown"

        except Exception as e:
            logger.error(f"Error detecting pool type: {e}")
            return "unknown"

    def get_fee_tier(self, pool_address: str, pool_type: str) -> float:
        """
        Get fee tier for the pool

        Args:
            pool_address: Pool address
            pool_type: Type of pool

        Returns:
            Fee as decimal (e.g., 0.003 for 0.3%)
        """
        try:
            if pool_type == "uniswap-v3":
                pool_address = Web3.to_checksum_address(pool_address)
                pool_contract = self.w3.eth.contract(address=pool_address, abi=UNISWAP_V3_POOL_ABI)
                fee_raw = pool_contract.functions.fee().call()
                # V3 fee is in hundredths of a bip (1 bip = 0.01%)
                return fee_raw / 1_000_000

            # Default for V2, SushiSwap
            elif pool_type in ["uniswap-v2", "sushiswap"]:
                return 0.003  # 0.3%

            # Curve typically lower fees
            elif pool_type == "curve":
                return 0.0004  # 0.04% typical

            # Balancer varies
            elif pool_type == "balancer":
                return 0.003  # Default

            return 0.003  # Default fallback

        except Exception as e:
            logger.error(f"Error getting fee tier: {e}")
            return 0.003
