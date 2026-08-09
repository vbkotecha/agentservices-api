#!/usr/bin/env node
/**
 * Verify the SDK's paid technical-indicator path without spending.
 *
 * Usage:
 *   node examples/sdk_paid_indicator_buyer_proof.js BTC
 *
 * The proof deliberately stops at HTTP 402. It decodes the live x402
 * payment requirements but never signs, submits, or settles a payment.
 */

const { AgentServicesClient } = require("../sdk");

function decodePaymentRequired(encoded) {
  if (!encoded) {
    throw new Error("402 response did not include payment requirements");
  }

  const value = encoded.trim();
  const normalized = value.startsWith("{")
    ? value
    : Buffer.from(
        value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (value.length % 4)) % 4),
        "base64",
      ).toString("utf8");

  const challenge = JSON.parse(normalized);
  if (!Array.isArray(challenge.accepts) || challenge.accepts.length === 0) {
    throw new Error("402 response contains no accepted payment requirements");
  }
  return challenge;
}

function firstRequirement(challenge) {
  if (!Array.isArray(challenge.accepts) || challenge.accepts.length === 0) {
    throw new Error("payment requirement contains no accepted options");
  }
  const requirement = challenge.accepts[0];
  const amount = requirement.maxAmountRequired || requirement.amount;
  if (!requirement.network || !amount || !requirement.payTo) {
    throw new Error("payment requirement is missing network, amount, or recipient");
  }
  return { ...requirement, amount };
}

function formatUsdc(amount) {
  const atomic = BigInt(String(amount));
  const whole = atomic / 1000000n;
  const fraction = String(atomic % 1000000n).padStart(6, "0");
  return `${whole}.${fraction} USDC`;
}

async function main() {
  const symbol = (process.argv[2] || "BTC").toUpperCase();
  const client = new AgentServicesClient();

  try {
    await client.getIndicators(symbol);
  } catch (error) {
    if (error.status !== 402 || !error.needsPayment) {
      throw error;
    }

    const challenge = decodePaymentRequired(error.paymentRequirements);
    const requirement = firstRequirement(challenge);
    const resource = challenge.resource || {};

    console.log(`SDK PAID PATH: GET /v1/indicators/${symbol} → HTTP 402 verified`);
    console.log(`protocol: x402 v${challenge.x402Version || "unknown"}`);
    console.log(`resource: ${resource.url || `${client.baseUrl}/v1/indicators/${symbol}`}`);
    console.log(`network: ${requirement.network}`);
    console.log(`asset: ${requirement.asset}`);
    console.log(`amount: ${requirement.amount} atomic units (${formatUsdc(requirement.amount)})`);
    console.log(`recipient: ${requirement.payTo}`);
    console.log("next step: an x402-compatible wallet may pay and retry with payment proof.");
    console.log("This proof decoded the live challenge only; no payment was signed or settled.");
    return;
  }

  throw new Error("Expected the paid indicator endpoint to return HTTP 402");
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`SDK paid buyer proof failed: ${error.message}`);
    process.exitCode = 1;
  });
}

module.exports = { decodePaymentRequired, firstRequirement, formatUsdc };
