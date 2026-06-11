---
name: osint
description: Use this skill when performing Open Source Intelligence gathering — social media, email, DNS, web, breach, phone, crypto, dark web
---

# OSINT Skill Guide

## Overview
FRIDAY has **460+ OSINT functions** across social media analysis, email discovery, DNS deep recon, web tech detection, URL scanning, breach analysis, phone intelligence, cryptocurrency tracking, dark web monitoring, and more. Use the dedicated osint_extra bridge for single-purpose tools, or `osint_full_scan` for comprehensive profiling.

## Triggers
- "OSINT", "reconnaissance", "investigate", "intelligence gathering"
- "find information about", "profile", "scan", "enumerate"
- "email lookup", "username search", "domain recon", "IP analysis"
- "breach check", "leak check", "dark web"
- "social media investigation", "digital footprint"

## Tool Categories & When to Use

### Social Media OSINT (username-based)
| Tool | Purpose |
|------|---------|
| `social_analyzer(username)` | Check username across 30+ social platforms |
| `instagram_osint(username)` | Public Instagram profile info |
| `twitter_osint(username)` | Public Twitter/X profile info |
| `facebook_osint(query)` | Facebook public directory search |
| `linkedin_osint(query)` | LinkedIn public profile search |
| `tiktok_osint(username)` | TikTok profile info |
| `telegram_osint(username)` | Telegram username existence |
| `reddit_osint(username)` | Reddit user info (karma, age via JSON API) |
| `social_links_extractor(url)` | Extract social links from a webpage |

### Email OSINT
| Tool | Purpose |
|------|---------|
| `holehe_check(email)` | Check if email is on 120+ services |
| `email_rep(email)` | Email reputation check |
| `email_format(first, last, domain)` | Generate email format permutations |
| `leak_check(email)` | Multi-source data breach check |
| `email_breach_multi(email)` | Extended multi-source breach check |

### DNS & Domain OSINT
| Tool | Purpose |
|------|---------|
| `dns_enum(domain)` | Full DNS enumeration (A, AAAA, MX, NS, TXT, SOA, CNAME) |
| `dns_bruteforce(domain)` | Brute-force subdomains (100+ wordlist) |
| `dns_zone_transfer(domain)` | Attempt zone transfer |
| `dns_reverse(ip)` | Reverse DNS lookup |
| `spf_check(domain)` | SPF record check |
| `dkim_check(domain)` | DKIM record check |
| `dmarc_check(domain)` | DMARC record check with policy analysis |
| `mx_lookup(domain)` | MX record with priority |
| `whois_lookup(domain)` | WHOIS lookup |
| `certificate_transparency(domain)` | crt.sh certificate transparency search |

### Web & URL OSINT
| Tool | Purpose |
|------|---------|
| `whatweb(url)` | Web technology fingerprinting (CMS, frameworks, CDN) |
| `whatcms(url)` | CMS-specific detection |
| `cdn_detect(domain)` | CDN provider detection |
| `web_server_headers(url)` | HTTP response headers |
| `url_analyze(url)` | URL structure analysis |
| `url_expander(url)` | Expand shortened URLs |
| `urlscan_submit/result(uuid)` | URLScan.io scanning |
| `wayback_snapshots(domain)` | Wayback Machine snapshot count |

### IP & Network OSINT
| Tool | Purpose |
|------|---------|
| `ip_geolocate_full(ip)` | Full IP geolocation |
| `ip_abuse_report(ip)` | AbuseIPDB check |
| `ip_threat_intel(ip)` | Multi-source threat intel |
| `ip_blacklist_check(ip)` | DNSBL check against 20+ blacklists |
| `ip_reverse_dns(ip)` | Reverse DNS |
| `ip_asn_info(ip)` | ASN information |
| `port_scan(host, ports)` | TCP port scanning |
| `ping_host(host)` | ICMP ping check |

### Cryptocurrency & Dark Web
| Tool | Purpose |
|------|---------|
| `btc_address_lookup(address)` | Bitcoin address transactions |
| `eth_address_lookup(address)` | Ethereum address info |
| `wallet_balance(address)` | Crypto wallet balance |
| `onion_check(url)` | Check .onion site accessibility |
| `tor_dns_lookup(domain)` | DNS via Tor proxy |

### Validation & Analysis
- `validate_*()` — Validate IP, domain, email, URL, phone, hash, MAC, SSN, CVE, VIN, IBAN, credit card, Bitcoin/Ethereum addresses
- `compare_*()` — Compare domains, emails, IPs, usernames, phones, URLs, names
- `analysis_*()` — Port scan summary, DNS record summary, email/domain/URL/IP/phone/username analysis
- `score_*()` — Threat level, confidence, reputation, risk score, trust level

### Pipeline Tools (High-Level)
| Tool | Purpose |
|------|---------|
| `full_ip_intel(ip)` | Complete IP intelligence pipeline |
| `full_domain_intel(domain)` | Complete domain intelligence pipeline |
| `full_email_intel(email)` | Complete email intelligence pipeline |
| `full_url_intel(url)` | Complete URL intelligence pipeline |
| `full_hash_intel(hash)` | Complete hash intelligence pipeline |
| `osint_full_scan(target, type)` | ALL tools against email/username in one shot |

## Guidelines
- **ALWAYS** use `osint_full_scan` first for comprehensive profiling of a target
- **ALWAYS** use `dns_enum` before `dns_zone_transfer` (zone transfer is aggressive)
- **NEVER** skip error handling — OSINT APIs go down frequently
- **NEVER** spam a single target — add small delays between requests
- **ALWAYS** validate inputs with `validate_*()` before passing to OSINT functions
- **NEVER** store OSINT results without noting collection timestamp
- **ALWAYS** use `leak_check` for breach data, `email_rep` for reputation
- **PREFER** extended variants (`*_extended`) for deeper results
- **PREFER** batch tools (`batch_*`) for bulk operations (100+ targets)
- **ALWAYS** call `osint_to_markdown(result)` or `osint_to_html_report(result)` to format results for display

## Verification
1. Confirm input target is valid before querying
2. Check returned data has actual results, not just error/empty
3. Cross-reference findings from multiple sources
4. Append timestamps to all results
5. Format output for readability before presenting
