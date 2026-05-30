"""FRIDAY tools package — re-exports all flat tools + OSINT sub-modules.

All tool functions are defined in tools_flat.py and re-exported here.
New modules (Metasploit, Email Analysis, Agent Terminal, OSINT Extra, OSINT Advanced)
are also re-exported for consistency.
"""

import sys as _sys
import friday.tools_flat as _tflat

# Re-export ALL public names from tools_flat
_mod = _sys.modules[__name__]
for _key in _tflat.__dict__:
    if not _key.startswith("_"):
        _mod.__dict__[_key] = _tflat.__dict__[_key]

# OSINT sub-module imports
from friday.tools.sherlock_tool import SherlockResult, run_sherlock
from friday.tools.exiftool_tool import ExifResult, run_exiftool, strip_metadata
from friday.tools.spiderfoot_tool import SpiderFootResult, SpiderFootEntity, SpiderFootThreat, run_spiderfoot

# New module imports (Metasploit, Email Analysis, Agent Terminal, OSINT Extra)
from friday.metasploit_tool import (
    metasploit_connect, metasploit_status, metasploit_exploit,
    metasploit_scan, metasploit_post_exploit, metasploit_payload_gen,
    msf_connect, msf_status, msf_console_exec, msf_search,
    msf_module_info, msf_exploit_run, msf_auxiliary_run,
    msf_sessions_list, msf_session_details, msf_session_shell,
    msf_payload_generate, msf_workspace_create, msf_workspace_list,
    msf_workspace_switch, msf_workspace_delete, msf_hosts_list,
    msf_vulns_list, msf_creds_list, msf_jobs_list, msf_job_stop,
    msf_resource_script, msf_loot_list, msf_services_list,
    msf_module_list, msf_session_stop, msf_session_meterpreter,
    msf_version, msf_compatible_payloads, msf_notes_list, msf_db_import,
)
from friday.email_analysis_tool import (
    analyze_email_headers, extract_received_chain, trace_email_path,
    detect_email_spoofing, extract_authentication_results,
    detect_header_forging, calculate_delivery_time,
    check_spf_record, analyze_spf_record, validate_spf,
    spf_include_chain, spf_recommendations, spf_dns_lookup_count,
    check_dkim_record, analyze_dkim_record, extract_dkim_signatures,
    decoded_dkim_public_key, dkim_selector_guess, dkim_recommendations,
    check_dmarc_record, analyze_dmarc_record, dmarc_policy_analysis,
    dmarc_recommendations, validate_dmarc,
    check_bimi_record, check_mta_sts, check_tls_rpt,
    email_security_score, email_security_report, compare_security_scores,
    check_email_reputation, email_disposable_check, verify_email_format,
    verify_email_domain, verify_email_smtp, email_role_account_check,
    forensic_investigate, forensic_phishing_detection, forensic_url_analysis,
    forensic_sender_verification, forensic_ip_analysis, forensic_spoof_score,
    email_full_analysis, email_domain_investigation, email_trace_route,
    email_validate_and_verify, behind_the_email,
)
from friday.agent_terminal import (
    agent_spawn_and_track, agent_delegate_with_terminal,
    friday_should_delegate, friday_parse_and_delegate,
    friday_key_check, friday_workflow_research_vuln_fix,
    agent_bus_status, agent_chain_research_vuln_fix,
    friday_multi_agent_task, close_all_agent_resources,
)
from friday.tools_osint_extra import (
    social_analyzer, instagram_osint, twitter_osint, facebook_osint,
    linkedin_osint, tiktok_osint, telegram_osint, reddit_osint,
    holehe_check, email_rep, username_search,
    phone_lookup, phone_format, phone_breach_check,
    dns_enum, dns_bruteforce, dns_zone_transfer, dns_reverse,
    spf_check, dkim_check, dmarc_check, mx_lookup,
    whatweb, whatcms, cdn_detect, web_server_headers,
    urlscan_submit, urlscan_result, virus_total_url, virus_total_domain,
    wayback_snapshots, wayback_urls, wayback_latest,
    leak_check, intelx_search, dehashed_search,
    ip_abuse_report, ip_threat_intel, ip_reverse_dns, ip_asn_info,
    ip_blacklist_check, ip_geolocate_full, ip_range_expand,
    domain_similar, domain_history, certificate_transparency,
    web_crawl, email_extractor, meta_extractor, page_text_extractor,
    security_headers, cors_check, hsts_check, robots_txt_check,
    btc_address_lookup, eth_address_lookup,
    format_osint_for_report, summarize_osint_findings, osint_to_markdown,
)
from friday.kimi_webbridge_tool import (
    webbridge_connect, webbridge_disconnect, webbridge_doctor,
    webbridge_navigate, webbridge_click, webbridge_fill,
    webbridge_type_text, webbridge_screenshot, webbridge_extract_text,
    webbridge_get_page_state, webbridge_scroll, webbridge_press_key,
    webbridge_key_combo, webbridge_evaluate, webbridge_submit_form,
    webbridge_select_option, webbridge_list_tabs, webbridge_close_tab,
    webbridge_get_current_url, webbridge_get_title, webbridge_hover,
    webbridge_focus, webbridge_double_click, webbridge_drag,
    webbridge_install_instructions,
)

# Merged __all__ for master.py and introspection
__all__ = _tflat.__all__ + [
    "SherlockResult", "run_sherlock",
    "ExifResult", "run_exiftool", "strip_metadata",
    "SpiderFootResult", "SpiderFootEntity", "SpiderFootThreat", "run_spiderfoot",
    "metasploit_connect", "metasploit_status", "metasploit_exploit",
    "metasploit_scan", "metasploit_post_exploit", "metasploit_payload_gen",
    "analyze_email_headers", "trace_email_path", "detect_email_spoofing",
    "check_spf_record", "check_dkim_record",
    "agent_spawn_and_track", "agent_delegate_with_terminal",
    "friday_should_delegate", "friday_parse_and_delegate",
    "friday_key_check", "friday_workflow_research_vuln_fix",
    "agent_bus_status", "friday_multi_agent_task",
    "social_analyzer", "dns_enum", "whatweb",
    "phone_lookup", "username_search", "holehe_check",
    "ip_abuse_report", "ip_threat_intel",
    "leak_check", "intelx_search", "dehashed_search",
    "security_headers", "cors_check",
    "wayback_snapshots", "wayback_urls",
    "certificate_transparency", "domain_similar",
    "webbridge_connect", "webbridge_disconnect", "webbridge_doctor",
    "webbridge_navigate", "webbridge_click", "webbridge_fill",
    "webbridge_type_text", "webbridge_screenshot", "webbridge_extract_text",
    "webbridge_get_page_state", "webbridge_scroll", "webbridge_press_key",
    "webbridge_key_combo", "webbridge_evaluate", "webbridge_submit_form",
    "webbridge_select_option", "webbridge_list_tabs", "webbridge_close_tab",
    "webbridge_get_current_url", "webbridge_get_title", "webbridge_hover",
    "webbridge_focus", "webbridge_double_click", "webbridge_drag",
    "webbridge_install_instructions",
    "friday_craft_delegation_prompt", "friday_delegate_with_prompt",
    "get_delegation_depth", "get_allowed_tools_for_agent",
    "store_agent_session", "load_agent_config",
]
