#!/usr/bin/env node
/**
 * AgentServices MCP Server — Pure JavaScript (zero dependencies)
 * 
 * 50+ paid APIs for AI agents: crypto data, DeFi yields, on-chain analytics,
 * portfolio intelligence, deep research, market intelligence, and more.
 * x402 micropayments via USDC on Base.
 * 
 * Usage in Claude Desktop / Cursor / Windsurf:
 *   npx agentservices-mcp
 * 
 * No Python required. No API key required for free endpoints.
 * Paid endpoints return 402 — agents pay via x402 (USDC on Base).
 */

const https = require('https');
const readline = require('readline');

const BASE_URL = 'agentservices.to';
const API_BASE = `https://${BASE_URL}`;

// ============================================================
// ENDPOINT DEFINITIONS — all 50+ services (paths match OpenAPI spec)
// ============================================================
// pathParams: listed in order of substitution into {placeholder} in path
// queryParams: appended as ?key=value
const TOOLS = [
  // === FREE ENDPOINTS ===
  { name: 'crypto_prices', description: 'Get current cryptocurrency prices for BTC, ETH, SOL, XRP and more. FREE.', method: 'GET', path: '/v1/prices', pathParams: [], queryParams: { symbols: 'Comma-separated crypto symbols (e.g. BTC,ETH,SOL)' } },
  { name: 'crypto_price_single', description: 'Get current price for a single cryptocurrency. FREE.', method: 'GET', path: '/v1/price/{symbol}', pathParams: [{ arg: 'symbol', desc: 'Crypto symbol (e.g. BTC)' }], queryParams: {} },
  { name: 'fear_greed', description: 'Get the crypto Fear & Greed Index (0=extreme fear, 100=extreme greed). FREE.', method: 'GET', path: '/v1/fear-greed', pathParams: [], queryParams: {} },
  { name: 'ip_geolocation', description: 'Get geolocation data for an IP address. FREE.', method: 'GET', path: '/v1/geo/{ip}', pathParams: [{ arg: 'ip', desc: 'IP address to look up' }], queryParams: {} },
  { name: 'trending_crypto', description: 'Get trending cryptocurrencies. FREE.', method: 'GET', path: '/v1/trending', pathParams: [], queryParams: {} },
  { name: 'global_market', description: 'Get global crypto market stats (total market cap, volume, BTC dominance). FREE.', method: 'GET', path: '/v1/global', pathParams: [], queryParams: {} },
  { name: 'gas_prices', description: 'Get current gas prices for major chains (Ethereum, Base, Polygon). FREE.', method: 'GET', path: '/v1/gas', pathParams: [], queryParams: {} },
  { name: 'swap_quote', description: 'Get a DEX swap quote — find the best rate for token swaps. FREE.', method: 'GET', path: '/v1/swap/quote', pathParams: [], queryParams: { chain: 'Blockchain (e.g. ethereum, base)', token_in: 'Input token address', token_out: 'Output token address', amount: 'Amount to swap' } },
  { name: 'crypto_news', description: 'Get latest crypto and blockchain news. FREE.', method: 'GET', path: '/v1/news', pathParams: [], queryParams: { category: 'News category (optional)' } },
  { name: 'social_trending', description: 'Get trending topics on crypto social media. FREE.', method: 'GET', path: '/v1/social', pathParams: [], queryParams: {} },
  { name: 'list_policies', description: 'List all available dispute resolution policy templates. FREE.', method: 'GET', path: '/v1/policies', pathParams: [], queryParams: {} },
  { name: 'crypto_predictions', description: 'Get crowd-sourced crypto price predictions. FREE.', method: 'GET', path: '/v1/predictions', pathParams: [], queryParams: { slug: 'Prediction market slug (optional, for specific market)' } },

  // === PAID — CRYPTO DATA ($0.01-0.04) ===
  { name: 'technical_indicators', description: 'Get technical indicators (RSI, MACD, Bollinger Bands, etc.) for any crypto. $0.02/call via x402.', method: 'GET', path: '/v1/indicators/{symbol}', pathParams: [{ arg: 'symbol', desc: 'Crypto symbol (e.g. BTC, ETH)' }], queryParams: { interval: 'Timeframe: 1h, 4h, 1d' } },
  { name: 'defi_yields', description: 'Get top DeFi yield pools across protocols and chains. $0.02/call via x402.', method: 'GET', path: '/v1/yields', pathParams: [], queryParams: { chain: 'Blockchain name (optional)', protocol: 'Protocol name (optional)' } },
  { name: 'url_metadata', description: 'Extract rich metadata from any URL (title, description, images, OpenGraph). $0.01/call via x402.', method: 'GET', path: '/v1/metadata', pathParams: [], queryParams: { url: 'URL to extract metadata from' } },
  { name: 'search_web', description: 'AI-powered web search optimized for agents. Returns clean, relevant results. $0.01/call via x402.', method: 'GET', path: '/v1/search', pathParams: [], queryParams: { q: 'Search query' } },
  { name: 'whale_tracker', description: 'Track large crypto transactions (whale movements). $0.02/call via x402.', method: 'GET', path: '/v1/whales', pathParams: [], queryParams: { symbol: 'Crypto symbol (optional)', min_value: 'Minimum USD value (optional)' } },
  { name: 'exchange_flows', description: 'Track exchange inflows/outflows for crypto. $0.02/call via x402.', method: 'GET', path: '/v1/exchange-flows', pathParams: [], queryParams: { symbol: 'Crypto symbol' } },
  { name: 'correlation_matrix', description: 'Get correlation matrix between major cryptocurrencies. $0.02/call via x402.', method: 'GET', path: '/v1/correlation', pathParams: [], queryParams: { symbols: 'Comma-separated symbols' } },
  { name: 'stablecoin_flows', description: 'Track stablecoin market caps and flows across chains. $0.02/call via x402.', method: 'GET', path: '/v1/stablecoin-flows', pathParams: [], queryParams: {} },
  { name: 'defi_tvl', description: 'Get Total Value Locked across DeFi protocols. $0.02/call via x402.', method: 'GET', path: '/v1/defi-tvl', pathParams: [], queryParams: { chain: 'Blockchain (optional)' } },
  { name: 'github_velocity', description: 'Measure GitHub commit velocity for any repo. $0.02/call via x402.', method: 'GET', path: '/v1/github-velocity', pathParams: [], queryParams: { repo: 'GitHub repo (owner/name)' } },
  { name: 'macro_indicators', description: 'Get macro economic indicators (CPI, GDP, unemployment, etc.). $0.02/call via x402.', method: 'GET', path: '/v1/macro', pathParams: [], queryParams: {} },

  // === PAID — SYNTHESIS ($0.03-0.04) ===
  { name: 'token_risk_score', description: 'Get a comprehensive risk assessment for any crypto token. $0.03/call via x402.', method: 'GET', path: '/v1/token-risk/{token}', pathParams: [{ arg: 'token', desc: 'Token symbol or contract address' }], queryParams: {} },
  { name: 'crypto_signals', description: 'Get aggregated trading signals (technical + on-chain + sentiment). $0.04/call via x402.', method: 'GET', path: '/v1/signals/{symbol}', pathParams: [{ arg: 'symbol', desc: 'Crypto symbol' }], queryParams: {} },
  { name: 'yield_comparison', description: 'Compare DeFi yields across protocols with risk-adjusted returns. $0.03/call via x402.', method: 'GET', path: '/v1/yield-comparison', pathParams: [], queryParams: { asset: 'Asset to compare yields for' } },
  { name: 'hn_sentiment', description: 'Get Hacker News sentiment analysis for any topic. $0.02/call via x402.', method: 'GET', path: '/v1/hn-sentiment', pathParams: [], queryParams: { topic: 'Topic to analyze' } },
  { name: 'npm_stats', description: 'Get npm package download statistics and trends. $0.02/call via x402.', method: 'GET', path: '/v1/npm-stats/{package}', pathParams: [{ arg: 'package', desc: 'npm package name' }], queryParams: {} },
  { name: 'github_trending', description: 'Get trending GitHub repositories by language/topic. $0.02/call via x402.', method: 'GET', path: '/v1/github-trending', pathParams: [], queryParams: { language: 'Programming language (optional)', since: 'Time range: daily, weekly, monthly' } },

  // === PAID — TRADITIONAL FINANCE ($0.01-0.02) ===
  { name: 'stock_quote', description: 'Get real-time stock price quotes. $0.02/call via x402.', method: 'GET', path: '/v1/stocks/{ticker}', pathParams: [{ arg: 'ticker', desc: 'Stock ticker symbol (e.g. AAPL)' }], queryParams: {} },
  { name: 'stock_history', description: 'Get historical stock price data. $0.02/call via x402.', method: 'GET', path: '/v1/stocks/{ticker}/history', pathParams: [{ arg: 'ticker', desc: 'Stock ticker symbol' }], queryParams: { period: 'Time period: 1d, 1w, 1m, 3m, 1y' } },
  { name: 'sec_filings', description: 'Search and parse SEC EDGAR filings (10-K, 10-Q, 8-K). $0.02/call via x402.', method: 'GET', path: '/v1/sec/{ticker}', pathParams: [{ arg: 'ticker', desc: 'Company ticker or CIK' }], queryParams: { type: 'Filing type (optional)' } },
  { name: 'commodities', description: 'Get commodity prices (gold, silver, oil, wheat, etc.). $0.02/call via x402.', method: 'GET', path: '/v1/commodities', pathParams: [], queryParams: {} },
  { name: 'economic_indicators', description: 'Get key economic indicators (interest rates, inflation, GDP). $0.02/call via x402.', method: 'GET', path: '/v1/economic', pathParams: [], queryParams: {} },
  { name: 'fx_rates', description: 'Get foreign exchange rates. $0.01/call via x402.', method: 'GET', path: '/v1/fx', pathParams: [], queryParams: { base: 'Base currency (default: USD)' } },

  // === PAID — UTILITY ($0.02-0.03) ===
  { name: 'web_extract', description: 'Extract clean text content from any web page. $0.02/call via x402.', method: 'GET', path: '/v1/extract', pathParams: [], queryParams: { url: 'URL to extract content from' } },
  { name: 'package_security', description: 'Get security audit for npm/pip packages. $0.02/call via x402.', method: 'GET', path: '/v1/security/{package}', pathParams: [{ arg: 'package', desc: 'Package name' }], queryParams: { ecosystem: 'npm or pip' } },
  { name: 'seo_keywords', description: 'Get SEO keyword suggestions and search volume data. $0.03/call via x402.', method: 'GET', path: '/v1/seo/keywords', pathParams: [], queryParams: { keyword: 'Seed keyword' } },

  // === PAID — MARKETING INTELLIGENCE ($0.03-0.04, POST) ===
  { name: 'marketing_sentiment', description: 'Analyze market sentiment for a brand or product. $0.03/call via x402.', method: 'POST', path: '/v1/marketing/sentiment', pathParams: [], queryParams: {}, bodyParams: { brand: 'Brand or product name' } },
  { name: 'marketing_trends', description: 'Get marketing trend analysis for an industry. $0.03/call via x402.', method: 'POST', path: '/v1/marketing/trends', pathParams: [], queryParams: {}, bodyParams: { industry: 'Industry name' } },
  { name: 'marketing_competitors', description: 'Get competitor analysis for a brand. $0.04/call via x402.', method: 'POST', path: '/v1/marketing/competitors', pathParams: [], queryParams: {}, bodyParams: { brand: 'Brand name' } },
  { name: 'marketing_content_gaps', description: 'Identify content gaps in a niche. $0.03/call via x402.', method: 'POST', path: '/v1/marketing/content-gaps', pathParams: [], queryParams: {}, bodyParams: { niche: 'Niche or topic' } },
  { name: 'marketing_ad_copy', description: 'Generate AI-powered ad copy variations. $0.04/call via x402.', method: 'POST', path: '/v1/marketing/ad-copy', pathParams: [], queryParams: {}, bodyParams: { product: 'Product name', audience: 'Target audience' } },

  // === PAID — BUNDLED INTELLIGENCE ($0.05-0.25) ===
  { name: 'deep_research', description: 'Deep research: search + extract + synthesize in one call. Returns a comprehensive report. $0.05/call via x402.', method: 'GET', path: '/v1/research', pathParams: [], queryParams: { q: 'Research query' } },
  { name: 'portfolio_intelligence', description: 'Portfolio analysis: price + technical signal + risk score + sentiment + verdict. $0.10/call via x402.', method: 'GET', path: '/v1/portfolio', pathParams: [], queryParams: { symbol: 'Crypto symbol (e.g. BTC)' } },
  { name: 'defi_strategy', description: 'DeFi investment strategy: top yields + TVL + comparison + risk assessment. $0.25/call via x402.', method: 'GET', path: '/v1/defi-strategy', pathParams: [], queryParams: {} },
  { name: 'market_pulse', description: 'Market direction signal: Fear&Greed + trending + news + social + whales + global. $0.05/call via x402.', method: 'GET', path: '/v1/market-pulse', pathParams: [], queryParams: {} },
  { name: 'onchain_overview', description: 'On-chain analytics: whales + exchange flows + stablecoin flows + correlation + TVL. $0.15/call via x402.', method: 'GET', path: '/v1/onchain-overview', pathParams: [], queryParams: {} },

  // === PAID — AI INFERENCE ($0.03, POST) ===
  { name: 'ai_inference', description: 'Run AI model inference (GPT-5.4, GPT-5.5). POST with messages array. $0.03/call via x402.', method: 'POST', path: '/v1/inference', pathParams: [], queryParams: {}, bodyParams: { messages: 'JSON array of message objects', model: 'Model name (gpt-5.4, gpt-5.4-mini, gpt-5.5)' } },
  { name: 'ai_complete', description: 'Quick AI text completion. $0.03/call via x402.', method: 'POST', path: '/v1/complete', pathParams: [], queryParams: {}, bodyParams: { prompt: 'Text prompt', model: 'Model name (optional)' } },

  // === PAID — DISPUTE RESOLUTION ($0.05, POST) ===
  { name: 'resolve_dispute', description: 'AI-powered dispute resolution. Policies: mileage_payment, physical_commerce, freelance_delivery, bug_bounty, api_quality, sla_monitoring, scope_dispute. $0.05/call via x402.', method: 'POST', path: '/v1/disputes', pathParams: [], queryParams: {}, bodyParams: { policy: 'Policy ID', dispute: 'Dispute details as JSON' } },
];

