"""
Advanced OSINT & Intelligence tools
Libraries: shodan, censys, dnspython, whois, scapy, nmap, geoip2,
emailhunter, clearbit, fullcontact, theHarvester, subfinder, nuclei
"""
import asyncio
import json
import os
import re
import socket
import ssl
import struct
import subprocess
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from ipaddress import ip_address, IPv4Network
from typing import Any, Optional

# ── Shodan ──
HAS_SHODAN = False
try:
    import shodan
    HAS_SHODAN = True
except ImportError:
    pass

SHODAN_API_KEY = os.environ.get("SHODAN_API_KEY", "")


async def shodan_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Shodan for devices matching a query."""
    if not SHODAN_API_KEY:
        return {"error": "SHODAN_API_KEY not set", "query": query}
    if not HAS_SHODAN:
        return {"error": "shodan Python package not installed"}
    try:
        client = shodan.Shodan(SHODAN_API_KEY)
        results = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.search(query, limit=limit)
        )
        return {
            "total": results.get("total", 0),
            "matches": [{
                "ip": m.get("ip_str"),
                "port": m.get("port"),
                "org": m.get("org"),
                "hostname": m.get("hostnames", []),
                "product": m.get("product"),
                "os": m.get("os"),
                "country": m.get("location", {}).get("country_name"),
                "city": m.get("location", {}).get("city"),
                "transport": m.get("transport"),
            } for m in results.get("matches", [])],
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except shodan.exception.APIError as e:
        return {"error": f"Shodan API error: {e}", "query": query}
    except Exception as e:
        return {"error": str(e), "query": query}


async def shodan_host(ip: str) -> dict[str, Any]:
    """Get detailed Shodan information for a specific IP."""
    if not SHODAN_API_KEY:
        return {"error": "SHODAN_API_KEY not set"}
    if not HAS_SHODAN:
        return {"error": "shodan not installed"}
    try:
        client = shodan.Shodan(SHODAN_API_KEY)
        host = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.host(ip)
        )
        ports = host.get("ports", [])
        data_simple = []
        for item in host.get("data", [])[:20]:
            data_simple.append({
                "port": item.get("port"),
                "transport": item.get("transport"),
                "product": item.get("product"),
                "version": item.get("version"),
                "org": item.get("org"),
                "isp": item.get("isp"),
                "hostnames": item.get("hostnames", []),
                "timestamp": item.get("timestamp"),
            })
        return {
            "ip": host.get("ip_str"),
            "org": host.get("org"),
            "os": host.get("os"),
            "ports": ports,
            "port_count": len(ports),
            "country": host.get("country_name"),
            "city": host.get("city"),
            "hostnames": host.get("hostnames"),
            "latitude": host.get("latitude"),
            "longitude": host.get("longitude"),
            "vulns": list(host.get("vulns", [])) if host.get("vulns") else [],
            "tags": host.get("tags", []),
            "data": data_simple,
            "last_update": host.get("last_update"),
        }
    except shodan.exception.APIError as e:
        return {"ip": ip, "error": f"Shodan API error: {e}"}
    except Exception as e:
        return {"ip": ip, "error": str(e)}


async def shodan_search_count(query: str) -> dict[str, Any]:
    """Get Shodan search result count without retrieving results."""
    if not SHODAN_API_KEY:
        return {"error": "SHODAN_API_KEY not set"}
    if not HAS_SHODAN:
        return {"error": "shodan not installed"}
    try:
        client = shodan.Shodan(SHODAN_API_KEY)
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.count(query)
        )
        return {"total": result.get("total", 0), "query": query}
    except Exception as e:
        return {"error": str(e)}


async def shodan_ports(ip: str) -> dict[str, Any]:
    """Quick Shodan port listing for an IP."""
    if not SHODAN_API_KEY:
        return {"error": "SHODAN_API_KEY not set"}
    if not HAS_SHODAN:
        return {"error": "shodan not installed"}
    try:
        client = shodan.Shodan(SHODAN_API_KEY)
        host = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.host(ip)
        )
        port_details = []
        for item in host.get("data", []):
            port_details.append({
                "port": item.get("port"),
                "protocol": item.get("transport"),
                "product": item.get("product"),
                "version": item.get("version"),
            })
        return {"ip": ip, "ports": host.get("ports", []), "port_details": port_details, "count": len(host.get("ports", []))}
    except Exception as e:
        return {"ip": ip, "error": str(e)}


async def shodan_dns_resolve(hostnames: list[str]) -> dict[str, Any]:
    """Resolve hostnames to IPs using Shodan DNS."""
    if not SHODAN_API_KEY:
        return {"error": "SHODAN_API_KEY not set"}
    query = ",".join(hostnames)
    try:
        client = shodan.Shodan(SHODAN_API_KEY)
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.dns_resolve(query)
        )
        return {"resolved": result, "count": len(result)}
    except Exception as e:
        return {"error": str(e)}


# ── Censys ──
HAS_CENSYS = False
try:
    from censys.search import CensysHosts, CensysCerts
    HAS_CENSYS = True
except ImportError:
    pass

CENSYS_API_ID = os.environ.get("CENSYS_API_ID", "")
CENSYS_API_SECRET = os.environ.get("CENSYS_API_SECRET", "")


async def censys_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Censys for hosts matching a query."""
    if not CENSYS_API_ID or not CENSYS_API_SECRET:
        return {"error": "CENSYS_API_ID/SECRET not set"}
    if not HAS_CENSYS:
        return {"error": "censys Python package not installed"}
    try:
        c = CensysHosts(api_id=CENSYS_API_ID, api_secret=CENSYS_API_SECRET)
        results = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(c.search(query, per_page=limit))
        )
        return {
            "results": [{
                "ip": r.get("ip"),
                "services": r.get("services", [])[:5],
                "location": r.get("location", {}),
                "autonomous_system": r.get("autonomous_system", {}),
            } for r in results],
            "query": query,
            "count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "query": query}


async def censys_host_view(ip: str) -> dict[str, Any]:
    """Get detailed Censys view for a host IP."""
    if not CENSYS_API_ID or not CENSYS_API_SECRET:
        return {"error": "CENSYS_API_ID/SECRET not set"}
    if not HAS_CENSYS:
        return {"error": "censys not installed"}
    try:
        c = CensysHosts(api_id=CENSYS_API_ID, api_secret=CENSYS_API_SECRET)
        host = await asyncio.get_event_loop().run_in_executor(
            None, lambda: c.view(ip)
        )
        return {
            "ip": host.get("ip"),
            "location": host.get("location", {}),
            "autonomous_system": host.get("autonomous_system", {}),
            "services": host.get("services", []),
            "whois": host.get("whois", {}),
        }
    except Exception as e:
        return {"error": str(e), "ip": ip}


async def censys_certificate_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Censys certificate transparency logs."""
    if not CENSYS_API_ID or not CENSYS_API_SECRET:
        return {"error": "CENSYS_API_ID/SECRET not set"}
    if not HAS_CENSYS:
        return {"error": "censys not installed"}
    try:
        from censys.search import CensysCerts
        c = CensysCerts(api_id=CENSYS_API_ID, api_secret=CENSYS_API_SECRET)
        results = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(c.search(query, per_page=limit))
        )
        return {
            "results": [{
                "fingerprint": r.get("fingerprint_sha256"),
                "issuer": r.get("issuer", {}),
                "subject": r.get("subject", {}),
                "valid_from": r.get("valid_from"),
                "valid_to": r.get("valid_to"),
                "names": r.get("names", []),
            } for r in results],
            "count": len(results),
        }
    except Exception as e:
        return {"error": str(e), "query": query}


# ── WHOIS ──
HAS_WHOIS = False
try:
    import whois
    HAS_WHOIS = True
except ImportError:
    pass


async def whois_lookup(domain: str) -> dict[str, Any]:
    """Perform WHOIS lookup for a domain with detailed results."""
    if not HAS_WHOIS:
        return {"error": "whois not installed. Install: pip install whois"}
    try:
        w = await asyncio.get_event_loop().run_in_executor(
            None, lambda: whois.whois(domain)
        )
        return {
            "domain": domain,
            "registrar": w.registrar,
            "registrant": w.org or w.registrant or w.name,
            "creation_date": str(w.creation_date) if w.creation_date else None,
            "expiration_date": str(w.expiration_date) if w.expiration_date else None,
            "updated_date": str(w.updated_date) if w.updated_date else None,
            "name_servers": list(w.name_servers) if w.name_servers else [],
            "emails": list(w.emails) if w.emails else [],
            "country": w.country,
            "state": w.state,
            "city": w.city,
            "address": w.address,
            "zipcode": w.zipcode,
            "status": list(w.status) if w.status else [],
            "dnssec": w.dnssec,
            "whois_server": w.whois_server,
            "referral_url": w.referral_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "domain": domain}


async def whois_raw_lookup(domain: str) -> dict[str, Any]:
    """Perform raw WHOIS lookup returning the full text output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "whois", domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        text = stdout.decode("utf-8", errors="replace")
        parsed = {}
        for line in text.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                val = val.strip()
                if key in parsed:
                    if isinstance(parsed[key], list):
                        parsed[key].append(val)
                    else:
                        parsed[key] = [parsed[key], val]
                else:
                    parsed[key] = val
        return {
            "domain": domain,
            "raw_length": len(text),
            "parsed_fields": len(parsed),
            "data": parsed,
        }
    except FileNotFoundError:
        return {"error": "whois binary not found in PATH", "domain": domain}
    except Exception as e:
        return {"error": str(e), "domain": domain}


async def whois_ip_lookup(ip: str) -> dict[str, Any]:
    """WHOIS lookup for an IP address (ARIN/RIPE/APNIC)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "whois", "-h", "whois.arin.net", f"n + {ip}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        text = stdout.decode("utf-8", errors="replace")
        parsed = {}
        for line in text.split("\n"):
            if ":" in line and not line.startswith("#"):
                key, val = line.split(":", 1)
                parsed[key.strip()] = val.strip()
        return {"ip": ip, "data": parsed, "source": "ARIN"}
    except Exception as e:
        return {"error": str(e), "ip": ip}


# ── theHarvester ──
HARVESTER_PATH = os.environ.get("HARVESTER_PATH", "theHarvester")
HARVESTER_SOURCES = [
    "baidu", "bing", "bingapi", "brave", "certspotter", "criminalip",
    "crtsh", "dnsdumpster", "dogpile", "duckduckgo", "exalead",
    "google", "googlecert", "googleprofiles", "hackertarget",
    "hunter", "intelx", "linkedin", "netcraft", "omnisint",
    "otx", "pentesttools", "projectdiscovery", "rapiddns",
    "rocketreach", "securitytrails", "sublist3r", "threatcrowd",
    "trello", "twitter", "urlscan", "virustotal", "yahoo",
    "yandex", "zoomeye",
]


async def harvester_enum(domain: str, sources: str = "all") -> dict[str, Any]:
    """Run theHarvester for email/subdomain enumeration."""
    if not domain or "." not in domain:
        return {"error": "Valid domain required", "domain": domain}
    try:
        proc = await asyncio.create_subprocess_exec(
            HARVESTER_PATH, "-d", domain, "-b", sources,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8", errors="replace")
        emails = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", output)))
        hosts = list(set(re.findall(r"Host:\s*(\S+)", output)))
        ips = list(set(re.findall(r"IP:\s*(\S+)", output)))
        linkedin_users = list(set(re.findall(r"Linkedin:\s*(\S+)", output)))
        return {
            "domain": domain,
            "emails": emails,
            "hosts": hosts,
            "ips": ips,
            "linkedin_users": linkedin_users,
            "email_count": len(emails),
            "host_count": len(hosts),
            "ip_count": len(ips),
            "sources": sources,
            "harvester_available": True,
        }
    except FileNotFoundError:
        return {
            "domain": domain,
            "error": "theHarvester not installed",
            "install_hint": "pip install theHarvester",
            "harvester_available": False,
        }
    except asyncio.TimeoutError:
        return {"error": "theHarvester timed out after 120s", "domain": domain}
    except Exception as e:
        return {"error": str(e), "domain": domain}


async def harvester_enum_all_sources(domain: str) -> dict[str, Any]:
    """Run theHarvester against all available sources sequentially."""
    all_results = {"domain": domain, "sources_results": {}, "total_emails": 0, "total_hosts": 0}
    for source in HARVESTER_SOURCES[:10]:
        result = await harvester_enum(domain, source)
        if not result.get("error"):
            all_results["sources_results"][source] = {
                "emails": result.get("emails", []),
                "hosts": result.get("hosts", []),
            }
            all_results["total_emails"] += result.get("email_count", 0)
            all_results["total_hosts"] += result.get("host_count", 0)
        await asyncio.sleep(1)
    all_results["unique_emails"] = list(set(
        e for r in all_results["sources_results"].values() for e in r.get("emails", [])
    ))
    return all_results


# ── Subfinder ──
SUBFINDER_PATH = os.environ.get("SUBFINDER_PATH", "subfinder")


async def subfinder_enum(domain: str, recursive: bool = False, resolve: bool = True) -> dict[str, Any]:
    """Run Subfinder for subdomain enumeration."""
    try:
        cmd = [SUBFINDER_PATH, "-d", domain, "-silent"]
        if recursive:
            cmd.extend(["-recursive"])
        if resolve:
            cmd.extend(["-resolve"])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        subs = [s.strip() for s in stdout.decode().split("\n") if s.strip()]
        return {
            "domain": domain,
            "subdomains": subs,
            "count": len(subs),
            "recursive": recursive,
            "resolve": resolve,
        }
    except FileNotFoundError:
        return {
            "error": "subfinder not installed",
            "install_hint": "go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        }
    except asyncio.TimeoutError:
        return {"error": "subfinder timed out after 120s", "domain": domain}
    except Exception as e:
        return {"error": str(e), "domain": domain}


async def subfinder_enum_multi(domains: list[str]) -> dict[str, Any]:
    """Run Subfinder against multiple domains."""
    all_results = {}
    total_subs = 0
    for domain in domains:
        result = await subfinder_enum(domain)
        all_results[domain] = result
        total_subs += result.get("count", 0)
    return {"domains": domains, "results": all_results, "total_subdomains": total_subs}


# ── Nuclei ──
NUCLEI_PATH = os.environ.get("NUCLEI_PATH", "nuclei")


async def nuclei_scan(target: str, severity: str = "medium", templates: Optional[str] = None,
                       exclude_templates: Optional[str] = None, rate_limit: int = 150,
                       timeout: int = 300) -> dict[str, Any]:
    """Run Nuclei vulnerability scanner against a target."""
    try:
        cmd = [NUCLEI_PATH, "-u", target, "-severity", severity, "-json", "-silent"]
        if templates:
            cmd.extend(["-t", templates])
        if exclude_templates:
            cmd.extend(["-et", exclude_templates])
        if rate_limit:
            cmd.extend(["-rl", str(rate_limit)])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        findings = []
        for line in stdout.decode().strip().split("\n"):
            if line.strip():
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        severity_counts = defaultdict(int)
        for f in findings:
            severity_counts[f.get("info", {}).get("severity", "unknown")] += 1
        return {
            "target": target,
            "severity": severity,
            "findings": findings,
            "count": len(findings),
            "severity_breakdown": dict(severity_counts),
            "templates_used": templates or "default",
        }
    except FileNotFoundError:
        return {
            "error": "nuclei not installed",
            "install_hint": "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        }
    except asyncio.TimeoutError:
        return {"error": f"nuclei timed out after {timeout}s", "target": target}
    except Exception as e:
        return {"error": str(e), "target": target}


async def nuclei_scan_list_targets(targets: list[str], severity: str = "medium") -> dict[str, Any]:
    """Run Nuclei against a list of targets."""
    all_results = {}
    for target in targets:
        result = await nuclei_scan(target, severity)
        all_results[target] = result
    return {"targets": targets, "results": all_results, "total": sum(r.get("count", 0) for r in all_results.values())}


async def nuclei_update_templates() -> dict[str, Any]:
    """Update Nuclei templates to the latest version."""
    try:
        proc = await asyncio.create_subprocess_exec(
            NUCLEI_PATH, "-update-templates",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        return {"status": "completed", "output": stdout.decode()[:500], "stderr": stderr.decode()[:500]}
    except FileNotFoundError:
        return {"error": "nuclei not installed"}
    except Exception as e:
        return {"error": str(e)}


# ── GeoIP ──
HAS_GEOIP = False
try:
    import geoip2.database
    import geoip2.errors
    HAS_GEOIP = True
except ImportError:
    pass

GEOIP_DB_PATH = os.environ.get("GEOIP_DB_PATH", "GeoLite2-City.mmdb")
GEOIP_ASN_DB_PATH = os.environ.get("GEOIP_ASN_DB_PATH", "GeoLite2-ASN.mmdb")


async def geoip_lookup(ip: str) -> dict[str, Any]:
    """Look up geographic information for an IP address."""
    result: dict[str, Any] = {"ip": ip, "timestamp": datetime.now(timezone.utc).isoformat()}
    if not HAS_GEOIP:
        result["error"] = "geoip2 not installed. Run: pip install geoip2"
        return result
    if not os.path.exists(GEOIP_DB_PATH):
        result["error"] = f"GeoIP City DB not found at {GEOIP_DB_PATH}. Download from maxmind.com"
        return result
    try:
        reader = geoip2.database.Reader(GEOIP_DB_PATH)
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: reader.city(ip))
        result.update({
            "city": response.city.name,
            "country": response.country.name,
            "country_iso": response.country.iso_code,
            "continent": response.continent.name,
            "continent_code": response.continent.code,
            "postal_code": response.postal.code,
            "location": {
                "latitude": response.location.latitude,
                "longitude": response.location.longitude,
                "accuracy_radius": response.location.accuracy_radius,
                "timezone": response.location.time_zone,
            },
            "subdivisions": [{"name": s.name, "iso_code": s.iso_code} for s in response.subdivisions],
        })
        reader.close()
    except geoip2.errors.AddressNotFoundError:
        result["error"] = "IP not found in GeoIP database"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
    if os.path.exists(GEOIP_ASN_DB_PATH):
        try:
            asn_reader = geoip2.database.Reader(GEOIP_ASN_DB_PATH)
            asn_resp = await asyncio.get_event_loop().run_in_executor(None, lambda: asn_reader.asn(ip))
            result["asn"] = asn_resp.autonomous_system_number
            result["asn_org"] = asn_resp.autonomous_system_organization
            asn_reader.close()
        except Exception:
            pass
    try:
        hostname = await asyncio.get_event_loop().run_in_executor(None, socket.gethostbyaddr, ip)
        result["hostname"] = hostname[0]
    except Exception:
        pass
    return result


async def geoip_bulk_lookup(ips: list[str]) -> dict[str, Any]:
    """Look up geographic information for multiple IPs."""
    results = []
    for ip in ips:
        result = await geoip_lookup(ip)
        results.append(result)
    return {"results": results, "count": len(results), "timestamp": datetime.now(timezone.utc).isoformat()}


async def geoip_asn_lookup(ip: str) -> dict[str, Any]:
    """Look up ASN information for an IP address."""
    result: dict[str, Any] = {"ip": ip}
    if not HAS_GEOIP:
        result["error"] = "geoip2 not installed"
        return result
    if not os.path.exists(GEOIP_ASN_DB_PATH):
        result["error"] = f"GeoIP ASN DB not found at {GEOIP_ASN_DB_PATH}"
        return result
    try:
        reader = geoip2.database.Reader(GEOIP_ASN_DB_PATH)
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: reader.asn(ip))
        result["asn"] = response.autonomous_system_number
        result["org"] = response.autonomous_system_organization
        reader.close()
    except Exception as e:
        result["error"] = str(e)
    return result


# ── Scapy (Packet manipulation) ──
HAS_SCAPY = False
try:
    from scapy.all import sr1, IP, TCP, ICMP, UDP, Ether, ARP, conf
    HAS_SCAPY = True
except ImportError:
    pass


async def ping_host(host: str, count: int = 3, timeout: float = 2.0) -> dict[str, Any]:
    """Ping a host and return response statistics."""
    result: dict[str, Any] = {"host": host, "count": count, "alive": False, "responses": []}
    if not HAS_SCAPY:
        try:
            ping_cmd = "ping"
            ping_args = ["-n" if os.name == "nt" else "-c", str(count), host]
            proc = await asyncio.create_subprocess_exec(
                ping_cmd, *ping_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = stdout.decode("utf-8", errors="replace")
            result["alive"] = proc.returncode == 0
            result["output"] = output[:1000]
            result["method"] = "system_ping"
            ms_times = re.findall(r"time[=<]\s*(\d+\.?\d*)", output, re.IGNORECASE)
            if ms_times:
                result["times_ms"] = [float(t) for t in ms_times]
                result["avg_ms"] = round(sum(result["times_ms"]) / len(result["times_ms"]), 1)
            return result
        except FileNotFoundError:
            result["error"] = "ping binary not found"
            return result
        except Exception as e:
            result["error"] = str(e)
            return result
    start = time.time()
    for i in range(count):
        try:
            pkt = IP(dst=host) / ICMP()
            reply = await asyncio.get_event_loop().run_in_executor(
                None, lambda: sr1(pkt, timeout=timeout, verbose=0)
            )
            response_time = round((time.time() - start) * 1000, 1)
            entry = {
                "seq": i + 1,
                "alive": reply is not None,
                "response_time_ms": response_time,
            }
            if reply:
                entry["ttl"] = reply.ttl
                entry["src"] = str(reply.src)
            result["responses"].append(entry)
        except Exception as e:
            result["responses"].append({"seq": i + 1, "error": str(e)})
    alive_count = sum(1 for r in result["responses"] if r.get("alive"))
    result["alive"] = alive_count > 0
    result["success_rate"] = f"{alive_count}/{count}"
    result["method"] = "scapy"
    times = [r["response_time_ms"] for r in result["responses"] if r.get("alive")]
    if times:
        result["avg_ms"] = round(sum(times) / len(times), 1)
        result["min_ms"] = min(times)
        result["max_ms"] = max(times)
    return result


async def port_scan(host: str, ports: Optional[list[int]] = None,
                     timeout: float = 1.0, scan_type: str = "connect") -> dict[str, Any]:
    """Scan ports on a target host."""
    if ports is None:
        ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995,
                 1433, 1521, 2049, 3306, 3389, 5432, 6379, 8080, 8443, 9090, 27017]
    result: dict[str, Any] = {
        "host": host,
        "ports_scanned": len(ports),
        "open_ports": [],
        "filtered_ports": [],
        "closed_ports": [],
        "scan_type": scan_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if scan_type == "syn" and HAS_SCAPY:
        for port in ports:
            try:
                pkt = IP(dst=host) / TCP(dport=port, flags="S")
                reply = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: sr1(pkt, timeout=timeout, verbose=0)
                )
                if reply and reply.haslayer(TCP):
                    flags = reply.getlayer(TCP).flags
                    if flags & 0x12:
                        result["open_ports"].append({"port": port, "protocol": "tcp", "state": "open"})
                    elif flags & 0x14:
                        result["closed_ports"].append({"port": port, "protocol": "tcp", "state": "closed"})
                    else:
                        result["filtered_ports"].append({"port": port, "protocol": "tcp", "state": "filtered"})
                else:
                    result["filtered_ports"].append({"port": port, "protocol": "tcp", "state": "filtered"})
            except Exception as e:
                result["filtered_ports"].append({"port": port, "protocol": "tcp", "state": "error", "error": str(e)})
    else:
        for port in ports[:20]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                start = time.time()
                r = s.connect_ex((host, port))
                elapsed = round((time.time() - start) * 1000, 1)
                entry = {"port": port, "protocol": "tcp", "time_ms": elapsed}
                if r == 0:
                    entry["state"] = "open"
                    try:
                        s.settimeout(2)
                        s.send(b"GET / HTTP/1.0\r\n\r\n")
                        banner = s.recv(256).decode("utf-8", errors="replace")[:100]
                        if banner:
                            entry["banner"] = banner
                    except Exception:
                        pass
                    result["open_ports"].append(entry)
                elif r == 111:
                    result["closed_ports"].append(entry | {"state": "closed"})
                else:
                    entry["state"] = "filtered"
                    entry["error_code"] = r
                    result["filtered_ports"].append(entry)
                s.close()
            except Exception as e:
                result["filtered_ports"].append({"port": port, "protocol": "tcp", "state": "error", "error": str(e)})
    result["open_count"] = len(result["open_ports"])
    result["closed_count"] = len(result["closed_ports"])
    result["filtered_count"] = len(result["filtered_ports"])
    return result


async def port_scan_range(host: str, start_port: int = 1, end_port: int = 1024,
                           timeout: float = 0.5, concurrent: int = 100) -> dict[str, Any]:
    """Scan a range of ports using concurrent connections."""
    if end_port - start_port > 10000:
        return {"error": "Port range too large (max 10000 ports)", "host": host}
    sem = asyncio.Semaphore(concurrent)
    found_ports = []

    async def check_port(port: int) -> None:
        async with sem:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                r = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: s.connect_ex((host, port))
                )
                if r == 0:
                    found_ports.append(port)
                s.close()
            except Exception:
                pass

    tasks = [check_port(p) for p in range(start_port, end_port + 1)]
    await asyncio.gather(*tasks, return_exceptions=True)
    found_ports.sort()
    return {
        "host": host,
        "range": f"{start_port}-{end_port}",
        "open_ports": found_ports,
        "open_count": len(found_ports),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def arp_scan(network: str = "192.168.1.0/24", timeout: float = 2.0) -> dict[str, Any]:
    """ARP scan local network for active hosts."""
    if not HAS_SCAPY:
        return {"error": "scapy not installed. ARP scan requires scapy."}
    result: dict[str, Any] = {"network": network, "hosts": [], "count": 0}
    try:
        net = IPv4Network(network, strict=False)
        total = net.num_addresses
        if total > 1024:
            return {"error": f"Network too large ({total} addresses). Use /24 or smaller."}
        live_hosts = []
        for ip in net.hosts():
            ip_str = str(ip)
            pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_str)
            reply = await asyncio.get_event_loop().run_in_executor(
                None, lambda: sr1(pkt, timeout=timeout, verbose=0)
            )
            if reply and reply.haslayer(ARP):
                live_hosts.append({"ip": ip_str, "mac": reply.hwsrc})
        result["hosts"] = live_hosts
        result["count"] = len(live_hosts)
    except ValueError as e:
        result["error"] = f"Invalid network: {e}"
    except Exception as e:
        result["error"] = str(e)
    return result


# ── Nmap ──
HAS_NMAP = False
try:
    import nmap
    HAS_NMAP = True
except ImportError:
    pass


async def nmap_scan(host: str, arguments: str = "-sV -F") -> dict[str, Any]:
    """Run Nmap scan against a host."""
    if not HAS_NMAP:
        return {"error": "python-nmap not installed. Run: pip install python-nmap"}
    try:
        nm = nmap.PortScanner()
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: nm.scan(host, arguments=arguments)
        )
        hosts = []
        for h in nm.all_hosts():
            host_info = {
                "host": h,
                "hostname": nm[h].hostname() if nm[h].hostname() else "",
                "state": nm[h].state(),
                "protocols": {},
            }
            for proto in nm[h].all_protocols():
                port_info = []
                for p in nm[h][proto]:
                    pdata = nm[h][proto][p]
                    port_info.append({
                        "port": p,
                        "state": pdata.get("state", ""),
                        "name": pdata.get("name", ""),
                        "product": pdata.get("product", ""),
                        "version": pdata.get("version", ""),
                        "extrainfo": pdata.get("extrainfo", ""),
                        "conf": pdata.get("conf", ""),
                        "cpe": pdata.get("cpe", ""),
                    })
                host_info["protocols"][proto] = port_info
            hosts.append(host_info)
        scan_stats = result.get("nmap", {}).get("scanstats", {})
        return {
            "hosts": hosts,
            "scan_stats": {
                "total_hosts": scan_stats.get("totalhosts", ""),
                "elapsed_seconds": scan_stats.get("elapsed", ""),
                "total_ports": scan_stats.get("totalports", ""),
            },
            "arguments": arguments,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "host": host}


async def nmap_quick_scan(host: str) -> dict[str, Any]:
    """Quick Nmap scan with common ports."""
    return await nmap_scan(host, "-sV -F")


async def nmap_full_scan(host: str) -> dict[str, Any]:
    """Full Nmap scan (1000 ports with service detection)."""
    return await nmap_scan(host, "-sV -sC -p 1-1000")


async def nmap_os_detection(host: str) -> dict[str, Any]:
    """Nmap OS detection scan."""
    return await nmap_scan(host, "-O -F")


async def nmap_vuln_scan(host: str) -> dict[str, Any]:
    """Nmap vulnerability scan using NSE scripts."""
    return await nmap_scan(host, "-sV --script vuln")


async def nmap_udp_scan(host: str) -> dict[str, Any]:
    """Nmap UDP port scan."""
    return await nmap_scan(host, "-sU -F")


# ── Email Hunter / Hunter.io ──
HAS_HUNTER = False
try:
    import requests
    HAS_HUNTER = True
except ImportError:
    pass

HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY", "")


async def hunter_email_search(domain: str) -> dict[str, Any]:
    """Search for email addresses associated with a domain."""
    if not HUNTER_API_KEY:
        return {"error": "HUNTER_API_KEY not set"}
    if not HAS_HUNTER:
        return {"error": "requests library not available"}
    try:
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(
                f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}",
                timeout=15,
            )
        )
        if r.status_code != 200:
            return {"error": f"Hunter API returned {r.status_code}: {r.text[:200]}", "domain": domain}
        data = r.json().get("data", {})
        emails = data.get("emails", [])
        return {
            "domain": domain,
            "emails": [{
                "value": e.get("value", ""),
                "type": e.get("type", ""),
                "confidence": e.get("confidence", 0),
                "position": e.get("position", ""),
                "sources": [{"domain": s.get("domain", ""), "uri": s.get("uri", "")} for s in e.get("sources", [])[:3]],
            } for e in emails],
            "total": len(emails),
            "pattern": data.get("pattern", ""),
            "organization": data.get("organization", ""),
            "country": data.get("country", ""),
        }
    except requests.exceptions.Timeout:
        return {"error": "Hunter API request timed out", "domain": domain}
    except Exception as e:
        return {"error": str(e), "domain": domain}


async def hunter_email_verify(email: str) -> dict[str, Any]:
    """Verify if an email address is valid using Hunter.io."""
    if not HUNTER_API_KEY:
        return {"error": "HUNTER_API_KEY not set"}
    if not HAS_HUNTER:
        return {"error": "requests not available"}
    try:
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(
                f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={HUNTER_API_KEY}",
                timeout=15,
            )
        )
        if r.status_code != 200:
            return {"error": f"Hunter API returned {r.status_code}", "email": email}
        data = r.json().get("data", {})
        return {
            "email": email,
            "result": data.get("result", ""),
            "score": data.get("score", 0),
            "regexp": data.get("regexp", False),
            "gibberish": data.get("gibberish", False),
            "disposable": data.get("disposable", False),
            "webmail": data.get("webmail", False),
            "mx_records": data.get("mx_records", False),
            "smtp_server": data.get("smtp_server", False),
            "smtp_check": data.get("smtp_check", False),
            "accept_all": data.get("accept_all", False),
            "block": data.get("block", False),
            "sources": data.get("sources", []),
        }
    except Exception as e:
        return {"error": str(e), "email": email}


# ── Clearbit ──
CLEARBIT_API_KEY = os.environ.get("CLEARBIT_API_KEY", "")


async def clearbit_company(domain: str) -> dict[str, Any]:
    """Look up company information via Clearbit."""
    if not CLEARBIT_API_KEY:
        return {"error": "CLEARBIT_API_KEY not set"}
    try:
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(
                f"https://company.clearbit.com/v2/companies/find?domain={domain}",
                auth=(CLEARBIT_API_KEY, ""),
                timeout=15,
            )
        )
        if r.status_code != 200:
            return {"error": f"Clearbit returned {r.status_code}", "domain": domain}
        data = r.json()
        return {
            "domain": domain,
            "name": data.get("name"),
            "legal_name": data.get("legalName"),
            "description": data.get("description"),
            "industry": data.get("category", {}).get("industry"),
            "sector": data.get("category", {}).get("sector"),
            "sub_industry": data.get("category", {}).get("subIndustry"),
            "employees": data.get("metrics", {}).get("employees"),
            "estimated_employees": data.get("metrics", {}).get("estimatedEmployees"),
            "market_cap": data.get("metrics", {}).get("marketCap"),
            "raised": data.get("metrics", {}).get("raised"),
            "annual_revenue": data.get("metrics", {}).get("annualRevenue"),
            "location": data.get("location"),
            "founded_year": data.get("foundedYear"),
            "phone_numbers": data.get("phone", {}),
            "tech_used": data.get("tech", []),
            "logo": data.get("logo"),
            "site": data.get("site", {}),
            "tags": data.get("tags", []),
            "type": data.get("type"),
        }
    except Exception as e:
        return {"error": str(e), "domain": domain}


async def clearbit_person(email: str) -> dict[str, Any]:
    """Look up person information via Clearbit."""
    if not CLEARBIT_API_KEY:
        return {"error": "CLEARBIT_API_KEY not set"}
    try:
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(
                f"https://person.clearbit.com/v2/people/find?email={email}",
                auth=(CLEARBIT_API_KEY, ""),
                timeout=15,
            )
        )
        if r.status_code != 200:
            return {"error": f"Clearbit returned {r.status_code}", "email": email}
        data = r.json()
        name = data.get("name", {})
        employment = data.get("employment", {})
        return {
            "email": email,
            "full_name": f"{name.get('givenName', '')} {name.get('familyName', '')}".strip(),
            "given_name": name.get("givenName"),
            "family_name": name.get("familyName"),
            "display_name": name.get("fullName"),
            "bio": data.get("bio"),
            "location": data.get("location"),
            "timezone": data.get("timezone"),
            "avatar": data.get("avatar"),
            "company": employment.get("name"),
            "company_domain": employment.get("domain"),
            "role": employment.get("role"),
            "title": employment.get("title"),
            "seniority": employment.get("seniority"),
            "twitter": data.get("twitter", {}).get("handle"),
            "twitter_followers": data.get("twitter", {}).get("followers"),
            "github": data.get("github", {}).get("handle"),
            "github_company": data.get("github", {}).get("company"),
            "github_followers": data.get("github", {}).get("followers"),
            "facebook": data.get("facebook", {}).get("handle"),
            "linkedin": data.get("linkedin", {}).get("handle"),
            "linkedin_connections": data.get("linkedin", {}).get("connections"),
            "googleplus": data.get("googleplus", {}).get("handle"),
            "fuzzy": data.get("fuzzy", False),
        }
    except Exception as e:
        return {"error": str(e), "email": email}


async def clearbit_name_to_email(company_domain: str, first_name: str, last_name: str) -> dict[str, Any]:
    """Generate probable email addresses using Clearbit's name-to-email API."""
    if not CLEARBIT_API_KEY:
        return {"error": "CLEARBIT_API_KEY not set"}
    try:
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(
                f"https://person.clearbit.com/v2/people/find?email={first_name}.{last_name}@{company_domain}",
                auth=(CLEARBIT_API_KEY, ""),
                timeout=15,
            )
        )
        patterns = [
            f"{first_name}@{company_domain}",
            f"{first_name}.{last_name}@{company_domain}",
            f"{first_name[0]}{last_name}@{company_domain}",
            f"{first_name}{last_name[0]}@{company_domain}",
            f"{first_name[0]}.{last_name}@{company_domain}",
            f"{first_name}.{last_name[0]}@{company_domain}",
            f"{last_name}@{company_domain}",
            f"{first_name[0]}{last_name[0]}@{company_domain}",
            f"{first_name}_{last_name}@{company_domain}",
            f"{first_name}-{last_name}@{company_domain}",
        ]
        return {
            "domain": company_domain,
            "first_name": first_name,
            "last_name": last_name,
            "possible_emails": patterns,
            "count": len(patterns),
        }
    except Exception as e:
        return {"error": str(e)}


