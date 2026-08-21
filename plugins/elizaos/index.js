/**
 * @agentservices/plugin-elizaos
 *
 * ElizaOS plugin exposing AgentServices (https://agentservices.to) as
 * Actions and a Provider. 50+ endpoints covering crypto data, market
 * intelligence, on-chain analytics, DeFi strategy, portfolio intelligence,
 * AI inference, and web search — all via x402 micropayments on Base Mainnet.
 *
 * Configuration (in agent character file):
 *   settings:
 *     AGENTSERVICES_BASE_URL: https://agentservices.to
 *     AGENTSERVICES_BUYER_PRIVATE_KEY: 0x... (optional, enables auto-pay)
 */

const BASE_URL_DEFAULT = 'https://agentservices.to';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

// ============ AUTO-PAY CLIENT ============

async function buildFetcher(runtime) {
  const privateKey =
    runtime?.getSetting?.('AGENTSERVICES_BUYER_PRIVATE_KEY') ||
    process.env.AGENTSERVICES_BUYER_PRIVATE_KEY;
  if (!privateKey) return fetch;

  try {
    const { createWalletClient } = await import('viem');
    const { privateKeyToAccount } = await import('viem/accounts');
    const { base } = await import('viem/chains');

    const account = privateKeyToAccount(privateKey);
    const walletClient = createWalletClient({
      account,
      chain: base,
      transport: (await import('viem')).http(),
    });

    return async (url, options = {}) => {
      const r1 = await fetch(url, options);
      if (r1.status !== 402) return r1;

      const header = r1.headers.get('payment-required');
      if (!header) return r1;
      const payload = JSON.parse(Buffer.from(header, 'base64').toString('utf8'));
      const accept = payload.accepts[0];

      const validAfter = 0;
      const validBefore =
        Math.floor(Date.now() / 1000) + (accept.maxTimeoutSeconds || 300);
      const nonce =
        '0x' +
        Array.from({ length: 64 }, () =>
          Math.floor(Math.random() * 16).toString(16)
        ).join('');

      const signature = await walletClient.signTypedData({
        account,
        domain: {
          name: 'USD Coin',
          version: '2',
          chainId: 8453,
          verifyingContract: USDC,
        },
        types: {
          TransferWithAuthorization: [
            { name: 'from', type: 'address' },
            { name: 'to', type: 'address' },
            { name: 'value', type: 'uint256' },
            { name: 'validAfter', type: 'uint256' },
            { name: 'validBefore', type: 'uint256' },
            { name: 'nonce', type: 'bytes32' },
          ],
        },
        primaryType: 'TransferWithAuthorization',
        message: {
          from: account.address,
          to: accept.payTo,
          value: BigInt(accept.maxAmountRequired),
          validAfter: BigInt(validAfter),
          validBefore: BigInt(validBefore),
          nonce,
        },
      });

      const paymentPayload = {
        x402Version: 2,
        scheme: 'exact',
        network: accept.network,
        payload: {
          signature,
          authorization: {
            from: account.address,
            to: accept.payTo,
            value: accept.maxAmountRequired,
            validAfter: String(validAfter),
            validBefore: String(validBefore),
            nonce,
          },
        },
      };
      const paymentHeader = Buffer.from(JSON.stringify(paymentPayload)).toString(
        'base64'
      );
      return fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'X-PAYMENT': paymentHeader,
        },
      });
    };
  } catch (e) {
    console.error('[agentservices] Auto-pay disabled:', e.message);
    return fetch;
  }
}

