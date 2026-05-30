import asyncio
import json
import os
import re
import socket
import ssl
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from ipaddress import ip_address, IPv4Network, IPv6Network
from typing import Any, Optional
from urllib.parse import urlparse

try:
    import dns.resolver
    import dns.zone
    import dns.query
    import dns.name
    import dns.update
    import dns.tsigkeyring
    import dns.reversename
    import dns.dnssec
    import dns.flags
    import dns.rdataclass
    import dns.rdatatype
    import dns.message
    import dns.asyncresolver
    import dns.asyncquery
    import dns.exception
    import dns.e164
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

# Default public resolvers for comparison
PUBLIC_RESOLVERS = [
    "8.8.8.8",
    "1.1.1.1",
    "9.9.9.9",
    "208.67.222.222",
    "8.8.4.4",
    "1.0.0.1",
    "149.112.112.112",
    "208.67.220.220",
]

# Common subdomain wordlist (built-in, no external file needed)
SUBDOMAIN_WORDLIST = [
    "www", "mail", "admin", "api", "blog", "dev", "test", "staging",
    "vpn", "remote", "webmail", "portal", "shop", "app", "cdn", "static",
    "assets", "images", "docs", "help", "support", "status", "ftp", "smtp",
    "pop", "imap", "mx", "ns1", "ns2", "ns3", "ns4", "dns", "dns1", "dns2",
    "autodiscover", "m", "mobile", "owa", "exchange", "lyncdiscover",
    "sip", "meet", "dialin", "teams", "skype", "lync", "webex", "zoom",
    "jira", "confluence", "bitbucket", "gitlab", "github", "git",
    "jenkins", "teamcity", "build", "ci", "cd", "deploy", "release",
    "monitor", "grafana", "prometheus", "kibana", "elastic", "logstash",
    "kafka", "rabbitmq", "redis", "memcached", "mysql", "postgres",
    "mongo", "mongodb", "couchdb", "cassandra", "couchbase", "mariadb",
    "db", "database", "sql", "nosql", "aurora", "rds",
    "backup", "backups", "snapshot", "snapshots", "archive", "archives",
    "upload", "uploads", "download", "downloads", "files", "file",
    "media", "video", "videos", "stream", "streaming", "live",
    "newsletter", "news", "notify", "notification", "push",
    "analytics", "metrics", "stats", "statistics", "dashboard",
    "search", "index", "catalog", "catalogue", "discovery",
    "auth", "login", "signin", "signup", "register", "registration",
    "sso", "oauth", "oauth2", "openid", "saml", "cas",
    "billing", "invoice", "payment", "payments", "checkout", "cart",
    "store", "shop", "market", "marketplace", "order", "orders",
    "partner", "partners", "affiliate", "affiliates", "reseller",
    "career", "careers", "jobs", "job", "hr", "human-resources",
    "recruit", "recruitment", "apply", "talent",
    "ir", "investor", "investors", "investor-relations",
    "press", "newsroom", "media-center", "mediacenter",
    "legal", "privacy", "terms", "gdpr", "compliance",
    "security", "trust", "safe", "safety", "abuse",
    "survey", "surveys", "feedback", "feature", "roadmap",
    "community", "forum", "forums", "discussion", "discuss",
    "wiki", "knowledgebase", "kb", "faq", "faqs",
    "training", "learn", "learning", "academy", "education",
    "demo", "demo1", "demo2", "sandbox", "playground",
    "stage", "staging", "uat", "qa", "qa1", "qa2", "quality",
    "beta", "beta1", "beta2", "alpha", "preprod", "pre-prod",
    "prod", "production", "live", "release", "rc", "v1", "v2",
    "us", "uk", "eu", "asia", "apac", "emea", "americas",
    "nyc", "london", "frankfurt", "singapore", "tokyo", "sydney",
    "aws", "ec2", "s3", "cloudfront", "elb", "alb", "nlb",
    "gcp", "compute", "storage", "bigquery", "appengine",
    "azure", "azurewebsites", "cloudapp", "trafficmanager",
    "docker", "k8s", "kubernetes", "swarm", "nomad",
    "grpc", "rpc", "api-gateway", "gateway", "proxy",
    "loadbalancer", "lb", "balancer", "ha", "cluster",
    "firewall", "fw", "waf", "ids", "ips", "honeypot",
    "ldap", "radius", "kerberos", "ntp", "dhcp",
    "caldav", "carddav", "webdav", "dav",
    "ns01", "ns02", "ns03", "ns1", "ns2", "ns3",
    "mail1", "mail2", "mail3", "smtp1", "smtp2",
    "pop3", "imap4", "exchange1", "exchange2",
    "owa", "ecp", "ews", "autodiscover",
    "lync", "lyncweb", "sfb", "skype",
    "adfs", "sts", "idp",
    "mdm", "jamf", "airwatch", "mobileiron",
    "virustotal", "google", "facebook", "twitter", "linkedin",
    "instagram", "youtube", "pinterest", "snapchat", "reddit",
    "wordpress", "wp", "wp-admin", "wp-content", "wp-includes",
    "joomla", "drupal", "magento", "shopify", "squarespace",
    "cpanel", "whm", "webmail", "webmailer", "roundcube",
    "phpmyadmin", "phpadmin", "adminer", "pgadmin",
    "tomcat", "jboss", "wildfly", "glassfish", "weblogic",
    "nginx", "apache", "httpd", "iis", "caddy",
    "php", "asp", "aspx", "jsp", "node", "python", "ruby",
    "ws", "wss", "websocket", "socketio", "mqtt",
    "rtmp", "rtsp", "hls", "dash", "mpegdash",
    "ipfs", "p2p", "tor", "i2p", "freenet",
    "mailgun", "sendgrid", "mailchimp", "constantcontact",
    "tawk", "livechat", "zendesk", "freshdesk", "helpscout",
    "s3", "bucket", "uploads", "assets",
    "xmlrpc", "xmlrpc.php", "wp-cron", "cron",
    "sitemap", "robots", "crossdomain", "clientaccesspolicy",
    "apple-touch-icon", "favicon", "manifest", "browserconfig",
    "serviceworker", "sw.js", "workbox",
    "manifest.json", "assetlinks.json", "apple-app-site-association",
    ".well-known", "well-known",
    "acme-challenge", "letsencrypt", "certbot",
    "pgp", "openpgp", "keybase", "key",
    "ssh", "sshfp", "sshkey", "authorized_keys",
    "git", "svn", "hg", "perforce",
    "brew", "homebrew", "cask",
    "rss", "atom", "feed", "feeds",
    "podcast", "podcasts", "itunes",
    "tickets", "support", "helpdesk",
    "remote-desktop", "rdp", "vnc", "teamviewer", "anydesk",
    "proxy", "squid", "nginx-proxy", "haproxy",
    "audit", "audits", "compliance", "sox", "hipaa",
    "devops", "sre", "platform", "infra", "infrastructure",
    "config", "configuration", "settings", "setup",
    "internal", "intranet", "corp", "corporate",
    "employee", "employees", "staff", "team",
    "edge", "iot", "device", "devices", "sensor",
    "labs", "lab", "research", "innovation",
    "status", "statuspage", "uptime", "down",
    "forms", "typeform", "google-forms",
    "events", "event", "webinar", "webinars",
    "docs", "documentation", "apidocs", "swagger",
    "redoc", "openapi", "api-docs", "api-documentation",
    "graphql", "gql", "hasura", "apollo",
    "sockjs", "sockjs-node", "webpack-hmr",
    "pma", "phpmyadmin", "mysql-admin", "adminer",
    "redis-admin", "redis-commander", "rabbitmq-admin",
    "kibana", "elasticsearch", "es",
    "alertmanager", "thanos", "cortex",
    "jupyter", "notebook", "lab", "hub",
    "airflow", "dagster", "prefect",
    "mlflow", "kubeflow", "polyaxon",
    "rancher", "portainer", "k9s",
]

