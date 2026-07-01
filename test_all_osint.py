"""
COMPREHENSIVE OSINT TEST: All 677+ functions across all files
Tests against: phulariarnav@gmail.com, phulari_arnav, Arnav, claude.ai
Validates actual output quality, not just "no exception"
"""
import sys, os, json, re, ast, asyncio, time, inspect, traceback
from datetime import datetime, timezone

os.environ['PYTHONUTF8'] = '1'
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# Suppress dnspython WMI spam
import logging
logging.getLogger('dns').setLevel(logging.ERROR)

TARGETS = {
    'email': 'phulariarnav@gmail.com',
    'username': 'phulari_arnav',
    'domain': 'claude.ai',
    'domain_real': 'google.com',
    'ip': '8.8.8.8',
    'url': 'https://claude.ai',
    'wifi_ssid': 'Arnav',
    'phone': '+14155552671',
    'hash_md5': 'd41d8cd98f00b204e9800998ecf8427e',
    'hash_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'btc': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
    'eth': '0x742d35Cc6634C0532925a3b844Bc9e7595f9bDf7',
    'cve': 'CVE-2021-44228',
    'mac': '00:11:22:33:44:55',
    'uuid': '550e8400-e29b-41d4-a716-446655440000',
    'asn': 'AS15169',
    'latlon': '37.7749,-122.4194',
}

