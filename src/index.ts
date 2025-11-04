import { createAgentApp } from "@lucid-dreams/agent-kit";
import { Hono } from "hono";
import { z } from "zod";

// Input schema
const ILInputSchema = z.object({
  initial_price_0: z.number().describe("Initial price of token 0 in USD"),
  initial_price_1: z.number().describe("Initial price of token 1 in USD"),
  current_price_ratio: z.number().describe("Current price ratio (price_0 / price_1)"),
  amount_0: z.number().describe("Amount of token 0 deposited"),
  amount_1: z.number().describe("Amount of token 1 deposited"),
  fees_earned: z.number().describe("Total fees earned in USD"),
  days_held: z.number().describe("Number of days position has been held"),
});

// Output schema
const ILOutputSchema = z.object({
  il_percentage: z.number(),
  il_usd: z.number(),
  initial_value_usd: z.number(),
  current_value_usd: z.number(),
  hodl_value_usd: z.number(),
  fee_apr: z.number(),
  net_apr: z.number(),
  recommendation: z.string(),
});

const { app, addEntrypoint, config } = createAgentApp(
  {
    name: "LP Impermanent Loss Estimator",
    version: "1.0.0",
    description: "Calculate impermanent loss and fee APR for any LP position or simulated deposit",
  },
  {
    config: {
      payments: {
        facilitatorUrl: "https://facilitator.daydreams.systems",
        payTo: "0x01D11F7e1a46AbFC6092d7be484895D2d505095c",
        network: "base",
        asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        defaultPrice: "$0.04", // 0.04 USDC
      },
    },
    useConfigPayments: true,
    ap2: {
      required: true,
      params: { roles: ["merchant"] },
    },
  }
);

function calculateImpermanentLoss(
  priceRatio: number,
  initialPrice0: number,
  initialPrice1: number,
  amount0: number,
  amount1: number,
  feesEarned: number,
  daysHeld: number
) {
  // Calculate new amounts using constant product formula (x * y = k)
  const k = amount0 * amount1;
  const newAmount0 = Math.sqrt(k / priceRatio);
  const newAmount1 = Math.sqrt(k * priceRatio);

  // Calculate values
  const initialValue = amount0 * initialPrice0 + amount1 * initialPrice1;
  const currentValue = newAmount0 * initialPrice0 * priceRatio + newAmount1 * initialPrice1;
  const hodlValue = amount0 * initialPrice0 * priceRatio + amount1 * initialPrice1;

  // Calculate impermanent loss
  const ilUsd = currentValue - hodlValue;
  const ilPercentage = (ilUsd / hodlValue) * 100;

  // Calculate APRs
  const annualFees = (feesEarned / daysHeld) * 365;
  const feeApr = (annualFees / initialValue) * 100;
  const netApr = feeApr + (ilPercentage / daysHeld) * 365;

  // Generate recommendation
  let recommendation = "Monitor position";
  if (ilPercentage < -5 && feeApr < Math.abs(ilPercentage)) {
    recommendation = "Consider exiting - IL exceeds fee earnings";
  } else if (netApr > 10) {
    recommendation = "Strong position - fees outpace IL";
  } else if (netApr > 0) {
    recommendation = "Profitable position - fees covering IL";
  } else if (ilPercentage < -10) {
    recommendation = "High IL detected - evaluate exit strategy";
  }

  return {
    il_percentage: Number(ilPercentage.toFixed(2)),
    il_usd: Number(ilUsd.toFixed(2)),
    initial_value_usd: Number(initialValue.toFixed(2)),
    current_value_usd: Number((currentValue + feesEarned).toFixed(2)),
    hodl_value_usd: Number(hodlValue.toFixed(2)),
    fee_apr: Number(feeApr.toFixed(2)),
    net_apr: Number(netApr.toFixed(2)),
    recommendation,
  };
}

// Register entrypoint
addEntrypoint({
  key: "lp-impermanent-loss-estimator",
  description: "Calculate impermanent loss and fee APR for LP positions with accurate yield estimates",
  input: ILInputSchema,
  output: ILOutputSchema,
  price: "$0.04", // 0.04 USDC
  async handler({ input }) {
    const result = calculateImpermanentLoss(
      input.current_price_ratio,
      input.initial_price_0,
      input.initial_price_1,
      input.amount_0,
      input.amount_1,
      input.fees_earned,
      input.days_held
    );

    return { output: result };
  },
});

// Create wrapper app for internal API
const wrapperApp = new Hono();

// Internal API endpoint (no payment required)
wrapperApp.post("/api/internal/lp-impermanent-loss-estimator", async (c) => {
  try {
    // Check API key authentication
    const apiKey = c.req.header("X-Internal-API-Key");
    const expectedKey = process.env.INTERNAL_API_KEY;

    if (!expectedKey) {
      console.error("[INTERNAL API] INTERNAL_API_KEY not set");
      return c.json({ error: "Server configuration error" }, 500);
    }

    if (apiKey !== expectedKey) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    // Get input from request body
    const input = await c.req.json();

    // Validate input
    const validatedInput = ILInputSchema.parse(input);

    // Call the same logic as x402 endpoint
    const result = calculateImpermanentLoss(
      validatedInput.current_price_ratio,
      validatedInput.initial_price_0,
      validatedInput.initial_price_1,
      validatedInput.amount_0,
      validatedInput.amount_1,
      validatedInput.fees_earned,
      validatedInput.days_held
    );

    return c.json(result);
  } catch (error) {
    console.error("[INTERNAL API] Error:", error);
    return c.json({ error: error instanceof Error ? error.message : "Internal error" }, 500);
  }
});

// Mount the x402 agent app (public, requires payment)
wrapperApp.route("/", app);

// Export for Bun
export default {
  port: parseInt(process.env.PORT || "3000"),
  fetch: wrapperApp.fetch,
};

// Bun server start
console.log(`🚀 LP Impermanent Loss Estimator running on port ${process.env.PORT || 3000}`);
console.log(`📝 Manifest: ${process.env.BASE_URL}/.well-known/agent.json`);
console.log(`💰 Payment address: ${config.payments?.payTo}`);
console.log(`🔓 Internal API: /api/internal/lp-impermanent-loss-estimator (requires API key)`);


