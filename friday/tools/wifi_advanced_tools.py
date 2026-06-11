"""
Advanced WiFi pentesting tools — smart wordlist generation,
handshake capture & cracking, deauth detection.
"""
from __future__ import annotations

import itertools
import os
import re
import shutil
import subprocess
import time as _time
from datetime import datetime
from typing import Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging
from friday.tools.wifi_tools import wifi_crack

logger = configure_logging(__name__)


# ─── Smart Password Generator ───────────────────────────────────────────────


_COMMON_WORDS = [
    "password", "admin", "welcome", "123456", "12345678", "123456789",
    "qwerty", "letmein", "monkey", "dragon", "master", "sunshine",
    "princess", "football", "iloveyou", "trustno1", "shadow", "superman",
    "batman", "michael", "andrew", "jennifer", "joshua", "matthew",
    "ashley", "bailey", "daniel", "william", "lovely", "summer",
    "winter", "spring", "autumn", "hunter", "ranger", "charlie",
    "thomas", "george", "harry", "jack", "samuel", "oliver",
    "default", "guest", "changeme", "temp", "test", "demo",
    "linksys", "netgear", "tplink", "dlink", "belkin", "cisco",
    "airlive", "speedtouch", "bthub", "virgin", "sky", "orange",
    "btrouter", "homehub", "wifi", "wireless", "internet",
]

_COMMON_NAMES = [
    "alex", "ben", "chris", "dan", "eric", "frank", "george",
    "harry", "ivan", "jack", "kevin", "leo", "mike", "nick",
    "oliver", "peter", "quinn", "rob", "sam", "tom", "victor",
    "will", "xander", "yuki", "zack",
    "anna", "bella", "chloe", "diana", "emma", "fiona", "grace",
    "hannah", "iris", "julia", "kate", "lily", "maria", "nina",
    "olivia", "penny", "quinn", "rose", "sara", "tina", "uma",
    "violet", "wendy", "xena", "yara", "zoe",
]

_YEARS = [str(y) for y in range(1980, 2031)]
_SHORT_YEARS = [str(y)[-2:] for y in range(1980, 2031)]


def _ssid_tokens(ssid: str) -> list[str]:
    """Split an SSID into meaningful tokens."""
    tokens = re.split(r"[-_\s.]", ssid)
    result = []
    for t in tokens:
        if not t:
            continue
        # further split on camelCase / boundary changes
        parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)|\d+", t)
        result.extend(p for p in (parts or [t]) if p)
    return [r.lower() for r in result if r]


def _contains_number(s: str) -> bool:
    return bool(re.search(r"\d", s))


def _contains_year(s: str) -> bool:
    return bool(re.match(r"^(19[8-9]\d|20[0-3]\d)$", s))