// ============================================================
// JSON-RPC OVER STDIO — MCP PROTOCOL
// ============================================================

const rl = readline.createInterface({ input: process.stdin, terminal: false });

function send(msg) {
  process.stdout.write(JSON.stringify(msg) + '\n');
}

function makeToolDefs() {
  return TOOLS.map(t => {
    const properties = {};
    const required = [];

    // Path params are required
    for (const p of t.pathParams) {
      properties[p.arg] = { type: 'string', description: p.desc };
      required.push(p.arg);
    }
    // Query params
    for (const [key, val] of Object.entries(t.queryParams || {})) {
      properties[key] = { type: 'string', description: val };
      if (!val.includes('optional')) required.push(key);
    }
    // Body params (for POST)
    for (const [key, val] of Object.entries(t.bodyParams || {})) {
      properties[key] = { type: 'string', description: val };
      if (!val.includes('optional')) required.push(key);
    }

    return {
      name: t.name,
      description: t.description,
      inputSchema: { type: 'object', properties, required }
    };
  });
}

function buildPath(tool, args) {
  let path = tool.path;
  for (const p of tool.pathParams) {
    path = path.replace(`{${p.arg}}`, encodeURIComponent(args[p.arg] || ''));
  }
  return path;
}

function buildQuery(tool, args) {
  const usedKeys = new Set([...tool.pathParams.map(p => p.arg), ...(tool.bodyParams ? Object.keys(tool.bodyParams) : [])]);
  const qs = Object.entries(args)
    .filter(([k, v]) => !usedKeys.has(k) && v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
  return qs ? `?${qs}` : '';
}

function buildBody(tool, args) {
  if (!tool.bodyParams) return null;
  const body = {};
  for (const key of Object.keys(tool.bodyParams)) {
    if (args[key] !== undefined && args[key] !== null && args[key] !== '') {
      // Try to parse JSON values (messages array, dispute object)
      if (typeof args[key] === 'string' && (args[key].startsWith('[') || args[key].startsWith('{'))) {
        try { body[key] = JSON.parse(args[key]); continue; } catch {}
      }
      body[key] = args[key];
    }
  }
  return JSON.stringify(body);
}

async function callAPI(tool, args) {
  return new Promise((resolve) => {
    const urlPath = buildPath(tool, args) + buildQuery(tool, args);
    const body = buildBody(tool, args);

    const options = {
      hostname: BASE_URL,
      path: urlPath,
      method: tool.method,
      headers: { 'Accept': 'application/json' },
      timeout: 30000,
    };
    if (body) {
      options.headers['Content-Type'] = 'application/json';
      options.headers['Content-Length'] = Buffer.byteLength(body);
    }

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 402) {
          let payInfo = {};
          try { payInfo = JSON.parse(data); } catch {}
          resolve({
            status: 402,
            payment_required: true,
            message: `This endpoint requires x402 payment. Send USDC on Base to complete this call.`,
            payment_details: payInfo,
            endpoint: `${API_BASE}${tool.path}`,
          });
        } else {
          let parsed;
          try { parsed = JSON.parse(data); } catch { parsed = data.substring(0, 5000); }
          resolve({ status: res.statusCode, data: parsed });
        }
      });
    });

    req.on('error', (err) => resolve({ status: 0, error: err.message }));
    req.on('timeout', () => { req.destroy(); resolve({ status: 0, error: 'Request timed out (30s)' }); });
    if (body) req.write(body);
    req.end();
  });
}

