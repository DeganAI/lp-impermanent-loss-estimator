# Production Setup Guide

Complete guide for deploying LP Impermanent Loss Estimator to production.

## Pre-Deployment Checklist

- [ ] Code pushed to GitHub repository
- [ ] Railway account created
- [ ] Environment variables prepared
- [ ] Payment address verified
- [ ] x402scan account ready for registration

## Step 1: GitHub Repository Setup

### Create Repository

```bash
# Initialize git (if not already done)
cd lp-impermanent-loss-estimator
git init

# Add remote
git remote add origin https://github.com/DeganAI/lp-impermanent-loss-estimator.git

# Commit and push
git add .
git commit -m "Initial commit: LP Impermanent Loss Estimator"
git push -u origin main
```

## Step 2: Railway Deployment

### Create New Project

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `DeganAI/lp-impermanent-loss-estimator`

### Configure Environment Variables

In Railway dashboard, add these variables:

```
PORT=8000
FREE_MODE=false
PAYMENT_ADDRESS=0x01D11F7e1a46AbFC6092d7be484895D2d505095c
BASE_URL=https://lp-impermanent-loss-estimator-production.up.railway.app
```

**Optional RPC URLs** (for better reliability):
```
ETHEREUM_RPC_URL=https://eth.llamarpc.com
POLYGON_RPC_URL=https://polygon.llamarpc.com
ARBITRUM_RPC_URL=https://arbitrum.llamarpc.com
OPTIMISM_RPC_URL=https://optimism.llamarpc.com
BASE_RPC_URL=https://base.llamarpc.com
BSC_RPC_URL=https://bsc.llamarpc.com
AVALANCHE_RPC_URL=https://avalanche.llamarpc.com
```

### Deploy

Railway will automatically:
1. Detect the Dockerfile
2. Build the container
3. Deploy to production URL
4. Set up health checks

**Wait for deployment to complete** (usually 2-5 minutes).

## Step 3: Verify Deployment

### Test Endpoints

```bash
# Set your service URL
SERVICE_URL="https://lp-impermanent-loss-estimator-production.up.railway.app"

# 1. Check landing page (should return HTML)
curl -I $SERVICE_URL/

# 2. Check health endpoint (should return 200)
curl $SERVICE_URL/health

# 3. Check agent.json (should return 200)
curl -I $SERVICE_URL/.well-known/agent.json

# 4. Check x402 metadata (should return 402)
curl -I $SERVICE_URL/.well-known/x402

# 5. Check AP2 entrypoint (should return 402)
curl -I $SERVICE_URL/entrypoints/lp-impermanent-loss-estimator/invoke

# 6. Test main endpoint
curl -X POST $SERVICE_URL/lp/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    "chain": 1,
    "window_hours": 24
  }'
```

### Verify Response Codes

✅ **Expected Results:**
- `/` - HTTP 200 (HTML page)
- `/health` - HTTP 200 (JSON)
- `/.well-known/agent.json` - HTTP 200 (JSON)
- `/.well-known/x402` - HTTP 402 (x402 metadata)
- `/entrypoints/lp-impermanent-loss-estimator/invoke` (GET) - HTTP 402
- `/lp/estimate` (POST with data) - HTTP 200 (in FREE_MODE) or 402 (without payment)

## Step 4: x402scan Registration

### Register Service

1. Go to https://www.x402scan.com/resources/register
2. Enter your endpoint URL:
   ```
   https://lp-impermanent-loss-estimator-production.up.railway.app/entrypoints/lp-impermanent-loss-estimator/invoke
   ```
3. Leave headers blank
4. Click "Add"

### Verify Registration

1. Check https://www.x402scan.com
2. Search for "LP Impermanent Loss Estimator"
3. Verify your service appears in the directory

**Common Issues:**
- If registration fails, verify the endpoint returns HTTP 402 with proper x402 schema
- Check that ALL required fields are present in the 402 response
- Ensure the response includes: `x402Version`, `scheme`, `network`, `maxAmountRequired`, `resource`, `description`, `mimeType`, `payTo`, `maxTimeoutSeconds`, `asset`

## Step 5: Production Testing

### Test with Real Pool Data

```bash
# Uniswap V3 WETH/USDC 0.05% pool (Ethereum)
curl -X POST $SERVICE_URL/lp/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    "chain": 1,
    "window_hours": 24
  }' | jq

# SushiSwap WETH/USDC pool (Ethereum)
curl -X POST $SERVICE_URL/lp/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "pool_address": "0x397FF1542f962076d0BFE58eA045FfA2d347ACa0",
    "chain": 1,
    "window_hours": 24
  }' | jq

# Uniswap V2 WETH/USDT pool (Ethereum)
curl -X POST $SERVICE_URL/lp/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "pool_address": "0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852",
    "chain": 1,
    "window_hours": 24
  }' | jq
```

### Verify Output

Check that responses include:
- ✅ `IL_percent` - Impermanent loss percentage
- ✅ `fee_apr_est` - Estimated fee APR
- ✅ `volume_window` - Trading volume
- ✅ `pool_info` - Pool details (type, tokens, fee tier, TVL)
- ✅ `price_changes` - Price change ratios
- ✅ `notes` - Context and warnings
- ✅ `timestamp` - ISO 8601 timestamp