# Common TLD list for domain expansion
COMMON_TLDS = [
    "com", "net", "org", "io", "co", "app", "dev", "me", "tv",
    "info", "biz", "xyz", "club", "online", "site", "tech", "store",
    "cloud", "digital", "live", "world", "top", "pro", "name",
    "uk", "de", "ca", "au", "fr", "eu", "jp", "in", "cn", "br",
    "nl", "it", "ru", "es", "se", "no", "fi", "dk", "pl", "at",
    "ch", "be", "ie", "nz", "sg", "hk", "kr", "za", "mx", "ar",
]

RECORD_TYPES_ALL = [
    "A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "SRV", "CAA",
    "SSHFP", "TLSA", "DNSKEY", "DS", "NSEC", "NSEC3", "RRSIG",
    "NAPTR", "PTR", "SPF", "LOC", "HINFO", "RP", "AFSDB",
    "CERT", "DHCID", "DNAME", "HIP", "IPSECKEY", "KEY", "KX",
    "MG", "MINFO", "MR", "MX", "NAPTR", "NSAP", "NSAP-PTR",
    "OPENPGPKEY", "RP", "RRSIG", "RT", "SIG", "SMIMEA",
    "SRV", "SSHFP", "TA", "TKEY", "TLSA", "TSIG", "TXT", "URI",
    "ZONEMD", "SVCB", "HTTPS",
]


async def dns_lookup(domain: str, record_types: Optional[list[str]] = None, resolver_ip: Optional[str] = None) -> dict[str, Any]:
    """Perform DNS lookups for multiple record types with detailed responses."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed. Run: pip install dnspython", "domain": domain}
    if record_types is None:
        record_types = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME", "SRV", "CAA", "SSHFP"]
    result: dict[str, Any] = {
        "domain": domain,
        "records": {},
        "timing_ms": {},
        "resolver": resolver_ip or "system",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    resolver = dns.resolver.Resolver()
    if resolver_ip:
        resolver.nameservers = [resolver_ip]
    resolver.timeout = 5
    resolver.lifetime = 10
    for rtype in record_types:
        start = time.time()
        try:
            answers = await asyncio.get_event_loop().run_in_executor(
                None, lambda rt=rtype: list(resolver.resolve(domain, rt))
            )
            elapsed = round((time.time() - start) * 1000, 1)
            parsed = []
            for a in answers:
                entry = {"value": str(a)}
                if rtype == "MX":
                    entry["preference"] = a.preference if hasattr(a, "preference") else None
                    entry["exchange"] = str(a.exchange) if hasattr(a, "exchange") else None
                elif rtype == "SOA":
                    entry["mname"] = str(a.mname) if hasattr(a, "mname") else None
                    entry["rname"] = str(a.rname) if hasattr(a, "rname") else None
                    entry["serial"] = a.serial if hasattr(a, "serial") else None
                    entry["refresh"] = a.refresh if hasattr(a, "refresh") else None
                    entry["retry"] = a.retry if hasattr(a, "retry") else None
                    entry["expire"] = a.expire if hasattr(a, "expire") else None
                    entry["minimum"] = a.minimum if hasattr(a, "minimum") else None
                elif rtype == "SRV":
                    entry["priority"] = a.priority if hasattr(a, "priority") else None
                    entry["weight"] = a.weight if hasattr(a, "weight") else None
                    entry["port"] = a.port if hasattr(a, "port") else None
                    entry["target"] = str(a.target) if hasattr(a, "target") else None
                elif rtype == "CAA":
                    entry["flags"] = a.flags if hasattr(a, "flags") else None
                    entry["tag"] = a.tag.decode() if hasattr(a, "tag") and isinstance(a.tag, bytes) else str(getattr(a, "tag", ""))
                    entry["value"] = a.value.decode() if hasattr(a, "value") and isinstance(a.value, bytes) else str(getattr(a, "value", ""))
                elif rtype == "SSHFP":
                    entry["algorithm"] = a.algorithm if hasattr(a, "algorithm") else None
                    entry["fp_type"] = a.fp_type if hasattr(a, "fp_type") else None
                    entry["fingerprint"] = a.fingerprint.hex() if hasattr(a, "fingerprint") else None
                parsed.append(entry)
            result["records"][rtype] = parsed
            result["timing_ms"][rtype] = elapsed
        except dns.resolver.NoAnswer:
            result["records"][rtype] = []
            result["timing_ms"][rtype] = 0
        except dns.resolver.NXDOMAIN:
            result["records"][rtype] = [{"error": "NXDOMAIN"}]
            result["timing_ms"][rtype] = 0
        except dns.exception.Timeout:
            result["records"][rtype] = [{"error": "TIMEOUT"}]
            result["timing_ms"][rtype] = -1
        except Exception as e:
            result["records"][rtype] = [{"error": str(e)}]
            result["timing_ms"][rtype] = -1
    return result


async def dns_bulk_lookup(domains: list[str], record_types: Optional[list[str]] = None) -> dict[str, Any]:
    """Perform DNS lookups for multiple domains in parallel."""
    if not domains:
        return {"error": "No domains provided", "results": []}
    tasks = [dns_lookup(d, record_types) for d in domains]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        "domains_checked": len(domains),
        "results": [
            r if not isinstance(r, Exception) else {"domain": domains[i], "error": str(r)}
            for i, r in enumerate(results)
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def dns_reverse_lookup(ip: str) -> dict[str, Any]:
    """Reverse DNS lookup - find hostname for an IP address."""
    result: dict[str, Any] = {
        "ip": ip,
        "hostname": None,
        "aliases": [],
        "ptr_record": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        hostname = await asyncio.get_event_loop().run_in_executor(None, socket.gethostbyaddr, ip)
        result["hostname"] = hostname[0]
        result["aliases"] = list(hostname[1])
    except socket.herror as e:
        result["error"] = f"No reverse record: {e}"
    except Exception as e:
        result["error"] = str(e)
    if HAS_DNSPYTHON:
        try:
            rev = dns.reversename.from_address(ip)
            answers = await asyncio.get_event_loop().run_in_executor(
                None, lambda: list(dns.resolver.resolve(rev, "PTR"))
            )
            result["ptr_record"] = [str(a) for a in answers]
        except Exception:
            pass
    return result


async def dns_reverse_sweep(network_cidr: str) -> dict[str, Any]:
    """Reverse DNS sweep across an entire CIDR subnet."""
    try:
        if "/" in network_cidr:
            net = IPv4Network(network_cidr, strict=False)
        else:
            net = IPv4Network(f"{network_cidr}/24", strict=False)
    except ValueError as e:
        return {"error": f"Invalid CIDR: {e}"}
    total = net.num_addresses
    if total > 4096:
        return {"error": f"Network too large ({total} hosts). Maximum 4096."}
    ips = [str(ip) for ip in net.hosts()]
    tasks = [dns_reverse_lookup(ip) for ip in ips]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    found = []
    for i, r in enumerate(results_list):
        if not isinstance(r, Exception) and r.get("hostname"):
            found.append({"ip": ips[i], "hostname": r["hostname"], "aliases": r.get("aliases", [])})
    return {
        "network": network_cidr,
        "total_scanned": total,
        "records_found": len(found),
        "results": found[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def dns_mx_lookup(domain: str) -> dict[str, Any]:
    """Detailed MX record lookup with priority sorting and mail server analysis."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {"domain": domain, "mail_servers": [], "count": 0}
    try:
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(domain, "MX"))
        )
        mx_records = [(a.preference, str(a.exchange)) for a in answers]
        mx_records.sort(key=lambda x: x[0])
        result["mail_servers"] = [
            {"priority": pref, "exchange": exch} for pref, exch in mx_records
        ]
        result["count"] = len(mx_records)
        for ms in result["mail_servers"]:
            try:
                a_recs = await dns_lookup(ms["exchange"], ["A", "AAAA"])
                ms["ips"] = a_recs.get("records", {}).get("A", [])
                ms["ipv6"] = a_recs.get("records", {}).get("AAAA", [])
            except Exception:
                ms["ips"] = []
    except dns.resolver.NoAnswer:
        result["error"] = "No MX records found"
    except dns.resolver.NXDOMAIN:
        result["error"] = "Domain does not exist (NXDOMAIN)"
    except Exception as e:
        result["error"] = str(e)
    return result


