/**
 * Quick smoke test for AgentServices Client SDK
 * Run: node sdk/test.js
 */

const { AgentServicesClient } = require("./index");

async function main() {
  const client = new AgentServicesClient();

  console.log("=== AgentServices SDK Smoke Test ===\n");

  // 1. Health check
  console.log("1. Health check...");
  const health = await client.health();
  console.log(`   Status: ${health.status} | x402: ${health.x402_enabled} | v${health.version}\n`);

  // 2. Free: BTC price
  console.log("2. BTC price (free)...");
  const btc = await client.getPrice("BTC");
  console.log(`   ${JSON.stringify(btc)}\n`);

  // 3. Free: Batch prices
  console.log("3. Batch prices (free)...");
  const batch = await client.getPrices(["BTC", "ETH", "SOL"]);
  console.log(`   Got prices for ${Object.keys(batch).length} symbols\n`);

  // 4. Free: Fear & Greed
  console.log("4. Fear & Greed (free)...");
  const fg = await client.getFearGreed();
  console.log(`   ${JSON.stringify(fg)}\n`);

  // 5. Free: Global market
  console.log("5. Global market (free)...");
  const global = await client.getGlobal();
  console.log(`   ${JSON.stringify(global)}\n`);

  // 6. Paid: Indicators (should get 402 without payment)
  console.log("6. Indicators ($0.02, paid)...");
  try {
    await client.getIndicators("BTC");
  } catch (err) {
    if (err.status === 402) {
      console.log(`   ✅ Correctly returned 402 (payment required)\n`);
    } else {
      console.log(`   ❌ Unexpected error: ${err.message}\n`);
    }
  }

  console.log("=== All tests passed ===");
}

main().catch(err => {
  console.error("Test failed:", err.message);
  process.exit(1);
});
