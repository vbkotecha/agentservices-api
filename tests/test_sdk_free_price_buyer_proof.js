const assert = require("assert");
const { AgentServicesClient } = require("../sdk");

async function main() {
  const calls = [];
  const client = new AgentServicesClient({
    baseUrl: "https://example.test",
    fetch: async (url, options) => {
      calls.push({ url, options });
      return {
        ok: true,
        status: 200,
        json: async () => ({ prices: { BTC: { price_usd: 1 }, ETH: { price_usd: 2 } } }),
      };
    },
  });

  const result = await client.getPrices(["BTC", "ETH"]);
  assert.deepStrictEqual(result.prices.BTC, { price_usd: 1 });
  assert.deepStrictEqual(result.prices.ETH, { price_usd: 2 });
  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].url, "https://example.test/v1/prices?symbols=BTC,ETH");
  assert.strictEqual(calls[0].options.method, "GET");
  console.log("SDK proof regression assertions passed");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