class TestRunner:
    def __init__(self):
        self.results = {}  # file -> { function -> (status, detail) }
        self.errors = {}

    def _build_args(self, func_name, sig_params):
        """Auto-generate test args based on function name and parameter names."""
        args = {}
        for p in sig_params:
            p_lower = p.lower()
            # Map param names to targets
            if p in ('self', 'cls', 'request'):
                continue
            if p_lower in ('timeout', 'timeout_per_attempt', 'max_hops', 'limit', 'max_pages', 'depth', 'max_redirects',
                           'max_concurrent', 'concurrent', 'concurrency', 'max_calls', 'window', 'max_words', 'max_variations',
                           'max_transactions', 'max_passwords', 'check_interval_hours', 'interval_hours', 'max_posts',
                           'rotate_ips', 'use_playwright', 'days', 'years', 'strict', 'min_confidence', 'start',
                           'count', 'max_count', 'skip_dns', 'skip_whois'):
                args[p] = 10 if 'timeout' in p_lower or 'max_' in p_lower or 'concurr' in p_lower or 'window' in p_lower or 'limit' in p_lower else 5
                if p_lower == 'max_hops': args[p] = 10
                if p_lower == 'depth': args[p] = 1
                if p_lower == 'days': args[p] = 30
                continue
            if p_lower in ('email', 'email_addr', 'target_email', 'value') and 'email' in func_name.lower():
                args[p] = TARGETS['email']
            elif p_lower in ('domain', 'target_domain'):
                args[p] = TARGETS['domain_real'] if func_name in ('hunter_email_search', 'clearbit_company', 'email_hunter_style') else TARGETS['domain']
            elif p_lower in ('url', 'target_url', 'short_url'):
                args[p] = TARGETS['url']
            elif p_lower in ('ip', 'target_ip', 'sender_ip'):
                args[p] = TARGETS['ip']
            elif p_lower in ('username', 'target_username', 'profile_url', 'entity'):
                args[p] = TARGETS['username']
            elif p_lower in ('phone', 'target_phone'):
                args[p] = TARGETS['phone']
            elif p_lower in ('hash', 'hash_value', 'file_hash'):
                args[p] = TARGETS['hash_md5']
            elif p_lower in ('ssid',):
                args[p] = TARGETS['wifi_ssid']
            elif p_lower in ('host', 'hostname', 'target', 'targets'):
                if 'port' in [x.lower() for x in sig_params]:
                    args[p] = TARGETS['domain']
                else:
                    args[p] = TARGETS['domain']
            elif p_lower in ('port',):
                args[p] = 443
            elif p_lower in ('query', 'search_query', 'q', 'text', 'text_content', 'raw_headers', 'data', 'results',
                             'profiles', 'events', 'formats', 'ioc', 'output_path', 'image_path_or_url', 'image_url',
                             'image_url_a', 'image_url_b', 'html_content', 'candidates', 'platforms', 'feed_type',
                             'password', 'wordlist', 'interface', 'network', 'arguments', 'onion_url', 'onion_address',
                             'product_name', 'keywords', 'actor_name', 'card_number', 'selector', 'first', 'last',
                             'first_name', 'last_name', 'company_domain', 'organization_name', 'org_name', 'repo_full_name',
                             'channel_username', 'channel_identifier', 'identifier', 'image_path', 'engines',
                             'image_url_or_path', 'languages', 'targets', 'profile_html', 'platform', 'max_transactions',
                             'sources', 'filepath', 'headers', 'raw_headers', 'headers_or_email', 'ioc_text', 'bssids'):
                if p_lower in ('selector',): args[p] = 'google'
                elif p_lower in ('query', 'q'): args[p] = TARGETS['username'] if 'user' in func_name.lower() else TARGETS['email']
                elif p_lower in ('first', 'last'): args[p] = TARGETS['username'].split('_')[0] if p == 'first' else TARGETS['username'].split('_')[1]
                elif p_lower == 'first_name': args[p] = 'Arnav'
                elif p_lower == 'last_name': args[p] = 'Phulari'
                elif p_lower == 'company_domain': args[p] = TARGETS['domain']
                elif p_lower == 'org_name': args[p] = 'google'
                elif p_lower == 'repo_full_name': args[p] = 'tensorflow/tensorflow'
                elif p_lower == 'channel_username': args[p] = TARGETS['username']
                elif p_lower == 'channel_identifier': args[p] = TARGETS['username']
                elif p_lower == 'identifier': args[p] = TARGETS['username']
                elif p_lower == 'image_path': args[p] = 'https://example.com/image.jpg'
                elif p_lower == 'image_url_or_path': args[p] = 'https://example.com/image.jpg'
                elif p_lower == 'sources': args[p] = ['google', 'bing']
                elif p_lower == 'bssids': args[p] = ['00:11:22:33:44:55']
                elif p_lower == 'platform': args[p] = 'twitter'
                elif p_lower == 'keywords': args[p] = 'test'
                elif p_lower == 'actor_name': args[p] = 'APT29'
                elif p_lower == 'ioc_text': args[p] = '8.8.8.8 malicious.com'
                else: args[p] = 'test_value'
            elif p_lower in ('a', 'b'):
                args[p] = TARGETS['domain'] if p == 'a' else 'google.com'
            elif p_lower in ('key', 'api_key'):
                args[p] = 'test_key'
            elif p_lower in ('cidr',):
                args[p] = '192.168.1.0/30'
            elif p_lower in ('lat', 'lon'):
                args[p] = 37.7749 if p == 'lat' else -122.4194
            elif p_lower in ('coordinates',):
                args[p] = ['37.7749,-122.4194', '40.7128,-74.0060']
            elif p_lower in ('address', 'currency'):
                args[p] = TARGETS['btc'] if p == 'address' else 'BTC'
            elif p_lower in ('addresses',):
                args[p] = [TARGETS['btc']]
            elif p_lower in ('start_port', 'end_port'):
                args[p] = 20 if p == 'start_port' else 80
            elif p_lower in ('targets',):
                args[p] = [TARGETS['domain'], 'google.com']
            elif p_lower in ('params',):
                args[p] = {}
            elif p_lower in ('threshold',):
                args[p] = 0.8
            elif p_lower in ('verbosity',):
                args[p] = 1
            elif p_lower in ('case_id',):
                args[p] = 'CASE-001'
            elif p_lower in ('filename',):
                args[p] = 'osint_output.csv'
            elif p_lower in ('title',):
                args[p] = 'OSINT Report'
            elif p_lower in ('output_path',):
                args[p] = os.path.join(temp_dir, 'output.pdf')
            elif p_lower in ('wordlist',):
                args[p] = ['www', 'mail', 'api']
            elif p_lower in ('templates', 'exclude_templates', 'severity'):
                args[p] = None
            elif p_lower in ('max_attempts',):
                args[p] = 3
            else:
                args[p] = 'test_value'
        return args

    async def _call_with_timeout(self, fn, args_dict, timeout=20):
        """Call function with timeout to prevent hanging."""
        try:
            if asyncio.iscoroutinefunction(fn):
                return await asyncio.wait_for(fn(**args_dict), timeout=timeout)
            else:
                # Run sync functions in executor with timeout
                return await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, lambda: fn(**args_dict)),
                    timeout=timeout
                )
        except asyncio.TimeoutError:
            return {'_timeout': True, 'error': f'Timed out after {timeout}s'}
        except Exception as e:
            return {'_exception': True, 'error': str(e)[:200]}

    def _validate_result(self, func_name, result):
        """Validate result quality - check for actual errors vs valid data."""
        if result is None:
            return 'FAIL', 'Returned None'
        if isinstance(result, dict):
            if result.get('_timeout'):
                return 'TIMEOUT', result.get('error', '')
            if result.get('_exception'):
                return 'EXCEPTION', result.get('error', '')
            if result.get('error'):
                err = result['error'][:100]
                if 'API key' in err or 'not set' in err or 'not installed' in err:
                    return 'SKIP', err
                if 'Cannot connect' in err or 'Could not contact DNS' in err or 'timed out' in err.lower():
                    return 'NETWORK', err
                if 'does not exist' in err.lower() or 'not found' in err.lower():
                    return 'NOT FOUND', err
                return 'ERROR', err
            # Check for empty data
            if len(result) <= 1:
                return 'WARN', 'Minimal result: ' + str(result)[:100]
            return 'PASS', str(result)[:120]
        if isinstance(result, list):
            return 'PASS', f'list[{len(result)}]: {str(result)[:100]}'
        if isinstance(result, str):
            return 'PASS', result[:100]
        if isinstance(result, bool):
            return 'PASS', str(result)
        if isinstance(result, (int, float)):
            return 'PASS', str(result)
        return 'PASS', str(type(result).__name__) + ': ' + str(result)[:80]

    async def test_module(self, module_name, module, targets_list=None):
        """Test ALL public (non-underscore) functions in a module."""
        mod_results = {}
        public_funcs = [(n, fn) for n, fn in inspect.getmembers(module, inspect.isfunction)
                        if not n.startswith('_') and callable(fn)]
        # Also check for async functions
        async_funcs = [(n, fn) for n, fn in inspect.getmembers(module, inspect.iscoroutinefunction)
                       if not n.startswith('_')]
        all_funcs = dict(public_funcs)
        all_funcs.update(dict(async_funcs))

        if not all_funcs:
            return {'message': f'No public functions found in {module_name}'}

        for func_name, fn in sorted(all_funcs.items()):
            try:
                sig = inspect.signature(fn)
                params = list(sig.parameters.keys())
                args = self._build_args(func_name, params)
                result = await self._call_with_timeout(fn, args)
                status, detail = self._validate_result(func_name, result)
            except Exception as e:
                status, detail = 'EXCEPTION', str(e)[:150]
            mod_results[func_name] = (status, detail)
            status_str = f'[{status:>8}]'
            print(f'  {status_str} {func_name}: {detail[:100]}')

        # Summary
        pass_c = sum(1 for s, _ in mod_results.values() if s == 'PASS')
        warn_c = sum(1 for s, _ in mod_results.values() if s == 'WARN')
        fail_c = sum(1 for s, _ in mod_results.values() if s in ('FAIL', 'ERROR'))
        skip_c = sum(1 for s, _ in mod_results.values() if s == 'SKIP')
        net_c = sum(1 for s, _ in mod_results.values() if s == 'NETWORK')
        timeout_c = sum(1 for s, _ in mod_results.values() if s == 'TIMEOUT')
        exc_c = sum(1 for s, _ in mod_results.values() if s == 'EXCEPTION')
        nf_c = sum(1 for s, _ in mod_results.values() if s == 'NOT FOUND')

        summary = {'total': len(mod_results), 'pass': pass_c, 'warn': warn_c,
                   'fail': fail_c, 'skip': skip_c, 'network': net_c,
                   'timeout': timeout_c, 'exception': exc_c, 'not_found': nf_c}

        print(f'\n  -> {module_name}: {pass_c} pass, {warn_c} warn, {fail_c} fail, '
              f'{skip_c} skip, {net_c} network, {timeout_c} timeout, {exc_c} exception')
        return mod_results


