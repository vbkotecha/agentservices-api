/**
 * AgentServices Client SDK
 *
 * Paid APIs for AI agents — crypto data, stocks, SEC filings, commodities,
 * FX rates, LLM inference, token risk, crypto signals, and more.
 * 50+ services, 34+ paid. x402 micropayments via USDC on Base.
 *
 * @module agentservices-client
 */

const DEFAULT_BASE_URL = "https://api.agentservices.to";

class AgentServicesClient {
  /**
   * Create an AgentServices client.
   * @param {Object} options
   * @param {string} [options.baseUrl] - API base URL (default: https://api.agentservices.to)
   * @param {string} [options.walletAddress] - Wallet for x402 payments (required for paid endpoints)
   * @param {string} [options.privateKey] - Private key for signing x402 payments
   */
  constructor(options = {}) {
    this.baseUrl = (options.baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");
    this.walletAddress = options.walletAddress || null;
    this.privateKey = options.privateKey || null;
    this._fetch = options.fetch || globalThis.fetch;
  }

  async _request(method, path, body = null) {
    const url = `${this.baseUrl}${path}`;
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);

    const response = await this._fetch(url, opts);

    if (response.status === 402) {
      const error = new Error("Payment required. This endpoint requires x402 payment (USDC on Base).");
      error.status = 402;
      error.needsPayment = true;
      const paymentHeader = response.headers.get("payment-required");
      if (paymentHeader) { error.paymentRequirements = paymentHeader; }
      throw error;
    }

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`API error ${response.status}: ${text}`);
    }

    return response.json();
  }

  // ─── FREE ENDPOINTS ──────────────────────────────────────────

  async getPrice(symbol) {
    return this._request("GET", `/v1/price/${encodeURIComponent(symbol)}`);
  }

  async getPrices(symbols = ["BTC", "ETH", "SOL", "XRP"]) {
    return this._request("GET", `/v1/prices?symbols=${symbols.join(",")}`);
  }

  async getFearGreed() {
    return this._request("GET", `/v1/fear-greed`);
  }

  async getGeo(ip) {
    return this._request("GET", `/v1/geo/${encodeURIComponent(ip)}`);
  }

  async getGlobal() {
    return this._request("GET", `/v1/global`);
  }

  async getTrending() {
    return this._request("GET", `/v1/trending`);
  }

  async getGas() {
    return this._request("GET", `/v1/gas`);
  }

  async getNews() {
    return this._request("GET", `/v1/news`);
  }

  // ─── PAID: CRYPTO DATA ──────────────────────────────────────

  async getIndicators(symbol) {
    return this._request("GET", `/v1/indicators/${encodeURIComponent(symbol)}`);
  }

  async getYields({ limit = 20, chain = "all" } = {}) {
    return this._request("GET", `/v1/yields?limit=${limit}&chain=${encodeURIComponent(chain)}`);
  }

  async getMetadata(url) {
    return this._request("GET", `/v1/metadata?url=${encodeURIComponent(url)}`);
  }

  async search(query) {
    return this._request("GET", `/v1/search?q=${encodeURIComponent(query)}`);
  }

  async getWhales() {
    return this._request("GET", `/v1/whales`);
  }

  async getExchangeFlows() {
    return this._request("GET", `/v1/exchange-flows`);
  }

  async getCorrelation() {
    return this._request("GET", `/v1/correlation`);
  }

  async getDefiTvl() {
    return this._request("GET", `/v1/defi-tvl`);
  }

  // ─── PAID: INFERENCE GATEWAY ────────────────────────────────

  async inference({ model = "gpt-5.4-mini", messages, temperature = 0.7, max_tokens = 1000 }) {
    return this._request("POST", `/v1/inference`, { model, messages, temperature, max_tokens });
  }

  async complete(prompt, { model = "gpt-5.4-mini", max_tokens = 500 } = {}) {
    return this._request("POST", `/v1/complete?prompt=${encodeURIComponent(prompt)}&model=${model}&max_tokens=${max_tokens}`);
  }

  // ─── PAID: SYNTHESIS ────────────────────────────────────────

  async getTokenRisk(token) {
    return this._request("GET", `/v1/token-risk/${encodeURIComponent(token)}`);
  }

  async getSignals(symbol) {
    return this._request("GET", `/v1/signals/${encodeURIComponent(symbol)}`);
  }

  async getYieldComparison(chain = "") {
    return this._request("GET", `/v1/yield-comparison?chain=${encodeURIComponent(chain)}`);
  }

  async getHnSentiment(query = "") {
    return this._request("GET", `/v1/hn-sentiment?query=${encodeURIComponent(query)}`);
  }

  async getNpmStats(package_name) {
    return this._request("GET", `/v1/npm-stats/${encodeURIComponent(package_name)}`);
  }

  async getGithubTrending(language = "") {
    return this._request("GET", `/v1/github-trending?language=${encodeURIComponent(language)}`);
  }

  // ─── PAID: TRADITIONAL FINANCE ──────────────────────────────

  async getStockQuote(ticker) {
    return this._request("GET", `/v1/stocks/${encodeURIComponent(ticker)}`);
  }

  async getStockHistory(ticker, range = "3mo") {
    return this._request("GET", `/v1/stocks/${encodeURIComponent(ticker)}/history?range=${range}`);
  }

  async getSecFilings(ticker, filingType = "10-K") {
    return this._request("GET", `/v1/sec/${encodeURIComponent(ticker)}?filing_type=${filingType}`);
  }

  async getCommodities() {
    return this._request("GET", `/v1/commodities`);
  }

  async getEconomicIndicators() {
    return this._request("GET", `/v1/economic`);
  }

  async getFxRates(base = "USD") {
    return this._request("GET", `/v1/fx?base=${base}`);
  }

  // ─── PAID: UTILITY ──────────────────────────────────────────

  async extractContent(url) {
    return this._request("GET", `/v1/extract?url=${encodeURIComponent(url)}`);
  }

  async scanPackageSecurity(package_name, ecosystem = "PyPI") {
    return this._request("GET", `/v1/security/${encodeURIComponent(package_name)}?ecosystem=${ecosystem}`);
  }

  async getSeoKeywords(keyword) {
    return this._request("GET", `/v1/seo/keywords?keyword=${encodeURIComponent(keyword)}`);
  }

  // ─── HEALTH ──────────────────────────────────────────────────

  async health() {
    return this._request("GET", `/health`);
  }
}

module.exports = { AgentServicesClient };
module.exports.default = AgentServicesClient;
module.exports.AgentServicesClient = AgentServicesClient;