async def dns_zone_transfer(domain: str, nameserver: Optional[str] = None) -> dict[str, Any]:
    """Attempt DNS zone transfer (AXFR) - security check."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {
        "domain": domain,
        "zone_transfer_possible": False,
        "records": [],
        "tested_servers": [],
        "warning": "Zone transfers should be restricted. If this succeeds, your DNS is misconfigured.",
    }
    if nameserver:
        ns_list = [nameserver]
    else:
        try:
            ns_answers = await asyncio.get_event_loop().run_in_executor(
                None, lambda: list(dns.resolver.resolve(domain, "NS"))
            )
            ns_list = [str(a) for a in ns_answers]
        except Exception:
            ns_list = PUBLIC_RESOLVERS[:3]
    for ns in ns_list:
        server_result = {"nameserver": ns, "success": False, "records_count": 0}
        try:
            zone = await asyncio.get_event_loop().run_in_executor(
                None, lambda ns=ns, domain=domain: dns.zone.from_xfr(dns.query.xfr(ns, domain, timeout=5))
            )
            if zone:
                records = []
                for name, node in zone.nodes.items():
                    rdataset = node.rdatasets
                    for rds in rdataset:
                        for rdata in rds:
                            records.append({
                                "name": str(name),
                                "type": dns.rdatatype.to_text(rds.rdtype),
                                "ttl": rds.ttl,
                                "value": str(rdata),
                            })
                server_result["success"] = True
                server_result["records_count"] = len(records)
                result["records"].extend(records)
                result["zone_transfer_possible"] = True
        except dns.exception.FormError:
            server_result["error"] = "FormError - zone transfer rejected"
        except dns.query.TransferError:
            server_result["error"] = "TransferError - zone transfer rejected"
        except ConnectionRefusedError:
            server_result["error"] = "Connection refused"
        except Exception as e:
            server_result["error"] = str(e)[:200]
        result["tested_servers"].append(server_result)
    return result


async def dns_compare_resolvers(domain: str, record_type: str = "A") -> dict[str, Any]:
    """Compare DNS results across multiple public resolvers (DNS poisoning detection)."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {
        "domain": domain,
        "record_type": record_type,
        "results": [],
        "all_identical": True,
        "resolvers_tested": 0,
    }
    first_result = None
    for resolver_ip in PUBLIC_RESOLVERS:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [resolver_ip]
            resolver.timeout = 3
            resolver.lifetime = 5
            answers = await asyncio.get_event_loop().run_in_executor(
                None, lambda: [str(a) for a in resolver.resolve(domain, record_type)]
            )
            entry = {"resolver": resolver_ip, "answers": answers}
            if first_result is None:
                first_result = set(answers)
            elif set(answers) != first_result:
                result["all_identical"] = False
                entry["mismatch"] = True
            else:
                entry["mismatch"] = False
            result["results"].append(entry)
            result["resolvers_tested"] += 1
        except Exception as e:
            result["results"].append({"resolver": resolver_ip, "error": str(e)[:100]})
            result["resolvers_tested"] += 1
    return result


async def dns_dnssec_check(domain: str) -> dict[str, Any]:
    """Check DNSSEC status for a domain."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {
        "domain": domain,
        "dnssec_signed": False,
        "algorithms": [],
        "digests": [],
        "flags": [],
        "errors": [],
    }
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 10
    try:
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(resolver.resolve(domain, "DNSKEY"))
        )
        result["dnssec_signed"] = True
        for key in answers:
            result["algorithms"].append({
                "algorithm": key.algorithm,
                "flags": key.flags,
                "protocol": key.protocol,
                "key_tag": key.key_tag() if hasattr(key, "key_tag") else None,
            })
            result["flags"].append(key.flags)
    except dns.resolver.NoAnswer:
        result["errors"].append("No DNSKEY records found - domain not DNSSEC signed")
    except dns.resolver.NXDOMAIN:
        result["errors"].append("Domain does not exist")
    except Exception as e:
        result["errors"].append(str(e))
    try:
        ds_answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(resolver.resolve(domain, "DS"))
        )
        for ds in ds_answers:
            result["digests"].append({
                "key_tag": ds.key_tag,
                "algorithm": ds.algorithm,
                "digest_type": ds.digest_type,
                "digest": ds.digest.hex(),
            })
    except Exception:
        pass
    return result


async def dns_spf_check(domain: str) -> dict[str, Any]:
    """Extract and analyze SPF records for email security assessment."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {
        "domain": domain,
        "spf_record": None,
        "spf_mechanisms": [],
        "all_mechanism": None,
        "includes": [],
        "ip4_ranges": [],
        "ip6_ranges": [],
        "has_redirect": False,
        "valid": False,
    }
    try:
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(domain, "TXT"))
        )
        for txt in answers:
            txt_str = str(txt)
            if txt_str.startswith("v=spf1"):
                result["spf_record"] = txt_str
                result["valid"] = True
                mechanisms = txt_str.split()
                for mech in mechanisms:
                    if mech == "-all":
                        result["all_mechanism"] = "hardfail"
                    elif mech == "~all":
                        result["all_mechanism"] = "softfail"
                    elif mech == "?all":
                        result["all_mechanism"] = "neutral"
                    elif mech == "+all":
                        result["all_mechanism"] = "pass"
                    elif mech.startswith("include:"):
                        result["includes"].append(mech[8:])
                    elif mech.startswith("ip4:"):
                        result["ip4_ranges"].append(mech[4:])
                    elif mech.startswith("ip6:"):
                        result["ip6_ranges"].append(mech[4:])
                    elif mech.startswith("redirect="):
                        result["has_redirect"] = True
                    result["spf_mechanisms"].append(mech)
                break
    except dns.resolver.NoAnswer:
        result["error"] = "No TXT records found"
    except Exception as e:
        result["error"] = str(e)
    return result