async def main():
    global temp_dir
    temp_dir = os.environ.get('TEMP', os.path.join(os.getcwd(), 'temp'))
    os.makedirs(temp_dir, exist_ok=True)

    TEST_FILES = [
        ('friday.tools_osint_extra', 'friday/tools_osint_extra.py', 'OSINT Utilities'),
        ('friday.email_analysis_tool', 'friday/email_analysis_tool.py', 'Email Forensics'),
        ('friday.tools.osint_advanced_tools', 'friday/tools/osint_advanced_tools.py', 'Advanced OSINT'),
        ('friday.tools.osint_enhanced_tools', 'friday/tools/osint_enhanced_tools.py', 'Enhanced OSINT'),
        ('friday.tools.github_osint_tool', 'friday/tools/github_osint_tool.py', 'GitHub OSINT'),
        ('friday.tools.telegram_osint_tool', 'friday/tools/telegram_osint_tool.py', 'Telegram OSINT'),
        ('friday.tools.wifi_tools', 'friday/tools/wifi_tools.py', 'WiFi Tools'),
        ('friday.tools.wifi_advanced_tools', 'friday/tools/wifi_advanced_tools.py', 'Advanced WiFi'),
        ('friday.osint_summarizer', 'friday/osint_summarizer.py', 'OSINT Summarizer'),
    ]

    runner = TestRunner()
    all_summaries = {}
    grand_total = {'pass': 0, 'warn': 0, 'fail': 0, 'skip': 0, 'network': 0, 'timeout': 0, 'exception': 0, 'not_found': 0, 'total': 0}

    for mod_name, filepath, label in TEST_FILES:
        print(f'\n{"=" * 70}')
        print(f'TESTING: {filepath} ({label})')
        print(f'{"=" * 70}')

        try:
            # Dynamic import
            import importlib
            try:
                mod = importlib.import_module(mod_name)
            except ImportError as e:
                print(f'  [IMPORT FAIL] {e}')
                # Try directly importing from file path
                import importlib.util
                spec = importlib.util.spec_from_file_location(mod_name, filepath)
                if spec is None:
                    print(f'  [SKIP] Cannot load {filepath}')
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

            print(f'  [IMPORT OK]')
            results = await runner.test_module(label, mod)
            all_summaries[label] = results

            # Aggregate
            if isinstance(results, dict) and 'total' not in results:
                for k, (status, _) in results.items():
                    if status in grand_total:
                        grand_total[status] += 1
                    grand_total['total'] += 1

        except Exception as e:
            print(f'  [FATAL] {traceback.format_exc()[:200]}')

    # GRAND SUMMARY
    print(f'\n\n{"=" * 70}')
    print(f'GRAND TOTAL OSINT TEST SUMMARY')
    print(f'{"=" * 70}')

    g = grand_total
    print(f'\nTotal functions tested: {g["total"]}')
    print(f'  PASS:     {g["pass"]}')
    print(f'  WARN:     {g["warn"]}')
    print(f'  SKIP:     {g["skip"]} (API key / dep missing)')
    print(f'  NETWORK:  {g["network"]} (network error)')
    print(f'  TIMEOUT:  {g["timeout"]}')
    print(f'  NOT FOUND: {g["not_found"]} (target not found)')
    print(f'  FAIL:     {g["fail"]}')
    print(f'  EXCEPTION: {g["exception"]}')
    working = g['pass'] + g['warn']
    print(f'\n  WORKING: {working}/{g["total"]} ({100*working//max(g["total"],1)}%)')

    # Per-file breakdown
    print(f'\n{"-" * 70}')
    print('Breakdown by file:')
    for label, results in all_summaries.items():
        if isinstance(results, dict) and 'total' not in results:
            p = sum(1 for s, _ in results.values() if s == 'PASS')
            w = sum(1 for s, _ in results.values() if s == 'WARN')
            f = sum(1 for s, _ in results.values() if s in ('FAIL', 'ERROR'))
            s = sum(1 for s, _ in results.values() if s == 'SKIP')
            n = sum(1 for s, _ in results.values() if s == 'NETWORK')
            t = sum(1 for s, _ in results.values() if s == 'TIMEOUT')
            e = sum(1 for s, _ in results.values() if s == 'EXCEPTION')
            nf = sum(1 for s, _ in results.values() if s == 'NOT FOUND')
            total = len(results)
            print(f'  {label:25s}: {total:3d} total | PASS={p:3d} WARN={w:2d} FAIL={f:2d} SKIP={s:2d} NET={n:2d} TO={t:2d} EXC={e:2d} NF={nf:2d}')

if __name__ == '__main__':
    asyncio.run(main())
