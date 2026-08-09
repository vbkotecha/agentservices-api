#!/usr/bin/env node
/**
 * Verify a real free AgentServices SDK call without credentials or payment.
 *
 * Usage:
 *   node examples/sdk_free_price_buyer_proof.js BTC ETH
 */

const { AgentServicesClient } = require("../sdk");

async function main() {
  const symbols = process.argv.slice(2);
  const requestedSymbols = symbols.length ? symbols : ["BTC", "ETH"];
  const client = new AgentServicesClient();
  const result = await client.getPrices(requestedSymbols);

  if (!result || typeof result !== "object" || !result.prices || typeof result.prices !== "object") {
    throw new Error("SDK response does not contain a prices object");
  }

  for (const symbol of requestedSymbols) {
    if (!result.prices[symbol]) {
      throw new Error(`SDK response is missing requested symbol: ${symbol}`);
    }
  }

  console.log(`SDK FREE TOOL: HTTP 200 — getPrices(${requestedSymbols.join(",")})`);
  console.log(JSON.stringify(result, null, 2));
  console.log("This proof validates the published SDK's free buyer path; no wallet, API key, or paid endpoint was used.");
}

main().catch((error) => {
  console.error(`SDK buyer proof failed: ${error.message}`);
  process.exitCode = 1;
});