async def dns_dmarc_check(domain: str) -> dict[str, Any]:
    """Check DMARC policy for a domain."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {
        "domain": domain,
        "dmarc_record": None,
        "policy": None,
        "subdomain_policy": None,
        "pct": None,
        "rua": [],
        "ruf": [],
        "fo": None,
        "adkim": None,
        "aspf": None,
        "tags": {},
    }
    try:
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(f"_dmarc.{domain}", "TXT"))
        )
        for txt in answers:
            txt_str = str(txt)
            if txt_str.startswith("v=DMARC1"):
                result["dmarc_record"] = txt_str
                tags = txt_str.split(";")
                for tag in tags:
                    tag = tag.strip()
                    if "=" in tag:
                        key, val = tag.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        result["tags"][key] = val
                        if key == "p":
                            result["policy"] = val
                        elif key == "sp":
                            result["subdomain_policy"] = val
                        elif key == "pct":
                            result["pct"] = int(val)
                        elif key == "rua":
                            result["rua"] = [u.strip() for u in val.split(",")]
                        elif key == "ruf":
                            result["ruf"] = [u.strip() for u in val.split(",")]
                        elif key == "fo":
                            result["fo"] = val
                        elif key == "adkim":
                            result["adkim"] = val
                        elif key == "aspf":
                            result["aspf"] = val
                break
    except dns.resolver.NoAnswer:
        result["error"] = "No DMARC record found"
    except dns.resolver.NXDOMAIN:
        result["error"] = "_dmarc subdomain does not exist"
    except Exception as e:
        result["error"] = str(e)
    return result


async def dns_dkim_check(domain: str, selector: str = "default") -> dict[str, Any]:
    """Check DKIM record for a specific selector."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {
        "domain": domain,
        "selector": selector,
        "dkim_record": None,
        "public_key": None,
        "version": None,
        "key_type": None,
        "flags": None,
        "service_type": None,
        "hash_algorithm": None,
        "tags": {},
    }
    try:
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(f"{selector}._domainkey.{domain}", "TXT"))
        )
        for txt in answers:
            txt_str = str(txt)
            if txt_str.startswith("v=DKIM1"):
                result["dkim_record"] = txt_str
                tags = txt_str.split(";")
                for tag in tags:
                    tag = tag.strip()
                    if "=" in tag:
                        key, val = tag.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        result["tags"][key] = val
                        if key == "v":
                            result["version"] = val
                        elif key == "k":
                            result["key_type"] = val
                        elif key == "p":
                            result["public_key"] = val
                        elif key == "s":
                            result["flags"] = val
                        elif key == "t":
                            result["service_type"] = val
                        elif key == "h":
                            result["hash_algorithm"] = val
                break
    except dns.resolver.NoAnswer:
        result["error"] = f"No DKIM record found for selector '{selector}'"
    except Exception as e:
        result["error"] = str(e)
    return result


async def dns_email_security_audit(domain: str) -> dict[str, Any]:
    """Comprehensive email security audit: SPF + DKIM + DMARC + MX + STARTTLS."""
    result: dict[str, Any] = {
        "domain": domain,
        "overall_score": 0,
        "max_score": 10,
        "checks": {},
        "recommendations": [],
    }
    spf_result = await dns_spf_check(domain)
    result["checks"]["spf"] = spf_result
    if spf_result.get("spf_record"):
        result["overall_score"] += 2
        if spf_result.get("all_mechanism") == "hardfail":
            result["overall_score"] += 1
    else:
        result["recommendations"].append("Add an SPF record to prevent email spoofing")
    dmarc_result = await dns_dmarc_check(domain)
    result["checks"]["dmarc"] = dmarc_result
    if dmarc_result.get("dmarc_record"):
        result["overall_score"] += 2
        policy = dmarc_result.get("policy")
        if policy == "reject":
            result["overall_score"] += 2
        elif policy == "quarantine":
            result["overall_score"] += 1
    else:
        result["recommendations"].append("Add a DMARC record to control email handling")
    for selector in ["default", "google", "dkim", "mail", "selector1", "s1", "smtp"]:
        dkim_result = await dns_dkim_check(domain, selector)
        if dkim_result.get("dkim_record"):
            result["checks"].setdefault("dkim", []).append(dkim_result)
            result["overall_score"] += 1
            break
    if "dkim" not in result["checks"]:
        result["recommendations"].append("Add DKIM signing to authenticate outgoing emails")
        result["checks"]["dkim"] = {"error": "No DKIM record found for common selectors"}
    mx_result = await dns_mx_lookup(domain)
    result["checks"]["mx"] = mx_result
    if mx_result.get("count", 0) > 0:
        result["overall_score"] += 1
        for server in mx_result.get("mail_servers", []):
            if "google.com" in server.get("exchange", "") or "protect" in server.get("exchange", ""):
                result["overall_score"] += 1
    else:
        result["recommendations"].append("Configure MX records for email delivery")
    if result["overall_score"] >= 8:
        result["rating"] = "Excellent"
    elif result["overall_score"] >= 5:
        result["rating"] = "Good"
    elif result["overall_score"] >= 3:
        result["rating"] = "Fair"
    else:
        result["rating"] = "Poor"
    return result


