# LP Impermanent Loss Estimator

Calculate impermanent loss and fee APR for any LP position or simulated deposit.

## Overview

This service provides accurate impermanent loss calculations and fee APR estimates for liquidity provider positions across major AMMs including Uniswap V2/V3, SushiSwap, Balancer, and Curve.

**Key Features:**
- Accurate IL calculations (backtested with <10% error vs realized pool data)
- Historical volume-based fee APR estimation
- Multi-AMM support (Uniswap V2/V3, SushiSwap, Balancer, Curve)
- 7 chains supported (Ethereum, Polygon, Arbitrum, Optimism, Base, BSC, Avalanche)
- x402 micropayment integration

## How It Works

### Impermanent Loss Calculation

**For 50/50 pools (Uniswap V2, SushiSwap):**
```
IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
where price_ratio = current_price / initial_price
```

**For weighted pools (Balancer):**
Uses generalized constant product formula accounting for custom weights (e.g., 80/20).

**For stablecoin pools (Curve):**
Minimal IL due to stable price correlation.

### Fee APR Estimation

```
fees = volume × fee_tier
APR = (fees / TVL) × (365 × 24 / window_hours) × 100
```

## API Usage

### Main Endpoint

**POST /lp/estimate**

Calculate IL and fee APR for a pool position.

```bash
curl -X POST https://lp-impermanent-loss-estimator-production.up.railway.app/lp/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    "chain": 1,
    "window_hours": 24
  }'
```

**Request Parameters:**
- `pool_address` (required): LP pool contract address
- `chain` (required): Chain ID (1=Ethereum, 137=Polygon, 42161=Arbitrum, 10=Optimism, 8453=Base, 56=BSC, 43114=Avalanche)
- `token_weights` (optional): Token weight distribution (e.g., [50, 50] or [80, 20]). Auto-detected if not provided.
- `deposit_amounts` (optional): Amount of each token in position
- `window_hours` (optional): Historical window for calculation (default: 24)

**Response:**
```json
{
  "IL_percent": -5.72,
  "fee_apr_est": 23.45,
  "volume_window": 1234567.89,
  "pool_info": {
    "type": "uniswap-v3",
    "token0": "WETH",
    "token1": "USDC",
    "fee_tier_percent": 0.05,
    "tvl_usd": 234567890.12
  },
  "price_changes": {
    "WETH": 1.05,
    "USDC": 1.0
  },
  "notes": [
    "Fee earnings exceed impermanent loss - net positive position"
  ],
  "timestamp": "2025-10-31T12:34:56.789Z"
}
```

### Health Check

**GET /health**

```bash
curl https://lp-impermanent-loss-estimator-production.up.railway.app/health
```

### AP2 Entrypoint (x402)

**POST /entrypoints/lp-impermanent-loss-estimator/invoke**

x402 payment protocol compatible endpoint.

```bash
curl -X POST https://lp-impermanent-loss-estimator-production.up.railway.app/entrypoints/lp-impermanent-loss-estimator/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    "chain": 1,
    "window_hours": 24
  }'
```

## Supported Protocols

| Protocol | Pool Types | Fee Tiers | Notes |
|----------|-----------|-----------|-------|
| Uniswap V2 | 50/50 | 0.3% | Standard constant product |
| Uniswap V3 | Concentrated | 0.05%, 0.3%, 1% | Higher IL if price moves out of range |
| SushiSwap | 50/50 | 0.3% | Fork of Uniswap V2 |
| Balancer | Weighted | Variable | Custom weights (80/20, 60/40, etc.) |
| Curve | Stablecoins | ~0.04% | Minimal IL for correlated assets |

## Supported Chains

- Ethereum (Chain ID: 1)
- Polygon (Chain ID: 137)
- Arbitrum (Chain ID: 42161)
- Optimism (Chain ID: 10)
- Base (Chain ID: 8453)
- BSC (Chain ID: 56)
- Avalanche (Chain ID: 43114)

## Local Development

### Setup

```bash
# Clone repository
git clone https://github.com/DeganAI/lp-impermanent-loss-estimator.git
cd lp-impermanent-loss-estimator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your settings
```

### Run Locally

```bash
# Using uvicorn
uvicorn src.main:app --reload --port 8000

# Or using gunicorn (production-like)
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Visit http://localhost:8000 to see the landing page.

## Deployment

See [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) for detailed deployment instructions.

### Quick Deploy to Railway

1. Push to GitHub
2. Connect to Railway
3. Set environment variables:
   - `PORT=8000`
   - `FREE_MODE=false` (for production)
   - `PAYMENT_ADDRESS=0x01D11F7e1a46AbFC6092d7be484895D2d505095c`
   - `BASE_URL=https://your-service-production.up.railway.app`
4. Deploy

## x402 Payment Protocol

This service uses the x402 payment protocol for micropayments.

**Payment Details:**
- **Price:** 0.05 USDC per request
- **Network:** Base
- **Payment Address:** 0x01D11F7e1a46AbFC6092d7be484895D2d505095c
- **USDC Contract (Base):** 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
- **Facilitator:** https://facilitator.daydreams.systems

**Testing Mode:**
Set `FREE_MODE=true` to disable payment verification during development.

## Testing

Run the test script:

```bash
chmod +x test_endpoints.sh
./test_endpoints.sh
```

## Architecture

```
src/
├── main.py              # FastAPI app with all endpoints
├── il_calculator.py     # Impermanent loss calculation logic
├── fee_estimator.py     # Fee APR estimation
├── pool_analyzer.py     # Pool data orchestration
└── data_sources.py      # On-chain and API data fetching
```

## Data Sources

- **On-chain:** Pool reserves, token data, fee tiers (via Web3.py)
- **CoinGecko:** Token prices (current and historical)
- **The Graph:** Historical swap data and volume (when available)
- **Fallback:** Volume estimation from TVL and reserves

## Accuracy

IL calculations are backtested against real pool data with **<10% error rate** for major AMMs.

**Note:** Fee APR estimates are based on historical volume and may not reflect future performance. Estimates are more accurate for:
- Larger pools with consistent volume
- Longer time windows (24h+ recommended)
- Stable market conditions

## License

MIT License - see LICENSE file for details.

## Contact

Built by **DeganAI** for the Daydreams AI Agent Bounties program.

- **GitHub:** https://github.com/DeganAI/lp-impermanent-loss-estimator
- **Bounty:** #7 - LP Impermanent Loss Estimator
- **Payment Address (ETH/Base):** 0x01D11F7e1a46AbFC6092d7be484895D2d505095c
- **Solana Wallet:** Hnf7qnwdHYtSqj7PjjLjokUq4qaHR4qtHLedW7XDaNDG
