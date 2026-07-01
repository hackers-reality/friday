"""Comprehensive OSINT test against real targets"""
import sys, os, json, time, asyncio

# Use venv
os.environ['PYTHONUTF8'] = '1'

TARGETS = {
    'email': 'phulariarnav@gmail.com',
    'username': 'phulari_arnav',
    'domain': 'claude.ai',
    'wifi_ssid': 'Arnav',
}

# ============================================================
# TEST tools_osint_extra.py — DNS, web, validation, lookup functions
# ============================================================
print('=' * 60)
print('TEST: tools_osint_extra.py')
print('=' * 60)

try:
    import friday.tools_osint_extra as OE
    print('[IMPORT OK] tools_osint_extra.py')
except Exception as e:
    import traceback
    print(f'[IMPORT FAIL] tools_osint_extra: {e}')
    traceback.print_exc()
    sys.exit(1)

# Test DNS functions (no API keys needed)
async def test_dns():
    results = []
    tests = [
        ('dns_enum', (TARGETS['domain'], 10)),
        ('dns_bruteforce', (TARGETS['domain'], ['www','mail','api','blog','admin'], 10)),
        ('mx_lookup', (TARGETS['domain'], 10)),
        ('spf_check', (TARGETS['domain'], 10)),
        ('dkim_check', (TARGETS['domain'], 'google', 10)),
        ('dmarc_check', (TARGETS['domain'], 10)),
        ('dns_wildcard_detect', (TARGETS['domain'], 10)),
        ('dns_dnssec_check', (TARGETS['domain'], 10)),
        ('dns_soa_check', (TARGETS['domain'], 10)),
        ('dns_caa_check', (TARGETS['domain'], 10)),
        ('dns_srv_lookup', (TARGETS['domain'], 10)),
        ('dns_reverse', ('142.250.80.46', 10)),
        ('dns_reverse_extended', ('142.250.80.46', 10)),
        ('dns_zone_transfer', (TARGETS['domain'], 10)),
    ]
    for name, args in tests:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            res_type = type(r).__name__
            if isinstance(r, dict):
                status = 'OK' if not r.get('error') else f"ERROR: {r['error'][:80]}"
            else:
                status = 'OK'
            results.append((name, status, f'{res_type}, {json.dumps(r)[:200] if isinstance(r, (dict,list)) else str(r)[:200]}'))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    return results

async def test_web():
    results = []
    tests = [
        ('whatweb', (TARGETS['domain'], 10)),
        ('cdn_detect', (TARGETS['domain'], 10)),
        ('web_server_headers', (TARGETS['domain'], 10)),
        ('hsts_check', (TARGETS['domain'], 10)),
        ('robots_txt_check', (f'https://{TARGETS["domain"]}', 10)),
        ('ssl_cert_check_full', (TARGETS['domain'], 443, 10)),
        ('security_headers', (f'https://{TARGETS["domain"]}', 10)),
        ('cors_check', (f'https://{TARGETS["domain"]}', 10)),
        ('url_analyze', (f'https://{TARGETS["domain"]}',)),
        ('certificate_transparency', (TARGETS['domain'], 10)),
        ('domain_age', (TARGETS['domain'], 10)),
    ]
    for name, args in tests:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            res_type = type(r).__name__
            if isinstance(r, dict):
                status = 'OK' if not r.get('error') else f"ERROR: {r['error'][:80]}"
            else:
                status = 'OK'
            results.append((name, status, f'{res_type}, {json.dumps(r)[:200] if isinstance(r, (dict,list)) else str(r)[:200]}'))
        except Exception as e:
            import traceback
            results.append((name, 'EXCEPTION', traceback.format_exc()[:100]))
    return results