async def dns_certificate_search(domain: str) -> dict[str, Any]:
    """Search crt.sh Certificate Transparency logs for subdomains."""
    if not HAS_HTTPX:
        return dns_certificate_search_fallback(domain)
    result: dict[str, Any] = {
        "domain": domain,
        "subdomains": [],
        "certificates_found": 0,
        "source": "crt.sh",
    }
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(
                f"https://crt.sh/?q=%25.{domain}&output=json",
                headers={"User-Agent": "FRIDAY-OSINT/2.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                seen = set()
                for entry in data:
                    name = entry.get("name_value", "")
                    if name:
                        for sub in name.split("\n"):
                            sub = sub.strip().lower()
                            if sub.endswith(f".{domain}") and sub not in seen:
                                seen.add(sub)
                                result["subdomains"].append({
                                    "hostname": sub,
                                    "issuer": entry.get("issuer_name", ""),
                                    "not_before": entry.get("not_before", ""),
                                    "not_after": entry.get("not_after", ""),
                                })
                result["certificates_found"] = len(data)
                result["unique_subdomains"] = len(seen)
    except Exception as e:
        result["error"] = f"crt.sh query failed: {str(e)[:200]}"
        result["subdomains"] = []
    return result


async def dns_certificate_search_fallback(domain: str) -> dict[str, Any]:
    """Fallback crt.sh lookup using raw socket/requests."""
    import urllib.request
    import json as j
    result: dict[str, Any] = {
        "domain": domain,
        "subdomains": [],
        "certificates_found": 0,
        "source": "crt.sh (fallback)",
    }
    try:
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        req = urllib.request.Request(url, headers={"User-Agent": "FRIDAY-OSINT/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = j.loads(resp.read().decode())
        seen = set()
        for entry in data:
            name = entry.get("name_value", "")
            if name:
                for sub in name.split("\n"):
                    sub = sub.strip().lower()
                    if sub.endswith(f".{domain}") and sub not in seen:
                        seen.add(sub)
                        result["subdomains"].append({"hostname": sub})
        result["certificates_found"] = len(data)
        result["unique_subdomains"] = len(seen)
    except Exception as e:
        result["error"] = f"crt.sh fallback failed: {str(e)[:200]}"
    return result


async def dns_bruteforce_subdomains(
    domain: str,
    wordlist: Optional[list[str]] = None,
    concurrent: int = 50,
    resolve: bool = True,
    timeout_sec: float = 3.0,
) -> dict[str, Any]:
    """Bruteforce subdomains using wordlist with concurrent resolution."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed", "domain": domain}
    if wordlist is None:
        wordlist = SUBDOMAIN_WORDLIST
    result: dict[str, Any] = {
        "domain": domain,
        "subdomains": [],
        "resolved": [],
        "total_tried": len(wordlist),
        "found": 0,
        "concurrent": concurrent,
        "elapsed_seconds": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout_sec
    resolver.lifetime = timeout_sec * 2
    sem = asyncio.Semaphore(concurrent)
    found: list[dict] = []
    start = time.time()

    async def check_sub(sub: str) -> None:
        fqdn = f"{sub}.{domain}"
        async with sem:
            try:
                answers = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: list(resolver.resolve(fqdn, "A"))
                )
                ips = [str(a) for a in answers]
                entry = {"host": fqdn, "ips": ips}
                if resolve:
                    try:
                        cname_resolver = dns.resolver.Resolver()
                        cname_resolver.timeout = 2
                        cname_resolver.lifetime = 3
                        cnames = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: list(cname_resolver.resolve(fqdn, "CNAME"))
                        )
                        if cnames:
                            entry["cname"] = str(cnames[0])
                    except Exception:
                        pass
                found.append(entry)
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
                pass
            except Exception:
                pass

    tasks = [check_sub(sub) for sub in wordlist]
    await asyncio.gather(*tasks, return_exceptions=True)
    result["elapsed_seconds"] = round(time.time() - start, 2)
    result["found"] = len(found)
    result["subdomains"] = [f["host"] for f in found]
    result["resolved"] = found
    return result


async def dns_enumeration(domain: str, aggressive: bool = False) -> dict[str, Any]:
    """Full DNS enumeration: standard lookups + zone transfer check + bruteforce + crt.sh."""
    result: dict[str, Any] = {
        "domain": domain,
        "standard_lookups": {},
        "zone_transfer": {},
        "subdomain_bruteforce": {},
        "certificate_search": {},
        "dnssec": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    standard = await dns_lookup(domain)
    result["standard_lookups"] = standard
    zt = await dns_zone_transfer(domain)
    result["zone_transfer"] = zt
    if aggressive:
        bf = await dns_bruteforce_subdomains(domain, concurrent=100)
        result["subdomain_bruteforce"] = bf
        cert = await dns_certificate_search(domain)
        result["certificate_search"] = cert
    dnssec = await dns_dnssec_check(domain)
    result["dnssec"] = dnssec
    return result


async def dns_amplification_check(resolver_ip: str) -> dict[str, Any]:
    """Check if a DNS resolver is vulnerable to amplification attacks (security audit)."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {
        "resolver": resolver_ip,
        "is_open_resolver": False,
        "amplification_factor": 0,
        "vulnerable": False,
        "checks": {},
    }
    request_sizes = {}
    for qtype, qname, label in [
        ("ANY", ".", "root_any"),
        ("ANY", "isc.org", "isc_any"),
        ("DNSSEC", ".", "root_dnssec"),
        ("TXT", "google.com", "google_txt"),
    ]:
        try:
            query = dns.message.make_query(qname, qtype)
            query.flags |= dns.flags.RD
            start = time.time()
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: dns.query.udp(query, resolver_ip, timeout=3)
            )
            elapsed = time.time() - start
            req_size = len(query.to_wire())
            resp_size = len(response.to_wire())
            factor = resp_size / max(req_size, 1)
            result["checks"][label] = {
                "request_bytes": req_size,
                "response_bytes": resp_size,
                "amplification_factor": round(factor, 2),
                "time_ms": round(elapsed * 1000, 1),
            }
            if factor > result["amplification_factor"]:
                result["amplification_factor"] = round(factor, 2)
            request_sizes[label] = factor
        except Exception as e:
            result["checks"][label] = {"error": str(e)[:100]}
    result["is_open_resolver"] = True
    result["vulnerable"] = result["amplification_factor"] > 10
    if result["vulnerable"]:
        result["severity"] = "HIGH" if result["amplification_factor"] > 50 else "MEDIUM"
        result["recommendation"] = "Restrict recursive queries to trusted networks only"
    else:
        result["severity"] = "LOW"
    return result


async def dns_history_lookup(domain: str) -> dict[str, Any]:
    """Look up historical DNS records via SecurityTrails API (requires API key)."""
    api_key = os.environ.get("SECURITYTRAILS_API_KEY", "")
    if not api_key:
        return {"error": "SECURITYTRAILS_API_KEY not set", "domain": domain}
    if not HAS_HTTPX:
        return {"error": "httpx not installed for HTTP requests", "domain": domain}
    result: dict[str, Any] = {"domain": domain, "historical_dns": {}, "source": "securitytrails"}
    try:
        async with httpx.AsyncClient(timeout=20, verify=False) as client:
            resp = await client.get(
                f"https://api.securitytrails.com/v1/history/{domain}/dns/a",
                headers={"APIKEY": api_key, "Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                result["historical_dns"]["A"] = [
                    {"ip": r.get("ip"), "first_seen": r.get("first_seen"), "last_seen": r.get("last_seen"), "organizations": r.get("organizations", [])}
                    for r in data.get("records", [])
                ]
            resp2 = await client.get(
                f"https://api.securitytrails.com/v1/history/{domain}/dns/mx",
                headers={"APIKEY": api_key, "Accept": "application/json"},
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                result["historical_dns"]["MX"] = [
                    {"host": r.get("host"), "priority": r.get("priority"), "first_seen": r.get("first_seen")}
                    for r in data2.get("records", [])
                ]
            resp3 = await client.get(
                f"https://api.securitytrails.com/v1/history/{domain}/dns/ns",
                headers={"APIKEY": api_key, "Accept": "application/json"},
            )
            if resp3.status_code == 200:
                data3 = resp3.json()
                result["historical_dns"]["NS"] = [
                    {"nameserver": r.get("nameserver"), "first_seen": r.get("first_seen")}
                    for r in data3.get("records", [])
                ]
    except Exception as e:
        result["error"] = str(e)[:300]
    return result


async def dns_tunneling_detect(domain: str, subdomains: Optional[list[str]] = None) -> dict[str, Any]:
    """Detect potential DNS tunneling activity by analyzing subdomain entropy and query patterns."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {
        "domain": domain,
        "suspicious_subdomains": [],
        "max_entropy": 0,
        "tunneling_risk": "LOW",
        "analysis": {},
    }
    if subdomains is None:
        bf = await dns_bruteforce_subdomains(domain, wordlist=SUBDOMAIN_WORDLIST[:50], concurrent=20)
        subdomains = bf.get("subdomains", [])
    for sub in subdomains:
        entropy = _calc_entropy(sub.replace(f".{domain}", ""))
        length = len(sub)
        hex_chars = sum(1 for c in sub if c in "0123456789abcdef")
        hex_ratio = hex_chars / max(len(sub), 1)
        subdomain_part = sub.replace(f".{domain}", "").split(".")[0] if sub.endswith(f".{domain}") else sub
        sub_entropy = _calc_entropy(subdomain_part)
        if sub_entropy > 3.5 or hex_ratio > 0.6:
            result["suspicious_subdomains"].append({
                "hostname": sub,
                "entropy": round(sub_entropy, 2),
                "length": length,
                "hex_ratio": round(hex_ratio, 2),
                "reason": "High entropy" if sub_entropy > 3.5 else "High hex ratio",
            })
            if sub_entropy > result["max_entropy"]:
                result["max_entropy"] = sub_entropy
    if result["max_entropy"] > 4.0:
        result["tunneling_risk"] = "HIGH"
    elif result["max_entropy"] > 3.5:
        result["tunneling_risk"] = "MEDIUM"
    if len(subdomains) > 0:
        result["analysis"]["total_analyzed"] = len(subdomains)
        result["analysis"]["suspicious_count"] = len(result["suspicious_subdomains"])
        result["analysis"]["suspicious_percentage"] = round(
            len(result["suspicious_subdomains"]) / len(subdomains) * 100, 1
        )
    return result


def _calc_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not s:
        return 0.0
    entropy = 0.0
    length = len(s)
    freq = defaultdict(int)
    for c in s:
        freq[c] += 1
    for count in freq.values():
        p = count / length
        entropy -= p * (p and __import__("math").log2(p) or 0)
    return entropy


async def dns_response_time(domain: str, record_type: str = "A", count: int = 3) -> dict[str, Any]:
    """Measure DNS response time across multiple resolvers."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {
        "domain": domain,
        "record_type": record_type,
        "resolver_results": [],
        "fastest_resolver": None,
        "fastest_ms": None,
    }
    for resolver_ip in PUBLIC_RESOLVERS:
        times = []
        errors = 0
        for _ in range(count):
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [resolver_ip]
                resolver.timeout = 3
                resolver.lifetime = 5
                start = time.time()
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: list(resolver.resolve(domain, record_type))
                )
                times.append(round((time.time() - start) * 1000, 1))
            except Exception:
                errors += 1
        if times:
            avg = round(sum(times) / len(times), 1)
            entry = {
                "resolver": resolver_ip,
                "avg_ms": avg,
                "min_ms": min(times),
                "max_ms": max(times),
                "samples": count,
                "errors": errors,
            }
            result["resolver_results"].append(entry)
            if result["fastest_ms"] is None or avg < result["fastest_ms"]:
                result["fastest_ms"] = avg
                result["fastest_resolver"] = resolver_ip
        else:
            result["resolver_results"].append({"resolver": resolver_ip, "error": "All queries failed", "errors": errors})
    return result


async def dns_whois_lookup(domain: str) -> dict[str, Any]:
    """WHOIS lookup for a domain using whois library or raw whois protocol."""
    try:
        import whois as whois_lib
        w = await asyncio.get_event_loop().run_in_executor(None, lambda: whois_lib.whois(domain))
        return {
            "domain": domain,
            "registrar": w.registrar,
            "registrant": w.org or w.registrant,
            "creation_date": str(w.creation_date) if w.creation_date else None,
            "expiration_date": str(w.expiration_date) if w.expiration_date else None,
            "name_servers": list(w.name_servers) if w.name_servers else [],
            "emails": list(w.emails) if w.emails else [],
            "country": w.country,
            "status": list(w.status) if w.status else [],
            "dnssec": w.dnssec,
            "whois_server": w.whois_server,
        }
    except ImportError:
        pass
    except Exception as e:
        pass
    result: dict[str, Any] = {"domain": domain, "error": None}
    try:
        import subprocess
        proc = await asyncio.create_subprocess_exec(
            "whois", domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        text = stdout.decode("utf-8", errors="replace")
        lines = text.split("\n")
        for line in lines:
            for key in ["Registrar:", "Creation Date:", "Expiry Date:", "Name Server:", "DNSSEC:", "Registrant Organization:", "Registrant Country:", "Admin Email:"]:
                if line.lower().startswith(key.lower()):
                    result[key.lower().replace(" ", "_").replace(":", "")] = line.split(":", 1)[1].strip()
        if not any(k.startswith("registrar") for k in result):
            result["raw"] = text[:2000]
    except FileNotFoundError:
        result["error"] = "whois binary not found in PATH"
    except Exception as e:
        result["error"] = str(e)[:300]
    return result


async def dns_rdap_lookup(ip_or_asn: str) -> dict[str, Any]:
    """RDAP lookup for IP address or ASN information."""
    if not HAS_HTTPX:
        return {"error": "httpx not installed"}
    result: dict[str, Any] = {"query": ip_or_asn}
    try:
        if ip_or_asn.startswith("AS") or ip_or_asn.startswith("as"):
            asn = ip_or_asn[2:]
            url = f"https://rdap.arin.net/registry/autnum/{asn}"
        else:
            url = f"https://rdap.arin.net/registry/ip/{ip_or_asn}"
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(url, headers={"Accept": "application/rdap+json"})
            if resp.status_code == 200:
                data = resp.json()
                result["handle"] = data.get("handle")
                result["name"] = data.get("name")
                result["type"] = data.get("type")
                result["start_address"] = data.get("startAddress")
                result["end_address"] = data.get("endAddress")
                result["ip_version"] = data.get("ipVersion")
                result["country"] = data.get("country")
                result["parent_handle"] = data.get("parentHandle")
                entities = data.get("entities", [])
                result["entities"] = [
                    {
                        "handle": e.get("handle"),
                        "roles": e.get("roles", []),
                        "name": (e.get("vcardArray", [])[1] or [None, None, None, None, None])[1] if len(e.get("vcardArray", [])) > 1 and e["vcardArray"][1] else None,
                    }
                    for e in entities[:5]
                ]
                events = data.get("events", [])
                result["events"] = {e.get("eventAction"): e.get("eventDate") for e in events}
            else:
                result["error"] = f"RDAP returned {resp.status_code}"
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


async def dns_txt_analyze(domain: str) -> dict[str, Any]:
    """Analyze all TXT records for security and configuration info."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {"domain": domain, "txt_records": [], "analysis": {}}
    try:
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(domain, "TXT"))
        )
        for answer in answers:
            txt = str(answer)
            result["txt_records"].append(txt)
            if txt.startswith("v=spf1"):
                result["analysis"]["type"] = "SPF"
                result["analysis"]["spf"] = txt[:300]
            elif txt.startswith("v=DMARC1"):
                result["analysis"]["type"] = "DMARC"
                result["analysis"]["dmarc"] = txt[:300]
            elif txt.startswith("google-site-verification"):
                result["analysis"]["type"] = "Google Verification"
            elif txt.startswith("MS="):
                result["analysis"]["type"] = "Microsoft Verification"
            elif txt.startswith("apple-domain-verification"):
                result["analysis"]["type"] = "Apple Verification"
            elif txt.startswith("facebook-domain-verification"):
                result["analysis"]["type"] = "Facebook Verification"
            elif txt.startswith("keybase-site-verification"):
                result["analysis"]["type"] = "Keybase Verification"
            elif txt.startswith("atlassian-domain-verification"):
                result["analysis"]["type"] = "Atlassian Verification"
            elif txt.startswith("zendesk-verification"):
                result["analysis"]["type"] = "Zendesk Verification"
            elif txt.startswith("stripe-verification"):
                result["analysis"]["type"] = "Stripe Verification"
            elif txt.startswith("hubspot-verification"):
                result["analysis"]["type"] = "HubSpot Verification"
            elif txt.startswith("miro-verification"):
                result["analysis"]["type"] = "Miro Verification"
            elif txt.startswith("notion-verification"):
                result["analysis"]["type"] = "Notion Verification"
            elif txt.startswith("figma-verification"):
                result["analysis"]["type"] = "Figma Verification"
            elif txt.startswith("canva-verification"):
                result["analysis"]["type"] = "Canva Verification"
            elif txt.startswith("linkedin-verification"):
                result["analysis"]["type"] = "LinkedIn Verification"
            elif txt.startswith("github-verification"):
                result["analysis"]["type"] = "GitHub Verification"
            elif txt.startswith("gitlab-verification"):
                result["analysis"]["type"] = "GitLab Verification"
            elif txt.startswith("slack-verification"):
                result["analysis"]["type"] = "Slack Verification"
            elif txt.startswith("loggly"):
                result["analysis"]["type"] = "Loggly"
            elif txt.startswith("statuspage"):
                result["analysis"]["type"] = "StatusPage"
            elif txt.startswith("trello"):
                result["analysis"]["type"] = "Trello"
            elif txt.startswith("evernote"):
                result["analysis"]["type"] = "Evernote"
            elif "=" in txt:
                key = txt.split("=")[0].strip().lower()
                if key in ["google", "ms", "apple", "facebook", "keybase", "atlassian", "zendesk", "stripe", "hubspot", "miro", "notion", "figma", "canva", "linkedin", "github", "gitlab", "slack"]:
                    result["analysis"]["type"] = f"{key.title()} Verification"
    except dns.resolver.NoAnswer:
        result["error"] = "No TXT records found"
    except Exception as e:
        result["error"] = str(e)
    return result


async def dns_caa_check(domain: str) -> dict[str, Any]:
    """Check CAA (Certificate Authority Authorization) records."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {"domain": domain, "caa_records": [], "allowed_cas": [], "policy": "permissive"}
    try:
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(domain, "CAA"))
        )
        for a in answers:
            issuer = a.value.decode() if isinstance(a.value, bytes) else str(a.value)
            tag = a.tag.decode() if isinstance(a.tag, bytes) else str(a.tag)
            entry = {"flags": a.flags, "tag": tag, "value": issuer}
            result["caa_records"].append(entry)
            if tag == "issue":
                result["allowed_cas"].append(issuer)
            elif tag == "iodef":
                result["reporting"] = issuer
            elif tag == "issuewild":
                result["wildcard_allowed"] = issuer
        if result["allowed_cas"]:
            result["policy"] = "restricted"
        else:
            result["policy"] = "permissive"
    except dns.resolver.NoAnswer:
        result["error"] = "No CAA records found"
    except Exception as e:
        result["error"] = str(e)
    return result


async def dns_ptr_lookup(ip: str) -> dict[str, Any]:
    """PTR record lookup with additional details."""
    if not HAS_DNSPYTHON:
        return await dns_reverse_lookup(ip)
    result: dict[str, Any] = {"ip": ip}
    try:
        rev = dns.reversename.from_address(ip)
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(rev, "PTR"))
        )
        result["hostnames"] = [str(a) for a in answers]
        result["ptr_domain"] = str(rev)
    except dns.resolver.NXDOMAIN:
        result["error"] = "No PTR record"
    except Exception as e:
        result["error"] = str(e)
    try:
        hostname = await asyncio.get_event_loop().run_in_executor(None, socket.gethostbyaddr, ip)
        result["forward_confirms"] = any(h == hostname[0] for h in result.get("hostnames", []))
    except Exception:
        result["forward_confirms"] = False
    return result


