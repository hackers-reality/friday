"""
OSINT Enhanced Tools — Knowledge Graph Integration & Multi-Agent Orchestration.
Inspired by PentAGI's architecture for distributed intelligence gathering.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import os
import re
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from friday.logging_utils import configure_logging
from friday._paths import FRIDAY_MEMORY
from friday.tools_osint_extra import dns_enum, dns_bruteforce
from friday.security_use_bridge import whois_lookup
from friday.tools.osint_advanced_tools import shodan_search, shodan_host, geoip_lookup

logger = configure_logging("osint_enhanced")

OSINT_STORAGE = os.path.join(FRIDAY_MEMORY, "osint_enhanced")


def _ensure_storage():
    os.makedirs(OSINT_STORAGE, exist_ok=True)


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=120)
    except RuntimeError:
        return asyncio.run(coro)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_label(score: float) -> str:
    if score >= 0.8:
        return "HIGH"
    elif score >= 0.5:
        return "MEDIUM"
    else:
        return "LOW"


def _safe_write_json(path: str, data: dict) -> None:
    try:
        _ensure_storage()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to write {path}: {e}")


def _safe_read_json(path: str) -> dict:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
    return {}


# ─── Knowledge Graph & Multi-Source Intelligence ─────────────────────────


def osint_knowledge_graph(entity: str, entity_type: str = "person") -> dict:
    """
    Build a knowledge graph around an entity.
    Searches multiple sources, extracts relationships, stores structured graph.
    """
    _ensure_storage()
    graph_path = os.path.join(OSINT_STORAGE, f"kg_{entity.lower().replace(' ', '_')}.json")

    def _search_social(username: str) -> dict:
        from friday.tools_osint_extra import social_analyzer, username_search
        social = _run_async(social_analyzer(username))
        dev = _run_async(username_search(username))
        return {"social_profiles": social, "dev_profiles": dev}

    def _search_web(entity: str) -> dict:
        results = []
        try:
            import requests
            search_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(entity)}&format=json&no_html=1"
            r = requests.get(search_url, headers={"User-Agent": "FRIDAY-OSINT/3.0"}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                results = data.get("RelatedTopics", [])[:10]
        except Exception:
            pass
        return {"web_results": len(results), "web_data": results}

    def _breach_check(entity: str) -> dict:
        from friday.tools_osint_extra import email_rep, holehe_check
        breaches = {}
        if "@" in entity:
            breaches["emailrep"] = _run_async(email_rep(entity))
            breaches["holehe"] = _run_async(holehe_check(entity))
        return breaches

    logger.info(f"Building knowledge graph for entity: {entity}")

    social_data = _search_social(entity)
    web_data = _search_web(entity)
    breach_data = _breach_check(entity)

    nodes = []
    edges = []
    seen = set()

    center_id = hashlib.sha256(entity.lower().encode()).hexdigest()[:12]
    nodes.append({
        "id": center_id, "label": entity, "type": entity_type,
        "source": "user_input", "confidence": 1.0,
        "properties": {"timestamp": _ts()},
    })
    seen.add(center_id)

    profiles = social_data.get("social_profiles", {}).get("profiles", [])
    for prof in profiles:
        platform = prof.get("platform", "unknown")
        plat_id = hashlib.sha256(f"{platform}:{entity}".encode()).hexdigest()[:12]
        if plat_id not in seen:
            seen.add(plat_id)
            nodes.append({
                "id": plat_id, "label": f"{platform}/{entity}", "type": "social_account",
                "source": "social_scan", "confidence": 0.7,
                "properties": {"platform": platform, "url": prof.get("url", "")},
            })
            edges.append({
                "source": center_id, "target": plat_id,
                "relation": "has_account_on", "weight": 0.8,
            })

    dev_profiles = social_data.get("dev_profiles", {}).get("profiles", [])
    for prof in dev_profiles:
        platform = prof.get("platform", "unknown")
        plat_id = hashlib.sha256(f"dev:{platform}:{entity}".encode()).hexdigest()[:12]
        if plat_id not in seen:
            seen.add(plat_id)
            nodes.append({
                "id": plat_id, "label": f"{platform}/{entity}", "type": "dev_account",
                "source": "dev_scan", "confidence": 0.75,
                "properties": {"platform": platform, "url": prof.get("url", "")},
            })
            edges.append({
                "source": center_id, "target": plat_id,
                "relation": "has_dev_account_on", "weight": 0.7,
            })

    if breach_data:
        for service, data in breach_data.items():
            if isinstance(data, dict) and not data.get("error"):
                breach_id = hashlib.sha256(f"breach:{service}:{entity}".encode()).hexdigest()[:12]
                if breach_id not in seen:
                    seen.add(breach_id)
                    nodes.append({
                        "id": breach_id, "label": f"breach_data/{service}", "type": "breach_info",
                        "source": "breach_check", "confidence": 0.5,
                        "properties": data,
                    })
                    edges.append({
                        "source": center_id, "target": breach_id,
                        "relation": "associated_with", "weight": 0.5,
                    })

    graph = {
        "entity": entity,
        "entity_type": entity_type,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": list(set(n["type"] for n in nodes)),
            "sources_used": ["social_scan", "web_search", "breach_check"],
            "timestamp": _ts(),
        },
    }

    _safe_write_json(graph_path, graph)
    logger.info(f"Knowledge graph saved to {graph_path} ({len(nodes)} nodes, {len(edges)} edges)")
    return graph


# ─── Multi-Agent OSINT Investigation ──────────────────────────────────────


def osint_multi_agent(target: str, depth: str = "basic") -> dict:
    """
    Multi-agent OSINT investigation with 4 specialized agents.
    Aggregates recon, social, technical, and threat intelligence.
    """
    _ensure_storage()
    report_path = os.path.join(OSINT_STORAGE, f"multiagent_{target.lower().replace(' ', '_')}.json")

    is_domain = "." in target and not target.startswith("+") and " " not in target
    is_email = "@" in target

    def _agent_recon(t: str) -> dict:
        findings = {}
        if is_domain:
            whois = _run_async(whois_lookup(t))
            findings["whois"] = whois if "error" not in whois else {"error": whois.get("error")}
            dns = _run_async(dns_enum(t))
            findings["dns"] = dns if "error" not in dns else {"error": dns.get("error")}
            subs = _run_async(dns_bruteforce(t))
            findings["subdomains"] = subs if "error" not in subs else {"error": subs.get("error")}
        findings["timestamp"] = _ts()
        return findings

    def _agent_social(t: str) -> dict:
        from friday.tools_osint_extra import social_analyzer, username_search
        findings = {}
        findings["social"] = _run_async(social_analyzer(t))
        findings["dev_accounts"] = _run_async(username_search(t))
        if is_email:
            from friday.tools_osint_extra import holehe_check
            findings["registered_services"] = _run_async(holehe_check(t))
        findings["timestamp"] = _ts()
        return findings

    def _agent_technical(t: str) -> dict:
        findings = {}
        if is_domain:
            from friday.tools_osint_extra import whatweb, web_server_headers, cdn_detect
            findings["technologies"] = _run_async(whatweb(t))
            findings["headers"] = _run_async(web_server_headers(t))
            findings["cdn"] = _run_async(cdn_detect(t))
            shodan_q = _run_async(shodan_search(t, limit=5))
            if "error" not in shodan_q:
                findings["shodan"] = shodan_q
            if depth == "deep":
                from friday.tools_osint_extra import whatcms, spf_check, dmarc_check, dkim_check, mx_lookup
                findings["cms"] = _run_async(whatcms(t))
                findings["spf"] = _run_async(spf_check(t))
                findings["dmarc"] = _run_async(dmarc_check(t))
                findings["dkim"] = _run_async(dkim_check(t))
                findings["mx"] = _run_async(mx_lookup(t))
        findings["timestamp"] = _ts()
        return findings

    def _agent_threat_intel(t: str) -> dict:
        findings = {}
        if is_domain:
            from friday.tools_osint_extra import virus_total_url, urlscan_submit
            vt = _run_async(virus_total_url(f"https://{t}"))
            if "error" not in vt:
                findings["virustotal"] = vt
            urlscan = _run_async(urlscan_submit(f"https://{t}"))
            if "error" not in urlscan:
                findings["urlscan"] = urlscan
        if is_email:
            from friday.tools_osint_extra import email_rep
            findings["emailrep"] = _run_async(email_rep(t))
        findings["timestamp"] = _ts()
        return findings

    logger.info(f"Multi-agent OSINT investigation starting for: {target} [depth={depth}]")
    agents = {
        "reconnaissance": _agent_recon(target),
        "social_footprint": _agent_social(target),
        "technical_analysis": _agent_technical(target),
        "threat_intelligence": _agent_threat_intel(target),
    }

    total_findings = sum(
        len(v) for agent_data in agents.values()
        for k, v in agent_data.items() if isinstance(v, (dict, list)) and k != "timestamp"
    )

    report = {
        "target": target,
        "depth": depth,
        "agents": agents,
        "summary": {
            "total_agents": 4,
            "total_findings": total_findings,
            "sources_checked": list(agents.keys()),
            "confidence": "HIGH" if depth == "deep" else "MEDIUM",
            "timestamp": _ts(),
        },
    }

    _safe_write_json(report_path, report)
    return report


# ─── OSINT Timeline ──────────────────────────────────────────────────────


def osint_timeline(target: str) -> dict:
    """
    Build a chronological timeline of events/activity for a target.
    Wayback Machine, certificate logs, DNS history, social activity.
    """
    _ensure_storage()
    timeline_path = os.path.join(OSINT_STORAGE, f"timeline_{target.lower().replace(' ', '_')}.json")
    timeline: list[dict] = []
    sources_used: list[str] = []
    errors: list[str] = []

    def _wayback_snapshots(domain: str) -> list[dict]:
        entries = []
        try:
            import requests
            cdx_url = f"https://web.archive.org/cdx/search/cdx?url={domain}&output=json&limit=100"
            r = requests.get(cdx_url, headers={"User-Agent": "FRIDAY-OSINT/3.0"}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                for row in data[1:]:
                    if len(row) >= 6:
                        ts_str = row[1]
                        try:
                            dt = datetime.strptime(ts_str, "%Y%m%d%H%M%S")
                            entries.append({
                                "date": dt.isoformat(),
                                "source": "wayback_machine",
                                "event": f"Snapshot captured: {row[2]}",
                                "url": f"https://web.archive.org/web/{ts_str}/{domain}",
                                "status_code": row[4],
                                "mime_type": row[3],
                            })
                        except ValueError:
                            pass
            else:
                errors.append(f"Wayback API returned {r.status_code}")
        except ImportError:
            errors.append("requests not available for wayback")
        except Exception as e:
            errors.append(f"Wayback error: {e}")
        return entries

    def _certificate_logs(domain: str) -> list[dict]:
        entries = []
        try:
            import requests
            r = requests.get(
                f"https://crt.sh/?q={domain}&output=json",
                headers={"User-Agent": "FRIDAY-OSINT/3.0"},
                timeout=15,
            )
            if r.status_code == 200:
                certs = r.json()
                seen_dates: set[str] = set()
                for cert in certs[:100]:
                    for date_field in ["not_before", "not_after", "entry_timestamp"]:
                        raw = cert.get(date_field)
                        if raw and raw not in seen_dates:
                            seen_dates.add(raw)
                            try:
                                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                            except (ValueError, TypeError):
                                try:
                                    dt = datetime.strptime(str(raw)[:19], "%Y-%m-%dT%H:%M:%S")
                                except ValueError:
                                    continue
                            entries.append({
                                "date": dt.isoformat(),
                                "source": "certificate_transparency",
                                "event": f"SSL cert {'issued' if date_field == 'not_before' else 'expiry' if date_field == 'not_after' else 'logged'}",
                                "issuer": cert.get("issuer_name", ""),
                                "subject": cert.get("name", ""),
                                "serial": cert.get("serial_number", "")[:16],
                            })
            else:
                errors.append(f"crt.sh returned {r.status_code}")
        except ImportError:
            errors.append("requests not available for crt.sh")
        except Exception as e:
            errors.append(f"Certificate log error: {e}")
        return entries

    def _dns_history(domain: str) -> list[dict]:
        entries = []
        try:
            import requests
            api_key = os.environ.get("SECURITYTRAILS_API_KEY", "")
            if api_key:
                r = requests.get(
                    f"https://api.securitytrails.com/v1/history/{domain}/dns/a",
                    headers={"APIKEY": api_key},
                    timeout=15,
                )
                if r.status_code == 200:
                    data = r.json()
                    for record in data.get("records", [])[:50]:
                        entries.append({
                            "date": record.get("first_seen", ""),
                            "source": "dns_history",
                            "event": f"DNS A record: {record.get('value', '')}",
                            "organizations": record.get("organizations", []),
                        })
        except Exception as e:
            errors.append(f"DNS history error: {e}")
        return entries

    is_domain = "." in target and " " not in target
    is_email = "@" in target
    is_username = not is_domain and not is_email

    if is_domain:
        logger.info(f"Building timeline for domain: {target}")
        snapshots = _wayback_snapshots(target)
        timeline.extend(snapshots)
        if snapshots:
            sources_used.append("wayback_machine")

        certs = _certificate_logs(target)
        timeline.extend(certs)
        if certs:
            sources_used.append("certificate_transparency")

        dns_hist = _dns_history(target)
        timeline.extend(dns_hist)
        if dns_hist:
            sources_used.append("dns_history")

    if is_email:
        sources_used.append("email_breach_history")
        from friday.tools_osint_extra import email_rep
        rep = _run_async(email_rep(target))
        if isinstance(rep, dict) and not rep.get("error"):
            timeline.append({
                "date": _ts(),
                "source": "email_reputation",
                "event": f"Email reputation: {rep.get('reputation', 'unknown')}",
                "details": rep.get("details", {}),
            })

    if is_username:
        from friday.tools_osint_extra import social_analyzer
        social = _run_async(social_analyzer(target))
        if isinstance(social, dict) and not social.get("error"):
            sources_used.append("social_media")
            for prof in social.get("profiles", []):
                timeline.append({
                    "date": _ts(),
                    "source": "social_media",
                    "event": f"Profile found on {prof.get('platform', 'unknown')}",
                    "url": prof.get("url", ""),
                })

    timeline.sort(key=lambda x: x.get("date", ""))
    result = {
        "target": target,
        "sources_used": list(set(sources_used)),
        "timeline_entries": timeline,
        "total_events": len(timeline),
        "time_span": {
            "earliest": timeline[0]["date"] if timeline else None,
            "latest": timeline[-1]["date"] if timeline else None,
        },
        "errors": errors if errors else None,
        "timestamp": _ts(),
    }
    _safe_write_json(timeline_path, result)
    return result


# ─── OSINT Correlation ──────────────────────────────────────────────────


def osint_correlation(targets: list[str]) -> dict:
    """
    Correlate multiple targets to find shared infrastructure and connections.
    """
    _ensure_storage()
    corr_path = os.path.join(OSINT_STORAGE, f"correlation_{hashlib.sha256(str(sorted(targets)).encode()).hexdigest()[:12]}.json")
    if not targets or len(targets) < 2:
        return {"error": "At least 2 targets required for correlation", "targets": targets}

    logger.info(f"Correlating {len(targets)} targets: {targets}")
    shared_ips: dict[str, list[str]] = defaultdict(list)
    shared_domains: dict[str, list[str]] = defaultdict(list)
    shared_emails: dict[str, list[str]] = defaultdict(list)
    shared_tech: dict[str, list[str]] = defaultdict(list)
    target_data: dict[str, dict] = {}

    for target in targets:
        is_domain = "." in target and " " not in target and not target.startswith("+")
        info: dict[str, Any] = {"target": target, "ips": [], "domains": [], "emails": [], "technologies": []}

        if is_domain:
            dns = _run_async(dns_enum(target))
            if "error" not in dns:
                ips = dns.get("records", {}).get("A", [])
                info["ips"] = ips
                for ip in ips:
                    shared_ips[ip].append(target)
            from friday.tools_osint_extra import whatweb
            tech = _run_async(whatweb(target))
            if "error" not in tech:
                for t in tech.get("technologies", []):
                    name = t.get("name", "unknown")
                    info["technologies"].append(name)
                    shared_tech[name].append(target)
        elif "@" in target:
            info["emails"] = [target]
            shared_emails[target].append(target)
            domain = target.split("@")[1]
            info["domains"].append(domain)
            shared_domains[domain].append(target)

        target_data[target] = info

    shared_findings = {
        "shared_ips": {ip: owners for ip, owners in shared_ips.items() if len(owners) > 1},
        "shared_domains": {d: owners for d, owners in shared_domains.items() if len(owners) > 1},
        "shared_emails": {e: owners for e, owners in shared_emails.items() if len(owners) > 1},
        "shared_technologies": {t: owners for t, owners in shared_tech.items() if len(owners) > 1},
    }

    correlation_graph = {
        "targets": targets,
        "nodes": [],
        "edges": [],
    }

    for target in targets:
        correlation_graph["nodes"].append({
            "id": hashlib.sha256(target.encode()).hexdigest()[:12],
            "label": target,
            "type": "target",
        })

    seen_connections: set[tuple[str, str]] = set()
    for ip, owners in shared_findings.get("shared_ips", {}).items():
        ip_id = hashlib.sha256(f"ip:{ip}".encode()).hexdigest()[:12]
        correlation_graph["nodes"].append({
            "id": ip_id, "label": ip, "type": "ip",
        })
        for owner in owners:
            owner_id = hashlib.sha256(owner.encode()).hexdigest()[:12]
            conn = (owner_id, ip_id)
            if conn not in seen_connections:
                seen_connections.add(conn)
                correlation_graph["edges"].append({
                    "source": owner_id, "target": ip_id,
                    "relation": "resolves_to", "weight": 0.9,
                })

    for tech, owners in shared_findings.get("shared_technologies", {}).items():
        tech_id = hashlib.sha256(f"tech:{tech}".encode()).hexdigest()[:12]
        correlation_graph["nodes"].append({
            "id": tech_id, "label": tech, "type": "technology",
        })
        for owner in owners:
            owner_id = hashlib.sha256(owner.encode()).hexdigest()[:12]
            conn = (owner_id, tech_id)
            if conn not in seen_connections:
                seen_connections.add(conn)
                correlation_graph["edges"].append({
                    "source": owner_id, "target": tech_id,
                    "relation": "uses", "weight": 0.6,
                })

    result = {
        "targets": targets,
        "target_data": target_data,
        "shared_infrastructure": shared_findings,
        "correlation_graph": correlation_graph,
        "summary": {
            "total_targets": len(targets),
            "shared_ips_found": len(shared_findings["shared_ips"]),
            "shared_domains_found": len(shared_findings["shared_domains"]),
            "shared_emails_found": len(shared_findings["shared_emails"]),
            "shared_technologies_found": len(shared_findings["shared_technologies"]),
            "graph_nodes": len(correlation_graph["nodes"]),
            "graph_edges": len(correlation_graph["edges"]),
            "timestamp": _ts(),
        },
    }

    _safe_write_json(corr_path, result)
    return result


# ─── OSINT Report Generation ──────────────────────────────────────────────


def osint_report(target: str, format: str = "markdown") -> str:
    """
    Generate a comprehensive OSINT report combining all osint_* findings.
    Returns formatted markdown with confidence indicators and sections.
    """
    _ensure_storage()
    logger.info(f"Generating OSINT report for: {target}")

    kg = osint_knowledge_graph(target)
    multi = osint_multi_agent(target, depth="deep" if format == "markdown" else "basic")
    timeline = osint_timeline(target)

    if format == "json":
        combined = {
            "target": target,
            "report_type": "json",
            "knowledge_graph": kg,
            "multi_agent": multi,
            "timeline": timeline,
            "generated_at": _ts(),
        }
        report_path = os.path.join(OSINT_STORAGE, f"report_{target.lower().replace(' ', '_')}.json")
        _safe_write_json(report_path, combined)
        return json.dumps(combined, indent=2, default=str)

    # Markdown report
    lines: list[str] = []
    lines.append(f"# OSINT Report: {target}")
    lines.append(f"**Generated:** {_ts()}")
    lines.append(f"**Confidence:** {_confidence_label(0.7)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section: Summary
    lines.append("## Executive Summary")
    lines.append("")
    kg_summary = kg.get("summary", {})
    multi_summary = multi.get("summary", {})
    lines.append(f"- **Knowledge Graph:** {kg_summary.get('total_nodes', 0)} nodes, {kg_summary.get('total_edges', 0)} edges")
    lines.append(f"- **Multi-Agent Findings:** {multi_summary.get('total_findings', 0)} data points across {multi_summary.get('total_agents', 0)} agents")
    lines.append(f"- **Timeline Events:** {timeline.get('total_events', 0)} events")
    lines.append("")

    # Section: Knowledge Graph
    lines.append("## Knowledge Graph")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Nodes | {kg_summary.get('total_nodes', 0)} |")
    lines.append(f"| Total Edges | {kg_summary.get('total_edges', 0)} |")
    lines.append(f"| Types | {', '.join(kg_summary.get('entity_types', []))} |")
    lines.append("")
    if kg.get("nodes"):
        lines.append("### Nodes")
        for node in kg["nodes"][:20]:
            label = node.get("label", "unknown")
            ntype = node.get("type", "unknown")
            conf = node.get("confidence", 0)
            indicator = "🟢" if conf >= 0.8 else "🟡" if conf >= 0.5 else "🔴"
            lines.append(f"- {indicator} **{label}** ({ntype}) — confidence: {conf:.0%}")
        if len(kg["nodes"]) > 20:
            lines.append(f"- *... and {len(kg['nodes']) - 20} more nodes*")
    lines.append("")
    if kg.get("edges"):
        lines.append("### Relationships")
        for edge in kg["edges"][:15]:
            lines.append(f"- **{edge.get('source', '?')[:8]}** → *{edge.get('relation', '?')}* → **{edge.get('target', '?')[:8]}**")
        lines.append("")

    # Section: Multi-Agent Findings
    lines.append("## Multi-Agent Investigation")
    lines.append("")
    for agent_name, agent_data in multi.get("agents", {}).items():
        title = agent_name.replace("_", " ").title()
        lines.append(f"### Agent: {title}")
        lines.append("")
        if isinstance(agent_data, dict):
            for key, value in agent_data.items():
                if key == "timestamp":
                    continue
                if isinstance(value, dict):
                    error = value.get("error")
                    if error:
                        lines.append(f"- ⚠️ **{key}**: Error — {error}")
                    elif "subdomains_found" in value:
                        count = value.get("found_count", 0)
                        lines.append(f"- ℹ️ **{key}**: {count} subdomains found")
                    elif "technologies" in value:
                        techs = [t.get("name", "") for t in value.get("technologies", [])]
                        lines.append(f"- ℹ️ **{key}**: {', '.join(techs) if techs else 'No tech detected'}")
                    elif "platforms_found" in value:
                        platforms = value.get("platforms_found", [])
                        lines.append(f"- ℹ️ **{key}**: {len(platforms)} platforms found — {', '.join(platforms[:5])}")
                    else:
                        lines.append(f"- ℹ️ **{key}**: Data collected")
                elif isinstance(value, list):
                    lines.append(f"- ℹ️ **{key}**: {len(value)} items")
        lines.append("")

    # Section: Timeline
    lines.append("## Timeline")
    lines.append("")
    entries = timeline.get("timeline_entries", [])
    if entries:
        lines.append("| Date | Event | Source |")
        lines.append("|------|-------|--------|")
        for entry in entries[:30]:
            date = entry.get("date", "")[:19]
            event = entry.get("event", "")[:60]
            source = entry.get("source", "")
            lines.append(f"| {date} | {event} | {source} |")
        if len(entries) > 30:
            lines.append(f"| ... | *{len(entries) - 30} more entries* | |")
    else:
        lines.append("No timeline events found.")
    lines.append("")

    # Section: Recommendations
    lines.append("## Recommendations")
    lines.append("")
    lines.append(f"- {' Review breach data and compromised credentials' if kg.get('summary', {}).get('total_nodes', 0) > 2 else ' No significant breaches detected'}")
    lines.append(f"- {' Monitor infrastructure changes and new subdomains' if multi.get('agents', {}).get('reconnaissance', {}).get('subdomains', {}).get('found_count', 0) > 0 else 'Basic infrastructure footprint is minimal'}")
    lines.append(f"- {' Track timeline for emerging patterns and changes' if timeline.get('total_events', 0) > 5 else 'Limited historical data available'}")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Report generated by FRIDAY OSINT Enhanced — {_ts()}*")
    lines.append("")

    report_text = "\n".join(lines)
    report_md_path = os.path.join(OSINT_STORAGE, f"report_{target.lower().replace(' ', '_')}.md")
    try:
        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write(report_text)
    except Exception as e:
        logger.error(f"Failed to write report markdown: {e}")

    return report_text


# ─── Continuous Monitoring ──────────────────────────────────────────────


def osint_continuous_monitor(target: str, interval_hours: int = 24) -> dict:
    """
    Set up continuous monitoring for a target.
    Tracks changes over time and alerts on significant changes.
    """
    _ensure_storage()
    monitor_path = os.path.join(OSINT_STORAGE, f"monitor_{target.lower().replace(' ', '_')}.json")

    state = _safe_read_json(monitor_path)
    is_first_run = not state or "baseline" not in state

    if is_first_run:
        logger.info(f"First-time monitoring setup for: {target}")
        baseline = osint_multi_agent(target, depth="basic")
        state = {
            "target": target,
            "interval_hours": interval_hours,
            "baseline": {
                "timestamp": _ts(),
                "findings": baseline,
                "findings_hash": hashlib.sha256(json.dumps(baseline, default=str).encode()).hexdigest(),
            },
            "history": [],
            "alerts": [],
            "monitoring_active": True,
            "next_scan": (datetime.now(timezone.utc) + timedelta(hours=interval_hours)).isoformat(),
            "created_at": _ts(),
            "updated_at": _ts(),
        }
        _safe_write_json(monitor_path, state)
        return {**state, "message": "Baseline capture complete. Monitoring activated."}

    logger.info(f"Running scheduled scan for: {target}")
    current = osint_multi_agent(target, depth="basic")
    current_hash = hashlib.sha256(json.dumps(current, default=str).encode()).hexdigest()
    baseline_hash = state["baseline"].get("findings_hash", "")

    changes_detected = current_hash != baseline_hash

    history_entry = {
        "scan_time": _ts(),
        "changes_detected": changes_detected,
        "findings_snapshot": current,
    }
    state.setdefault("history", []).append(history_entry)

    if changes_detected:
        alert_msg = f"Changes detected for {target} at {_ts()}"
        logger.warning(alert_msg)
        state.setdefault("alerts", []).append({
            "timestamp": _ts(),
            "type": "change_detected",
            "message": alert_msg,
            "severity": "medium",
        })
        state["baseline"]["findings_hash"] = current_hash

    if len(state["history"]) > 50:
        state["history"] = state["history"][-50:]

    if len(state["alerts"]) > 100:
        state["alerts"] = state["alerts"][-100:]

    state["next_scan"] = (datetime.now(timezone.utc) + timedelta(hours=interval_hours)).isoformat()
    state["updated_at"] = _ts()

    _safe_write_json(monitor_path, state)
    return {
        **state,
        "message": f"Scan complete. {'Changes detected!' if changes_detected else 'No changes.'}",
    }


# ─── Attack Surface Mapping ──────────────────────────────────────────────


def osint_attack_surface(domain: str) -> dict:
    """
    Map the complete attack surface of a domain:
    subdomains, IPs, technologies, ports, SSL/TLS, email servers, DNS, dependencies.
    """
    _ensure_storage()
    surface_path = os.path.join(OSINT_STORAGE, f"attack_surface_{domain.lower().replace(' ', '_')}.json")
    logger.info(f"Mapping attack surface for: {domain}")

    def _find_subdomains(d: str) -> list[dict]:
        subs = _run_async(dns_bruteforce(d))
        return subs.get("subdomains_found", [])

    def _find_technologies(d: str) -> list[dict]:
        from friday.tools_osint_extra import whatweb, cdn_detect, web_server_headers
        techs = _run_async(whatweb(d))
        cdn = _run_async(cdn_detect(d))
        headers = _run_async(web_server_headers(d))
        result = []
        for t in techs.get("technologies", []):
            result.append(t)
        if cdn.get("cdn"):
            result.append({"name": cdn["cdn"], "category": "cdn"})
        return result

    def _check_ssl(d: str) -> dict:
        from friday.tools.osint_advanced_tools import ssl_certificate_check
        return _run_async(ssl_certificate_check(d))

    def _dns_analysis(d: str) -> dict:
        dns = _run_async(dns_enum(d))
        from friday.tools_osint_extra import spf_check, dmarc_check, dkim_check, mx_lookup
        spf = _run_async(spf_check(d))
        dmarc = _run_async(dmarc_check(d))
        dkim = _run_async(dkim_check(d))
        mx = _run_async(mx_lookup(d))
        return {
            "dns_records": dns.get("records", {}),
            "spf": spf,
            "dmarc": dmarc,
            "dkim": dkim,
            "mx": mx.get("mx_records", []),
        }

    def _email_servers(d: str) -> list[str]:
        from friday.tools_osint_extra import mx_lookup
        mx = _run_async(mx_lookup(d))
        return [m["host"] for m in mx.get("mx_records", []) if "host" in m]

    def _third_party_deps(d: str) -> list[dict]:
        deps = []
        try:
            import requests
            r = requests.get(
                f"https://{d}",
                headers={"User-Agent": "FRIDAY-OSINT/3.0"},
                timeout=10,
            )
            if r.status_code == 200:
                text = r.text.lower()
                known_third_party = {
                    "google-analytics": "Google Analytics",
                    "googletagmanager": "Google Tag Manager",
                    "facebook.net": "Facebook Pixel",
                    "cdn.jsdelivr": "jsDelivr CDN",
                    "cdnjs.cloudflare": "Cloudflare CDN",
                    "unpkg.com": "UNPKG CDN",
                    "fonts.googleapis": "Google Fonts",
                    "maps.googleapis": "Google Maps",
                    "s3.amazonaws": "AWS S3",
                    "cloudfront.net": "AWS CloudFront",
                    "stripe.com": "Stripe",
                    "paypal.com": "PayPal",
                    "api.github": "GitHub API",
                    "disqus.com": "Disqus",
                }
                for pattern, name in known_third_party.items():
                    if pattern in text:
                        deps.append({"name": name, "pattern": pattern})
        except Exception:
            pass
        return deps

    subdomains = _find_subdomains(domain)
    technologies = _find_technologies(domain)
    ssl_info = _check_ssl(domain)
    dns_info = _dns_analysis(domain)
    email_mxs = _email_servers(domain)
    third_party = _third_party_deps(domain)

    all_ips: list[str] = []
    for sub in subdomains:
        all_ips.extend(sub.get("ips", []))
    unique_ips = list(set(all_ips))

    shodan_info = {}
    for ip in unique_ips[:10]:
        sh = _run_async(shodan_host(ip))
        if "error" not in sh:
            shodan_info[ip] = {
                "ports": sh.get("ports", []),
                "os": sh.get("os"),
                "org": sh.get("org"),
                "country": sh.get("country"),
                "vulns": sh.get("vulns", []),
            }

    result = {
        "domain": domain,
        "subdomains": {
            "count": len(subdomains),
            "entries": subdomains,
        },
        "ip_addresses": {
            "count": len(unique_ips),
            "addresses": unique_ips,
        },
        "technologies": {
            "count": len(technologies),
            "entries": technologies,
        },
        "ssl_tls": ssl_info,
        "dns_analysis": dns_info,
        "email_servers": email_mxs,
        "third_party_dependencies": {
            "count": len(third_party),
            "entries": third_party,
        },
        "shodan_intel": shodan_info,
        "risk_indicators": {
            "exposed_ports": sum(len(v.get("ports", [])) for v in shodan_info.values()),
            "known_vulnerabilities": sum(len(v.get("vulns", [])) for v in shodan_info.values()),
            "subdomain_count": len(subdomains),
            "email_servers_exposed": len(email_mxs),
            "third_party_services": len(third_party),
            "risk_score": min(
                100,
                (len(subdomains) * 2) + (len(unique_ips) * 3) +
                (sum(len(v.get("ports", [])) for v in shodan_info.values()) * 2) +
                (len(email_mxs) * 5) + (len(third_party) * 3)
            ),
        },
        "timestamp": _ts(),
    }

    _safe_write_json(surface_path, result)
    return result