# ── Recon-ng ──
RECONNG_PATH = os.environ.get("RECONNG_PATH", "recon-ng")


async def reconng_workspace(name: str) -> dict[str, Any]:
    """Create and list Recon-ng workspace."""
    try:
        proc = await asyncio.create_subprocess_exec(
            RECONNG_PATH, "-w", name, "-x", "show modules",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return {"workspace": name, "module_list": stdout.decode()[:2000]}
    except FileNotFoundError:
        return {"error": "recon-ng not found. Install: pip install recon-ng"}
    except Exception as e:
        return {"error": str(e)}


async def reconng_run_module(workspace: str, module: str, source: str = "") -> dict[str, Any]:
    """Run a specific Recon-ng module in a workspace."""
    cmds = f"workspaces select {workspace}; modules load {module}; "
    if source:
        cmds += f"set SOURCE {source}; "
    cmds += "run; exit"
    try:
        proc = await asyncio.create_subprocess_exec(
            RECONNG_PATH, "-x", cmds,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode()
        contacts = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", output)))
        hosts = list(set(re.findall(r"\d+\.\d+\.\d+\.\d+", output)))
        return {
            "workspace": workspace,
            "module": module,
            "source": source,
            "contacts_found": len(contacts),
            "contacts": contacts[:50],
            "hosts_found": len(hosts),
            "hosts": hosts[:50],
            "output": output[:2000],
        }
    except FileNotFoundError:
        return {"error": "recon-ng not found"}
    except Exception as e:
        return {"error": str(e)}


# ── HIBP / Breach Checking ──
HAS_HIBP = False
try:
    import requests
    HAS_HIBP = True
except ImportError:
    pass

HIBP_API_KEY = os.environ.get("HIBP_API_KEY", "")


async def hibp_breach_check(email: str, truncate: bool = True) -> dict[str, Any]:
    """Check if an email was involved in known data breaches."""
    if not HIBP_API_KEY:
        return {"error": "HIBP_API_KEY not set", "email": email}
    if not HAS_HIBP:
        return {"error": "requests not available for API call"}
    try:
        headers = {"hibp-api-key": HIBP_API_KEY, "user-agent": "FRIDAY-OSINT/2.0"}
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
        if truncate:
            url += "?truncateResponse=true"
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(url, headers=headers, timeout=15)
        )
        if r.status_code == 200:
            breaches = r.json()
            return {
                "email": email,
                "breach_count": len(breaches),
                "breaches": [{"name": b.get("Name", ""), "domain": b.get("Domain", ""),
                              "date": b.get("BreachDate", ""), "classes": b.get("DataClasses", [])} for b in breaches],
                "pwned": True,
            }
        elif r.status_code == 404:
            return {"email": email, "breach_count": 0, "pwned": False, "message": "No breaches found"}
        else:
            return {"error": f"HIBP returned {r.status_code}", "email": email}
    except Exception as e:
        return {"error": str(e), "email": email}


async def hibp_paste_check(email: str) -> dict[str, Any]:
    """Check if an email appeared in pastes."""
    if not HIBP_API_KEY:
        return {"error": "HIBP_API_KEY not set"}
    if not HAS_HIBP:
        return {"error": "requests not available"}
    try:
        headers = {"hibp-api-key": HIBP_API_KEY, "user-agent": "FRIDAY-OSINT/2.0"}
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(
                f"https://haveibeenpwned.com/api/v3/pasteaccount/{email}",
                headers=headers, timeout=15,
            )
        )
        if r.status_code == 200:
            pastes = r.json()
            return {
                "email": email,
                "paste_count": len(pastes),
                "pastes": [{"source": p.get("Source", ""), "title": p.get("Title", ""),
                            "date": p.get("Date", ""), "email_count": p.get("EmailCount", 0)} for p in pastes],
            }
        elif r.status_code == 404:
            return {"email": email, "paste_count": 0, "message": "No pastes found"}
        else:
            return {"error": f"HIBP returned {r.status_code}", "email": email}
    except Exception as e:
        return {"error": str(e), "email": email}