async def dns_resolve_all(hostnames: list[str]) -> dict[str, Any]:
    """Resolve multiple hostnames to IPs in parallel."""
    tasks = []
    for h in hostnames:
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", h):
            tasks.append(dns_reverse_lookup(h))
        else:
            tasks.append(dns_lookup(h, ["A", "AAAA", "CNAME"]))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    output = []
    for i, r in enumerate(results):
        entry = {"query": hostnames[i]}
        if isinstance(r, Exception):
            entry["error"] = str(r)
        else:
            entry["result"] = r
        output.append(entry)
    return {"results": output, "count": len(output)}


async def dns_format_for_llm(result: dict[str, Any]) -> str:
    """Format DNS results as a concise string for LLM consumption."""
    lines = []
    domain = result.get("domain", "")
    if domain:
        lines.append(f"=== DNS Results: {domain} ===")
    records = result.get("records", {})
    for rtype, entries in records.items():
        if entries:
            values = []
            for e in entries:
                if isinstance(e, dict):
                    val = e.get("value") or e.get("exchange") or e.get("hostname") or str(e)
                    extra = []
                    if "preference" in e:
                        extra.append(f"priority={e['preference']}")
                    if "port" in e and "target" in e:
                        extra.append(f"{e['target']}:{e['port']}")
                    if "algorithm" in e:
                        extra.append(f"alg={e['algorithm']}")
                    if extra:
                        val = f"{val} ({', '.join(extra)})"
                    values.append(val)
                else:
                    values.append(str(e))
            lines.append(f"  {rtype}: {', '.join(values[:5])}")
            if len(values) > 5:
                lines[-1] += f" (+{len(values) - 5} more)"
    timing = result.get("timing_ms", {})
    if timing:
        avg = sum(v for v in timing.values() if isinstance(v, (int, float)) and v > 0)
        count = sum(1 for v in timing.values() if isinstance(v, (int, float)) and v > 0)
        if count:
            lines.append(f"  Avg resolution: {round(avg / count, 1)}ms")
    return "\n".join(lines) if lines else f"No DNS records found for {domain}"