def generate_smart_wordlist(
    ssid: str,
    hints: Optional[list[str]] = None,
    max_words: int = 10000,
) -> list[str]:
    """Analyze an SSID and generate a smart, targeted wordlist.

    Args:
        ssid: The target network SSID.
        hints: Optional context (company name, person name, location, etc.).
        max_words: Maximum number of passwords to generate.

    Returns:
        A list of candidate passwords.
    """
    tokens = _ssid_tokens(ssid)
    context = [t.lower() for t in (hints or []) if t]
    password_set: set[str] = set()

    def _add(*candidates: str) -> None:
        for c in candidates:
            c = c.strip()
            if c and len(c) >= 4:
                password_set.add(c)

    # ── 1. SSID-based combinations (most likely to succeed) ──
    ssid_lower = ssid.lower().replace(" ", "").replace("-", "").replace("_", "")
    if ssid_lower:
        _add(ssid_lower)
        _add(ssid_lower + "123")
        _add(ssid_lower + "1234")
        _add(ssid_lower + "12345")
        _add(ssid_lower + "123456")
        _add(ssid_lower + "!")
        _add(ssid_lower + "@")
        _add("123" + ssid_lower)
        _add(ssid_lower + ssid_lower)
        for y in _YEARS:
            _add(ssid_lower + y)
        for sy in _SHORT_YEARS:
            _add(ssid_lower + sy)

    # Token-level SSID combos
    for token in tokens:
        if not token or len(token) < 2:
            continue
        _add(token)
        _add(token + "123")
        _add(token + "1234")
        _add(token + "!")
        _add(token + "@")
        for y in _YEARS:
            _add(token + y)
        for sy in _SHORT_YEARS:
            _add(token + sy)

    # Token pairs
    if len(tokens) >= 2:
        for a, b in itertools.permutations(tokens, 2):
            _add(a + b)
            _add(a + "_" + b)
            _add(a + "-" + b)

    # ── 2. Hint-based combinations ──
    for hint in context:
        hint_clean = hint.lower().replace(" ", "").replace("-", "").replace("_", "")
        if not hint_clean:
            continue
        _add(hint_clean)
        _add(hint_clean + "123")
        _add(hint_clean + "1234")
        _add(hint_clean + "123456")
        _add(hint_clean + "!")
        _add(hint_clean + "@")
        _add("123" + hint_clean)
        for y in _YEARS:
            _add(hint_clean + y)
        for sy in _SHORT_YEARS:
            _add(hint_clean + sy)
        _add(ssid_lower + hint_clean)
        _add(hint_clean + ssid_lower)
        if tokens:
            for token in tokens:
                _add(token + hint_clean)
                _add(hint_clean + token)

    # SSID + hint combinations
    for hint in context:
        hint_clean = hint.lower().replace(" ", "").replace("-", "").replace("_", "")
        if not hint_clean:
            continue
        for token in tokens:
            _add(ssid_lower + hint_clean + token)
            _add(token + hint_clean + ssid_lower)
            _add(hint_clean + token)

    # ── 3. Common word + number combos ──
    for word in _COMMON_WORDS:
        _add(word)
        _add(word + "123")
        _add(word + "1234")
        _add(word + "12345")
        _add(word + "123456")
        _add(word + "!")
        _add(word + "@")
        _add(word + "1")
        _add(word + "2023")
        _add(word + "2024")
        _add(word + "2025")
        _add(word + "2026")
        _add("123" + word)
    for name in _COMMON_NAMES:
        for y in _YEARS:
            _add(name + y)
        for sy in _SHORT_YEARS:
            _add(name + sy)
        _add(name + "123")
        _add(name + "1234")
        _add(name + "123456")
        _add(name + "!")
        _add(name + "@")
        _add(name + "1")
        _add(name + "2023")
        _add(name + "2024")
        _add(name + "2025")
        _add(name + "2026")

    # ── 6. Common patterns from rockyou ──
    rockyou_patterns = [
        "qwerty123", "password123", "admin123", "letmein123",
        "welcome123", "abc123", "test123", "pass123",
        "qwerty1", "password1", "admin1", "letmein1",
        "welcome1", "test1", "pass1",
        "qwerty1234", "password1234", "admin1234",
        "123qwerty", "123password", "123admin",
        "passw0rd", "p@ssword", "P@ssw0rd",
        "changeme", "default", "temp123", "guest123",
    ]
    for pat in rockyou_patterns:
        _add(pat)

    # ── 7. Years 1980-2030 ──
    for y in _YEARS:
        _add(y)
    for sy in _SHORT_YEARS:
        _add(sy)

    # ── 8. 4-digit PINs 0000-9999 ──
    for pin in range(10000):
        _add(f"{pin:04d}")
        if len(password_set) >= max_words:
            return _sorted_truncate(password_set, max_words)

    # ── 9. 8-digit numbers ──
    for n in itertools.product("0123456789", repeat=8):
        _add("".join(n))
        if len(password_set) >= max_words:
            return _sorted_truncate(password_set, max_words)

    # ── 10. alphanumeric shorts (aaaa - zzzz) limited ──
    for combo in itertools.product("abcdefghijklmnopqrstuvwxyz", repeat=4):
        _add("".join(combo))
        if len(password_set) >= max_words:
            return _sorted_truncate(password_set, max_words)

    for combo in itertools.product("abcdefghijklmnopqrstuvwxyz", repeat=5):
        _add("".join(combo) + "1")
        if len(password_set) >= max_words:
            return _sorted_truncate(password_set, max_words)

    return _sorted_truncate(password_set, max_words)