async def hibp_domain_breaches(domain: str) -> dict[str, Any]:
    """Check all breaches for a domain."""
    api_key = os.environ.get("HIBP_API_KEY", "")
    if not api_key:
        return {"error": "HIBP_API_KEY not set"}
    try:
        headers = {"hibp-api-key": api_key, "user-agent": "FRIDAY-OSINT/2.0"}
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(
                f"https://haveibeenpwned.com/api/v3/breaches?domain={domain}",
                headers=headers, timeout=15,
            )
        )
        if r.status_code == 200:
            breaches = r.json()
            return {
                "domain": domain,
                "breach_count": len(breaches),
                "breaches": [{"name": b.get("Name"), "date": b.get("BreachDate"),
                              "data_classes": b.get("DataClasses", []), "pwn_count": b.get("PwnCount"),
                              "description": b.get("Description", "")[:200]} for b in breaches],
            }
        else:
            return {"error": f"HIBP returned {r.status_code}", "domain": domain}
    except Exception as e:
        return {"error": str(e), "domain": domain}


# ── SSL/TLS Certificate Check ──


async def ssl_certificate_check(hostname: str, port: int = 443) -> dict[str, Any]:
    """Retrieve and analyze SSL/TLS certificate from a server."""
    result: dict[str, Any] = {"hostname": hostname, "port": port}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(hostname, port, ssl=ctx),
            timeout=10,
        )
        sock = writer.get_extra_info("ssl_object")
        cert = sock.getpeercert()
        writer.close()
        if not cert:
            result["error"] = "No certificate returned"
            return result
        result["subject"] = dict(cert.get("subject", [[("", "")]])[0])
        result["issuer"] = dict(cert.get("issuer", [[("", "")]])[0])
        result["serial"] = cert.get("serialNumber")
        result["version"] = cert.get("version")
        result["not_before"] = cert.get("notBefore")
        result["not_after"] = cert.get("notAfter")
        result["subject_alt_names"] = [san[1] for san in cert.get("subjectAltName", [])]
        result["valid_from"] = cert.get("notBefore")
        result["valid_to"] = cert.get("notAfter")
        not_after = cert.get("notAfter", "")
        if not_after:
            try:
                from datetime import datetime as dt
                expiry = dt.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry - dt.now()).days
                result["days_until_expiry"] = days_left
                if days_left < 0:
                    result["status"] = "expired"
                elif days_left < 30:
                    result["status"] = "expiring_soon"
                else:
                    result["status"] = "valid"
            except Exception:
                pass
        else:
            result["status"] = "unknown"
    except asyncio.TimeoutError:
        result["error"] = f"Connection to {hostname}:{port} timed out"
    except ssl.SSLCertVerificationError as e:
        result["error"] = f"SSL verification failed: {e}"
        result["cert_invalid"] = True
    except ConnectionRefusedError:
        result["error"] = f"Connection refused to {hostname}:{port}"
    except Exception as e:
        result["error"] = str(e)
    return result