async def dns_soa_check(domain: str) -> dict[str, Any]:
    """Detailed SOA record analysis."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {"domain": domain}
    try:
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(domain, "SOA"))
        )
        soa = answers[0]
        result["primary_ns"] = str(soa.mname)
        result["responsible_email"] = str(soa.rname)
        result["serial"] = soa.serial
        result["refresh"] = soa.refresh
        result["retry"] = soa.retry
        result["expire"] = soa.expire
        result["minimum_ttl"] = soa.minimum
        serial_time = datetime.fromtimestamp(soa.serial, tz=timezone.utc) if soa.serial > 2000000000 else None
        if serial_time:
            result["serial_date"] = serial_time.isoformat()
            result["days_since_change"] = (datetime.now(timezone.utc) - serial_time).days
        result["expire_days"] = round(soa.expire / 86400, 1) if soa.expire else None
    except Exception as e:
        result["error"] = str(e)
    return result


async def dns_cname_chain(domain: str) -> dict[str, Any]:
    """Follow CNAME chain to resolution."""
    if not HAS_DNSPYTHON:
        return {"error": "dnspython not installed"}
    result: dict[str, Any] = {"domain": domain, "chain": [], "final_target": None}
    current = domain
    visited = set()
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3
    resolver.lifetime = 5
    while current and current not in visited:
        visited.add(current)
        try:
            answers = await asyncio.get_event_loop().run_in_executor(
                None, lambda: list(resolver.resolve(current, "CNAME"))
            )
            if answers:
                cname = str(answers[0].target) if hasattr(answers[0], "target") else str(answers[0])
                result["chain"].append({"from": current, "type": "CNAME", "to": cname})
                try:
                    a_answers = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: list(resolver.resolve(current, "A"))
                    )
                    result["chain"][-1]["also_has_a"] = [str(a) for a in a_answers]
                except Exception:
                    pass
                current = cname
            else:
                a_answers = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: list(resolver.resolve(current, "A"))
                )
                ips = [str(a) for a in a_answers]
                result["chain"].append({"from": current, "type": "A", "to": ips})
                result["final_target"] = current
                result["final_ips"] = ips
                current = None
        except Exception:
            result["chain"].append({"from": current, "error": "Resolution failed"})
            current = None
    return result


DNS_TOOL_DESCRIPTIONS = {
    "dns_lookup": ("Standard DNS lookup for multiple record types", {"domain": "Domain to query", "record_types": "Record types (default: A,AAAA,MX,NS,TXT,SOA,CNAME,SRV,CAA,SSHFP)", "resolver_ip": "Specific resolver IP to use"}),
    "dns_bulk_lookup": ("Bulk DNS lookup for multiple domains", {"domains": "List of domains to query"}),
    "dns_reverse_lookup": ("Reverse DNS lookup - IP to hostname", {"ip": "IP address to look up"}),
    "dns_reverse_sweep": ("Reverse DNS sweep across a CIDR subnet", {"network_cidr": "CIDR notation (e.g. 192.168.1.0/24)"}),
    "dns_mx_lookup": ("Mail server MX record lookup", {"domain": "Domain to query"}),
    "dns_zone_transfer": ("Attempt DNS zone transfer (AXFR) - security check", {"domain": "Target domain", "nameserver": "Specific nameserver to try (optional)"}),
    "dns_compare_resolvers": ("Compare DNS results across public resolvers", {"domain": "Domain to query", "record_type": "Record type (default: A)"}),
    "dns_dnssec_check": ("Check DNSSEC status", {"domain": "Domain to check"}),
    "dns_spf_check": ("SPF record analysis", {"domain": "Domain to check"}),
    "dns_dmarc_check": ("DMARC policy check", {"domain": "Domain to check"}),
    "dns_dkim_check": ("DKIM record check", {"domain": "Domain to check", "selector": "DKIM selector (default: default)"}),
    "dns_email_security_audit": ("Full email security audit (SPF+DKIM+DMARC+MX)", {"domain": "Domain to audit"}),
    "dns_certificate_search": ("Search crt.sh for subdomains via SSL certs", {"domain": "Domain to search"}),
    "dns_bruteforce_subdomains": ("Bruteforce subdomain discovery", {"domain": "Target domain", "wordlist": "Custom wordlist (optional)", "concurrent": "Concurrent lookups (default: 50)", "resolve": "Resolve to IPs (default: true)"}),
    "dns_enumeration": ("Full DNS enumeration", {"domain": "Target domain", "aggressive": "Include bruteforce + crt.sh (default: false)"}),
    "dns_amplification_check": ("Check if resolver is vulnerable to amplification attacks", {"resolver_ip": "Resolver IP to test"}),
    "dns_history_lookup": ("Historical DNS records (requires SECURITYTRAILS_API_KEY)", {"domain": "Domain to look up"}),
    "dns_tunneling_detect": ("Detect DNS tunneling via entropy analysis", {"domain": "Domain to analyze", "subdomains": "Subdomain list (optional)"}),
    "dns_response_time": ("Measure DNS response times across resolvers", {"domain": "Domain to query", "record_type": "Record type (default: A)", "count": "Queries per resolver (default: 3)"}),
    "dns_whois_lookup": ("WHOIS domain lookup", {"domain": "Domain to look up"}),
    "dns_rdap_lookup": ("RDAP lookup for IP/ASN", {"ip_or_asn": "IP address or ASN (e.g. AS15169)"}),
    "dns_txt_analyze": ("Analyze TXT records for service verification", {"domain": "Domain to analyze"}),
    "dns_caa_check": ("CAA record check", {"domain": "Domain to check"}),
    "dns_ptr_lookup": ("PTR record lookup with forward confirmation", {"ip": "IP address"}),
    "dns_resolve_all": ("Resolve multiple hostnames in parallel", {"hostnames": "List of hostnames/IPs"}),
    "dns_soa_check": ("SOA record analysis", {"domain": "Domain to check"}),
    "dns_cname_chain": ("Follow CNAME chain to final resolution", {"domain": "Starting domain"}),
}