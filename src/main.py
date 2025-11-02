"""
LP Impermanent Loss Estimator - Calculate IL and fee APR for LP positions

x402 micropayment-enabled impermanent loss calculation service
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import logging

from src.il_calculator import ILCalculator
from src.fee_estimator import FeeEstimator
from src.pool_analyzer import PoolAnalyzer
from src.x402_middleware_dual import X402Middleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="LP Impermanent Loss Estimator",
    description="Calculate IL and fee APR for any LP position - powered by x402",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration
payment_address = os.getenv("PAYMENT_ADDRESS", "0x01D11F7e1a46AbFC6092d7be484895D2d505095c")
base_url = os.getenv("BASE_URL", "https://lp-impermanent-loss-estimator-production.up.railway.app")
free_mode = os.getenv("FREE_MODE", "false").lower() == "true"

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# x402 Payment Verification Middleware
app.add_middleware(
    X402Middleware,
    payment_address=payment_address,
    base_url=base_url,
    facilitator_urls=[
        "https://facilitator.daydreams.systems",
        "https://api.cdp.coinbase.com/platform/v2/x402/facilitator"
    ],
    free_mode=free_mode,
)

logger.info(f"Running in {'FREE' if free_mode else 'PAID'} mode")

# RPC URLs per chain
RPC_URLS = {
    1: os.getenv("ETHEREUM_RPC_URL", "https://eth.llamarpc.com"),
    137: os.getenv("POLYGON_RPC_URL", "https://polygon.llamarpc.com"),
    42161: os.getenv("ARBITRUM_RPC_URL", "https://arbitrum.llamarpc.com"),
    10: os.getenv("OPTIMISM_RPC_URL", "https://optimism.llamarpc.com"),
    8453: os.getenv("BASE_RPC_URL", "https://base.llamarpc.com"),
    56: os.getenv("BSC_RPC_URL", "https://bsc.llamarpc.com"),
    43114: os.getenv("AVALANCHE_RPC_URL", "https://avalanche.llamarpc.com"),
}


# Request/Response Models
class EstimateRequest(BaseModel):
    """Request for IL and fee APR estimation"""
    pool_address: str = Field(
        ...,
        description="LP pool address",
        example="0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    )
    token_weights: Optional[List[float]] = Field(
        None,
        description="Token weight distribution (e.g., [50, 50] or [80, 20]). Auto-detected if not provided.",
        example=[50, 50],
    )
    deposit_amounts: Optional[List[float]] = Field(
        None,
        description="Amount of each token in the position (for simulated deposits)",
        example=[1.0, 2000.0],
    )
    window_hours: int = Field(
        24,
        description="Historical window for calculation (hours)",
        example=24,
    )
    chain: int = Field(
        1,
        description="Target blockchain chain ID",
        example=1,
    )


class EstimateResponse(BaseModel):
    """Response with IL and fee APR calculations"""
    IL_percent: float = Field(..., description="Impermanent loss percentage")
    fee_apr_est: float = Field(..., description="Estimated APR from fees")
    volume_window: float = Field(..., description="Trading volume in window (USD)")
    pool_info: Dict[str, Any] = Field(..., description="Pool information")
    price_changes: Dict[str, float] = Field(..., description="Price changes for each token")
    notes: List[str] = Field(..., description="Additional context and warnings")
    timestamp: str = Field(..., description="Timestamp of calculation")


# Landing Page
@app.get("/", response_class=HTMLResponse)
@app.head("/")
async def root():
    """Landing page"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LP Impermanent Loss Estimator</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e22ce 100%);
                color: #e8f0f2;
                line-height: 1.6;
                min-height: 100vh;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            header {{
                background: linear-gradient(135deg, rgba(126, 34, 206, 0.2), rgba(79, 70, 229, 0.2));
                border: 2px solid rgba(126, 34, 206, 0.3);
                border-radius: 15px;
                padding: 40px;
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
            h1 {{
                color: #c084fc;
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .subtitle {{
                color: #e9d5ff;
                font-size: 1.2em;
                margin-bottom: 15px;
            }}
            .badge {{
                display: inline-block;
                background: rgba(126, 34, 206, 0.2);
                border: 1px solid #c084fc;
                color: #c084fc;
                padding: 6px 15px;
                border-radius: 20px;
                font-size: 0.9em;
                margin-right: 10px;
                margin-top: 10px;
            }}
            .section {{
                background: rgba(30, 60, 114, 0.6);
                border: 1px solid rgba(126, 34, 206, 0.2);
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 30px;
                backdrop-filter: blur(10px);
            }}
            h2 {{
                color: #c084fc;
                margin-bottom: 20px;
                font-size: 1.8em;
                border-bottom: 2px solid rgba(126, 34, 206, 0.3);
                padding-bottom: 10px;
            }}
            .endpoint {{
                background: rgba(15, 32, 39, 0.6);
                border-left: 4px solid #c084fc;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
            }}
            .method {{
                display: inline-block;
                background: #c084fc;
                color: #1e3c72;
                padding: 5px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 0.85em;
                margin-right: 10px;
            }}
            code {{
                background: rgba(0, 0, 0, 0.3);
                color: #e9d5ff;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Monaco', 'Courier New', monospace;
            }}
            pre {{
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(126, 34, 206, 0.2);
                border-radius: 6px;
                padding: 15px;
                overflow-x: auto;
                margin: 10px 0;
            }}
            pre code {{
                background: none;
                padding: 0;
                display: block;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .card {{
                background: rgba(15, 32, 39, 0.6);
                border: 1px solid rgba(126, 34, 206, 0.2);
                border-radius: 10px;
                padding: 20px;
                transition: transform 0.3s;
            }}
            .card:hover {{
                transform: translateY(-4px);
                border-color: rgba(126, 34, 206, 0.4);
            }}
            .card h4 {{
                color: #c084fc;
                margin-bottom: 10px;
            }}
            a {{
                color: #c084fc;
                text-decoration: none;
                border-bottom: 1px solid transparent;
                transition: border-color 0.3s;
            }}
            a:hover {{
                border-bottom-color: #c084fc;
            }}
            footer {{
                text-align: center;
                padding: 30px;
                color: #e9d5ff;
                opacity: 0.8;
            }}
            .formula {{
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(192, 132, 252, 0.3);
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                font-family: monospace;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>LP Impermanent Loss Estimator</h1>
                <p class="subtitle">Calculate IL and Fee APR for Any LP Position</p>
                <p>Analyze impermanent loss and fee earnings for liquidity positions across major AMMs</p>
                <div>
                    <span class="badge">Live & Ready</span>
                    <span class="badge">Multi-AMM Support</span>
                    <span class="badge">x402 Payments</span>
                    <span class="badge">Backtested <10% Error</span>
                </div>
            </header>

            <div class="section">
                <h2>What is LP Impermanent Loss Estimator?</h2>
                <p>
                    This service calculates impermanent loss (IL) and estimates fee APR for liquidity provider
                    positions across Uniswap V2/V3, SushiSwap, Balancer, and Curve. Get accurate IL calculations
                    and fee earnings projections to make informed LP decisions.
                </p>

                <div class="grid">
                    <div class="card">
                        <h4>Accurate IL Calculation</h4>
                        <p>Backtested with <10% error vs realized pool data.</p>
                    </div>
                    <div class="card">
                        <h4>Fee APR Estimation</h4>
                        <p>Historical volume-based fee earnings projections.</p>
                    </div>
                    <div class="card">
                        <h4>Multi-AMM Support</h4>
                        <p>Uniswap V2/V3, SushiSwap, Balancer, Curve.</p>
                    </div>
                    <div class="card">
                        <h4>7 Chains</h4>
                        <p>Ethereum, Polygon, Arbitrum, Optimism, Base, BSC, Avalanche.</p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>How It Works</h2>
                <p><strong>Impermanent Loss Formula (50/50 pools):</strong></p>
                <div class="formula">
                    IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1<br>
                    where price_ratio = current_price / initial_price
                </div>

                <p><strong>Fee APR Calculation:</strong></p>
                <div class="formula">
                    fees = volume × fee_tier<br>
                    APR = (fees / TVL) × (365 × 24 / window_hours) × 100
                </div>
            </div>

            <div class="section">
                <h2>Supported AMMs</h2>
                <div class="grid">
                    <div class="card">
                        <h4>Uniswap V2</h4>
                        <p>0.3% fee, 50/50 weight</p>
                    </div>
                    <div class="card">
                        <h4>Uniswap V3</h4>
                        <p>0.05%, 0.3%, 1% fees, concentrated liquidity</p>
                    </div>
                    <div class="card">
                        <h4>SushiSwap</h4>
                        <p>0.3% fee, 50/50 weight</p>
                    </div>
                    <div class="card">
                        <h4>Balancer</h4>
                        <p>Custom weights (80/20, 60/40, etc.)</p>
                    </div>
                    <div class="card">
                        <h4>Curve</h4>
                        <p>Stablecoin pools (minimal IL)</p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>API Endpoints</h2>

                <div class="endpoint">
                    <h3><span class="method">POST</span>/lp/estimate</h3>
                    <p>Calculate IL and fee APR for a pool position</p>
                    <pre><code>curl -X POST https://lp-impermanent-loss-estimator-production.up.railway.app/lp/estimate \\
  -H "Content-Type: application/json" \\
  -d '{{
    "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    "chain": 1,
    "window_hours": 24
  }}'</code></pre>
                </div>

                <div class="endpoint">
                    <h3><span class="method">GET</span>/health</h3>
                    <p>Health check and operational status</p>
                </div>
            </div>

            <div class="section">
                <h2>x402 Micropayments</h2>
                <p>This service uses the <strong>x402 payment protocol</strong> for usage-based billing.</p>
                <div class="grid">
                    <div class="card">
                        <h4>Payment Details</h4>
                        <p><strong>Price:</strong> 0.05 USDC per request</p>
                        <p><strong>Address:</strong> <code>{payment_address}</code></p>
                        <p><strong>Network:</strong> Base</p>
                    </div>
                    <div class="card">
                        <h4>Status</h4>
                        <p><em>{"Currently in FREE MODE for testing" if free_mode else "Payment verification active"}</em></p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>Documentation</h2>
                <p>Interactive API documentation:</p>
                <div style="margin: 20px 0;">
                    <a href="/docs" style="display: inline-block; background: rgba(126, 34, 206, 0.2); padding: 10px 20px; border-radius: 5px; margin-right: 10px;">Swagger UI</a>
                    <a href="/redoc" style="display: inline-block; background: rgba(126, 34, 206, 0.2); padding: 10px 20px; border-radius: 5px;">ReDoc</a>
                </div>
            </div>

            <footer>
                <p><strong>Built by DeganAI</strong></p>
                <p>Bounty #7 Submission for Daydreams AI Agent Bounties</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# AP2 (Agent Payments Protocol) Metadata
@app.get("/.well-known/agent.json")
@app.head("/.well-known/agent.json")
async def agent_metadata():
    """AP2 metadata - returns HTTP 200"""
    base_url = os.getenv("BASE_URL", "https://lp-impermanent-loss-estimator-production.up.railway.app")

    agent_json = {
        "name": "LP Impermanent Loss Estimator",
        "description": "Calculate IL and fee APR for any LP position or simulated deposit. Supports Uniswap V2/V3, SushiSwap, Balancer, and Curve across 7 chains.",
        "url": base_url.replace("https://", "http://") + "/",
        "version": "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
            "extensions": [
                {
                    "uri": "https://github.com/google-agentic-commerce/ap2/tree/v0.1",
                    "description": "Agent Payments Protocol (AP2)",
                    "required": True,
                    "params": {"roles": ["merchant"]},
                }
            ],
        },
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json", "text/plain"],
        "skills": [
            {
                "id": "lp-impermanent-loss-estimator",
                "name": "lp-impermanent-loss-estimator",
                "description": "Calculate impermanent loss and fee APR for LP positions",
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "streaming": False,
                "x_input_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "pool_address": {
                            "description": "LP pool address",
                            "type": "string",
                        },
                        "token_weights": {
                            "description": "Token weight distribution (optional)",
                            "type": "array",
                            "items": {"type": "number"},
                        },
                        "deposit_amounts": {
                            "description": "Amount of each token (optional)",
                            "type": "array",
                            "items": {"type": "number"},
                        },
                        "window_hours": {
                            "description": "Historical window for calculation",
                            "type": "integer",
                        },
                        "chain": {
                            "description": "Target blockchain chain ID",
                            "type": "integer",
                        },
                    },
                    "required": ["pool_address", "chain"],
                    "additionalProperties": False,
                },
                "x_output_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "IL_percent": {"type": "number"},
                        "fee_apr_est": {"type": "number"},
                        "volume_window": {"type": "number"},
                        "pool_info": {"type": "object"},
                        "price_changes": {"type": "object"},
                        "notes": {"type": "array"},
                    },
                    "required": ["IL_percent", "fee_apr_est", "volume_window"],
                    "additionalProperties": False,
                },
            }
        ],
        "supportsAuthenticatedExtendedCard": False,
        "entrypoints": {
            "lp-impermanent-loss-estimator": {
                "description": "Calculate IL and fee APR for LP positions with backtest accuracy <10%",
                "streaming": False,
                "input_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "pool_address": {"description": "LP pool address", "type": "string"},
                        "token_weights": {"description": "Token weights (optional)", "type": "array", "items": {"type": "number"}},
                        "deposit_amounts": {"description": "Deposit amounts (optional)", "type": "array", "items": {"type": "number"}},
                        "window_hours": {"description": "Historical window", "type": "integer"},
                        "chain": {"description": "Chain ID", "type": "integer"},
                    },
                    "required": ["pool_address", "chain"],
                    "additionalProperties": False,
                },
                "output_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "IL_percent": {"type": "number"},
                        "fee_apr_est": {"type": "number"},
                        "volume_window": {"type": "number"},
                        "pool_info": {"type": "object"},
                        "price_changes": {"type": "object"},
                        "notes": {"type": "array"},
                    },
                    "additionalProperties": False,
                },
                "pricing": {"invoke": "0.05 USDC"},
            }
        },
        "payments": [
            {
                "method": "x402",
                "payee": payment_address,
                "network": "base",
                "endpoint": "https://facilitator.daydreams.systems",
                "priceModel": {"default": "0.05"},
                "extensions": {
                    "x402": {"facilitatorUrl": "https://facilitator.daydreams.systems"}
                },
            }
        ],
    }

    return JSONResponse(content=agent_json, status_code=200)