async def ssl_certificate_check_multi(hostnames: list[str], port: int = 443) -> dict[str, Any]:
    """Check SSL certificates for multiple hosts."""
    results = []
    for hostname in hostnames:
        result = await ssl_certificate_check(hostname, port)
        results.append(result)
    return {"results": results, "count": len(results)}


# ── Banner Grabbing ──


async def banner_grab(host: str, port: int, timeout: float = 5.0) -> dict[str, Any]:
    """Grab service banner from a specific port."""
    result: dict[str, Any] = {"host": host, "port": port}
    probes = {
        21: b"",
        22: b"",
        23: b"",
        25: b"EHLO\r\n",
        80: b"GET / HTTP/1.0\r\n\r\n",
        110: b"",
        143: b"",
        443: b"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n",
        445: b"",
        993: b"",
        995: b"",
        8080: b"GET / HTTP/1.0\r\n\r\n",
        8443: b"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n",
    }
    try:
        if port == 443 or port == 8443:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ctx),
                timeout=timeout,
            )
        else:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
        probe = probes.get(port, b"")
        if probe:
            writer.write(probe)
            await writer.drain()
        try:
            banner_data = await asyncio.wait_for(reader.read(1024), timeout=3)
            text = banner_data.decode("utf-8", errors="replace")[:500]
            result["banner"] = text
            if port == 80 or port == 8080:
                server_match = re.search(r"Server:\s*(.+)", text, re.IGNORECASE)
                if server_match:
                    result["server"] = server_match.group(1).strip()
            elif port == 22:
                ssh_match = re.search(r"SSH-\d+\.\d+[-\s]*(.+)", text, re.IGNORECASE)
                if ssh_match:
                    result["ssh_version"] = ssh_match.group(1).strip()
        except asyncio.TimeoutError:
            result["banner"] = "(no banner)"
        except Exception as e:
            result["banner"] = f"(error: {e})"
        writer.close()
    except ConnectionRefusedError:
        result["error"] = "Connection refused"
    except asyncio.TimeoutError:
        result["error"] = "Connection timed out"
    except Exception as e:
        result["error"] = str(e)
    return result


