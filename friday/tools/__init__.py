"""FRIDAY tools package — re-exports all flat tools + all module tools.

All tool functions from tools_flat.py, individual tool modules (voice, system,
osint, scraping, social, doc, vision, nlp, security, memory, knowledge, wifi, dns),
google_clients, and new subsystem modules (Metasploit, Email Analysis, Agent Terminal,
OSINT Extra) are re-exported here for consistency.
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

# ── Individual tool module imports ──
from friday.tools.voice_tools import (
    list_audio_devices, record_audio, transcribe_audio, speak_text,
    list_tts_voices, analyze_audio, get_audio_metadata, convert_audio, merge_audio,
)
from friday.tools.system_tools import (
    get_processes, kill_process, get_volume, set_volume, mute_audio,
    get_brightness, set_brightness, take_screenshot, list_windows, focus_window,
    mouse_click, mouse_move, get_mouse_position, type_text_auto, play_system_sound, read_registry,
)
from friday.tools.osint_advanced_tools import (
    shodan_search, shodan_host, censys_search, whois_lookup,
    harvester_enum, subfinder_enum, nuclei_scan, ping_host, port_scan, nmap_scan,
    geoip_lookup, hunter_email_search, clearbit_company, clearbit_person,
)
from friday.tools.scraping_tools import (
    fetch_page, extract_html, extract_article, html_to_markdown, parse_feed, xpath_extract,
)
from friday.tools.social_tools import (
    twitter_user_info, twitter_search, reddit_hot, reddit_search,
    instagram_user_info, youtube_info, youtube_download, spotify_search, flickr_search,
)
from friday.tools.doc_tools import (
    read_docx, create_docx, read_excel, create_excel, analyze_csv,
    read_pdf, create_pdf, read_pptx, create_pptx,
)
from friday.tools.vision_advanced_tools import (
    ocr_image, detect_objects, detect_faces, pose_detection, hand_detection,
    image_enhance, image_analysis, resize_image,
)
from friday.tools.nlp_tools import (
    sentiment_analysis, extract_entities, summarize_text, classify_text, compute_embeddings,
)
from friday.tools.security_tools import (
    generate_fernet_key, encrypt_text, decrypt_text, hash_text,
    bcrypt_hash, bcrypt_verify, jwt_encode, jwt_decode,
    generate_totp_secret, verify_totp,
)
from friday.tools.memory_tools import (
    chroma_create_collection, chroma_add, chroma_query,
    redis_set, redis_get, redis_delete, mongo_find,
)
from friday.tools.knowledge_tools import (
    neo4j_run_query, neo4j_create_entity, neo4j_find_entities, analyze_graph, create_graph_visualization,
)
from friday.tools.wifi_tools import (
    wifi_list_profiles, wifi_show_password, wifi_scan, wifi_connection_status,
    network_connections, arp_table, traceroute,
)
from friday.tools.dns_tool import (
    dns_lookup, dns_reverse_lookup,
)

# ── Google Clients imports ──
from friday.google_clients import (
    drive_list, drive_search, drive_upload, drive_download, drive_create_folder, drive_delete,
    sheets_create, sheets_read, sheets_write, sheets_append, sheets_list,
    docs_create, docs_read, docs_append_text,
    slides_create, slides_read, slides_add_slide,
    people_list, people_search, people_create_contact,
    maps_geocode, maps_reverse_geocode, maps_places_search, maps_directions, maps_elevation,
    translate_text, translate_detect_language,
    tts_synthesize, stt_transcribe,
    vision_annotate,
    bigquery_query, storage_list, storage_upload,
    firestore_get, firestore_query, firestore_set, firestore_delete,
    classroom_list_courses, classroom_list_coursework, classroom_list_students,
    books_search, books_get_volume,
    youtube_analytics_advanced,
)

# ── New subsystem imports (Metasploit, Email Analysis, Agent Terminal, OSINT Extra) ──
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
    friday_craft_delegation_prompt, friday_delegate_with_prompt,
    get_delegation_depth, get_allowed_tools_for_agent,
    store_agent_session, load_agent_config,
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
    # ── Voice Tools ──
    "list_audio_devices", "record_audio", "transcribe_audio", "speak_text",
    "list_tts_voices", "analyze_audio", "get_audio_metadata", "convert_audio", "merge_audio",
    # ── System Tools ──
    "get_processes", "kill_process", "get_volume", "set_volume", "mute_audio",
    "get_brightness", "set_brightness", "take_screenshot", "list_windows", "focus_window",
    "mouse_click", "mouse_move", "get_mouse_position", "type_text_auto", "play_system_sound", "read_registry",
    # ── OSINT Advanced Tools ──
    "shodan_search", "shodan_host", "censys_search", "whois_lookup",
    "harvester_enum", "subfinder_enum", "nuclei_scan", "ping_host", "port_scan", "nmap_scan",
    "geoip_lookup", "hunter_email_search", "clearbit_company", "clearbit_person",
    # ── Scraping Tools ──
    "fetch_page", "extract_html", "extract_article", "html_to_markdown", "parse_feed", "xpath_extract",
    # ── Social Tools ──
    "twitter_user_info", "twitter_search", "reddit_hot", "reddit_search",
    "instagram_user_info", "youtube_info", "youtube_download", "spotify_search", "flickr_search",
    # ── Document Tools ──
    "read_docx", "create_docx", "read_excel", "create_excel", "analyze_csv",
    "read_pdf", "create_pdf", "read_pptx", "create_pptx",
    # ── Vision Advanced Tools ──
    "ocr_image", "detect_objects", "detect_faces", "pose_detection", "hand_detection",
    "image_enhance", "image_analysis", "resize_image",
    # ── NLP Tools ──
    "sentiment_analysis", "extract_entities", "summarize_text", "classify_text", "compute_embeddings",
    # ── Security Tools ──
    "generate_fernet_key", "encrypt_text", "decrypt_text", "hash_text",
    "bcrypt_hash", "bcrypt_verify", "jwt_encode", "jwt_decode",
    "generate_totp_secret", "verify_totp",
    # ── Memory Tools ──
    "chroma_create_collection", "chroma_add", "chroma_query",
    "redis_set", "redis_get", "redis_delete", "mongo_find",
    # ── Knowledge Tools ──
    "neo4j_run_query", "neo4j_create_entity", "neo4j_find_entities", "analyze_graph", "create_graph_visualization",
    # ── WiFi Tools ──
    "wifi_list_profiles", "wifi_show_password", "wifi_scan", "wifi_connection_status",
    "network_connections", "arp_table", "traceroute",
    # ── DNS Tools ──
    "dns_lookup", "dns_reverse_lookup",
    # ── Google Clients ──
    "drive_list", "drive_search", "drive_upload", "drive_download", "drive_create_folder", "drive_delete",
    "sheets_create", "sheets_read", "sheets_write", "sheets_append", "sheets_list",
    "docs_create", "docs_read", "docs_append_text",
    "slides_create", "slides_read", "slides_add_slide",
    "people_list", "people_search", "people_create_contact",
    "maps_geocode", "maps_reverse_geocode", "maps_places_search", "maps_directions", "maps_elevation",
    "translate_text", "translate_detect_language",
    "tts_synthesize", "stt_transcribe",
    "vision_annotate",
    "bigquery_query", "storage_list", "storage_upload",
    "firestore_get", "firestore_query", "firestore_set", "firestore_delete",
    "classroom_list_courses", "classroom_list_coursework", "classroom_list_students",
    "books_search", "books_get_volume",
    "youtube_analytics_advanced",
    # ── Metasploit ──
    "metasploit_connect", "metasploit_status", "metasploit_exploit",
    "metasploit_scan", "metasploit_post_exploit", "metasploit_payload_gen",
    # ── Email Analysis ──
    "analyze_email_headers", "trace_email_path", "detect_email_spoofing",
    "check_spf_record", "check_dkim_record",
    # ── Agent Terminal ──
    "agent_spawn_and_track", "agent_delegate_with_terminal",
    "friday_should_delegate", "friday_parse_and_delegate",
    "friday_key_check", "friday_workflow_research_vuln_fix",
    "agent_bus_status", "agent_chain_research_vuln_fix",
    "friday_multi_agent_task", "close_all_agent_resources",
    "friday_craft_delegation_prompt", "friday_delegate_with_prompt",
    "get_delegation_depth", "get_allowed_tools_for_agent",
    "store_agent_session", "load_agent_config",
    # ── OSINT Extra ──
    "social_analyzer", "dns_enum", "whatweb",
    "phone_lookup", "username_search", "holehe_check",
    "ip_abuse_report", "ip_threat_intel",
    "leak_check", "intelx_search", "dehashed_search",
    "security_headers", "cors_check",
    "wayback_snapshots", "wayback_urls",
    "certificate_transparency", "domain_similar",
    # ── Kimi WebBridge ──
    "webbridge_connect", "webbridge_disconnect", "webbridge_doctor",
    "webbridge_navigate", "webbridge_click", "webbridge_fill",
    "webbridge_type_text", "webbridge_screenshot", "webbridge_extract_text",
    "webbridge_get_page_state", "webbridge_scroll", "webbridge_press_key",
    "webbridge_key_combo", "webbridge_evaluate", "webbridge_submit_form",
    "webbridge_select_option", "webbridge_list_tabs", "webbridge_close_tab",
    "webbridge_get_current_url", "webbridge_get_title", "webbridge_hover",
    "webbridge_focus", "webbridge_double_click", "webbridge_drag",
    "webbridge_install_instructions",
]