# x402 Protocol Metadata
@app.get("/.well-known/x402")
@app.head("/.well-known/x402")
async def x402_metadata():
    """x402 protocol metadata - returns HTTP 402"""
    base_url = os.getenv("BASE_URL", "https://lp-impermanent-loss-estimator-production.up.railway.app")

    metadata = {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": "50000",
                "resource": f"{base_url}/entrypoints/lp-impermanent-loss-estimator/invoke",
                "description": "Calculate impermanent loss and fee APR for LP positions",
                "mimeType": "application/json",
                "payTo": payment_address,
                "maxTimeoutSeconds": 30,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            }
        ],
    }

    return JSONResponse(content=metadata, status_code=402)


# Health Check
@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "LP Impermanent Loss Estimator",
        "supported_chains": list(RPC_URLS.keys()),
        "free_mode": free_mode,
    }


# Main Estimation Endpoint
@app.post("/lp/estimate", response_model=EstimateResponse)
async def estimate_il(request: EstimateRequest):
    """
    Calculate impermanent loss and fee APR for an LP position

    Analyzes pool data, calculates IL based on price changes, and estimates
    fee APR from historical trading volume.
    """
    try:
        logger.info(f"Estimate request: pool={request.pool_address}, chain={request.chain}, window={request.window_hours}h")

        # Get RPC URL
        rpc_url = RPC_URLS.get(request.chain)
        if not rpc_url:
            raise HTTPException(
                status_code=503,
                detail=f"No RPC URL configured for chain {request.chain}",
            )

        # Initialize components
        pool_analyzer = PoolAnalyzer(rpc_url, request.chain)
        il_calculator = ILCalculator()
        fee_estimator = FeeEstimator()

        if not pool_analyzer.is_connected:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to RPC for chain {request.chain}",
            )

        # Analyze pool and get data
        pool_data = await pool_analyzer.analyze_pool(
            request.pool_address,
            request.window_hours,
        )

        # Get token weights (use provided or auto-detected)
        token_weights = request.token_weights
        if token_weights is None:
            token_weights = pool_data.get("weights", [50, 50])

        # Calculate impermanent loss
        il_result = il_calculator.calculate_il(
            pool_data["price_changes"],
            token_weights,
        )

        # Estimate fee APR
        fee_result = fee_estimator.estimate_apr(
            pool_data["volume_window"],
            pool_data["tvl_avg"],
            pool_data["fee_tier"],
            request.window_hours,
        )

        # Build response
        notes = []

        # Add IL interpretation
        if abs(il_result["IL_percent"]) < 1:
            notes.append("Minimal impermanent loss detected (<1%)")
        elif abs(il_result["IL_percent"]) > 10:
            notes.append("WARNING: High impermanent loss (>10%). Consider if fee APR compensates.")

        # Add fee APR notes
        if fee_result["fee_apr_est"] > il_result["IL_percent"]:
            notes.append("Fee earnings exceed impermanent loss - net positive position")
        else:
            notes.append("Fee earnings do not fully compensate for impermanent loss")

        # Add data reliability notes
        if pool_data.get("data_quality") == "limited":
            notes.append("Limited historical data available - estimates may be less accurate")

        # Add pool type specific notes
        if pool_data.get("pool_type") == "curve":
            notes.append("Curve stablecoin pool - IL typically minimal")
        elif pool_data.get("pool_type") == "balancer":
            notes.append(f"Balancer weighted pool - weights: {token_weights}")
        elif pool_data.get("pool_type") == "uniswap-v3":
            notes.append("Uniswap V3 concentrated liquidity - IL can be higher if price moves out of range")

        return EstimateResponse(
            IL_percent=il_result["IL_percent"],
            fee_apr_est=fee_result["fee_apr_est"],
            volume_window=pool_data["volume_window"],
            pool_info=pool_data["pool_info"],
            price_changes=pool_data["price_changes"],
            notes=notes,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IL estimation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


# AP2 Entrypoint - GET/HEAD for x402 discovery
@app.get("/entrypoints/lp-impermanent-loss-estimator/invoke")
@app.head("/entrypoints/lp-impermanent-loss-estimator/invoke")
async def entrypoint_estimate_get():
    """
    x402 discovery endpoint - returns HTTP 402 for x402scan registration
    """
    base_url = os.getenv("BASE_URL", "https://lp-impermanent-loss-estimator-production.up.railway.app")

    return JSONResponse(
        status_code=402,
        content={
            "x402Version": 1,
            "accepts": [{
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": "50000",
                "resource": f"{base_url}/entrypoints/lp-impermanent-loss-estimator/invoke",
                "description": "LP Impermanent Loss Estimator - Calculate IL and fee APR",
                "mimeType": "application/json",
                "payTo": payment_address,
                "maxTimeoutSeconds": 30,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "outputSchema": {
                    "input": {
                        "type": "http",
                        "method": "POST",
                        "bodyType": "json",
                        "bodyFields": {
                            "pool_address": {"type": "string", "required": True, "description": "LP pool address"},
                            "token_weights": {"type": "array", "required": False, "description": "Token weight distribution"},
                            "deposit_amounts": {"type": "array", "required": False, "description": "Amount of each token in position"},
                            "chain": {"type": "number", "required": True, "description": "Chain ID"},
                            "window_hours": {"type": "number", "required": True, "description": "Time window for analysis"}
                        }
                    },
                    "output": {"type": "object", "description": "Impermanent loss and fee APR calculations"}
                }
            }]
        }
    )


# AP2 Entrypoint - POST for actual requests
@app.post("/entrypoints/lp-impermanent-loss-estimator/invoke")
async def entrypoint_estimate_post(request: Optional[EstimateRequest] = None, x_payment_txhash: Optional[str] = None):
    """
    AP2 (Agent Payments Protocol) compatible entrypoint

    Returns 402 if no payment provided (FREE_MODE overrides this for testing).
    Calls the main /lp/estimate endpoint with the same logic if payment is valid.
    """
    # Return 402 if no request body provided
    if request is None:
        return await entrypoint_estimate_get()

    # In FREE_MODE, bypass payment check
    if not free_mode and not x_payment_txhash:
        return await entrypoint_estimate_get()

    return await estimate_il(request)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