async def banner_grab_multi(host: str, ports: Optional[list[int]] = None) -> dict[str, Any]:
    """Grab banners from multiple ports on a host."""
    if ports is None:
        ports = [21, 22, 25, 80, 110, 143, 443, 445, 993, 995, 8080, 8443]
    results = []
    for port in ports:
        result = await banner_grab(host, port)
        if result.get("banner") or result.get("error"):
            results.append(result)
    return {"host": host, "banners": results, "count": len(results)}


# ── Formatting for LLM ──


async def format_osint_for_llm(result: dict[str, Any], tool_name: str = "") -> str:
    """Format OSINT results as a concise string for LLM consumption."""
    lines = []
    if not result:
        return "No results returned."
    if "error" in result:
        return f"[{tool_name}] Error: {result['error']}"
    if tool_name == "shodan_search" or tool_name == "shodan":
        lines.append(f"Shodan Search: {result.get('total', 0)} results")
        for m in result.get("matches", [])[:5]:
            lines.append(f"  {m.get('ip')}:{m.get('port')} ({m.get('product', '?')}) - {m.get('org', '')}")
        if len(result.get("matches", [])) > 5:
            lines.append(f"  ... and {len(result['matches']) - 5} more")
    elif tool_name == "shodan_host":
        lines.append(f"Shodan Host: {result.get('ip')}")
        lines.append(f"  Org: {result.get('org', '?')} | OS: {result.get('os', '?')}")
        lines.append(f"  Ports ({result.get('port_count', 0)}): {', '.join(str(p) for p in result.get('ports', [])[:20])}")
        if result.get("vulns"):
            lines.append(f"  Vulns: {', '.join(result['vulns'][:10])}")
    elif tool_name == "whois":
        lines.append(f"WHOIS: {result.get('domain')}")
        lines.append(f"  Registrar: {result.get('registrar', '?')}")
        lines.append(f"  Created: {result.get('creation_date', '?')} | Expires: {result.get('expiration_date', '?')}")
        lines.append(f"  NS: {', '.join(result.get('name_servers', [])[:5])}")
    elif tool_name == "nuclei_scan" or tool_name == "nuclei":
        lines.append(f"Nuclei Scan: {result.get('target')}")
        breakdown = result.get("severity_breakdown", {})
        if breakdown:
            lines.append(f"  Severities: {dict(breakdown)}")
        lines.append(f"  Findings: {result.get('count', 0)}")
        for f in result.get("findings", [])[:5]:
            info = f.get("info", {})
            lines.append(f"  [{f.get('severity', '?')}] {info.get('name', '?')} - {f.get('host', '')}")
    elif tool_name == "nmap":
        for h in result.get("hosts", []):
            lines.append(f"Nmap: {h.get('host')} ({h.get('state')})")
            for proto, ports in h.get("protocols", {}).items():
                for p in ports[:10]:
                    lines.append(f"  {p.get('port')}/{proto} {p.get('state')} {p.get('name')} {p.get('product', '')} {p.get('version', '')}")
    elif tool_name == "geoip":
        lines.append(f"GeoIP: {result.get('ip')}")
        lines.append(f"  Location: {result.get('city', '?')}, {result.get('country', '?')}")
        loc = result.get("location", {})
        if loc:
            lines.append(f"  Lat/Lon: {loc.get('latitude')}, {loc.get('longitude')}")
        if result.get("asn"):
            lines.append(f"  ASN: AS{result.get('asn')} ({result.get('asn_org', '')})")
    elif tool_name == "hunter" or tool_name == "hunter_email_search":
        lines.append(f"Hunter: {result.get('domain')} - {result.get('total', 0)} emails")
        for e in result.get("emails", [])[:5]:
            lines.append(f"  {e.get('value')} [{e.get('type')}] (confidence: {e.get('confidence')})")
    elif tool_name == "hibp_breach_check" or tool_name == "breach_check":
        lines.append(f"Breach Check: {result.get('email')}")
        lines.append(f"  Breaches: {result.get('breach_count', 0)}")
        for b in result.get("breaches", [])[:5]:
            lines.append(f"  {b.get('name')} ({b.get('date')}) - {', '.join(b.get('classes', []))}")
    elif tool_name == "ssl_certificate_check" or tool_name == "ssl":
        lines.append(f"SSL Cert: {result.get('hostname')}:{result.get('port')}")
        lines.append(f"  Subject: {result.get('subject', {})}")
        lines.append(f"  Issuer: {result.get('issuer', {})}")
        lines.append(f"  Expires: {result.get('not_after', '?')} ({result.get('days_until_expiry', '?')} days)")
        lines.append(f"  Status: {result.get('status', '?')}")
        sans = result.get("subject_alt_names", [])
        if sans:
            lines.append(f"  SANs: {len(sans)} domains")
    else:
        lines.append(f"{tool_name}: {json.dumps(result, indent=2)[:500]}")
    return "\n".join(lines)