def _sorted_truncate(s: set[str], limit: int) -> list[str]:
    return sorted(s)[:limit]


# ─── Handshake Capture ──────────────────────────────────────────────────────


def _program_files_dirs() -> list[str]:
    """Get Program Files directories dynamically (platform-aware)."""
    dirs = []
    pf = os.environ.get("ProgramFiles")
    if pf:
        dirs.append(pf)
    pf86 = os.environ.get("ProgramFiles(x86)")
    if pf86 and pf86 != pf:
        dirs.append(pf86)
    if not dirs:
        dirs = ["C:\\Program Files", "C:\\Program Files (x86)"]
    return dirs


def _check_aircrack() -> Optional[str]:
    """Return path to aircrack-ng or None if not found."""
    for cmd in ("aircrack-ng", "aircrack-ng.exe"):
        try:
            r = subprocess.run(
                [cmd, "--help"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 or "aircrack-ng" in (r.stdout + r.stderr).lower():
                return shutil.which(cmd) or cmd
        except FileNotFoundError:
            continue
        except Exception:
            continue

    # Check common install locations dynamically
    for pf in _program_files_dirs():
        candidate = os.path.join(pf, "aircrack-ng", "bin", "aircrack-ng.exe")
        if os.path.isfile(candidate):
            return candidate
    return None


def _check_airodump() -> Optional[str]:
    """Return path to airodump-ng or None if not found."""
    for cmd in ("airodump-ng", "airodump-ng.exe"):
        try:
            r = subprocess.run(
                [cmd, "--help"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 or "airodump-ng" in (r.stdout + r.stderr).lower():
                return shutil.which(cmd) or cmd
        except FileNotFoundError:
            continue
        except Exception:
            continue
    for pf in _program_files_dirs():
        candidate = os.path.join(pf, "aircrack-ng", "bin", "airodump-ng.exe")
        if os.path.isfile(candidate):
            return candidate
    return None


def _check_aireplay() -> Optional[str]:
    """Return path to aireplay-ng or None if not found."""
    for cmd in ("aireplay-ng", "aireplay-ng.exe"):
        try:
            r = subprocess.run(
                [cmd, "--help"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 or "aireplay-ng" in (r.stdout + r.stderr).lower():
                return shutil.which(cmd) or cmd
        except FileNotFoundError:
            continue
        except Exception:
            continue
    for pf in _program_files_dirs():
        candidate = os.path.join(pf, "aircrack-ng", "bin", "aireplay-ng.exe")
        if os.path.isfile(candidate):
            return candidate
    return None


def _get_airodump_install_instructions() -> str:
    return (
        "airodump-ng is not installed or not in PATH.\n\n"
        "Install aircrack-ng:\n"
        "  Windows: Download from https://www.aircrack-ng.org/downloads.html\n"
        "           or use: winget install aircrack-ng\n"
        "  Linux:   sudo apt install aircrack-ng\n"
        "  macOS:   brew install aircrack-ng\n\n"
        "After installing, ensure aircrack-ng binaries are in your PATH."
    )


def wifi_capture_handshake(
    ssid: str,
    interface: str = "Wi-Fi",
    timeout: int = 60,
) -> dict:
    """Capture a WPA/WPA2 handshake for a target SSID.

    Requires aircrack-ng suite (airodump-ng).
    The WiFi interface must support monitor mode.

    Args:
        ssid: Target network SSID.
        interface: Interface name to use (default: "Wi-Fi").
        timeout: Max seconds to listen for handshake (default: 60).

    Returns:
        Dict with status, file path, and captured station MACs.
    """
    airodump = _check_airodump()
    if not airodump:
        return {
            "status": "error",
            "error": "airodump-ng not found",
            "instructions": _get_airodump_install_instructions(),
        }

    handshake_dir = os.path.join(FRIDAY_MEMORY, "handshakes")
    os.makedirs(handshake_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cap_basename = f"{ssid}_{timestamp}"
    cap_path = os.path.join(handshake_dir, cap_basename)

    logger.info(
        "Starting handshake capture for SSID '%s' on %s (timeout=%ds)",
        ssid, interface, timeout,
    )

    try:
        proc = subprocess.Popen(
            [
                airodump,
                "--bssid", "FF:FF:FF:FF:FF:FF",
                "--channel", "1",
                "--write", cap_path,
                "--output-format", "pcap",
                interface,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        return {
            "status": "error",
            "error": "airodump-ng not found",
            "instructions": _get_airodump_install_instructions(),
        }
    except Exception as exc:
        logger.error("Failed to start airodump-ng: %s", exc)
        return {"status": "error", "error": str(exc)}

    deadline = _time.time() + timeout
    captured = None
    station_macs: list[str] = []

    try:
        while _time.time() < deadline:
            _time.sleep(1)

            # Check if .cap file has data — look for handshake in CSV
            csv_path = cap_path + "-01.csv"
            if os.path.isfile(csv_path):
                try:
                    with open(csv_path, encoding="utf-8", errors="replace") as f:
                        for line in f:
                            parts = line.strip().split(",")
                            if len(parts) >= 6:
                                mac = parts[0].strip()
                                if mac and ":" in mac and mac != "BSSID":
                                    if mac not in station_macs:
                                        station_macs.append(mac)
                except Exception:
                    pass

            cap_file = cap_path + "-01.cap"
            if os.path.isfile(cap_file) and os.path.getsize(cap_file) > 100:
                # Check for handshake using aircrack-ng
                aircrack = _check_aircrack()
                if aircrack:
                    try:
                        r = subprocess.run(
                            [aircrack, "--bssid", "FF:FF:FF:FF:FF:FF", cap_file],
                            capture_output=True, text=True, timeout=10,
                        )
                        output = r.stdout + r.stderr
                        if "1 handshake" in output.lower() or "wpa handshake" in output.lower():
                            captured = cap_file
                            logger.info("Handshake captured in %s", cap_file)
                            break
                    except Exception:
                        pass

            # Check if we have a .cap with any data packets
            if not captured:
                for fname in os.listdir(handshake_dir):
                    if fname.startswith(cap_basename) and fname.endswith(".cap"):
                        fpath = os.path.join(handshake_dir, fname)
                        if os.path.getsize(fpath) > 200:
                            captured = fpath
                            break

    except KeyboardInterrupt:
        logger.info("Handshake capture interrupted by user")
    except Exception as exc:
        logger.error("Error during handshake capture: %s", exc)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # Find the actual .cap file
    final_cap = None
    for fname in os.listdir(handshake_dir):
        if fname.startswith(cap_basename) and fname.endswith(".cap"):
            final_cap = os.path.join(handshake_dir, fname)
            break

    if captured and final_cap:
        return {
            "status": "success",
            "ssid": ssid,
            "interface": interface,
            "cap_file": final_cap,
            "station_macs": list(set(station_macs)),
            "message": "WPA handshake captured successfully",
        }

    # If no explicit handshake found but we have a cap file, return as partial
    if final_cap and os.path.getsize(final_cap) > 50:
        return {
            "status": "partial",
            "ssid": ssid,
            "interface": interface,
            "cap_file": final_cap,
            "station_macs": list(set(station_macs)),
            "message": f"Capture file created but handshake not confirmed within {timeout}s",
        }

    return {
        "status": "error",
        "ssid": ssid,
        "interface": interface,
        "error": "No handshake captured within the timeout period",
        "message": f"No handshake detected after {timeout}s. Ensure the target is active and the interface supports monitor mode.",
    }


# ─── Handshake Cracker ──────────────────────────────────────────────────────


def wifi_crack_handshake(
    cap_file: str,
    wordlist_file: str = "friday_memory/rockyou.txt",
) -> dict:
    """Crack a captured WPA/WPA2 handshake using a wordlist.

    Args:
        cap_file: Path to the .cap handshake file.
        wordlist_file: Path to wordlist file.

    Returns:
        Dict with success/failure and password if found.
    """
    aircrack = _check_aircrack()
    if not aircrack:
        return {
            "status": "error",
            "error": "aircrack-ng not found",
            "instructions": _get_airodump_install_instructions(),
        }

    # Resolve wordlist path
    if not os.path.isabs(wordlist_file):
        wordlist_file = os.path.join(FRIDAY_MEMORY, os.path.basename(wordlist_file))

    if not os.path.isfile(wordlist_file):
        return {
            "status": "error",
            "error": f"Wordlist not found: {wordlist_file}",
        }

    if not os.path.isfile(cap_file):
        return {
            "status": "error",
            "error": f"Capture file not found: {cap_file}",
        }

    logger.info("Cracking handshake %s with wordlist %s", cap_file, wordlist_file)

    try:
        result = subprocess.run(
            [aircrack, "-w", wordlist_file, cap_file],
            capture_output=True, text=True, timeout=3600,
        )
        output = result.stdout + result.stderr

        # Parse aircrack-ng output for KEY FOUND!
        key_match = re.search(r"KEY FOUND!\s*\[(.+?)\]", output)
        if key_match:
            password = key_match.group(1).strip()
            return {
                "status": "success",
                "cracked": True,
                "cap_file": cap_file,
                "password": password,
                "message": f"Password found: {password}",
            }

        # Check if password was found with a different format
        pw_line = re.search(r"KEY FOUND!\s*\S+\s+\(.*?\)", output)
        if pw_line:
            password = pw_line.group(0).replace("KEY FOUND!", "").strip()
            password = re.sub(r"\s+\(.*$", "", password).strip()
            password = password.strip("[]")
            return {
                "status": "success",
                "cracked": True,
                "cap_file": cap_file,
                "password": password,
                "message": f"Password found: {password}",
            }

        # No passwords matched
        attempts_match = re.search(r"(\d+)\s+of\s+(\d+)\s+keys\s+tested", output)
        tested = int(attempts_match.group(1)) if attempts_match else 0
        total = int(attempts_match.group(2)) if attempts_match else 0

        return {
            "status": "fail",
            "cracked": False,
            "cap_file": cap_file,
            "password": None,
            "keys_tested": tested,
            "total_keys": total,
            "message": f"No password found. Tested {tested}/{total} keys.",
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": "aircrack-ng timed out (1h limit)",
            "cracked": False,
            "cap_file": cap_file,
            "password": None,
        }
    except Exception as exc:
        logger.error("aircrack-ng failed: %s", exc)
        return {
            "status": "error",
            "error": str(exc),
            "cracked": False,
            "cap_file": cap_file,
            "password": None,
        }


# ─── Wordlist Manager ───────────────────────────────────────────────────────


_DEFAULT_ROCKYOU_URL = (
    "https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt"
)


def download_wordlist(url: Optional[str] = None) -> dict:
    """Download rockyou.txt from a GitHub mirror if not already present.

    OPT-IN ONLY: This function should only be called when the user explicitly
    requests or confirms the download. The wordlist (~140MB compressed,
    ~14GB uncompressed) is NOT auto-downloaded.

    Args:
        url: Download URL (defaults to a known GitHub mirror).

    Returns:
        Dict with path, size, and word count.
    """
    import urllib.request
    import io

    dest = os.path.join(FRIDAY_MEMORY, "rockyou.txt")
    if os.path.isfile(dest):
        logger.info("Wordlist already exists at %s", dest)
        count = _count_lines(dest)
        size = os.path.getsize(dest)
        return {
            "status": "exists",
            "path": dest,
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "word_count": count,
            "message": "Wordlist already downloaded",
        }

    download_url = url or _DEFAULT_ROCKYOU_URL
    logger.info("Downloading wordlist from %s", download_url)

    try:
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=300) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 8192
            last_log = 0.0

            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total > 0:
                        pct = downloaded / total * 100
                        now = _time.time()
                        if now - last_log >= 2.0:
                            logger.info(
                                "Download progress: %.1f%% (%s/%s MB)",
                                pct,
                                round(downloaded / (1024 * 1024), 1),
                                round(total / (1024 * 1024), 1),
                            )
                            last_log = now

        size = os.path.getsize(dest)
        word_count = _count_lines(dest)
        logger.info("Download complete: %s (%d words, %.1f MB)", dest, word_count, size / (1024 * 1024))
        return {
            "status": "downloaded",
            "path": dest,
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "word_count": word_count,
            "message": f"Downloaded from {download_url}",
        }

    except Exception as exc:
        logger.error("Download failed: %s", exc)
        # Clean up partial file
        if os.path.isfile(dest):
            try:
                os.remove(dest)
            except Exception:
                pass
        return {
            "status": "error",
            "error": str(exc),
            "message": "Failed to download wordlist. Try a different URL or download manually.",
        }


# ─── Wordlist Stats ─────────────────────────────────────────────────────────


def _count_lines(filepath: str) -> int:
    """Count lines in a file efficiently."""
    try:
        with open(filepath, "rb") as f:
            buf_size = 1024 * 1024
            lines = 0
            while True:
                buf = f.read(buf_size)
                if not buf:
                    break
                lines += buf.count(b"\n")
        return lines
    except Exception:
        return 0


def wordlist_stats(wordlist_path: str = "friday_memory/rockyou.txt") -> dict:
    """Return statistics about a wordlist file.

    Args:
        wordlist_path: Path to the wordlist file.

    Returns:
        Dict with line count, file size, unique word count.
    """
    if not os.path.isabs(wordlist_path):
        wordlist_path = os.path.join(FRIDAY_MEMORY, os.path.basename(wordlist_path))

    if not os.path.isfile(wordlist_path):
        return {
            "status": "error",
            "error": f"File not found: {wordlist_path}",
        }

    try:
        size = os.path.getsize(wordlist_path)
        total_lines = _count_lines(wordlist_path)

        # Count unique words by sampling or full scan (only for smaller files)
        unique_words = 0
        if size < 500 * 1024 * 1024:
            words_seen: set[str] = set()
            try:
                with open(wordlist_path, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        w = line.strip()
                        if w:
                            words_seen.add(w)
                unique_words = len(words_seen)
            except Exception:
                unique_words = total_lines
        else:
            unique_words = total_lines

        return {
            "status": "success",
            "path": wordlist_path,
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "size_gb": round(size / (1024 * 1024 * 1024), 3),
            "total_lines": total_lines,
            "unique_words": unique_words,
            "message": f"{total_lines} lines, {unique_words} unique words, {round(size / (1024 * 1024), 1)} MB",
        }

    except Exception as exc:
        logger.error("Failed to read wordlist stats: %s", exc)
        return {
            "status": "error",
            "error": str(exc),
        }


# ─── Smart WiFi Cracker ─────────────────────────────────────────────────────


def wifi_smart_crack(
    ssid: str,
    wordlist: Optional[list[str]] = None,
    max_passwords: int = 100000,
) -> dict:
    """Crack a WiFi password using a smart, SSID-targeted wordlist.

    Generates a targeted wordlist based on SSID analysis, then
    delegates the actual cracking to wifi_crack() from wifi_tools.

    Args:
        ssid: Target network SSID.
        wordlist: Optional pre-generated wordlist (generates one if None).
        max_passwords: Maximum passwords to try (default: 100000).

    Returns:
        Same dict format as wifi_crack().
    """
    if wordlist is None:
        logger.info(
            "Generating smart wordlist for SSID '%s' (max=%d)",
            ssid, max_passwords,
        )
        wordlist = generate_smart_wordlist(ssid, max_words=max_passwords)
        logger.info("Generated %d candidate passwords", len(wordlist))

    return wifi_crack(ssid, wordlist=wordlist)


# ─── Deauth Detection ───────────────────────────────────────────────────────


def wifi_detect_deauth(interface: str = "Wi-Fi", timeout: int = 30) -> dict:
    """Monitor for deauthentication packets on the specified interface.

    Uses netsh to capture and analyze deauth frames (limited on Windows).
    For full deauth detection, use a tool like Wireshark or airdump-ng
    on an interface that supports monitor mode.

    Args:
        interface: Interface name to monitor (default: "Wi-Fi").
        timeout: Seconds to monitor (default: 30).

    Returns:
        Dict with deauth statistics.
    """
    logger.info("Monitoring deauth packets on %s (timeout=%ds)", interface, timeout)

    # Phase 1: Get baseline stats from netsh
    baseline_errors = _get_netsh_radio_errors(interface)

    _time.sleep(timeout)

    # Phase 2: Get post-monitor stats
    current_errors = _get_netsh_radio_errors(interface)

    deauth_count = 0
    error_deltas: dict[str, int] = {}

    if baseline_errors and current_errors:
        for key in baseline_errors:
            if key in current_errors:
                delta = current_errors[key] - baseline_errors[key]
                if delta > 0:
                    error_deltas[key] = delta
                    if "deauthentication" in key.lower():
                        deauth_count += delta

    # Phase 3: Try airodump-ng for better detection if available
    airodump = _check_airodump()
    airodump_output = ""

    if airodump:
        try:
            r = subprocess.run(
                [airodump, "--band", "abg", "--encrypt", "WPA", "--write", "-", interface],
                capture_output=True, text=True, timeout=min(timeout, 15),
            )
            airodump_output = r.stdout + r.stderr
        except Exception:
            pass

    # Parse airodump output for deauth indicators
    airodump_deauths = 0
    for line in airodump_output.splitlines():
        if re.search(r"deauth|DEAUTH|Deauth", line, re.IGNORECASE):
            m = re.search(r"(\d+)", line)
            if m:
                airodump_deauths += int(m.group(1))

    total_deauths = deauth_count + airodump_deauths

    result = {
        "status": "success",
        "interface": interface,
        "monitor_duration_s": timeout,
        "deauth_packets_detected": total_deauths,
        "error_deltas": error_deltas,
        "message": f"Detected {total_deauths} deauth-related events in {timeout}s",
    }

    if total_deauths > 5:
        result["alert"] = "High number of deauth packets detected — possible deauth attack in progress"
    elif total_deauths > 0:
        result["alert"] = "Some deauth activity detected"

    return result


def _get_netsh_radio_errors(interface: str) -> dict[str, int]:
    """Get radio error counters from netsh for a given interface."""
    errors: dict[str, int] = {}
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interface"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
        )
        lines = result.stdout.splitlines()
        in_target = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Name") and interface.lower() in stripped.lower():
                in_target = True
                continue
            if in_target and stripped.startswith("Name") and ":" in stripped:
                break
            if in_target and ":" in stripped:
                key, _, val = stripped.partition(":")
                try:
                    num = int(val.strip().split()[0]) if val.strip() else 0
                    errors[key.strip()] = num
                except (ValueError, IndexError):
                    pass
    except Exception as exc:
        logger.warning("Failed to get netsh radio errors: %s", exc)
    return errors
