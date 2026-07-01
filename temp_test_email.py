"""Test email_analysis_tool.py"""
import sys, os, json, asyncio

os.environ['PYTHONUTF8'] = '1'
TARGET_DOMAIN = 'claude.ai'
TARGET_EMAIL = 'phulariarnav@gmail.com'

SAMPLE_HEADERS = """\
Received: from mail-sor-f69.google.com (209.85.220.69) by
 mx.google.com with SMTPS id abc123 for <recipient@gmail.com>;
 Mon, 28 Jun 2026 10:00:00 -0700 (PDT)
Received: from mail-vs1-f53.google.com (209.85.217.53) by
 mail-sor-f69.google.com with SMTP id def456;
 Mon, 28 Jun 2026 10:00:00 -0700 (PDT)
Received: from mail-sor-f69.google.com (209.85.220.69) by
 mx.google.com with SMTPS id abc123 for <recipient@example.com>;
 Mon, 28 Jun 2026 10:00:00 -0700 (PDT)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
 d=gmail.com; s=20230601; h=from:to:subject:date:message-id;
 bh=abc123def456=; b=xyz789=
From: Sender <sender@gmail.com>
To: Recipient <recipient@gmail.com>
Subject: Test email
Date: Mon, 28 Jun 2026 10:00:00 -0700
Message-ID: <abc@mail.gmail.com>
Authentication-Results: mx.google.com;
       spf=pass (google.com: domain of sender@gmail.com designates 209.85.220.69 as permitted sender) smtp.mailfrom=sender@gmail.com;
       dkim=pass header.i=@gmail.com header.s=20230601 header.b=xyz789;
       dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=gmail.com
"""

print('========== TEST: email_analysis_tool.py ==========')

try:
    import friday.email_analysis_tool as EA
    print('[IMPORT OK]')
except Exception as e:
    import traceback
    print(f'[IMPORT FAIL] {e}')
    traceback.print_exc()
    sys.exit(1)

async def run_tests():
    results = []

    # 1. Parse helpers
    print('\n--- Parse Helpers ---')
    for name, args, expected in [
        ('_extract_domain', (TARGET_EMAIL,), None),
        ('_parse_email_addr', ('"Test User" <test@example.com>',), None),
        ('_decode_mime_header', ('=?UTF-8?B?dGVzdA==?=',), None),
        ('_parse_date_header', ('Mon, 28 Jun 2026 10:00:00 -0700',), None),
        ('_is_ip_private', ('192.168.1.1',), None),
        ('_is_ip_private', ('8.8.8.8',), None),
        ('_is_ip_reserved', ('0.0.0.0',), None),
        ('_extract_ip_port', ('[209.85.220.69]:25',), None),
        ('_parse_received_line', ('from mail-sor-f69.google.com (209.85.220.69) by mx.google.com with SMTPS id abc123; Mon, 28 Jun 2026 10:00:00 -0700 (PDT)',), None),
        ('_parse_authentication_results_field', ('mx.google.com; spf=pass (google.com: domain of sender@gmail.com designates 209.85.220.69 as permitted sender) smtp.mailfrom=sender@gmail.com; dkim=pass header.i=@gmail.com header.s=20230601 header.b=xyz789; dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=gmail.com',), None),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))

    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

    # 2. DNS Resolution
    print('\n--- DNS Resolution ---')
    for name, args in [
        ('_resolve_dns_txt', ('claude.ai',)),
        ('_resolve_dns_mx', ('gmail.com',)),
        ('_resolve_dns_a', ('claude.ai',)),
        ('_resolve_ptr', ('8.8.8.8',)),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

    # 3. SPF Analysis
    print('\n--- SPF Analysis ---')
    for name, args in [
        ('check_spf_record', (TARGET_DOMAIN,)),
        ('analyze_spf_record', ('v=spf1 include:_spf.google.com ~all',)),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

    # 4. DKIM Analysis
    print('\n--- DKIM Analysis ---')
    for name, args in [
        ('check_dkim_record', (TARGET_DOMAIN, 'google')),
        ('dkim_selector_guess', (TARGET_DOMAIN,)),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

    # 5. DMARC Analysis
    print('\n--- DMARC Analysis ---')
    for name, args in [
        ('check_dmarc_record', (TARGET_DOMAIN, 10)),
        ('dmarc_policy_analysis', (TARGET_DOMAIN,)),
        ('validate_dmarc', (TARGET_DOMAIN,)),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

    # 6. Email Security Score
    print('\n--- Email Security Score ---')
    for name, args in [
        ('email_security_score', (TARGET_DOMAIN,)),
        ('email_security_report', (TARGET_DOMAIN,)),
        ('email_domain_investigation', (TARGET_DOMAIN,)),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

    # 7. Header Analysis
    print('\n--- Header Analysis ---')
    for name, args in [
        ('analyze_email_headers', (SAMPLE_HEADERS,)),
        ('trace_email_path', (SAMPLE_HEADERS,)),
        ('detect_email_spoofing', (SAMPLE_HEADERS,)),
        ('extract_authentication_results', (SAMPLE_HEADERS,)),
        ('detect_header_forging', (SAMPLE_HEADERS,)),
        ('calculate_delivery_time', (SAMPLE_HEADERS,)),
        ('extract_received_chain', (SAMPLE_HEADERS,)),
        ('extract_dkim_signatures', (SAMPLE_HEADERS,)),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

    # 8. Email Verification
    print('\n--- Email Verification ---')
    for name, args in [
        ('verify_email_format', (TARGET_EMAIL,)),
        ('verify_email_domain', (TARGET_EMAIL,)),
        ('email_disposable_check', (TARGET_EMAIL,)),
        ('email_role_account_check', (TARGET_EMAIL,)),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

    # 9. Forensic
    print('\n--- Forensic Analysis ---')
    for name, args in [
        ('forensic_investigate', (SAMPLE_HEADERS,)),
        ('forensic_spoof_score', (SAMPLE_HEADERS,)),
        ('forensic_sender_verification', (SAMPLE_HEADERS,)),
        ('forensic_ip_analysis', (SAMPLE_HEADERS,)),
        ('behind_the_email', (SAMPLE_HEADERS,)),
        ('email_full_analysis', (SAMPLE_HEADERS,)),
        ('email_trace_route', (TARGET_EMAIL,)),
        ('email_validate_and_verify', (TARGET_EMAIL,)),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

    # 10. Advanced
    print('\n--- Advanced Checks ---')
    for name, args in [
        ('check_bimi_record', (TARGET_DOMAIN,)),
        ('check_mta_sts', (TARGET_DOMAIN,)),
        ('check_tls_rpt', (TARGET_DOMAIN,)),
    ]:
        try:
            fn = getattr(EA, name, None)
            if fn is None:
                results.append((name, 'SKIP', 'not found'))
                continue
            r = await fn(*args) if asyncio.iscoroutinefunction(fn) else fn(*args)
            results.append((name, 'OK', str(r)[:150]))
        except Exception as e:
            results.append((name, 'EXCEPTION', str(e)[:100]))
    for name, s, d in results:
        print(f'  [{s:>9}] {name}: {d[:120]}')
    results.clear()

if __name__ == '__main__':
    asyncio.run(run_tests())