async def test_validation():
    results = []
    # All validate_* functions take value and timeout
    val_tests = [
        ('validate_ip', '8.8.8.8'),
        ('validate_domain', 'google.com'),
        ('validate_email', 'user@example.com'),
        ('validate_url', 'https://example.com'),
        ('validate_phone', '+14155552671'),
        ('validate_username', 'johndoe'),
        ('validate_md5', 'd41d8cd98f00b204e9800998ecf8427e'),
        ('validate_sha256', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
        ('validate_btc_address', '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'),
        ('validate_eth_address', '0x742d35Cc6634C0532925a3b844Bc9e7595f9bDf7'),
        ('validate_cve', 'CVE-2021-44228'),
        ('validate_mac', '00:11:22:33:44:55'),
        ('validate_port', '80'),
        ('validate_asn', 'AS15169'),
        ('validate_uuid', '550e8400-e29b-41d4-a716-446655440000'),
        ('validate_iban', 'GB33BUKB20201555555555'),
        ('validate_credit_card', '4111111111111111'),
        ('validate_ssn', '123-45-6789'),
        ('validate_vin', '1HGBH41JXMN109186'),
        ('validate_latlon', '37.7749,-122.4194'),
    ]
    for name, val in val_tests:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(val, 10) if asyncio.iscoroutinefunction(fn) else fn(val, 10)
            results.append((name, 'OK', str(r)[:100]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    return results

async def test_utils():
    results = []
    # text extraction utilities
    utils = [
        ('ip_range_expander', ('192.168.1.0/30',)),
        ('domain_pattern_match', (TARGETS['domain'],)),
        ('url_decompose', (f'https://{TARGETS["domain"]}/path?q=1',)),
        ('email_deobfuscate', ('john [at] example [dot] com',)),
        ('hash_type_detect', ('d41d8cd98f00b204e9800998ecf8427e',)),
        ('text_extract_emails', (f'Contact {TARGETS["email"]} or admin@example.com', 10)),
        ('text_extract_urls', (f'Visit https://{TARGETS["domain"]}/page and http://google.com', 10)),
        ('text_extract_phones', ('Call +1-415-555-2671 or 212-555-1234', 10)),
        ('text_extract_hashes', ('Hash: d41d8cd98f00b204e9800998ecf8427e and e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 10)),
        ('text_extract_domains', (f'Domains: {TARGETS["domain"]}, google.com, test.org', 10)),
        ('text_extract_cves', ('Found CVE-2021-44228 and CVE-2024-1234', 10)),
    ]
    for name, args in utils:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    return results

async def test_social():
    results = []
    social_tests = [
        ('username_search', (TARGETS['username'], 15)),
        ('social_analyzer', (TARGETS['username'], 15)),
    ]
    for name, args in social_tests:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            if isinstance(r, dict):
                found = sum(1 for v in r.values() if isinstance(v, dict) and v.get('found') in (True, 'yes', 'Yes'))
                results.append((name, 'OK', f'Platforms checked: {len(r)}, found on: {found}'))
            else:
                results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            import traceback
            results.append((name, 'EXCEPTION', traceback.format_exc()[:150]))
    return results

async def test_email():
    results = []
    email_tests = [
        ('holehe_check', (TARGETS['email'], 15)),
        ('email_rep', (TARGETS['email'], 10)),
        ('email_format', ('Arnav', 'Phulari', 'gmail.com')),
        ('email_extractor', (f'https://{TARGETS["domain"]}', 10)),
    ]
    for name, args in email_tests:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    return results

async def test_intel():
    results = []
    intel_tests = [
        ('ip_geolocate_full', ('8.8.8.8', 10)),
        ('ip_reverse_dns', ('8.8.8.8', 10)),
        ('ip_asn_info', ('8.8.8.8', 10)),
        ('ip_blacklist_check', ('8.8.8.8', 10)),
        ('ip_threat_intel', ('8.8.8.8', 10)),
        ('url_phishing_detect', (f'https://{TARGETS["domain"]}', 10)),
        ('url_redirect_chain', (f'https://{TARGETS["domain"]}', 5, 10)),
        ('url_expander', ('https://bit.ly/3x9VwYH', 10)),
        ('wayback_snapshots', (TARGETS['domain'], 10)),
        ('wayback_latest', (TARGETS['domain'], 10)),
    ]
    for name, args in intel_tests:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            if isinstance(r, dict):
                status = 'OK' if not r.get('error') else f"ERROR: {r['error'][:80]}"
            else:
                status = 'OK'
            results.append((name, status, str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    return results

async def test_auth():
    results = []
    auth_tests = [
        ('email_auth_report', (TARGETS['domain'], 10)),
        ('spf_check_extended', (TARGETS['domain'], 10)),
        ('dkim_check_extended', (TARGETS['domain'], 'google', 10)),
        ('dmarc_check_extended', (TARGETS['domain'], 10)),
        ('mx_lookup_extended', (TARGETS['domain'], 10)),
    ]
    for name, args in auth_tests:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            status = 'OK' if isinstance(r, dict) and not r.get('error') else (str(r)[:80] if isinstance(r, dict) and r.get('error') else 'OK')
            results.append((name, status, str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    return results

async def test_reporting():
    results = []
    try:
        r = await OE.osint_to_markdown({'test': 'data', 'domain': TARGETS['domain']}, 'Test Report')
        results.append(('osint_to_markdown', 'OK', str(r)[:150]))
    except Exception as e:
        results.append(('osint_to_markdown', 'EXCEPTION', str(e)[:100]))
    try:
        r = await OE.osint_to_html_report({'test': 'data'}, 'Test') if asyncio.iscoroutinefunction(OE.osint_to_html_report) else OE.osint_to_html_report({'test': 'data'}, 'Test')
        results.append(('osint_to_html_report', 'OK', str(r)[:150]))
    except Exception as e:
        results.append(('osint_to_html_report', 'EXCEPTION', str(e)[:100]))
    try:
        # format_osint_for_report
        r = await OE.format_osint_for_report({'dns': {'a': ['1.2.3.4']}}, 'DNS Results') if asyncio.iscoroutinefunction(OE.format_osint_for_report) else OE.format_osint_for_report({'dns': {'a': ['1.2.3.4']}}, 'DNS Results')
        results.append(('format_osint_for_report', 'OK', str(r)[:150]))
    except Exception as e:
        results.append(('format_osint_for_report', 'EXCEPTION', str(e)[:100]))
    try:
        r = await OE.summarize_osint_findings({'domain': TARGETS['domain']}) if asyncio.iscoroutinefunction(OE.summarize_osint_findings) else OE.summarize_osint_findings({'domain': TARGETS['domain']})
        results.append(('summarize_osint_findings', 'OK', str(r)[:150]))
    except Exception as e:
        results.append(('summarize_osint_findings', 'EXCEPTION', str(e)[:100]))
    return results

async def test_username_intel():
    results = []
    uname_tests = [
        ('username_search_extended', (TARGETS['username'], 15)),
        ('username_to_real_name', (TARGETS['username'], 15)),
    ]
    for name, args in uname_tests:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    return results

async def test_compare():
    results = []
    compare_tests = [
        ('compare_domains', (TARGETS['domain'], 'google.com', 0.8, 10)),
        ('compare_emails', (TARGETS['email'], 'admin@gmail.com', 0.8, 10)),
        ('compare_usernames', (TARGETS['username'], 'arnav_phulari', 0.8, 10)),
    ]
    for name, args in compare_tests:
        try:
            fn = getattr(OE, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'function not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    return results

async def run_all_tests():
    all_results = {}
    
    sections = [
        ('DNS Enumeration', test_dns()),
        ('Web Analysis', test_web()),
        ('Validation Functions', test_validation()),
        ('Utility Functions', test_utils()),
        ('Social Media', test_social()),
        ('Email Lookup', test_email()),
        ('IP Intelligence', test_intel()),
        ('Email Auth', test_auth()),
        ('Reporting', test_reporting()),
        ('Username Intel', test_username_intel()),
        ('Compare Functions', test_compare()),
    ]
    
    passed_all = 0
    failed_all = 0
    skipped_all = 0
    
    for section_name, coro in sections:
        print(f'\n{"-" * 60}')
        print(f'Section: {section_name}')
        print(f'{"-" * 60}')
        results = await coro
        passed = sum(1 for _, s, _ in results if s == 'OK')
        failed = sum(1 for _, s, _ in results if s not in ('OK', 'SKIP'))
        skipped = sum(1 for _, s, _ in results if s == 'SKIP')
        passed_all += passed
        failed_all += failed
        skipped_all += skipped
        
        for name, status, detail in results:
            display = 'PASS' if status == 'OK' else status
            print(f'  [{display:>9}] {name}: {detail[:120]}')
        
        print(f'  -> {passed} passed, {failed} failed, {skipped} skipped')
    
    print(f'\n{"=" * 60}')
    print(f'TOTAL: {passed_all} passed, {failed_all} failed, {skipped_all} skipped')
    print(f'{"=" * 60}')
    
    return passed_all, failed_all, skipped_all

if __name__ == '__main__':
    asyncio.run(run_all_tests())
