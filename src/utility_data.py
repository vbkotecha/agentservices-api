"""
Utility Data — Web extraction, package security, SEO keywords.
Niche endpoints that fill gaps on agentic.market Bazaar.

Web extraction: $0.002/call (volume play, 6 providers but all busy)
Package security: $0.02/call (only 1 provider — tensorfeed.ai)
SEO keywords: $0.01/call (SpyFu has 46 endpoints — proven demand)
"""
import urllib.request
import urllib.parse
import json
import re
import html
from html.parser import HTMLParser
from datetime import datetime
import os


def _fetch(url, timeout=10, headers=None):
    """Fetch raw content from URL."""
    h = {"User-Agent": "AgentServices/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode(errors="replace")


def _fetch_json(url, timeout=10, headers=None):
    """Fetch JSON from URL."""
    return json.loads(_fetch(url, timeout, headers))


# ============================================================
# BACKLINK LIST
# Public discovery providers return URL-level references. Bing remains an
# optional verified-site provider; domain-graph signals are not backlinks.
# ============================================================
def _bing_key():
    from letta_keys import load_key

    key = os.getenv("BING_WEBMASTER_API_KEY", "").strip()
    if key:
        return key
    return load_key("bing-webmaster.key", "BING_WEBMASTER_API_KEY") or load_key(
        "bing_webmaster.key", "BING_WEBMASTER_API_KEY"
    )


def _bing_json(method, params):
    key = _bing_key()
    if not key:
        return None
    query = urllib.parse.urlencode({**params, "apikey": key})
    url = f"https://ssl.bing.com/webmaster/api.svc/json/{method}?{query}"
    return _fetch_json(url, timeout=15)


def _bing_pages(site_url, method, page_limit=5):
    rows = []
    total_pages = None
    for page in range(page_limit):
        payload = _bing_json(method, {"siteUrl": site_url, "page": page})
        if not payload:
            break
        data = payload.get("d", payload)
        items = data.get("Links", []) if method == "GetLinkCounts" else data.get("Details", [])
        rows.extend(items)
        total_pages = data.get("TotalPages", total_pages)
        if total_pages is None or page + 1 >= total_pages:
            break
    return rows, total_pages


def _common_crawl_rank(domain):
    # Common Crawl publishes a compact lookup artifact for the top 1,000
    # domains. Do not download the multi-GB raw rank archive per request.
    payload = _fetch_json("https://commoncrawl.github.io/cc-webgraph-statistics/domain-lookup.json", timeout=15)
    reverse = ".".join(reversed(domain.lower().rstrip(".").split(".")))
    values = payload.get("domains", {}).get(reverse)
    if not values:
        return {"found": False, "scope": "top-ranked domains only", "releases": payload.get("releases", [])}
    releases = payload.get("releases", [])
    hc = values[0] if values else []
    pr = values[1] if len(values) > 1 else []
    latest = len(releases) - 1
    return {
        "found": True,
        "scope": "top-ranked domains only",
        "release": releases[latest] if latest >= 0 else None,
        "harmonic_centrality": hc[latest] if latest < len(hc) else None,
        "pagerank": pr[latest] if latest < len(pr) else None,
        "history": [{"release": r, "harmonic_centrality": hc[i] if i < len(hc) else None, "pagerank": pr[i] if i < len(pr) else None} for i, r in enumerate(releases)],
    }


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href, self._text = None, []


def _public_search_references(domain, limit=25):
    """Discover ordinary indexed web results without claiming an index count."""
    query_text = f'"{domain}" -site:{domain}'
    query = urllib.parse.quote(query_text)
    url = f"https://html.duckduckgo.com/html/?q={query}"
    raw = _fetch(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (compatible; AgentServices/1.0)"})
    parser = _LinkParser()
    parser.feed(raw)
    rows, seen = [], set()
    for href, text in parser.links:
        href = html.unescape(href)
        match = re.search(r"/url\?q=(https?://[^&]+)", href)
        href = urllib.parse.unquote(match.group(1)) if match else href
        if href.startswith("//duckduckgo.com/l/?uddg="):
            href = urllib.parse.parse_qs(urllib.parse.urlparse("https:" + href).query).get("uddg", [href])[0]
        if href.startswith("//duckduckgo.com/l/?uddg="):
            href = urllib.parse.parse_qs(urllib.parse.urlparse("https:" + href).query).get("uddg", [href])[0]
        if not href.startswith(("http://", "https://")) or _is_self_url(href, domain) or href in seen:
            continue
        seen.add(href)
        rows.append(_evidence(href, domain, "public_search", "indexed_reference", verified=False,
            evidence="public search result for exact target-domain query", title=html.unescape(text)[:300]))
        if len(rows) >= limit:
            break
    return {"query": query_text, "pages": rows, "count": len(rows), "verified": False}


def _exa_key():
    return os.getenv("EXA_API_KEY", "").strip()


def _hostname(url):
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def _is_self_url(url, domain):
    host = _hostname(url)
    return host == domain or host.endswith("." + domain)


def _evidence(url, domain, source, kind, *, verified=False, **extra):
    row = {
        "url": url,
        "source_domain": _hostname(url),
        "source": source,
        "type": kind,
        "target": "https://" + domain + "/",
        "verified": verified,
    }
    row.update(extra)
    return row


def _exa_backlinks(domain, limit=25):
    key = _exa_key()
    if not key:
        return {"configured": False, "pages": [], "error": "not_configured"}
    query = f'pages linking to or documenting "{domain}"'
    payload = {"query": query, "numResults": min(max(limit, 1), 50), "contents": {"text": {"maxCharacters": 12000}}}
    req = urllib.request.Request("https://api.exa.ai/search", data=json.dumps(payload).encode(),
        headers={"x-api-key": key, "Content-Type": "application/json", "User-Agent": "AgentServices/1.0"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode(errors="replace"))
    pages = []
    for item in data.get("results", []):
        url, text = (item.get("url") or "").strip(), item.get("text") or ""
        if url and not _is_self_url(url, domain) and domain in text.lower():
            pages.append(_evidence(url, domain, "exa", "indexed_reference", evidence="target domain present in indexed page content", title=item.get("title", "")))
    return {"configured": True, "query": query, "pages": pages, "count": len(pages)}


def _github_references(domain, limit=50):
    """Search GitHub code and return a bounded, domain-dedupable candidate set."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AgentServices/1.0"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    query = urllib.parse.quote(f'"{domain}"')
    req = urllib.request.Request(f"https://api.github.com/search/code?q={query}&per_page={min(limit, 50)}", headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode(errors="replace"))
    pages = []
    for item in data.get("items", []):
        url = item.get("html_url")
        repo = item.get("repository", {})
        if not url or _is_self_url(url, domain):
            continue
        pages.append(_evidence(url, domain, "github", "indexed_reference", verified=True,
            evidence="GitHub code search matched the target domain", title=item.get("name", ""),
            repository=repo.get("full_name", ""), path=item.get("path", "")))
    return {"query": f'"{domain}"', "pages": pages, "count": len(pages),
            "code_search_total": data.get("total_count"), "repositories_scanned": len(data.get("items", []))}


def _npm_references(domain, limit=50):
    data = _fetch_json(f"https://registry.npmjs.org/-/v1/search?text={urllib.parse.quote(domain)}&size={min(limit, 250)}", timeout=15)
    pages = []
    for item in data.get("objects", []):
        package = item.get("package", {})
        name, links = package.get("name"), package.get("links", {})
        if not name:
            continue
        homepage = links.get("homepage", "")
        repo = links.get("repository", "")
        # npm search can match package names/descriptions without a link.
        if domain not in (homepage + " " + repo).lower():
            continue
        # A package owned by the target is a first-party surface, not an
        # external backlink. Do not count it in this endpoint.
        if _is_self_url(homepage, domain) or _is_self_url(repo, domain):
            continue
        pages.append(_evidence(f"https://www.npmjs.com/package/{urllib.parse.quote(name, safe='@/')}", domain,
            "npm", "ecosystem_surface", verified=True, evidence="npm metadata homepage or repository points to target domain",
            title=name, description=package.get("description", ""), version=package.get("version"), homepage=homepage, repository=repo))
    return {"query": domain, "pages": pages, "count": len(pages)}


def backlink_intelligence(domain: str, site_url: str | None = None):
    """Return a URL-level list of external pages that reference the domain."""
    domain = domain.strip().lower().replace("https://", "").replace("http://", "").split("/", 1)[0]
    if not domain or "." not in domain or any(ch in domain for ch in " <>\\\"'"):
        raise ValueError("domain must be a hostname")

    result = {
        "domain": domain,
        "status": "insufficient_data",
        "count": 0,
        "backlinks": [],
        "referring_domains": [],
    }
    providers = (
        ("github", _github_references, "GitHub code search"),
        ("npm", _npm_references, "npm package metadata"),
        ("public_search", _public_search_references, "public search results"),
        ("exa", _exa_backlinks, "Exa indexed pages"),
    )
    for name, loader, _label in providers:
        try:
            data = loader(domain)
            rows = [row for row in data.get("pages", []) if row.get("url") and not _is_self_url(row["url"], domain)]
            result["backlinks"].extend(rows)
        except Exception:
            continue

    # One canonical evidence URL per referring domain. The backlink list and
    # referring_domains summary must represent the same deduplicated set.
    by_domain = {}
    for row in result["backlinks"]:
        url = row.get("url")
        referring_domain = row.get("source_domain") or _hostname(url or "")
        if not url or not referring_domain:
            continue
        row["referring_domain"] = referring_domain
        by_domain.setdefault(referring_domain, row)
    result["backlinks"] = list(by_domain.values())[:1000]
    result["referring_domains"] = [row["referring_domain"] for row in result["backlinks"]]
    result["count"] = len(result["backlinks"])
    if result["count"]:
        result["status"] = "ok"
    return result


# ============================================================
# WEB CONTENT EXTRACTION — Clean text from any URL
# $0.002 per call (volume play)
# ============================================================
def extract_web_content(url: str):
    """
    Fetch a URL and extract clean, token-efficient text.
    Strips navigation, ads, scripts, and boilerplate.
    Returns markdown-formatted content.

    6 providers on Bazaar charge $0.001-$0.01 for this. We're competitive at $0.002.
    """
    try:
        raw = _fetch(url, timeout=15)

        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', raw, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # Remove scripts, styles, nav, footer, header
        clean = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<nav[^>]*>.*?</nav>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<footer[^>]*>.*?</footer>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<header[^>]*>.*?</header>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<aside[^>]*>.*?</aside>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<!--.*?-->', '', clean, flags=re.DOTALL)

        # Convert common HTML to text
        # Preserve paragraphs and headings
        clean = re.sub(r'<h[1-6][^>]*>', '\n## ', clean, flags=re.IGNORECASE)
        clean = re.sub(r'</h[1-6]>', '\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'<p[^>]*>', '\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'</p>', '\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'<br[^>]*/?>', '\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'<li[^>]*>', '\n- ', clean, flags=re.IGNORECASE)

        # Extract meta description
        desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', raw, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else ""

        # og:description fallback
        if not description:
            og_match = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', raw, re.IGNORECASE)
            description = og_match.group(1).strip() if og_match else ""

        # Strip remaining HTML tags
        clean = re.sub(r'<[^>]+>', ' ', clean)

        # Decode HTML entities
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")

        # Collapse whitespace
        clean = re.sub(r'[ \t]+', ' ', clean)
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        clean = clean.strip()

        # Truncate to reasonable length for agents (token-efficient)
        max_chars = 10000
        truncated = len(clean) > max_chars
        clean = clean[:max_chars]

        return {
            "url": url,
            "title": title[:200],
            "description": description[:500],
            "content": clean,
            "content_length": len(clean),
            "truncated": truncated,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "url": url, "status": "error"}


# ============================================================
# PACKAGE SECURITY SCAN — Check PyPI/npm packages for vulnerabilities
# $0.02 per call (only 1 provider — tensorfeed.ai)
# Data: OSV API (free, open vulnerability database)
# ============================================================
def scan_package_security(package: str, ecosystem: str = "PyPI"):
    """
    Check a package for known security vulnerabilities.
    Returns risk score and vulnerability details.

    Only 1 provider on Bazaar (tensorfeed.ai at $0.02). We match the price.
    Data source: OSV.dev (Google's open vulnerability database) — free.
    """
    try:
        # Query OSV API
        payload = json.dumps({"package": {"name": package, "ecosystem": ecosystem}}).encode()
        req = urllib.request.Request(
            "https://api.osv.dev/v1/query",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        vulns = data.get("vulns", [])

        if not vulns:
            return {
                "package": package,
                "ecosystem": ecosystem,
                "risk_score": 0,
                "risk_label": "Safe",
                "vulnerabilities_found": 0,
                "summary": f"No known vulnerabilities for {package} in {ecosystem}.",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        # Analyze vulnerabilities
        critical = []
        high = []
        moderate = []
        low = []

        for v in vulns:
            severity = "MODERATE"
            for s in v.get("severity", []):
                if s.get("type") == "CVSS_V3":
                    score_str = s.get("score", "")
                    # Extract CVSS score from vector string
                    cvss_match = re.search(r'CVSS:3.[01]/.*', score_str)
                    if cvss_match:
                        severity = "CRITICAL" if "ACUTE" in score_str.upper() else severity

            # Use database_specific severity if available
            db_specific = v.get("database_specific", {})
            if "severity" in db_specific:
                sev = db_specific["severity"].upper()
                if "CRITICAL" in sev:
                    severity = "CRITICAL"
                elif "HIGH" in sev:
                    severity = "HIGH"
                elif "MODERATE" in sev or "MEDIUM" in sev:
                    severity = "MODERATE"
                elif "LOW" in sev:
                    severity = "LOW"

            vuln_info = {
                "id": v.get("id", ""),
                "summary": v.get("summary", "")[:200],
                "severity": severity,
                "fixed_in": [],
                "aliases": v.get("aliases", [])[:5],
            }

            # Get fix versions
            for affected in v.get("affected", []):
                for r in affected.get("ranges", []):
                    for event in r.get("events", []):
                        if "fixed" in event:
                            vuln_info["fixed_in"].append(event["fixed"])

            if severity == "CRITICAL":
                critical.append(vuln_info)
            elif severity == "HIGH":
                high.append(vuln_info)
            elif severity == "MODERATE":
                moderate.append(vuln_info)
            else:
                low.append(vuln_info)

        # Risk score: weighted by severity
        risk_score = min(100, len(critical) * 30 + len(high) * 15 + len(moderate) * 5 + len(low))
        risk_label = "Critical" if risk_score >= 70 else "High" if risk_score >= 40 else "Moderate" if risk_score >= 15 else "Low"

        return {
            "package": package,
            "ecosystem": ecosystem,
            "risk_score": risk_score,
            "risk_label": risk_label,
            "vulnerabilities_found": len(vulns),
            "critical_count": len(critical),
            "high_count": len(high),
            "moderate_count": len(moderate),
            "low_count": len(low),
            "critical": critical[:5],
            "high": high[:5],
            "moderate": moderate[:5],
            "recommendation": "Update immediately" if critical or high else "Monitor for updates" if moderate else "Package appears safe",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "package": package, "status": "error"}


# ============================================================
# SEO KEYWORD RESEARCH — Search volume and competition
# $0.01 per call (SpyFu has 46 endpoints — proven demand)
# Data: Google Suggest API (free)
# ============================================================
def seo_keywords(keyword: str):
    """
    Keyword research data: related keywords, search suggestions,
    and competition signals.

    SpyFu charges $0.01 with 46 endpoints — proven demand.
    Data: Google Autocomplete API (free).
    """
    try:
        # Get Google autocomplete suggestions
        url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(keyword)}"
        data = _fetch_json(url, timeout=8)

        suggestions = data[1] if len(data) > 1 else []

        # Generate keyword variations
        variations = []
        for s in suggestions[:15]:
            # Estimate relative volume (higher position = higher volume)
            position = suggestions.index(s) + 1
            est_volume = max(100, 10000 // position)

            variations.append({
                "keyword": s,
                "estimated_monthly_volume": est_volume,
                "competition": "High" if position <= 3 else "Medium" if position <= 8 else "Low",
                "cpc_estimate": round(0.5 + (10 / position), 2),
            })

        # Question-based keywords (high intent)
        question_prefixes = ["how to", "what is", "best", "why", "when", "where", "vs"]
        questions = []
        for prefix in question_prefixes:
            q_url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(prefix + ' ' + keyword)}"
            try:
                q_data = _fetch_json(q_url, timeout=5)
                for q in q_data[1][:3]:
                    questions.append(q)
            except:
                continue

        return {
            "keyword": keyword,
            "related_keywords": variations,
            "question_keywords": questions[:10],
            "total_suggestions": len(variations),
            "top_keyword": variations[0]["keyword"] if variations else keyword,
            "top_volume_estimate": variations[0]["estimated_monthly_volume"] if variations else 0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "note": "Volume estimates are relative rankings from autocomplete position, not exact search volumes.",
        }
    except Exception as e:
        return {"error": str(e), "keyword": keyword, "status": "error"}