// ============================================================
// REQUEST HANDLERS
// ============================================================

rl.on('line', (line) => {
  let msg;
  try { msg = JSON.parse(line); } catch { return; }

  const { id, method, params } = msg;

  switch (method) {
    case 'initialize':
      send({ jsonrpc: '2.0', id, result: { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'agentservices', version: '5.3.0' } } });
      break;

    case 'notifications/initialized':
      break;

    case 'tools/list':
      send({ jsonrpc: '2.0', id, result: { tools: makeToolDefs() } });
      break;

    case 'tools/call': {
      const toolName = params?.name;
      const args = params?.arguments || {};
      const tool = TOOLS.find(t => t.name === toolName);

      if (!tool) {
        send({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: `Unknown tool: ${toolName}. Available: ${TOOLS.map(t => t.name).join(', ')}` }], isError: true } });
        break;
      }

      callAPI(tool, args).then((result) => {
        let text;
        if (result.payment_required) {
          text = JSON.stringify(result, null, 2);
        } else if (result.status >= 200 && result.status < 300) {
          text = typeof result.data === 'string' ? result.data : JSON.stringify(result.data, null, 2);
        } else {
          text = `HTTP ${result.status}: ${JSON.stringify(result.data || result.error, null, 2)}`;
        }
        send({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text }], isError: result.status === 402 || result.status === 0 } });
      });
      break;
    }

    case 'ping':
      send({ jsonrpc: '2.0', id, result: {} });
      break;

    default:
      if (id) send({ jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } });
  }
});

rl.on('close', () => process.exit(0));
process.stderr.write('AgentServices MCP Server v5.3.0 started. 50 tools available (11 free, 39 paid via x402).\n');