async function callEndpoint(runtime, path, params = {}) {
  const baseUrl =
    runtime?.getSetting?.('AGENTSERVICES_BASE_URL') ||
    process.env.AGENTSERVICES_BASE_URL ||
    BASE_URL_DEFAULT;
  const url = new URL(baseUrl + path);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
  }
  const fetcher = await buildFetcher(runtime);
  const res = await fetcher(url.toString());
  if (res.status === 402) {
    const header = res.headers.get('payment-required');
    let info = {};
    if (header) {
      try {
        info = JSON.parse(Buffer.from(header, 'base64').toString('utf8'));
      } catch {}
    }
    const price = info.accepts?.[0]?.maxAmountRequired
      ? `$${(info.accepts[0].maxAmountRequired / 1e6).toFixed(3)}`
      : 'micro-USDC';
    throw new Error(
      `Payment required (${price}). Set AGENTSERVICES_BUYER_PRIVATE_KEY to enable auto-pay. Fund wallet with USDC on Base.`
    );
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`AgentServices API error ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

// ============ ACTIONS ============

const cryptoPricesAction = {
  name: 'GET_CRYPTO_PRICES',
  description: 'Get current cryptocurrency prices (free)',
  similes: ['CRYPTO_PRICE', 'BITCOIN_PRICE', 'ETH_PRICE', 'TOKEN_PRICE'],
  examples: [],
  handler: async (runtime, message) => {
    const data = await callEndpoint(runtime, '/v1/prices', {});
    return {
      text: formatPrices(data),
      values: { priceData: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const indicatorsAction = {
  name: 'GET_TECHNICAL_INDICATORS',
  description: 'Get technical indicators (RSI, MACD, SMA, EMA) for a crypto asset — $0.02',
  similes: ['RSI', 'MACD', 'TECHNICAL_ANALYSIS', 'TA', 'INDICATORS'],
  examples: [],
  handler: async (runtime, message, state) => {
    const symbol = extractSymbol(message, state) || 'BTC';
    const data = await callEndpoint(runtime, '/v1/indicators/' + symbol.toUpperCase(), {});
    return {
      text: formatIndicators(symbol, data),
      values: { symbol, indicatorData: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const defiYieldsAction = {
  name: 'GET_DEFI_YIELDS',
  description: 'Get top DeFi yield opportunities across chains — $0.02',
  similes: ['DEFI', 'YIELD', 'APY', 'STAKING', 'FARMING'],
  examples: [],
  handler: async (runtime, message) => {
    const data = await callEndpoint(runtime, '/v1/yields', {});
    return {
      text: formatYields(data),
      values: { yieldData: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const fearGreedAction = {
  name: 'GET_FEAR_GREED',
  description: 'Get crypto Fear & Greed Index (free)',
  similes: ['FEAR_GREED', 'SENTIMENT', 'MARKET_SENTIMENT', 'FEAR', 'GREED'],
  examples: [],
  handler: async (runtime) => {
    const data = await callEndpoint(runtime, '/v1/fear-greed', {});
    return {
      text: `Fear & Greed Index: ${data.value || data.data?.value || '?'} (${data.classification || data.data?.classification || 'N/A'})`,
      values: { fearGreed: String(data.value || data.data?.value || '') },
    };
  },
  validate: async () => true,
};

const portfolioAction = {
  name: 'GET_PORTFOLIO_INTELLIGENCE',
  description: 'Comprehensive portfolio analysis for a crypto asset — price, signals, risk, sentiment, verdict — $0.10',
  similes: ['PORTFOLIO', 'PORTFOLIO_ANALYSIS', 'CRYPTO_ANALYSIS', 'INVESTMENT_ANALYSIS'],
  examples: [],
  handler: async (runtime, message, state) => {
    const symbol = extractSymbol(message, state) || 'BTC';
    const data = await callEndpoint(runtime, '/v1/portfolio', { symbol: symbol.toUpperCase() });
    return {
      text: formatPortfolio(symbol, data),
      values: { symbol, portfolioData: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const marketPulseAction = {
  name: 'GET_MARKET_PULSE',
  description: 'Aggregated market overview — fear/greed, trending, news, social, whales, global market — $0.05',
  similes: ['MARKET_PULSE', 'MARKET_OVERVIEW', 'MARKET_SUMMARY', 'MARKET_SNAPSHOT'],
  examples: [],
  handler: async (runtime) => {
    const data = await callEndpoint(runtime, '/v1/market-pulse', {});
    return {
      text: formatMarketPulse(data),
      values: { marketPulse: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const defiStrategyAction = {
  name: 'GET_DEFI_STRATEGY',
  description: 'DeFi investment strategy report — top yields, TVL, cross-chain comparison, risk assessment — $0.25',
  similes: ['DEFI_STRATEGY', 'DEFI_REPORT', 'YIELD_STRATEGY', 'DEFI_INVESTMENT'],
  examples: [],
  handler: async (runtime) => {
    const data = await callEndpoint(runtime, '/v1/defi-strategy', {});
    return {
      text: formatDefiStrategy(data),
      values: { defiStrategy: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const onchainAction = {
  name: 'GET_ONCHAIN_OVERVIEW',
  description: 'On-chain analytics — whale movements, exchange flows, stablecoin flows, correlations, DeFi TVL — $0.15',
  similes: ['ONCHAIN', 'WHALES', 'EXCHANGE_FLOWS', 'CHAIN_ANALYTICS', 'ON_CHAIN'],
  examples: [],
  handler: async (runtime) => {
    const data = await callEndpoint(runtime, '/v1/onchain-overview', {});
    return {
      text: formatOnchain(data),
      values: { onchainData: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const researchAction = {
  name: 'DO_RESEARCH',
  description: 'Deep research — search + extract + synthesize any topic into a report — $0.05',
  similes: ['RESEARCH', 'SEARCH', 'INVESTIGATE', 'LOOK_UP', 'FIND_OUT'],
  examples: [],
  handler: async (runtime, message, state) => {
    const query = extractQuery(message, state);
    if (!query) return { text: 'What would you like me to research?' };
    const data = await callEndpoint(runtime, '/v1/research', { q: query });
    return {
      text: formatResearch(query, data),
      values: { researchData: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const searchAction = {
  name: 'WEB_SEARCH',
  description: 'Web search via AgentServices — $0.01 per query',
  similes: ['SEARCH', 'GOOGLE', 'LOOK_UP', 'FIND'],
  examples: [],
  handler: async (runtime, message, state) => {
    const query = extractQuery(message, state);
    if (!query) return { text: 'What would you like to search for?' };
    const data = await callEndpoint(runtime, '/v1/search', { q: query });
    return {
      text: formatSearch(query, data),
      values: { searchData: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const trendingAction = {
  name: 'GET_TRENDING',
  description: 'Get trending cryptocurrencies (free)',
  similes: ['TRENDING', 'HOT_COINS', 'TRENDING_CRYPTO'],
  examples: [],
  handler: async (runtime) => {
    const data = await callEndpoint(runtime, '/v1/trending', {});
    return {
      text: formatTrending(data),
      values: { trending: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

const newsAction = {
  name: 'GET_CRYPTO_NEWS',
  description: 'Get latest crypto news headlines (free)',
  similes: ['NEWS', 'CRYPTO_NEWS', 'HEADLINES', 'LATEST_NEWS'],
  examples: [],
  handler: async (runtime) => {
    const data = await callEndpoint(runtime, '/v1/news', {});
    return {
      text: formatNews(data),
      values: { news: JSON.stringify(data).slice(0, 4000) },
    };
  },
  validate: async () => true,
};

// ============ FORMATTERS ============

function formatPrices(data) {
  if (Array.isArray(data)) {
    return data.slice(0, 15).map(c =>
      `${c.symbol || c.id}: $${Number(c.price || c.current_price).toLocaleString()}`
    ).join('\n');
  }
  return JSON.stringify(data, null, 2).slice(0, 2000);
}

function formatIndicators(symbol, data) {
  const lines = [`Technical Indicators for ${symbol}:`];
  if (data.rsi) lines.push(`RSI: ${data.rsi}`);
  if (data.macd) lines.push(`MACD: ${data.macd}`);
  if (data.sma_20) lines.push(`SMA 20: $${data.sma_20}`);
  if (data.ema_20) lines.push(`EMA 20: $${data.ema_20}`);
  if (data.signal) lines.push(`Signal: ${data.signal}`);
  if (lines.length === 1) lines.push(JSON.stringify(data, null, 2).slice(0, 1500));
  return lines.join('\n');
}

function formatYields(data) {
  const pools = Array.isArray(data) ? data : data.pools || data.top_yields || [];
  if (!Array.isArray(pools) || pools.length === 0) return JSON.stringify(data, null, 2).slice(0, 2000);
  return 'Top DeFi Yields:\n' + pools.slice(0, 10).map(p =>
    `${p.project || p.protocol}: ${p.symbol || p.token} — ${p.apy || p.apy_pct || '?'}% APY ($${(p.tvl || 0).toLocaleString()} TVL)`
  ).join('\n');
}

function formatPortfolio(symbol, data) {
  const lines = [`Portfolio Intelligence: ${symbol}`];
  if (data.price) lines.push(`Price: $${data.price}`);
  if (data.signal) lines.push(`Signal: ${data.signal}`);
  if (data.risk_score !== undefined) lines.push(`Risk Score: ${data.risk_score}/100`);
  if (data.sentiment) lines.push(`Sentiment: ${data.sentiment}`);
  if (data.verdict) lines.push(`\nVerdict: ${data.verdict}`);
  if (lines.length === 1) lines.push(JSON.stringify(data, null, 2).slice(0, 1500));
  return lines.join('\n');
}

function formatMarketPulse(data) {
  const lines = ['Market Pulse'];
  if (data.fear_greed) lines.push(`Fear/Greed: ${typeof data.fear_greed === 'object' ? data.fear_greed.value : data.fear_greed}`);
  if (data.trending) lines.push(`Trending: ${Array.isArray(data.trending) ? data.trending.slice(0, 5).join(', ') : data.trending}`);
  if (data.global) lines.push(`Global Cap: ${typeof data.global === 'object' ? JSON.stringify(data.global).slice(0, 200) : data.global}`);
  if (data.direction) lines.push(`Direction: ${data.direction}`);
  if (lines.length === 1) lines.push(JSON.stringify(data, null, 2).slice(0, 1500));
  return lines.join('\n');
}

function formatDefiStrategy(data) {
  const lines = ['DeFi Strategy Report'];
  if (data.top_yields) lines.push(`Top Yields: ${Array.isArray(data.top_yields) ? data.top_yields.length : '?'} pools`);
  if (data.total_tvl) lines.push(`Total TVL: $${data.total_tvl}`);
  if (data.risk_assessment) lines.push(`Risk: ${data.risk_assessment}`);
  if (data.recommendation) lines.push(`\nRecommendation: ${data.recommendation}`);
  if (lines.length === 1) lines.push(JSON.stringify(data, null, 2).slice(0, 1500));
  return lines.join('\n');
}

function formatOnchain(data) {
  const lines = ['On-Chain Overview'];
  if (data.whales) lines.push(`Whale activity: ${typeof data.whales === 'object' ? JSON.stringify(data.whales).slice(0, 200) : data.whales}`);
  if (data.exchange_flows) lines.push(`Exchange flows: ${typeof data.exchange_flows === 'object' ? JSON.stringify(data.exchange_flows).slice(0, 200) : data.exchange_flows}`);
  if (data.stablecoin_flows) lines.push(`Stablecoin flows: detected`);
  if (data.defi_tvl) lines.push(`DeFi TVL: ${typeof data.defi_tvl === 'object' ? JSON.stringify(data.defi_tvl).slice(0, 200) : data.defi_tvl}`);
  if (lines.length === 1) lines.push(JSON.stringify(data, null, 2).slice(0, 1500));
  return lines.join('\n');
}

function formatResearch(query, data) {
  const lines = [`Research: "${query}"`];
  if (data.summary) lines.push(`\n${data.summary}`);
  if (data.synthesis) lines.push(`\n${data.synthesis}`);
  if (data.sources) lines.push(`\nSources: ${Array.isArray(data.sources) ? data.sources.length : '?'} references`);
  if (lines.length === 1) lines.push(JSON.stringify(data, null, 2).slice(0, 2000));
  return lines.join('\n');
}

function formatSearch(query, data) {
  const results = Array.isArray(data) ? data : data.results || [];
  if (results.length === 0) return `No results for "${query}"`;
  return `Search results for "${query}":\n` + results.slice(0, 5).map(r =>
    `- ${r.title || r.name || '?'}: ${(r.snippet || r.description || '').slice(0, 150)}`
  ).join('\n');
}

function formatTrending(data) {
  const coins = Array.isArray(data) ? data : data.coins || [];
  if (coins.length === 0) return JSON.stringify(data, null, 2).slice(0, 2000);
  return 'Trending:\n' + coins.slice(0, 10).map((c, i) =>
    `${i + 1}. ${c.symbol || c.name || c.id || '?'} — $${c.price || '?'}`
  ).join('\n');
}

function formatNews(data) {
  const articles = Array.isArray(data) ? data : data.articles || data.news || [];
  if (articles.length === 0) return JSON.stringify(data, null, 2).slice(0, 2000);
  return 'Latest News:\n' + articles.slice(0, 8).map(a =>
    `- ${a.title || '?'} (${a.source || ''})`
  ).join('\n');
}

// ============ HELPERS ============

function extractSymbol(message, state) {
  const text = (typeof message === 'string' ? message : message?.content?.text || '') || '';
  const symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOT', 'LINK', 'MATIC', 'ARB', 'OP'];
  const upper = text.toUpperCase();
  for (const s of symbols) {
    if (upper.includes(s)) return s;
  }
  return null;
}

function extractQuery(message, state) {
  const text = (typeof message === 'string' ? message : message?.content?.text || '') || '';
  // Remove trigger words to get the query
  const cleaned = text.replace(/^(search|research|look up|find|investigate)\s+(for|about|on)?\s*/i, '').trim();
  return cleaned || null;
}

// ============ PROVIDER ============

const marketContextProvider = {
  name: 'agentservices_market_context',
  description: 'Passively injects current BTC/ETH prices and Fear & Greed sentiment into every agent turn.',
  get: async (runtime, message, state) => {
    try {
      const data = await callEndpoint(runtime, '/v1/prices', {});
      const btc = Array.isArray(data) ? data.find(c => c.symbol === 'BTC' || c.id === 'bitcoin') : null;
      const eth = Array.isArray(data) ? data.find(c => c.symbol === 'ETH' || c.id === 'ethereum') : null;
      const lines = [];
      if (btc) lines.push(`BTC: $${Number(btc.price || btc.current_price).toLocaleString()}`);
      if (eth) lines.push(`ETH: $${Number(eth.price || eth.current_price).toLocaleString()}`);
      if (lines.length > 0) {
        return { text: `[AgentServices Market Context] ${lines.join(' | ')}`, values: {}, data: {} };
      }
    } catch (e) {
      // Silent fail for provider
    }
    return { text: '', values: {}, data: {} };
  },
};

// ============ EXPORT ============

export const agentservicesPlugin = {
  name: 'agentservices',
  description: 'AgentServices — 50+ paid APIs for AI agents. Crypto data, market intelligence, DeFi strategy, portfolio analysis, on-chain analytics, AI inference, and web search via x402 micropayments on Base.',
  actions: [
    cryptoPricesAction,
    indicatorsAction,
    defiYieldsAction,
    fearGreedAction,
    portfolioAction,
    marketPulseAction,
    defiStrategyAction,
    onchainAction,
    researchAction,
    searchAction,
    trendingAction,
    newsAction,
  ],
  providers: [marketContextProvider],
};

export default agentservicesPlugin;