## Step 6: Enable Payment Verification

### Switch to Paid Mode

In Railway dashboard, update environment variable:
```
FREE_MODE=false
```

Railway will automatically redeploy.

### Test Payment Flow

```bash
# Request without payment should return 402
curl -X POST $SERVICE_URL/entrypoints/lp-impermanent-loss-estimator/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    "chain": 1,
    "window_hours": 24
  }'

# Should return 402 with x402 payment schema
```

## Step 7: Monitoring

### Railway Logs

Monitor service logs in Railway dashboard:
1. Click on your service
2. Go to "Deployments" tab
3. Click on latest deployment
4. View logs

### Health Checks

Set up monitoring (optional):
- Use UptimeRobot or similar
- Monitor `/health` endpoint
- Alert on downtime

### Usage Metrics

Track in Railway dashboard:
- Request count
- Response times
- Error rates
- Resource usage (CPU, memory)

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | Yes | 8000 | Port for the service |
| `FREE_MODE` | No | false | Enable free testing mode |
| `PAYMENT_ADDRESS` | Yes | - | Base network payment address |
| `BASE_URL` | Yes | - | Your service URL |
| `ETHEREUM_RPC_URL` | No | llamarpc | Ethereum RPC endpoint |
| `POLYGON_RPC_URL` | No | llamarpc | Polygon RPC endpoint |
| `ARBITRUM_RPC_URL` | No | llamarpc | Arbitrum RPC endpoint |
| `OPTIMISM_RPC_URL` | No | llamarpc | Optimism RPC endpoint |
| `BASE_RPC_URL` | No | llamarpc | Base RPC endpoint |
| `BSC_RPC_URL` | No | llamarpc | BSC RPC endpoint |
| `AVALANCHE_RPC_URL` | No | llamarpc | Avalanche RPC endpoint |

## Troubleshooting

### Service Won't Start

1. Check Railway logs for errors
2. Verify all required environment variables are set
3. Check Dockerfile builds successfully locally:
   ```bash
   docker build -t lp-estimator .
   docker run -p 8000:8000 -e PORT=8000 -e FREE_MODE=true lp-estimator
   ```

### 402 Endpoint Not Working

1. Verify endpoint returns proper x402 schema:
   ```bash
   curl -s $SERVICE_URL/.well-known/x402 | jq
   ```
2. Check that ALL required fields are present
3. Verify `asset` address is correct for Base USDC
4. Check `payTo` address matches `PAYMENT_ADDRESS`

### x402scan Registration Failed

1. Confirm endpoint is publicly accessible
2. Verify GET request to entrypoint returns HTTP 402
3. Check response includes complete x402 schema
4. Try manual registration with full URL

### Price Data Not Loading

1. Check CoinGecko API limits (free tier: 10-50 calls/minute)
2. Verify RPC endpoints are responding
3. Check logs for API errors
4. Consider using paid RPC providers for better reliability

### IL Calculations Seem Wrong

1. Verify pool address is correct
2. Check that price data is loading (check logs)
3. Confirm pool type is detected correctly
4. For V3 pools, note that concentrated liquidity affects IL

## Performance Optimization

### RPC Providers

For production, consider using:
- **Alchemy** (Ethereum, Polygon, Arbitrum, Optimism, Base)
- **Infura** (Ethereum, Polygon, Arbitrum, Optimism)
- **QuickNode** (multi-chain)

Set custom RPC URLs in environment variables.

### Caching

Consider implementing:
- Redis for price data caching
- In-memory caching for pool metadata
- Rate limiting for external APIs

### Scaling

Railway auto-scales, but for high traffic:
1. Increase worker count in Dockerfile
2. Enable horizontal scaling in Railway
3. Add load balancer if needed

## Security Best Practices

1. ✅ Never commit `.env` file
2. ✅ Use environment variables for secrets
3. ✅ Validate all user inputs
4. ✅ Rate limit API endpoints
5. ✅ Monitor for suspicious activity
6. ✅ Keep dependencies updated
7. ✅ Use HTTPS only (Railway handles this)

## Support

For issues:
1. Check Railway logs first
2. Review this guide
3. Test endpoints with provided curl commands
4. Open issue on GitHub if problem persists

## Deployment Checklist

- [ ] Service deployed to Railway
- [ ] All environment variables configured
- [ ] Health check passing
- [ ] Landing page accessible
- [ ] `/.well-known/agent.json` returns 200
- [ ] `/.well-known/x402` returns 402
- [ ] Entrypoint returns 402 on GET
- [ ] Main endpoint works with test data
- [ ] Service registered on x402scan
- [ ] Payment mode enabled (FREE_MODE=false)
- [ ] Logs monitored for errors
- [ ] Documentation updated with live URL

## Success Criteria

Your service is production-ready when:

✅ All endpoints respond correctly
✅ Registered and visible on x402scan
✅ IL calculations return accurate results (<10% error)
✅ Fee APR estimates are reasonable
✅ Payment verification works (when FREE_MODE=false)
✅ No errors in Railway logs
✅ Response times < 5 seconds for most requests

---

**Congratulations!** Your LP Impermanent Loss Estimator is now live in production.
