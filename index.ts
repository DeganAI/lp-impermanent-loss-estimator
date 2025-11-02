import { createAgentApp } from '@lucid-dreams/agent-kit';
import { Hono } from 'hono';

console.log('[STARTUP] ===== LP IMPERMANENT LOSS ESTIMATOR =====');

const PORT = parseInt(process.env.PORT || '3000', 10);
const HOST = '0.0.0.0';
const FACILITATOR_URL = process.env.FACILITATOR_URL || 'https://facilitator.cdp.coinbase.com';
const WALLET_ADDRESS = process.env.ADDRESS || '0x01D11F7e1a46AbFC6092d7be484895D2d505095c';
const NETWORK = process.env.NETWORK || 'base';

interface ILResult {
  il_percentage: number;
  il_usd: number;
  initial_value_usd: number;
  current_value_usd: number;
  hodl_value_usd: number;
  fee_apr: number;
  net_apr: number;
  recommendation: string;
}

function calculateImpermanentLoss(priceRatio: number, initialPrice0: number, initialPrice1: number, amount0: number, amount1: number, feesEarned: number, daysHeld: number): ILResult {
  const k = amount0 * amount1;
  const newAmount0 = Math.sqrt(k / priceRatio);
  const newAmount1 = Math.sqrt(k * priceRatio);

  const initialValue = amount0 * initialPrice0 + amount1 * initialPrice1;
  const currentValue = newAmount0 * initialPrice0 * priceRatio + newAmount1 * initialPrice1;
  const hodlValue = amount0 * initialPrice0 * priceRatio + amount1 * initialPrice1;

  const ilUsd = currentValue - hodlValue;
  const ilPercentage = (ilUsd / hodlValue) * 100;

  const annualFees = (feesEarned / daysHeld) * 365;
  const feeApr = (annualFees / initialValue) * 100;
  const netApr = feeApr + (ilPercentage / daysHeld) * 365;

  let recommendation = 'Monitor position';
  if (ilPercentage < -5 && feeApr < Math.abs(ilPercentage)) {
    recommendation = 'Consider exiting - IL exceeds fee earnings';
  } else if (netApr > 10) {
    recommendation = 'Strong position - fees outpace IL';
  }

  return {
    il_percentage: ilPercentage,
    il_usd: ilUsd,
    initial_value_usd: initialValue,
    current_value_usd: currentValue + feesEarned,
    hodl_value_usd: hodlValue,
    fee_apr: feeApr,
    net_apr: netApr,
    recommendation,
  };
}

const app = createAgentApp({
  name: 'LP Impermanent Loss Estimator',
  description: 'Calculate IL and fee APR for LP positions',
  version: '1.0.0',
  paymentsConfig: {
    facilitatorUrl: FACILITATOR_URL,
    address: WALLET_ADDRESS as `0x${string}`,
    network: NETWORK,
    defaultPrice: '$0.04',
  },
});

const honoApp = app.app;

honoApp.get('/health', (c) => c.json({ status: 'ok', service: 'LP Impermanent Loss Estimator' }));

honoApp.get('/og-image.png', (c) => {
  const svg = `<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <rect width="1200" height="630" fill="#0f3460"/>
  <text x="600" y="280" font-family="Arial" font-size="60" fill="#6de8a5" text-anchor="middle" font-weight="bold">LP IL Estimator</text>
  <text x="600" y="350" font-family="Arial" font-size="32" fill="#b2dfdb" text-anchor="middle">Impermanent Loss Calculator</text>
</svg>`;
  c.header('Content-Type', 'image/svg+xml');
  return c.body(svg);
});

app.addEntrypoint({
  key: 'lp-il-estimator',
  name: 'LP Impermanent Loss Estimator',
  description: 'Calculate IL and fee APR for any LP position',
  price: '$0.04',
  outputSchema: {
    input: {
      type: 'http',
      method: 'POST',
      discoverable: true,
      bodyType: 'json',
      bodyFields: {
        initial_price_0: { type: 'number', required: true },
        initial_price_1: { type: 'number', required: true },
        current_price_ratio: { type: 'number', required: true },
        amount_0: { type: 'number', required: true },
        amount_1: { type: 'number', required: true },
        fees_earned: { type: 'number', required: true },
        days_held: { type: 'number', required: true },
      },
    },
    output: {
      type: 'object',
      required: ['il_percentage', 'fee_apr', 'net_apr'],
      properties: {
        il_percentage: { type: 'number' },
        il_usd: { type: 'number' },
        fee_apr: { type: 'number' },
        net_apr: { type: 'number' },
        recommendation: { type: 'string' },
      },
    },
  } as any,
  handler: async (ctx) => {
    const { initial_price_0, initial_price_1, current_price_ratio, amount_0, amount_1, fees_earned, days_held } = ctx.input as any;
    return calculateImpermanentLoss(current_price_ratio, initial_price_0, initial_price_1, amount_0, amount_1, fees_earned, days_held);
  },
});

const wrapperApp = new Hono();
wrapperApp.get('/favicon.ico', (c) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#6de8a5"/><text y=".9em" x="50%" text-anchor="middle" font-size="90">📊</text></svg>`;
  c.header('Content-Type', 'image/svg+xml');
  return c.body(svg);
});
wrapperApp.get('/', (c) => c.html(`<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>LP IL Estimator - x402 Agent</title><link rel="icon" type="image/svg+xml" href="/favicon.ico"><meta property="og:title" content="LP IL Estimator - x402 Agent"><meta property="og:description" content="Calculate impermanent loss and fee APR for LP positions"><meta property="og:image" content="https://lp-impermanent-loss-estimator-production-62b5.up.railway.app/og-image.png"><style>body{font-family:system-ui;max-width:1200px;margin:40px auto;padding:20px;background:#0f3460;color:#e8f0f2}h1{color:#6de8a5}</style></head><body><h1>LP Impermanent Loss Estimator</h1><p>$0.04 USDC per request</p></body></html>`));
wrapperApp.all('*', async (c) => honoApp.fetch(c.req.raw));

if (typeof Bun !== 'undefined') {
  Bun.serve({ port: PORT, hostname: HOST, fetch: wrapperApp.fetch });
} else {
  const { serve } = await import('@hono/node-server');
  serve({ fetch: wrapperApp.fetch, port: PORT, hostname: HOST });
}

console.log(`[SUCCESS] ✓ Server running at http://${HOST}:${PORT}`);
