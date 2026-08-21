const assert = require("assert");
const {
  decodePaymentRequired,
  firstRequirement,
  formatUsdc,
} = require("../examples/sdk_paid_indicator_buyer_proof");

const encoded = Buffer.from(JSON.stringify({
  x402Version: 2,
  resource: { url: "https://example.test/v1/indicators/BTC" },
  accepts: [{
    scheme: "exact",
    network: "eip155:8453",
    asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bDa02913",
    maxAmountRequired: "20000",
    payTo: "0x9863aB6242663FCc84c33632741711dB78f8Fd15",
  }],
})).toString("base64url");

const challenge = decodePaymentRequired(encoded);
const requirement = firstRequirement(challenge);
assert.strictEqual(challenge.x402Version, 2);
assert.strictEqual(requirement.network, "eip155:8453");
assert.strictEqual(requirement.amount, "20000");
assert.strictEqual(formatUsdc(requirement.amount), "0.020000 USDC");
assert.throws(() => decodePaymentRequired(""), /payment requirements/);
assert.throws(() => firstRequirement({ accepts: [] }), /no accepted/);
console.log("SDK paid-indicator proof regression assertions passed");