OSINT_TOOL_DESCRIPTIONS = {
    "shodan_search": ("Search Shodan for devices", {"query": "Search query (e.g. apache port:80)", "limit": "Max results (default 10)"}),
    "shodan_host": ("Get Shodan info for an IP", {"ip": "Target IP address"}),
    "shodan_search_count": ("Get Shodan result count", {"query": "Search query"}),
    "shodan_ports": ("List open ports from Shodan", {"ip": "Target IP"}),
    "shodan_dns_resolve": ("Resolve hostnames via Shodan DNS", {"hostnames": "List of hostnames to resolve"}),
    "censys_search": ("Search Censys for hosts", {"query": "Search query", "limit": "Max results (default 10)"}),
    "censys_host_view": ("View Censys host details", {"ip": "Target IP"}),
    "censys_certificate_search": ("Search Censys certificate logs", {"query": "Certificate query", "limit": "Max results (default 10)"}),
    "whois_lookup": ("WHOIS domain lookup", {"domain": "Domain to query"}),
    "whois_raw_lookup": ("Raw WHOIS text output", {"domain": "Domain to query"}),
    "whois_ip_lookup": ("WHOIS IP address lookup", {"ip": "IP address to query"}),
    "harvester_enum": ("Run theHarvester OSINT", {"domain": "Target domain", "sources": "Sources (default: all, comma-separated)"}),
    "harvester_enum_all_sources": ("Run theHarvester across all sources", {"domain": "Target domain"}),
    "subfinder_enum": ("Subdomain discovery via Subfinder", {"domain": "Target domain", "recursive": "Recursive search (default: false)", "resolve": "Resolve subdomains (default: true)"}),
    "subfinder_enum_multi": ("Subfinder on multiple domains", {"domains": "List of domains"}),
    "nuclei_scan": ("Nuclei vulnerability scanner", {"target": "Target URL/IP", "severity": "Min severity (info,low,medium,high,critical)", "templates": "Specific template or directory", "timeout": "Scan timeout seconds (default 300)"}),
    "nuclei_scan_list_targets": ("Nuclei scan on multiple targets", {"targets": "List of targets", "severity": "Min severity"}),
    "nuclei_update_templates": ("Update Nuclei templates", {}),
    "geoip_lookup": ("GeoIP location lookup", {"ip": "IP address"}),
    "geoip_bulk_lookup": ("GeoIP lookup for multiple IPs", {"ips": "List of IP addresses"}),
    "geoip_asn_lookup": ("ASN lookup for an IP", {"ip": "IP address"}),
    "ping_host": ("Ping a host (ICMP/system ping)", {"host": "Hostname or IP", "count": "Ping count (default 3)", "timeout": "Per-ping timeout (default 2s)"}),
    "port_scan": ("Port scan a host (TCP connect/SYN)", {"host": "Target host", "ports": "Port list (default: common ports)", "timeout": "Per-port timeout (default 1s)", "scan_type": "connect or syn (default: connect)"}),
    "port_scan_range": ("Scan a port range concurrently", {"host": "Target host", "start_port": "Start port (default 1)", "end_port": "End port (default 1024)", "concurrent": "Concurrent sockets (default 100)"}),
    "arp_scan": ("ARP scan local network (requires scapy)", {"network": "CIDR network (default 192.168.1.0/24)", "timeout": "Per-host ARP timeout"}),
    "nmap_scan": ("Nmap scan with custom args", {"host": "Target host", "arguments": "nmap args (default: -sV -F)"}),
    "nmap_quick_scan": ("Quick Nmap scan (top ports)", {"host": "Target host"}),
    "nmap_full_scan": ("Full Nmap scan (1000 ports + scripts)", {"host": "Target host"}),
    "nmap_os_detection": ("Nmap OS detection", {"host": "Target host"}),
    "nmap_vuln_scan": ("Nmap vulnerability scan (NSE vuln scripts)", {"host": "Target host"}),
    "nmap_udp_scan": ("Nmap UDP port scan", {"host": "Target host"}),
    "hunter_email_search": ("Hunter.io email domain search", {"domain": "Domain to search"}),
    "hunter_email_verify": ("Hunter.io email verification", {"email": "Email address to verify"}),
    "clearbit_company": ("Clearbit company lookup", {"domain": "Company domain"}),
    "clearbit_person": ("Clearbit person lookup", {"email": "Person email address"}),
    "clearbit_name_to_email": ("Generate possible emails from name", {"company_domain": "Company domain", "first_name": "First name", "last_name": "Last name"}),
    "reconng_workspace": ("Create/query Recon-ng workspace", {"name": "Workspace name"}),
    "reconng_run_module": ("Run Recon-ng module", {"workspace": "Workspace name", "module": "Module path (e.g. recon/contacts-contacts/hunter)"}),
    "hibp_breach_check": ("Check email against HIBP breaches", {"email": "Email to check"}),
    "hibp_paste_check": ("Check email against HIBP pastes", {"email": "Email to check"}),
    "hibp_domain_breaches": ("Check all breaches for a domain", {"domain": "Domain to check"}),
    "ssl_certificate_check": ("Check SSL/TLS certificate", {"hostname": "Server hostname", "port": "Port (default 443)"}),
    "ssl_certificate_check_multi": ("Check SSL certs for multiple hosts", {"hostnames": "List of hostnames", "port": "Port (default 443)"}),
    "banner_grab": ("Grab service banner from port", {"host": "Target host", "port": "Port number", "timeout": "Timeout seconds (default 5)"}),
    "banner_grab_multi": ("Grab banners from multiple ports", {"host": "Target host", "ports": "Port list (default: common ports)"}),
    "format_osint_for_llm": ("Format OSINT results for LLM consumption", {"result": "OSINT result dict", "tool_name": "Tool name for context"}),
}
