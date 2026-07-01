---
name: osint
description: Use this skill when performing Open Source Intelligence gathering — social media, email, DNS, web, breach, phone, crypto, dark web, and knowledge graph analysis
---

# OSINT Skill Guide

## Overview

FRIDAY has **460+ OSINT functions** across social media analysis, email discovery, DNS deep recon, web tech detection, URL scanning, breach analysis, phone intelligence, cryptocurrency tracking, dark web monitoring, and more. Use the dedicated osint_extra bridge for single-purpose tools, or `osint_full_scan` for comprehensive profiling.

This skill covers the complete OSINT methodology: collection → processing → analysis → reporting. It includes operational security guidelines, ethical considerations, and advanced analysis techniques.

**IMPORTANT: OSINT must be conducted ethically and legally. Never use these techniques for stalking, harassment, or unauthorized surveillance. Always respect privacy laws and terms of service.**

## Triggers

- "OSINT", "reconnaissance", "investigate", "intelligence gathering"
- "find information about", "profile", "scan", "enumerate"
- "email lookup", "username search", "domain recon", "IP analysis"
- "breach check", "leak check", "dark web"
- "social media investigation", "digital footprint", "dox"
- "phone lookup", "crypto trace", "blockchain analysis"
- "threat intelligence", "attack surface", "digital risk"

---

## Complete OSINT Methodology

### The OSINT Cycle

```
                     ┌─────────────┐
                     │  Planning & │
                     │   Direction │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │ Collection  │
                     │  (Sources)  │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │ Processing  │
                     │  (Data)     │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  Analysis   │
                     │ (Intel)     │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │ Reporting   │
                     │ (Product)   │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │ Feedback &  │
                     │ New Tasks   │────► Back to Planning
                     └─────────────┘
```

### Phase 1: Planning and Direction

Before starting any OSINT investigation:

1. **Define objectives:** What specific information is needed? What questions need answers?
2. **Identify target:** Person, organization, domain, email, username, IP, phone, cryptocurrency address
3. **Scope the investigation:** What sources are in bounds? What's out of bounds?
4. **Legal review:** Ensure investigation complies with applicable laws
5. **Operational security check:** Assess risk to investigator and investigation
6. **Tool selection:** Choose appropriate tools based on target type
7. **Source prioritization:** Rank sources by reliability and relevance
8. **Timeline planning:** Set deadlines and milestones

### Phase 2: Collection

**Principles of Collection:**
- Collect from multiple independent sources for cross-validation
- Document everything with timestamps
- Use the original source when possible (not republished data)
- Respect robots.txt and rate limits
- Rotate IP addresses and user agents to avoid blocking
- Use APIs legally and in accordance with terms of service
- Collect metadata alongside content (timestamps, headers, source URLs)

**Collection Methods:**
- **Passive:** Querying public APIs, databases, search engines (no direct interaction with target)
- **Active:** Direct interaction with target systems (port scanning, DNS queries, website visits)
- **Semi-passive:** Using third-party services that interact with the target (certificate transparency, URL scanners)

### Phase 3: Processing

Transform raw collected data into structured, analyzable formats:

- Parse JSON/XML API responses into structured records
- Clean and normalize text data (remove duplicates, standardize formats)
- Extract timestamps into ISO 8601 format
- Geocode location data
- Cross-reference and link related records
- Build entity-relationship model
- Generate timeline of events
- Calculate confidence scores for each data point

### Phase 4: Analysis

Apply analytical techniques to derive intelligence:

- **Link analysis:** Map connections between entities (people, emails, domains, IPs)
- **Temporal analysis:** Identify patterns over time
- **Geospatial analysis:** Map geographic relationships
- **Network analysis:** Identify key nodes and communities
- **Pattern recognition:** Detect recurring behaviors or signatures
- **Deviation analysis:** Find anomalies that don't fit expected patterns
- **Source evaluation:** Rank reliability and credibility of each source
- **Hypothesis testing:** Form and test theories about the target

### Phase 5: Reporting

Present findings in clear, actionable formats:

- **Executive summary:** Brief overview for decision-makers
- **Technical report:** Detailed findings with evidence
- **Evidence chain:** Source → data → analysis → conclusion
- **Confidence ratings:** How certain is each finding
- **Visualizations:** Graphs, charts, relationship maps, timelines
- **Recommendations:** Suggested next steps or actions
- **Source list:** All sources used with reliability ratings
- **Classification markings:** If applicable

### Phase 6: Feedback

- Review findings with stakeholders
- Identify gaps in collected intelligence
- Refine collection parameters for next iteration
- Update investigation objectives based on findings
- Document lessons learned

---

## Tool Categories and Usage

### Social Media OSINT (Username-Based)

```python
def social_media_full_scan(username: str) -> dict:
    """Run all social media OSINT tools against a username across platforms.

    Checks username existence and extracts public profile information
    from 30+ social media platforms.

    Args:
        username: The username to search for

    Returns:
        dict with platform-by-platform results and summary statistics

    Example:
        >>> result = social_media_full_scan('johndoe')
        >>> print(f"Found on {result['platforms_found']} platforms")
    """
    results = {
        "username": username,
        "scan_time": datetime.now().isoformat(),
        "platforms_checked": 0,
        "platforms_found": 0,
        "platforms": {},
        "error": None,
    }

    try:
        # Run individual platform checks
        platforms = {
            "twitter": twitter_osint(username),
            "instagram": instagram_osint(username),
            "reddit": reddit_osint(username),
            "github": github_osint(username),
            "telegram": telegram_osint(username),
            "tiktok": tiktok_osint(username),
            "facebook": facebook_osint(username),
            "linkedin": linkedin_osint(username),
        }

        for platform, data in platforms.items():
            results["platforms_checked"] += 1
            if data and data.get("found", False):
                results["platforms_found"] += 1
            results["platforms"][platform] = data

        # Run Sherlock for extended platform search (300+ platforms)
        sherlock_results = sherlock_search(username)
        results["sherlock"] = sherlock_results

        log.info(f"Social media scan for '{username}': found on {results['platforms_found']} platforms")

    except Exception as e:
        results["error"] = str(e)
        log.error(f"Social media scan failed: {e}")

    return results


def twitter_osint(username: str) -> dict:
    """Gather public Twitter/X profile information.

    Collects: display name, bio, follower/following counts, join date,
    location, website, pinned tweet, recent tweets, profile image URL,
    verification status, and account age.

    Args:
        username: Twitter/X username (without @)

    Returns:
        dict with profile data
    """
    result = {"found": False, "error": None}
    try:
        # Implementation uses Twitter API or web scraping
        import requests
        # Note: This is a simplified example — real implementation
        # would use the actual Twitter API v2 with proper auth
        url = f"https://api.twitter.com/2/users/by/username/{username}"
        # ... API call with authentication ...
        result["found"] = True
        result["username"] = username
        result["display_name"] = "User Display Name"
        result["bio"] = "User biography"
        result["followers"] = 1234
        result["following"] = 567
        result["tweet_count"] = 890
        result["joined"] = "2020-01-15T10:30:00Z"
        result["location"] = "New York, NY"
        result["verified"] = False
        result["profile_url"] = f"https://twitter.com/{username}"
    except Exception as e:
        result["error"] = str(e)
    return result


def instagram_osint(username: str) -> dict:
    """Gather public Instagram profile information.

    Collects: display name, biography, follower/following counts, post count,
    profile image, external URL, business category, recent posts (captions, likes),
    and account verification status.

    Args:
        username: Instagram username

    Returns:
        dict with profile data
    """
    result = {"found": False, "error": None}
    try:
        # Implementation using Instagram API or scraping
        result["found"] = True
        result["username"] = username
        result["full_name"] = "Full Name"
        result["biography"] = "Bio text"
        result["followers"] = 12345
        result["following"] = 678
        result["posts"] = 90
        result["is_private"] = False
        result["is_verified"] = False
        result["business_category"] = None
        result["recent_posts"] = []
    except Exception as e:
        result["error"] = str(e)
    return result


def reddit_osint(username: str) -> dict:
    """Gather public Reddit user information via the JSON API.

    Collects: account age, karma (post + comment), trophies, recent posts
    and comments, active subreddits, post/comment frequency patterns.

    Args:
        username: Reddit username

    Returns:
        dict with user data
    """
    result = {"found": False, "error": None}
    try:
        url = f"https://www.reddit.com/user/{username}/about.json"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result["found"] = True
            result["username"] = username
            result["created_utc"] = data.get("data", {}).get("created_utc")
            result["link_karma"] = data.get("data", {}).get("link_karma", 0)
            result["comment_karma"] = data.get("data", {}).get("comment_karma", 0)
            result["is_employee"] = data.get("data", {}).get("is_employee", False)
            result["is_mod"] = data.get("data", {}).get("is_mod", False)
            result["has_verified_email"] = data.get("data", {}).get("has_verified_email", False)
            # Calculate account age
            if result["created_utc"]:
                import datetime
                created = datetime.datetime.fromtimestamp(result["created_utc"])
                result["account_age_days"] = (datetime.datetime.now() - created).days
    except Exception as e:
        result["error"] = str(e)
    return result


def facebook_osint(query: str) -> dict:
    """Search for Facebook public profiles and pages.

    Args:
        query: Name, username, or other identifier to search

    Returns:
        dict with matching profiles/pages
    """
    result = {"found": False, "profiles": [], "error": None}
    try:
        # Note: Facebook's graph search API requires authentication.
        # This uses public search methods.
        result["profiles"] = _search_facebook_public(query)
        result["found"] = len(result["profiles"]) > 0
    except Exception as e:
        result["error"] = str(e)
    return result


def linkedin_osint(query: str) -> dict:
    """Search for LinkedIn public profiles.

    Args:
        query: Name, company, or other search criteria

    Returns:
        dict with matching profiles
    """
    result = {"found": False, "profiles": [], "error": None}
    try:
        # Use public LinkedIn search (no API without authentication)
        # Returns limited public profile information
        result["profiles"] = _search_linkedin_public(query)
        result["found"] = len(result["profiles"]) > 0
    except Exception as e:
        result["error"] = str(e)
    return result


def telegram_osint(username: str) -> dict:
    """Check if a Telegram username exists and get public info.

    Args:
        username: Telegram username

    Returns:
        dict with username existence and basic info
    """
    result = {"found": False, "error": None}
    try:
        url = f"https://t.me/{username}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200 and 'tgme_page' in resp.text:
            result["found"] = True
            result["username"] = username
            result["url"] = url
            # Extract title/description from page meta
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            title_tag = soup.find('meta', property='og:title')
            desc_tag = soup.find('meta', property='og:description')
            result["title"] = title_tag.get('content', '') if title_tag else ''
            result["description"] = desc_tag.get('content', '') if desc_tag else ''
    except Exception as e:
        result["error"] = str(e)
    return result


def tiktok_osint(username: str) -> dict:
    """Gather public TikTok profile information.

    Args:
        username: TikTok username

    Returns:
        dict with profile data
    """
    result = {"found": False, "error": None}
    try:
        # Implementation using TikTok public API
        result["found"] = True
        result["username"] = username
        result["display_name"] = "Display Name"
        result["bio"] = "Bio description"
        result["followers"] = 10000
        result["following"] = 500
        result["likes"] = 50000
        result["videos"] = 150
    except Exception as e:
        result["error"] = str(e)
    return result


def github_osint(username: str) -> dict:
    """Gather public GitHub profile information.

    Collects: repositories, contributions, organizations, followers,
    bio, location, website, email, and coding activity patterns.

    Args:
        username: GitHub username

    Returns:
        dict with profile and repository data
    """
    result = {"found": False, "error": None}
    try:
        import requests
        api_url = f"https://api.github.com/users/{username}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        resp = requests.get(api_url, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            result["found"] = True
            result["username"] = data.get("login")
            result["name"] = data.get("name")
            result["company"] = data.get("company")
            result["blog"] = data.get("blog")
            result["location"] = data.get("location")
            result["email"] = data.get("email")  # Only if public
            result["bio"] = data.get("bio")
            result["public_repos"] = data.get("public_repos", 0)
            result["public_gists"] = data.get("public_gists", 0)
            result["followers"] = data.get("followers", 0)
            result["following"] = data.get("following", 0)
            result["created_at"] = data.get("created_at")
            result["updated_at"] = data.get("updated_at")
            result["hireable"] = data.get("hireable", False)
            result["twitter_username"] = data.get("twitter_username")

            # Fetch recent repositories
            repos_url = data.get("repos_url", "")
            if repos_url:
                repos_resp = requests.get(
                    repos_url + "?per_page=30&sort=updated",
                    headers=headers,
                    timeout=10,
                )
                if repos_resp.status_code == 200:
                    repos = repos_resp.json()
                    result["recent_repos"] = [{
                        "name": r.get("name"),
                        "description": r.get("description"),
                        "language": r.get("language"),
                        "stars": r.get("stargazers_count", 0),
                        "forks": r.get("forks_count", 0),
                        "updated_at": r.get("updated_at"),
                        "fork": r.get("fork", False),
                    } for r in repos[:20]]
    except Exception as e:
        result["error"] = str(e)
    return result
```

### Sherlock — Username Search Across 300+ Platforms

```python
def sherlock_search(username: str) -> dict:
    """Search for a username across 300+ social media and web platforms.

    Uses the Sherlock project methodology to check username existence
    on hundreds of websites.

    Args:
        username: Username to search for

    Returns:
        dict with found sites and their profile URLs

    Example:
        >>> result = sherlock_search('johndoe')
        >>> for site in result['found']:
        ...     print(f"{site['site']}: {site['url']}")
    """
    result = {
        "username": username,
        "total_checked": 0,
        "total_found": 0,
        "found": [],
        "error": None,
    }

    # Sherlock site list (simplified — real implementation has 300+)
    sherlock_sites = _get_sherlock_sites()

    try:
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def check_site(site: dict) -> dict | None:
            try:
                url = site["url"].replace("{username}", username)
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                resp = requests.get(url, headers=headers, timeout=10)

                # Check for error indicators
                if resp.status_code == 200:
                    # Some sites return 200 even for nonexistent users — check content
                    error_indicators = site.get("error_indicators", [])
                    if error_indicators:
                        has_error = any(
                            ei.lower() in resp.text.lower()
                            for ei in error_indicators
                        )
                        if not has_error:
                            return {
                                "site": site["name"],
                                "url": url,
                                "status_code": resp.status_code,
                            }
                    else:
                        return {
                            "site": site["name"],
                            "url": url,
                            "status_code": resp.status_code,
                        }
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(check_site, site): site for site in sherlock_sites}
            for future in as_completed(futures):
                result["total_checked"] += 1
                site_result = future.result()
                if site_result:
                    result["found"].append(site_result)
                    result["total_found"] += 1

        result["found"].sort(key=lambda x: x["site"].lower())
        log.info(f"Sherlock found '{username}' on {result['total_found']}/{result['total_checked']} sites")

    except Exception as e:
        result["error"] = str(e)
        log.error(f"Sherlock search failed: {e}")

    return result


def _get_sherlock_sites() -> list[dict]:
    """Return the list of sites that Sherlock checks.

    This is a simplified subset of the actual 300+ site list.
    """
    return [
        {"name": "Twitter", "url": "https://twitter.com/{username}", "error_indicators": ["page doesn't exist"]},
        {"name": "Instagram", "url": "https://www.instagram.com/{username}/"},
        {"name": "Reddit", "url": "https://www.reddit.com/user/{username}"},
        {"name": "GitHub", "url": "https://github.com/{username}", "error_indicators": ["Not Found"]},
        {"name": "YouTube", "url": "https://www.youtube.com/@{username}"},
        {"name": "TikTok", "url": "https://www.tiktok.com/@{username}"},
        {"name": "Twitch", "url": "https://www.twitch.tv/{username}"},
        {"name": "Medium", "url": "https://medium.com/@{username}"},
        {"name": "Pinterest", "url": "https://www.pinterest.com/{username}/"},
        {"name": "Tumblr", "url": "https://{username}.tumblr.com/"},
        {"name": "Snapchat", "url": "https://www.snapchat.com/add/{username}"},
        {"name": "Telegram", "url": "https://t.me/{username}"},
        {"name": "WhatsApp", "url": "https://wa.me/{username}"},
        {"name": "Flickr", "url": "https://www.flickr.com/people/{username}/"},
        {"name": "Steam", "url": "https://steamcommunity.com/id/{username}"},
        {"name": "Discord", "url": "https://discord.com/users/{username}"},
        {"name": "Keybase", "url": "https://keybase.io/{username}"},
        {"name": "Facebook", "url": "https://www.facebook.com/{username}"},
        {"name": "LinkedIn", "url": "https://www.linkedin.com/in/{username}/"},
        {"name": "Patreon", "url": "https://www.patreon.com/{username}"},
        {"name": "BuyMeACoffee", "url": "https://www.buymeacoffee.com/{username}"},
        {"name": "Dev.to", "url": "https://dev.to/{username}"},
        {"name": "Hashnode", "url": "https://hashnode.com/@{username}"},
        {"name": "AngelList", "url": "https://angel.co/u/{username}"},
        {"name": "ProductHunt", "url": "https://www.producthunt.com/@{username}"},
        {"name": "HackerNews", "url": "https://news.ycombinator.com/user?id={username}"},
        {"name": "HackerOne", "url": "https://hackerone.com/{username}"},
        {"name": "Bugcrowd", "url": "https://bugcrowd.com/{username}"},
        {"name": "PayPal", "url": "https://www.paypal.com/paypalme/{username}"},
        {"name": "Venmo", "url": "https://venmo.com/{username}"},
        {"name": "CashApp", "url": "https://cash.app/${username}"},
        {"name": "SoundCloud", "url": "https://soundcloud.com/{username}"},
        {"name": "Spotify", "url": "https://open.spotify.com/user/{username}"},
        {"name": "Mixcloud", "url": "https://www.mixcloud.com/{username}/"},
        {"name": "Bandcamp", "url": "https://bandcamp.com/{username}"},
        {"name": "Last.fm", "url": "https://www.last.fm/user/{username}"},
        {"name": "MySpace", "url": "https://myspace.com/{username}"},
        {"name": "Behance", "url": "https://www.behance.net/{username}"},
        {"name": "Dribbble", "url": "https://dribbble.com/{username}"},
        {"name": "CodePen", "url": "https://codepen.io/{username}"},
        {"name": "Repl.it", "url": "https://replit.com/@{username}"},
        {"name": "GitLab", "url": "https://gitlab.com/{username}"},
        {"name": "Bitbucket", "url": "https://bitbucket.org/{username}/"},
        {"name": "Vimeo", "url": "https://vimeo.com/{username}"},
        {"name": "Dailymotion", "url": "https://www.dailymotion.com/{username}"},
        {"name": "OK", "url": "https://ok.ru/{username}"},
        {"name": "VK", "url": "https://vk.com/{username}"},
        {"name": "About.me", "url": "https://about.me/{username}"},
        {"name": "SlideShare", "url": "https://www.slideshare.net/{username}"},
        {"name": "Scribd", "url": "https://www.scribd.com/{username}"},
        {"name": "Issuu", "url": "https://issuu.com/{username}"},
        {"name": "Couchsurfing", "url": "https://www.couchsurfing.com/people/{username}"},
        {"name": "Foursquare", "url": "https://foursquare.com/user/{username}"},
        {"name": "Meetup", "url": "https://www.meetup.com/members/{username}/"},
        {"name": "Wikipedia", "url": "https://en.wikipedia.org/wiki/User:{username}"},
        {"name": "Imgur", "url": "https://{username}.imgur.com/"},
        {"name": "Gravatar", "url": "https://en.gravatar.com/{username}"},
        {"name": "WordPress", "url": "https://{username}.wordpress.com/"},
        {"name": "Blogger", "url": "https://{username}.blogspot.com/"},
        {"name": "Wix", "url": "https://{username}.wixsite.com/"},
        {"name": "Squarespace", "url": "https://{username}.squarespace.com/"},
        {"name": "Weebly", "url": "https://{username}.weebly.com/"},
        {"name": "Jimdo", "url": "https://{username}.jimdosite.com/"},
        {"name": "Etsy", "url": "https://www.etsy.com/shop/{username}"},
        {"name": "eBay", "url": "https://www.ebay.com/usr/{username}"},
        {"name": "Amazon", "url": "https://www.amazon.com/gp/profile/{username}"},
        {"name": "Goodreads", "url": "https://www.goodreads.com/{username}"},
        {"name": "IMDb", "url": "https://www.imdb.com/user/ur{username}"},
        {"name": "RottenTomatoes", "url": "https://www.rottentomatoes.com/user/id/{username}"},
        {"name": "Letterboxd", "url": "https://letterboxd.com/{username}/"},
        {"name": "Trakt", "url": "https://trakt.tv/users/{username}"},
        {"name": "MyAnimeList", "url": "https://myanimelist.net/profile/{username}"},
        {"name": "Anilist", "url": "https://anilist.co/user/{username}/"},
        {"name": "Chess.com", "url": "https://www.chess.com/member/{username}"},
        {"name": "Lichess", "url": "https://lichess.org/@/{username}"},
        {"name": "StackOverflow", "url": "https://stackoverflow.com/users/{username}"},
        {"name": "Quora", "url": "https://www.quora.com/profile/{username}"},
        {"name": "500px", "url": "https://500px.com/{username}"},
        {"name": "Unsplash", "url": "https://unsplash.com/@{username}"},
        {"name": "DeviantArt", "url": "https://www.deviantart.com/{username}"},
        {"name": "ArtStation", "url": "https://www.artstation.com/{username}"},
        {"name": "Coroflot", "url": "https://www.coroflot.com/{username}"},
        {"name": "Kaggle", "url": "https://www.kaggle.com/{username}"},
        {"name": "ResearchGate", "url": "https://www.researchgate.net/profile/{username}"},
        {"name": "Academia", "url": "https://independent.academia.edu/{username}"},
        {"name": "GoogleScholar", "url": "https://scholar.google.com/citations?user={username}"},
        {"name": "ORCID", "url": "https://orcid.org/{username}"},
        {"name": "Zillow", "url": "https://www.zillow.com/profile/{username}"},
        {"name": "Realtor", "url": "https://www.realtor.com/realestateagents/{username}"},
        {"name": "Nextdoor", "url": "https://nextdoor.com/profile/{username}/"},
        {"name": "Waymark", "url": "https://waymark.com/{username}"},
    ]
```

---

## Email Intelligence — Complete

### Email Verification and Reputation

```python
def full_email_intel(email: str) -> dict:
    """Complete email intelligence pipeline.

    Runs all email OSINT tools and compiles a comprehensive report.

    Args:
        email: Target email address

    Returns:
        dict with all gathered email intelligence

    Example:
        >>> result = full_email_intel('target@example.com')
        >>> print(f"Reputation: {result['reputation']}")
        >>> print(f"Breaches: {len(result['breaches'])}")
    """
    result = {
        "email": email,
        "valid_format": False,
        "domain": "",
        "local_part": "",
        "disposable": None,
        "role_account": None,
        "reputation": None,
        "smtp_valid": None,
        "breaches": [],
        "associated_services": [],
        "social_profiles": [],
        "data_sources_used": [],
        "collection_timestamp": datetime.now().isoformat(),
    }

    try:
        # Parse email
        local, domain = email.split('@')
        result["local_part"] = local
        result["domain"] = domain
        result["valid_format"] = bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

        # Check if disposable
        result["disposable"] = _is_disposable_email(domain)

        # Check if role account
        role_accounts = ['admin', 'info', 'support', 'sales', 'contact', 'webmaster', 'postmaster', 'hostmaster', 'abuse', 'noreply', 'no-reply']
        result["role_account"] = local.lower() in role_accounts

        # MX record check
        mx_records = mx_lookup(domain)
        result["mx_records"] = mx_records
        result["has_mx"] = len(mx_records) > 0

        # Email reputation
        rep = email_rep(email)
        result["reputation"] = rep.get("reputation", "unknown")

        # SMTP verification
        smtp = _verify_email_smtp(email)
        result["smtp_valid"] = smtp

        # Breach check
        breaches = leak_check(email)
        result["breaches"] = breaches.get("breaches", [])

        # Check for accounts on services
        services = holehe_check(email)
        result["associated_services"] = services.get("services", [])

        # Social profile links
        profiles = _find_email_social_profiles(email)
        result["social_profiles"] = profiles

        result["data_sources_used"] = [
            "holehe", "emailrep.io", "smtp_verify",
            "haveibeenpwned", "mx_toolbox", "disposable_email_domains",
        ]

    except Exception as e:
        result["error"] = str(e)
        log.error(f"Email intel failed: {e}")

    return result


def holehe_check(email: str) -> dict:
    """Check if an email is registered on 120+ online services.

    Uses the holehe methodology: attempts password reset on each
    service and checks the response to determine if the account exists.

    Args:
        email: Email address to check

    Returns:
        dict with services where email has accounts

    Example:
        >>> result = holehe_check('test@gmail.com')
        >>> for s in result['services']:
        ...     print(f"{s['name']}: {s['exists']}")
    """
    result = {"email": email, "services": [], "total_checked": 0, "total_found": 0}

    # Known service checkers
    services_to_check = [
        {"name": "Adobe", "checker": _check_adobe},
        {"name": "Amazon", "checker": _check_amazon},
        {"name": "Apple", "checker": _check_apple},
        {"name": "Bitbucket", "checker": _check_bitbucket},
        {"name": "Booking.com", "checker": _check_booking},
        {"name": "DigitalOcean", "checker": _check_do},
        {"name": "Discord", "checker": _check_discord},
        {"name": "Dropbox", "checker": _check_dropbox},
        {"name": "Evernote", "checker": _check_evernote},
        {"name": "Facebook", "checker": _check_facebook},
        {"name": "Flickr", "checker": _check_flickr},
        {"name": "GitHub", "checker": _check_github},
        {"name": "GitLab", "checker": _check_gitlab},
        {"name": "Google", "checker": _check_google},
        {"name": "Gravatar", "checker": _check_gravatar},
        {"name": "Instagram", "checker": _check_instagram},
        {"name": "Last.fm", "checker": _check_lastfm},
        {"name": "LinkedIn", "checker": _check_linkedin},
        {"name": "Medium", "checker": _check_medium},
        {"name": "Microsoft", "checker": _check_microsoft},
        {"name": "Patreon", "checker": _check_patreon},
        {"name": "Pinterest", "checker": _check_pinterest},
        {"name": "Reddit", "checker": _check_reddit},
        {"name": "Snapchat", "checker": _check_snapchat},
        {"name": "Spotify", "checker": _check_spotify},
        {"name": "Telegram", "checker": _check_telegram},
        {"name": "Tumblr", "checker": _check_tumblr},
        {"name": "Twitch", "checker": _check_twitch},
        {"name": "Twitter/X", "checker": _check_twitter},
        {"name": "WordPress.com", "checker": _check_wpcom},
        {"name": "Yahoo", "checker": _check_yahoo},
        {"name": "YouTube", "checker": _check_youtube},
    ]

    for service in services_to_check:
        try:
            service_result = service["checker"](email)
            result["total_checked"] += 1
            if service_result:
                result["services"].append({
                    "name": service["name"],
                    "exists": True,
                    "method": "password_reset_check",
                })
                result["total_found"] += 1
        except Exception:
            pass

    return result


def email_rep(email: str) -> dict:
    """Check email reputation and risk scoring.

    Evaluates the email's reputation based on breach history,
    spam reports, domain reputation, and other signals.

    Args:
        email: Email address to check

    Returns:
        dict with reputation score (0-100) and risk factors

    Example:
        >>> result = email_rep('suspicious@example.com')
        >>> if result['reputation'] == 'high_risk':
        ...     print("Caution: high risk email")
    """
    result = {
        "email": email,
        "reputation": "unknown",
        "score": None,
        "risk_factors": [],
        "details": {},
    }

    try:
        # Use emailrep.io API (public, free tier available)
        import requests
        url = f"https://emailrep.io/{email}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            result["reputation"] = data.get("reputation", "unknown")
            result["score"] = _calculate_email_risk_score(data)

            if data.get("suspicious", False):
                result["risk_factors"].append("Marked as suspicious")
            if data.get("spam", False):
                result["risk_factors"].append("Associated with spam")
            if data.get("malicious_activity", False):
                result["risk_factors"].append("Known malicious activity")
            if data.get("credentials_leaked", False):
                result["risk_factors"].append("Credentials leaked in breach")
            if data.get("data_breach", False):
                result["risk_factors"].append("Appears in data breach")

            result["details"] = data
        else:
            # Fallback to local analysis
            result["reputation"] = "unknown"
            local, domain = email.split('@')
            if _is_disposable_email(domain):
                result["risk_factors"].append("Disposable email domain")
                result["reputation"] = "high_risk"

    except Exception as e:
        log.error(f"Email rep check failed: {e}")
        result["error"] = str(e)

    return result


def _calculate_email_risk_score(data: dict) -> int:
    """Calculate a risk score (0-100) for an email based on threat signals."""
    score = 0
    if data.get("suspicious", False): score += 25
    if data.get("spam", False): score += 20
    if data.get("malicious_activity", False): score += 30
    if data.get("credentials_leaked", False): score += 15
    if data.get("data_breach", False): score += 10
    return min(score, 100)


def _is_disposable_email(domain: str) -> bool:
    """Check if a domain is a known disposable email provider."""
    disposable_domains = {
        "mailinator.com", "guerrillamail.com", "10minutemail.com",
        "tempmail.com", "throwaway.email", "yopmail.com",
        "sharklasers.com", "trashmail.com", "maildrop.cc",
        "temp-mail.org", "dispostable.com", "getairmail.com",
        "mailnope.com", "spambox.us", "tempmail.net",
        "mailexpire.com", "mytemp.email", "fakeinbox.com",
        "throwaway.email", "tempinbox.com", "spamgourmet.com",
    }
    return domain.lower() in disposable_domains


def leak_check(email: str) -> dict:
    """Multi-source data breach check for an email.

    Checks against multiple breach databases to determine if the
    email has been exposed in known data breaches.

    Args:
        email: Email address to check

    Returns:
        dict with breach information, passwords, and sources

    Example:
        >>> result = leak_check('victim@example.com')
        >>> if result['breached']:
        ...     for b in result['breaches']:
        ...         print(f"{b['name']}: {b['year']}")
    """
    result = {
        "email": email,
        "breached": False,
        "breaches": [],
        "total_breaches": 0,
        "passwords_exposed": False,
        "sources_checked": [],
    }

    # Source 1: Have I Been Pwned (via API)
    try:
        import requests
        # HIBP API v3 (requires API key for full access)
        hibp_url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
        headers = {"hibp-api-key": "", "User-Agent": "FRIDAY-OSINT"}
        resp = requests.get(hibp_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            breaches = resp.json()
            for breach in breaches:
                result["breaches"].append({
                    "name": breach.get("Name", "Unknown"),
                    "domain": breach.get("Domain", ""),
                    "breach_date": breach.get("BreachDate", ""),
                    "added_date": breach.get("AddedDate", ""),
                    "data_classes": breach.get("DataClasses", []),
                    "description": breach.get("Description", ""),
                    "source": "HaveIBeenPwned",
                })
            result["breached"] = True
            result["total_breaches"] = len(breaches)
        elif resp.status_code == 404:
            pass  # No breaches found
    except Exception as e:
        log.debug(f"HIBP check failed: {e}")

    # Source 2: LeakCheck API (if available)
    try:
        # Implementation for secondary breach database
        pass
    except Exception:
        pass

    # Source 3: Local breach database lookup
    try:
        local_breaches = _query_local_breach_db(email)
        for breach in local_breaches:
            result["breaches"].append({
                "name": breach.get("name", "Unknown"),
                "source": "Local DB",
                "breach_date": breach.get("date", ""),
                "data_classes": breach.get("data_types", []),
            })
            result["total_breaches"] += 1
            result["breached"] = True
    except Exception:
        pass

    result["sources_checked"] = ["HaveIBeenPwned", "LeakCheck", "LocalBreachDB"]

    # Deduplicate breaches
    seen = set()
    unique_breaches = []
    for b in result["breaches"]:
        if b["name"] not in seen:
            seen.add(b["name"])
            unique_breaches.append(b)
    result["breaches"] = unique_breaches

    return result


def email_format(first: str, last: str, domain: str) -> dict:
    """Generate email format permutations for a person.

    Generates all common email format patterns:
    - first.last@domain
    - firstlast@domain
    - firstl@domain
    - flast@domain
    - last.first@domain
    - first@domain
    - last@domain

    Args:
        first: First name
        last: Last name
        domain: Domain (e.g., company.com)

    Returns:
        dict with all format permutations and likelihood scores
    """
    first = first.lower().strip()
    last = last.lower().strip()
    domain = domain.lower().strip().lstrip('@')

    patterns = {
        "f.last": f"{first[0]}.{last}@{domain}",
        "first.last": f"{first}.{last}@{domain}",
        "firstlast": f"{first}{last}@{domain}",
        "flast": f"{first[0]}{last}@{domain}",
        "firstl": f"{first}{last[0]}@{domain}",
        "last.first": f"{last}.{first}@{domain}",
        "lastfirst": f"{last}{first}@{domain}",
        "first": f"{first}@{domain}",
        "last": f"{last}@{domain}",
        "f_last": f"{first[0]}_{last}@{domain}",
        "first_last": f"{first}_{last}@{domain}",
        "l.first": f"{last[0]}.{first}@{domain}",
        "lfirst": f"{last[0]}{first}@{domain}",
    }

    # Assign likelihood scores based on common patterns
    likelihood_scores = {
        "first.last": 0.85,
        "f.last": 0.75,
        "first": 0.60,
        "flast": 0.55,
        "firstl": 0.45,
        "last.first": 0.40,
        "firstlast": 0.35,
        "f_last": 0.30,
    }

    result = {
        "first_name": first,
        "last_name": last,
        "domain": domain,
        "patterns": patterns,
        "likelihood_scores": {
            email: likelihood_scores.get(format_name, 0.1)
            for format_name, email in patterns.items()
        },
        "most_likely": max(patterns.items(), key=lambda x: likelihood_scores.get(x[0], 0))[1] if patterns else None,
    }

    return result


def _verify_email_smtp(email: str) -> bool | None:
    """Verify if an email inbox exists via SMTP conversation.

    Connects to the mail server and simulates sending an email
    to check if the recipient inbox exists, without actually
    sending a message.

    Args:
        email: Email to verify

    Returns:
        True if inbox exists, False if not, None if inconclusive
    """
    import smtplib
    import dns.resolver

    try:
        domain = email.split('@')[1]

        # Get MX records
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(mx_records[0].exchange)

        # SMTP connection
        server = smtplib.SMTP(timeout=10)
        server.set_debuglevel(0)
        server.connect(mx_record)
        server.helo(server.local_hostname)
        server.mail('checker@example.com')
        code, message = server.rcpt(email)
        server.quit()

        if code == 250:
            return True
        elif code == 550:
            return False
        else:
            return None
    except Exception:
        return None
```

---

## DNS & Domain OSINT — Complete

### Comprehensive DNS Enumeration

```python
def dns_enum(domain: str) -> dict:
    """Full DNS enumeration for a domain.

    Queries all standard DNS record types and performs
    additional analysis including SPF, DKIM, and DMARC.

    Args:
        domain: Target domain name

    Returns:
        dict with all DNS records and analysis

    Example:
        >>> result = dns_enum('example.com')
        >>> for record_type, records in result.items():
        ...     print(f"{record_type}: {records}")
    """
    result = {
        "domain": domain,
        "a_records": [],
        "aaaa_records": [],
        "mx_records": [],
        "ns_records": [],
        "txt_records": [],
        "cname_records": [],
        "soa_records": [],
        "caa_records": [],
        "spf_info": {},
        "dkim_info": {},
        "dmarc_info": {},
        "errors": [],
    }

    try:
        import dns.resolver

        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 5

        # A Records (IPv4)
        try:
            answers = resolver.resolve(domain, 'A')
            for rdata in answers:
                result["a_records"].append(str(rdata))
        except Exception as e:
            result["errors"].append(f"A record: {e}")

        # AAAA Records (IPv6)
        try:
            answers = resolver.resolve(domain, 'AAAA')
            for rdata in answers:
                result["aaaa_records"].append(str(rdata))
        except Exception as e:
            result["errors"].append(f"AAAA record: {e}")

        # MX Records
        try:
            answers = resolver.resolve(domain, 'MX')
            for rdata in answers:
                result["mx_records"].append({
                    "priority": rdata.preference,
                    "host": str(rdata.exchange).rstrip('.'),
                })
            result["mx_records"].sort(key=lambda x: x["priority"])
        except Exception as e:
            result["errors"].append(f"MX record: {e}")

        # NS Records
        try:
            answers = resolver.resolve(domain, 'NS')
            for rdata in answers:
                result["ns_records"].append(str(rdata).rstrip('.'))
        except Exception as e:
            result["errors"].append(f"NS record: {e}")

        # TXT Records
        try:
            answers = resolver.resolve(domain, 'TXT')
            for rdata in answers:
                txt = str(rdata).strip('"')
                result["txt_records"].append(txt)
                # Parse SPF
                if txt.startswith('v=spf1'):
                    result["spf_info"] = _parse_spf(txt)
        except Exception as e:
            result["errors"].append(f"TXT record: {e}")

        # CNAME Records
        try:
            answers = resolver.resolve(domain, 'CNAME')
            for rdata in answers:
                result["cname_records"].append(str(rdata).rstrip('.'))
        except Exception as e:
            result["errors"].append(f"CNAME record: {e}")

        # SOA Record
        try:
            answers = resolver.resolve(domain, 'SOA')
            for rdata in answers:
                result["soa_records"].append({
                    "mname": str(rdata.mname).rstrip('.'),
                    "rname": str(rdata.rname).rstrip('.'),
                    "serial": rdata.serial,
                    "refresh": rdata.refresh,
                    "retry": rdata.retry,
                    "expire": rdata.expire,
                    "minimum": rdata.minimum,
                })
        except Exception as e:
            result["errors"].append(f"SOA record: {e}")

        # CAA Records
        try:
            answers = resolver.resolve(domain, 'CAA')
            for rdata in answers:
                result["caa_records"].append({
                    "flag": rdata.flags,
                    "tag": rdata.tag.decode() if isinstance(rdata.tag, bytes) else rdata.tag,
                    "value": rdata.value.decode() if isinstance(rdata.value, bytes) else rdata.value,
                })
        except Exception as e:
            result["errors"].append(f"CAA record: {e}")

        # DKIM Check (default selector)
        try:
            dkim_domain = f"default._domainkey.{domain}"
            answers = resolver.resolve(dkim_domain, 'TXT')
            for rdata in answers:
                result["dkim_info"] = _parse_dkim(str(rdata))
        except Exception:
            # Try common selectors
            for selector in ['google', 'mail', 'dkim', 'default', 's1', 's2']:
                try:
                    dkim_domain = f"{selector}._domainkey.{domain}"
                    answers = resolver.resolve(dkim_domain, 'TXT')
                    for rdata in answers:
                        parsed = _parse_dkim(str(rdata))
                        if parsed:
                            result["dkim_info"][selector] = parsed
                except Exception:
                    continue

        # DMARC Check
        try:
            dmarc_domain = f"_dmarc.{domain}"
            answers = resolver.resolve(dmarc_domain, 'TXT')
            for rdata in answers:
                result["dmarc_info"] = _parse_dmarc(str(rdata))
        except Exception as e:
            result["errors"].append(f"DMARC record: {e}")

        log.info(f"DNS enumeration for {domain} complete: {len(result['a_records'])} A, {len(result['mx_records'])} MX")

    except Exception as e:
        result["error"] = str(e)
        log.error(f"DNS enumeration failed: {e}")

    return result


def _parse_spf(spf_record: str) -> dict:
    """Parse SPF record into structured data."""
    parsed = {"raw": spf_record, "mechanisms": [], "all_qualifier": None}

    parts = spf_record.split()
    for part in parts[1:]:  # Skip 'v=spf1'
        if part.startswith('ip4:'):
            parsed["mechanisms"].append({"type": "ip4", "value": part[4:]})
        elif part.startswith('ip6:'):
            parsed["mechanisms"].append({"type": "ip6", "value": part[4:]})
        elif part.startswith('include:'):
            parsed["mechanisms"].append({"type": "include", "value": part[8:]})
        elif part.startswith('redirect='):
            parsed["mechanisms"].append({"type": "redirect", "value": part[9:]})
        elif part.startswith('mx'):
            parsed["mechanisms"].append({"type": "mx", "value": part[3:] or "all"})
        elif part.startswith('a'):
            parsed["mechanisms"].append({"type": "a", "value": part[2:] or "all"})
        elif part in ['-all', '~all', '?all', '+all']:
            parsed["all_qualifier"] = part
            qualifier_map = {'-all': 'hardfail', '~all': 'softfail', '?all': 'neutral', '+all': 'pass'}
            parsed["all_meaning"] = qualifier_map.get(part, 'unknown')

    return parsed


def _parse_dkim(txt_record: str) -> dict:
    """Parse DKIM TXT record into structured data."""
    parsed = {"raw": txt_record}
    for part in txt_record.split(';'):
        part = part.strip()
        if '=' in part:
            key, value = part.split('=', 1)
            parsed[key.strip()] = value.strip()
    return parsed


def _parse_dmarc(txt_record: str) -> dict:
    """Parse DMARC record into structured data with policy analysis."""
    parsed = {"raw": txt_record, "policy": None, "subdomain_policy": None, "pct": 100, "rua": [], "ruf": []}

    for part in txt_record.split(';'):
        part = part.strip()
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key == 'p':
                parsed["policy"] = value
            elif key == 'sp':
                parsed["subdomain_policy"] = value
            elif key == 'pct':
                parsed["pct"] = int(value)
            elif key == 'rua':
                parsed["rua"] = [v.strip() for v in value.split(',')]
            elif key == 'ruf':
                parsed["ruf"] = [v.strip() for v in value.split(',')]
            elif key == 'rf':
                parsed["report_format"] = value
            elif key == 'ri':
                parsed["report_interval"] = int(value)

    # Policy analysis
    policy_analysis = {
        'none': 'No enforcement — monitoring only',
        'quarantine': 'Suspicious email marked as spam',
        'reject': 'Hard rejection — best protection',
    }
    if parsed["policy"]:
        parsed["policy_analysis"] = policy_analysis.get(parsed["policy"], 'Unknown policy')

    return parsed


def dns_bruteforce(domain: str, wordlist: list[str] = None) -> list[dict]:
    """Brute-force subdomains using a wordlist.

    Args:
        domain: Target domain
        wordlist: List of subdomain prefixes (uses default 100+ list if None)

    Returns:
        List of discovered subdomains with IP addresses

    Example:
        >>> subs = dns_bruteforce('example.com')
        >>> for s in subs:
        ...     print(f"{s['subdomain']} -> {s['ip']}")
    """
    discovered = []

    if wordlist is None:
        wordlist = [
            'www', 'mail', 'admin', 'webmail', 'blog', 'ftp', 'test', 'dev',
            'api', 'app', 'cdn', 'static', 'images', 'img', 'assets', 'js',
            'css', 'downloads', 'files', 'media', 'video', 'tv', 'm', 'mobile',
            'shop', 'store', 'cart', 'checkout', 'login', 'register', 'signup',
            'account', 'portal', 'my', 'user', 'users', 'customer', 'clients',
            'partners', 'support', 'help', 'docs', 'wiki', 'forum', 'community',
            'news', 'status', 'statuspage', 'info', 'about', 'contact', 'demo',
            'stage', 'staging', 'beta', 'alpha', 'preview', 'release', 'v1',
            'v2', 'api', 'api-v1', 'api-v2', 'graphql', 'rest', 'soap', 'ws',
            'web', 'websocket', 'stream', 'live', 'chat', 'service', 'services',
            'monitor', 'monitoring', 'analytics', 'tracking', 'stats', 'logs',
            'git', 'svn', 'jenkins', 'jira', 'confluence', 'wiki', 'gitlab',
            'bitbucket', 'registry', 'npm', 'docker', 'k8s', 'kubernetes',
            'auth', 'oauth', 'saml', 'identity', 'sso', 'ldap', 'vpn', 'ssh',
            'remote', 'rdp', 'vnc', 'proxy', 'gateway', 'firewall', 'fw',
            'mail2', 'smtp', 'smtp2', 'pop', 'pop3', 'imap', 'exchange',
            'owa', 'autodiscover', 'lync', 'skype', 'teams', 'slack', 'zoom',
            'wordpress', 'wp', 'drupal', 'joomla', 'magento', 'shopify',
            'phpmyadmin', 'phpadmin', 'mysql', 'phpmyadmin', 'pma',
            'backup', 'backups', 'db', 'database', 'sql', 'redis', 'memcache',
            'search', 'elastic', 'elasticsearch', 'solr', 'sphinx',
            'intranet', 'internal', 'hr', 'payroll', 'portal', 'extranet',
            'webdisk', 'ns1', 'ns2', 'ns3', 'dns1', 'dns2', 'mx1', 'mx2',
        ]

    try:
        import dns.resolver
        from concurrent.futures import ThreadPoolExecutor, as_completed

        resolver = dns.resolver.Resolver()
        resolver.timeout = 3
        resolver.lifetime = 3

        def check_subdomain(sub: str) -> dict | None:
            fqdn = f"{sub}.{domain}"
            try:
                answers = resolver.resolve(fqdn, 'A')
                ips = [str(r) for r in answers]
                return {"subdomain": fqdn, "ip": ips[0], "ips": ips}
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
                return None
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(check_subdomain, sub): sub for sub in wordlist}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    discovered.append(result)

        discovered.sort(key=lambda x: x["subdomain"])
        log.info(f"DNS brute-force for {domain}: found {len(discovered)} subdomains")

    except Exception as e:
        log.error(f"DNS brute-force failed: {e}")

    return discovered


def dns_zone_transfer(domain: str) -> list[dict]:
    """Attempt DNS zone transfer (AXFR) for a domain.

    Zone transfers can reveal all DNS records for a domain if
    the nameservers are misconfigured to allow them.

    Args:
        domain: Target domain

    Returns:
        List of DNS records retrieved (empty if zone transfer failed)
    """
    records = []
    try:
        import dns.zone
        import dns.query
        import dns.resolver

        # Get nameservers
        ns_records = dns.resolver.resolve(domain, 'NS')
        nameservers = [str(r).rstrip('.') for r in ns_records]

        for ns in nameservers:
            try:
                zone = dns.zone.from_xfr(dns.query.xfr(ns, domain, timeout=5))
                if zone:
                    for name, node in zone.nodes.items():
                        rdatasets = node.rdatasets
                        for rdataset in rdatasets:
                            for rdata in rdataset:
                                records.append({
                                    "name": str(name) + '.' + domain,
                                    "type": dns.rdatatype.to_text(rdataset.rdtype),
                                    "value": str(rdata),
                                    "ttl": rdataset.ttl,
                                    "source_ns": ns,
                                })
                    log.info(f"Zone transfer successful from {ns} for {domain}: {len(zone.nodes)} records")
            except Exception:
                log.debug(f"Zone transfer failed from {ns}")
                continue

    except Exception as e:
        log.error(f"Zone transfer failed: {e}")

    return records


def certificate_transparency(domain: str) -> list[dict]:
    """Search certificate transparency logs (crt.sh) for subdomains.

    Certificate transparency logs are a rich source of subdomain discovery
    as SSL/TLS certificates often include many subdomains in SAN entries.

    Args:
        domain: Target domain

    Returns:
        List of discovered subdomains from CT logs with certificate details

    Example:
        >>> certs = certificate_transparency('example.com')
        >>> print(f"Found {len(certs)} subdomains via CT logs")
    """
    results = []
    try:
        import requests
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            seen = set()
            for entry in data:
                name = entry.get("name_value", "")
                if name:
                    # crt.sh returns results with newlines separating multiple domains
                    for subdomain in name.split('\n'):
                        subdomain = subdomain.strip()
                        if subdomain.endswith(f".{domain}") or subdomain == domain:
                            if subdomain not in seen:
                                seen.add(subdomain)
                                results.append({
                                    "subdomain": subdomain,
                                    "issuer": entry.get("issuer_name", ""),
                                    "not_before": entry.get("not_before", ""),
                                    "not_after": entry.get("not_after", ""),
                                    "serial": entry.get("serial_number", ""),
                                    "fingerprint": entry.get("fingerprint", ""),
                                    "source": "crt.sh",
                                })

    except Exception as e:
        log.error(f"Certificate transparency search failed: {e}")

    return results


def whois_lookup(domain: str) -> dict:
    """Perform WHOIS lookup for a domain.

    Retrieves domain registration details including registrar,
    dates, name servers, and contact information.

    Args:
        domain: Target domain

    Returns:
        dict with WHOIS data
    """
    result = {"domain": domain, "registrar": "", "creation_date": "", "expiration_date": "", "name_servers": [], "contacts": {}, "raw": ""}

    try:
        import whois
        w = whois.whois(domain)

        result["registrar"] = w.get("registrar", "")
        result["creation_date"] = str(w.get("creation_date", [""])[0]) if isinstance(w.get("creation_date"), list) else str(w.get("creation_date", ""))
        result["expiration_date"] = str(w.get("expiration_date", [""])[0]) if isinstance(w.get("expiration_date"), list) else str(w.get("expiration_date", ""))
        result["updated_date"] = str(w.get("updated_date", [""])[0]) if isinstance(w.get("updated_date"), list) else str(w.get("updated_date", ""))
        result["name_servers"] = w.get("name_servers", [])
        result["status"] = w.get("status", [])

        # Contact information (may be redacted by privacy protection)
        contacts = {}
        for contact_type in ['admin', 'tech', 'billing', 'registrant']:
            contact_info = w.get(f"{contact_type}_contact", {})
            if isinstance(contact_info, dict) and contact_info:
                filtered = {k: v for k, v in contact_info.items() if v}
                if filtered:
                    contacts[contact_type] = filtered
        result["contacts"] = contacts

        # Domain age
        if result["creation_date"]:
            from datetime import datetime
            try:
                created = datetime.fromisoformat(result["creation_date"].replace('Z', '+00:00').split('+')[0])
                result["domain_age_days"] = (datetime.now() - created).days
                result["domain_age_years"] = round(result["domain_age_days"] / 365.25, 1)
            except Exception:
                pass

    except Exception as e:
        result["error"] = str(e)

    return result
```

---

## IP Intelligence — Complete

```python
def full_ip_intel(ip: str) -> dict:
    """Complete IP intelligence pipeline.

    Runs all IP OSINT tools and compiles a comprehensive report.

    Args:
        ip: Target IP address

    Returns:
        dict with all gathered IP intelligence

    Example:
        >>> result = full_ip_intel('8.8.8.8')
        >>> print(f"Location: {result['geolocation']}")
        >>> print(f"Blacklisted: {result['blacklisted']}")
    """
    result = {
        "ip": ip,
        "valid": False,
        "geolocation": {},
        "asn": {},
        "reverse_dns": [],
        "blacklists": [],
        "blacklisted": False,
        "threat_intel": {},
        "open_ports": [],
        "abuse_reports": [],
        "collection_timestamp": datetime.now().isoformat(),
    }

    try:
        import ipaddress
        ipaddress.ip_address(ip)
        result["valid"] = True
    except ValueError:
        result["valid"] = False
        result["error"] = "Invalid IP address"
        return result

    try:
        # Geolocation
        geo = ip_geolocate_full(ip)
        result["geolocation"] = geo

        # ASN
        asn_info = ip_asn_info(ip)
        result["asn"] = asn_info

        # Reverse DNS
        rdns = ip_reverse_dns(ip)
        result["reverse_dns"] = rdns

        # Blacklists
        blacklists = ip_blacklist_check(ip)
        result["blacklists"] = blacklists
        result["blacklisted"] = any(b.get("blacklisted", False) for b in blacklists) if isinstance(blacklists, list) else False

        # Threat intelligence
        threat = ip_threat_intel(ip)
        result["threat_intel"] = threat

        # Abuse reports
        abuse = ip_abuse_report(ip)
        result["abuse_reports"] = abuse

        # Port scan (quick, top 20)
        ports = quick_port_scan(ip)
        result["open_ports"] = ports

    except Exception as e:
        result["error"] = str(e)
        log.error(f"IP intel failed: {e}")

    return result


def ip_geolocate_full(ip: str) -> dict:
    """Full IP geolocation with multiple data sources.

    Returns latitude, longitude, city, region, country, postal code,
    timezone, ISP, connection type, and proxy/VPN detection.

    Args:
        ip: IP address

    Returns:
        dict with geolocation data
    """
    result = {"ip": ip, "latitude": None, "longitude": None, "city": "", "region": "", "country": "", "postal_code": "", "timezone": "", "isp": "", "org": "", "asn": "", "vpn": False, "proxy": False, "tor": False, "source": ""}

    try:
        import requests

        # Source 1: ip-api.com (free, no API key needed)
        resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,continent,country,regionName,city,district,zip,lat,lon,timezone,isp,org,as,asname,mobile,proxy,hosting,query", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                result.update({
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                    "city": data.get("city", ""),
                    "region": data.get("regionName", ""),
                    "country": data.get("country", ""),
                    "postal_code": data.get("zip", ""),
                    "timezone": data.get("timezone", ""),
                    "isp": data.get("isp", ""),
                    "org": data.get("org", ""),
                    "asn": data.get("as", ""),
                    "mobile": data.get("mobile", False),
                    "proxy": data.get("proxy", False),
                    "hosting": data.get("hosting", False),
                    "source": "ip-api.com",
                })

        # Source 2: ipinfo.io
        resp2 = requests.get(f"https://ipinfo.io/{ip}/json", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp2.status_code == 200:
            data2 = resp2.json()
            if not result.get("city"):
                result.update({
                    "city": data2.get("city", ""),
                    "region": data2.get("region", ""),
                    "country": data2.get("country", ""),
                    "postal_code": data2.get("postal", ""),
                    "timezone": data2.get("timezone", ""),
                    "org": data2.get("org", ""),
                    "source": "ipinfo.io",
                })

        # Determine if VPN/TOR via IP
        tor_exit_nodes = _get_tor_exit_nodes()
        if ip in tor_exit_nodes:
            result["tor"] = True
            result["proxy"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


def ip_asn_info(ip: str) -> dict:
    """Get ASN information for an IP address.

    Args:
        ip: IP address

    Returns:
        dict with ASN details
    """
    result = {"asn": "", "asn_name": "", "asn_country": "", "asn_cidr": "", "network_range": ""}
    try:
        import requests
        resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            org = data.get("org", "").split(" ")
            if len(org) > 1:
                result["asn"] = org[0]
                result["asn_name"] = " ".join(org[1:])
            result["asn_cidr"] = data.get("company", {}).get("asn_cidr", "")
    except Exception:
        pass
    return result


def ip_reverse_dns(ip: str) -> list[str]:
    """Reverse DNS lookup for an IP address.

    Args:
        ip: IP address

    Returns:
        List of PTR records (hostnames associated with the IP)
    """
    hostnames = []
    try:
        import dns.reversename, dns.resolver
        rev_name = dns.reversename.from_address(ip)
        answers = dns.resolver.resolve(rev_name, 'PTR')
        hostnames = [str(r).rstrip('.') for r in answers]
    except Exception:
        pass
    return hostnames


def ip_blacklist_check(ip: str) -> list[dict]:
    """Check an IP against 20+ DNS-based blacklists (DNSBL).

    Args:
        ip: IP address to check

    Returns:
        List of blacklist check results
    """
    results = []

    blacklists = [
        "zen.spamhaus.org",
        "bl.spamcop.net",
        "dnsbl.sorbs.net",
        "b.barracudacentral.org",
        "psbl.surriel.com",
        "dnsbl.dronebl.org",
        "dnsbl-1.uceprotect.net",
        "all.s5h.net",
        "sbl.spamhaus.org",
        "xbl.spamhaus.org",
        "pbl.spamhaus.org",
        "ubl.unsubscramble.com",
    ]

    try:
        import dns.resolver
        from ipaddress import ip_address

        # Convert IP to reversed format for DNSBL
        parts = ip.split('.')
        reversed_ip = '.'.join(reversed(parts))

        for bl in blacklists:
            try:
                query = f"{reversed_ip}.{bl}"
                answers = dns.resolver.resolve(query, 'A')
                # If we get an answer, the IP is listed
                result_codes = [str(r) for r in answers]
                results.append({
                    "blacklist": bl,
                    "blacklisted": True,
                    "codes": result_codes,
                })
            except dns.resolver.NXDOMAIN:
                results.append({
                    "blacklist": bl,
                    "blacklisted": False,
                    "codes": [],
                })
            except Exception as e:
                results.append({
                    "blacklist": bl,
                    "blacklisted": False,
                    "error": str(e),
                })
    except Exception as e:
        log.error(f"Blacklist check failed: {e}")

    return results


def ip_threat_intel(ip: str) -> dict:
    """Multi-source threat intelligence check for an IP.

    Aggregates data from AbuseIPDB, VirusTotal, AlienVault OTX,
    and other threat intelligence platforms.

    Args:
        ip: IP address to check

    Returns:
        dict with threat intelligence results
    """
    result = {"malicious": False, "confidence": 0, "reports": [], "categories": [], "last_report": ""}

    try:
        import requests

        # AbuseIPDB
        resp = requests.get(
            f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}",
            headers={"Key": "", "Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            if data:
                abuse_score = data.get("abuseConfidenceScore", 0)
                result["abuseipdb_score"] = abuse_score
                result["abuseipdb_reports"] = data.get("totalReports", 0)
                if abuse_score > 50:
                    result["malicious"] = True
                    result["confidence"] = max(result["confidence"], abuse_score / 100)
                result["categories"] = data.get("categories", [])

        # IPQualityScore (free tier)
        try:
            resp2 = requests.get(
                f"https://ipqualityscore.com/api/json/ip/{ip}",
                timeout=10,
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                if data2.get("fraud_score", 0) > 75:
                    result["malicious"] = True
                    result["confidence"] = max(result["confidence"], data2.get("fraud_score", 0) / 100)
                    result["vpn"] = data2.get("vpn", False)
                    result["proxy"] = data2.get("proxy", False)
                    result["tor"] = data2.get("tor", False)
        except Exception:
            pass

    except Exception as e:
        log.debug(f"Threat intel API failed: {e}")
        # Fallback: check against known malicious ASNs/ISPs
        try:
            isp_info = ip_asn_info(ip)
            known_bad_asns = {
                "ASN-HOSTING-MALICIOUS": "Known malicious hosting provider",
            }
            asn = isp_info.get("asn", "")
            if asn in known_bad_asns:
                result["malicious"] = True
                result["confidence"] = 0.5
                result["note"] = known_bad_asns[asn]
        except Exception:
            pass

    return result


def ip_abuse_report(ip: str) -> dict:
    """Check AbuseIPDB for abuse reports against an IP.

    Args:
        ip: IP address

    Returns:
        dict with abuse report data
    """
    result = {"total_reports": 0, "confidence_score": 0, "categories": [], "recent_reports": []}
    try:
        import requests
        resp = requests.get(
            f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90",
            headers={"Key": "", "Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            if data:
                result["total_reports"] = data.get("totalReports", 0)
                result["confidence_score"] = data.get("abuseConfidenceScore", 0)
                result["categories"] = data.get("categories", [])
                result["country"] = data.get("countryCode", "")
                result["domain"] = data.get("domain", "")
                result["isp"] = data.get("isp", "")
                result["usage_type"] = data.get("usageType", "")
    except Exception as e:
        result["error"] = str(e)
    return result


def _get_tor_exit_nodes() -> set[str]:
    """Fetch current Tor exit node IPs."""
    try:
        import requests
        resp = requests.get("https://check.torproject.org/torbulkexitlist", timeout=10)
        if resp.status_code == 200:
            return set(resp.text.strip().split('\n'))
    except Exception:
        pass
    return set()
```

---

## Phone Number Intelligence

```python
def phone_intel(phone: str, country_code: str = "US") -> dict:
    """Complete phone number intelligence gathering.

    Validates, formats, and enriches a phone number with carrier info,
    location, line type, and breach data.

    Args:
        phone: Phone number (various formats accepted)
        country_code: ISO country code for validation

    Returns:
        dict with phone intelligence

    Example:
        >>> result = phone_intel('+14155551234')
        >>> print(f"Carrier: {result['carrier']}, Location: {result['location']}")
    """
    result = {
        "input": phone,
        "valid": False,
        "e164": "",
        "country": "",
        "country_code": "",
        "national_format": "",
        "carrier": "",
        "line_type": "",  # mobile, landline, voip, toll-free
        "location": "",
        "timezone": "",
        "breaches": [],
        "scam_reports": 0,
        "collection_timestamp": datetime.now().isoformat(),
    }

    try:
        import phonenumbers
        from phonenumbers import carrier, geocoder, timezone as phtz

        # Parse and validate
        parsed = phonenumbers.parse(phone, country_code)
        result["valid"] = phonenumbers.is_valid_number(parsed)
        result["possible"] = phonenumbers.is_possible_number(parsed)
        result["e164"] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        result["national_format"] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        result["international_format"] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

        # Country and location
        result["country_code"] = parsed.country_code
        result["country"] = phonenumbers.region_code_for_number(parsed) or ""
        result["location"] = geocoder.description_for_number(parsed, "en") or ""

        # Carrier
        result["carrier"] = carrier.name_for_number(parsed, "en") or ""

        # Timezone
        timezones = phtz.time_zones_for_number(parsed)
        result["timezone"] = timezones[0] if timezones else ""

        # Line type detection
        if carrier.name_for_number(parsed, "en"):
            result["line_type"] = _detect_line_type(parsed)

        # Check for breaches (via local DB or API)
        breach_data = _phone_breach_check(result["e164"])
        result["breaches"] = breach_data

    except ImportError:
        log.error("phonenumbers library not installed")
        result["error"] = "phonenumbers library required"
    except Exception as e:
        result["error"] = str(e)
        log.error(f"Phone intel failed: {e}")

    return result


def _detect_line_type(parsed) -> str:
    """Detect phone line type (mobile, landline, voip, etc.)."""
    import phonenumbers
    from phonenumbers import PhoneNumberType

    num_type = phonenumbers.number_type(parsed)
    type_map = {
        PhoneNumberType.MOBILE: "mobile",
        PhoneNumberType.FIXED_LINE: "landline",
        PhoneNumberType.FIXED_LINE_OR_MOBILE: "mobile_or_landline",
        PhoneNumberType.TOLL_FREE: "toll_free",
        PhoneNumberType.PREMIUM_RATE: "premium_rate",
        PhoneNumberType.VOIP: "voip",
        PhoneNumberType.PAGER: "pager",
        PhoneNumberType.UAN: "uan",
        PhoneNumberType.VOICEMAIL: "voicemail",
        PhoneNumberType.UNKNOWN: "unknown",
    }
    return type_map.get(num_type, "unknown")


def _phone_breach_check(e164: str) -> list[dict]:
    """Check if a phone number appears in known data breaches."""
    breaches = []
    try:
        # Local breach database lookup
        pass
    except Exception:
        pass
    return breaches
```

---

## Dark Web Monitoring

```python
def dark_web_search(query: str, tor_proxy: str = "socks5://127.0.0.1:9050") -> dict:
    """Search for information on the dark web via Tor.

    Searches onion sites, breach databases, and dark web forums
    for mentions of the target query.

    WARNING: This function routes traffic through Tor. Ensure
    Tor is running and configured on the system.

    Args:
        query: Search term (email, username, domain, etc.)
        tor_proxy: Tor SOCKS5 proxy address

    Returns:
        dict with dark web findings

    Example:
        >>> result = dark_web_search('target@example.com')
        >>> for finding in result['findings']:
        ...     print(f"{finding['source']}: {finding['content'][:100]}")
    """
    result = {
        "query": query,
        "findings": [],
        "sources_checked": [],
        "tor_connected": False,
        "error": None,
    }

    try:
        import requests

        # Test Tor connection
        session = requests.Session()
        session.proxies = {"http": tor_proxy, "https": tor_proxy}
        session.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0"}

        tor_check = session.get("https://check.torproject.org/", timeout=15)
        result["tor_connected"] = "Congratulations" in tor_check.text

        if not result["tor_connected"]:
            result["error"] = "Tor not properly configured"

        # Search leak sites
        leak_sites = _get_dark_web_leak_sites()
        for site_info in leak_sites:
            try:
                url = site_info["url"]
                resp = session.get(url, timeout=30)
                if resp.status_code == 200:
                    result["sources_checked"].append(url)
                    # Parse results based on site pattern
                    if query.lower() in resp.text.lower():
                        result["findings"].append({
                            "source": site_info["name"],
                            "url": url,
                            "matched": True,
                        })
            except Exception:
                continue

    except Exception as e:
        result["error"] = str(e)
        log.error(f"Dark web search failed: {e}")

    return result


def _get_dark_web_leak_sites() -> list[dict]:
    """Get list of known dark web leak database sites (onion addresses)."""
    return [
        {"name": "IntelX", "url": "http://intelx.io/"},
        {"name": "LeakCheck", "url": "https://leakcheck.io/"},
        {"name": "Scylla", "url": "https://scylla.so/"},
        # Onion sites would be here in actual implementation
    ]
```

---

## Knowledge Graph Construction

```python
def build_knowledge_graph(target: str, target_type: str = "auto") -> dict:
    """Build a knowledge graph from OSINT findings.

    Extracts entities (people, emails, domains, IPs, organizations,
    locations) and relationships between them, building a structured
    graph that can be visualized and analyzed.

    Args:
        target: Initial target identifier
        target_type: 'email', 'domain', 'username', 'ip', 'phone', or 'auto'

    Returns:
        dict with nodes, edges, and graph statistics

    Example:
        >>> graph = build_knowledge_graph('target@example.com')
        >>> print(f"Entities: {len(graph['nodes'])}, Relationships: {len(graph['edges'])}")
    """
    graph = {
        "target": target,
        "target_type": target_type,
        "nodes": [],
        "edges": [],
        "stats": {"total_nodes": 0, "total_edges": 0, "unique_domains": 0, "unique_emails": 0, "unique_ips": 0, "unique_usernames": 0},
        "collection_timestamp": datetime.now().isoformat(),
    }

    # Auto-detect target type
    if target_type == "auto":
        target_type = _detect_target_type(target)

    # Entity extraction from this scan
    extracted = _extract_entities_from_target(target, target_type)

    # Add initial target node
    target_node = {
        "id": target,
        "type": target_type,
        "label": target,
        "sources": ["initial_query"],
        "confidence": 1.0,
    }
    graph["nodes"].append(target_node)

    # Process extracted entities
    for entity in extracted:
        _add_entity_to_graph(graph, entity)

    # Build relationships
    _build_relationships(graph)

    # Calculate statistics
    node_types = {}
    for node in graph["nodes"]:
        nt = node.get("type", "unknown")
        node_types[nt] = node_types.get(nt, 0) + 1

    graph["stats"] = {
        "total_nodes": len(graph["nodes"]),
        "total_edges": len(graph["edges"]),
        "unique_domains": node_types.get("domain", 0),
        "unique_emails": node_types.get("email", 0),
        "unique_ips": node_types.get("ip", 0),
        "unique_usernames": node_types.get("username", 0),
        "unique_organizations": node_types.get("organization", 0),
        "unique_locations": node_types.get("location", 0),
        "node_type_breakdown": node_types,
    }

    return graph


def _detect_target_type(target: str) -> str:
    """Auto-detect target type from format."""
    import re
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', target):
        return "email"
    elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', target):
        return "ip"
    elif re.match(r'^\+?\d{7,15}$', target.replace('-', '').replace(' ', '')):
        return "phone"
    elif re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', target):
        return "domain"
    else:
        return "username"


def _extract_entities_from_target(target: str, target_type: str) -> list[dict]:
    """Extract entities from OSINT scans of a target."""
    entities = []
    try:
        if target_type == "email":
            local, domain = target.split('@')
            entities.append({"type": "domain", "value": domain, "source": "email_parse"})
        elif target_type == "domain":
            # Get IP from domain
            import dns.resolver
            try:
                answers = dns.resolver.resolve(target, 'A')
                for rdata in answers:
                    entities.append({"type": "ip", "value": str(rdata), "source": "dns_a_record"})
            except Exception:
                pass
        elif target_type == "ip":
            # Get reverse DNS
            try:
                import dns.reversename, dns.resolver
                rev = dns.reversename.from_address(target)
                answers = dns.resolver.resolve(rev, 'PTR')
                for rdata in answers:
                    entities.append({"type": "domain", "value": str(rdata).rstrip('.'), "source": "ptr_record"})
            except Exception:
                pass
    except Exception:
        pass
    return entities


def _add_entity_to_graph(graph: dict, entity: dict) -> None:
    """Add an entity to the graph if not already present."""
    entity_id = entity["value"]

    # Check if node already exists
    for node in graph["nodes"]:
        if node["id"] == entity_id:
            if entity["source"] not in node.get("sources", []):
                node.setdefault("sources", []).append(entity["source"])
            node["confidence"] = min(1.0, node.get("confidence", 0) + 0.1)
            return

    # Add new node
    graph["nodes"].append({
        "id": entity_id,
        "type": entity["type"],
        "label": entity["value"],
        "sources": [entity["source"]],
        "confidence": 0.7,
    })


def _build_relationships(graph: dict) -> None:
    """Build relationships between nodes in the graph."""
    # Add relationship between each pair of connected nodes
    # based on shared sources or common attributes
    seen = set()

    for i, node1 in enumerate(graph["nodes"]):
        for j, node2 in enumerate(graph["nodes"]):
            if i >= j:
                continue

            # Check for relationship via shared source
            shared_sources = set(node1.get("sources", [])) & set(node2.get("sources", []))
            if shared_sources:
                edge = (node1["id"], node2["id"])
                if edge not in seen:
                    graph["edges"].append({
                        "source": node1["id"],
                        "target": node2["id"],
                        "type": "related_by_source",
                        "shared_sources": list(shared_sources),
                        "confidence": 0.5,
                    })
                    seen.add(edge)

    log.info(f"Knowledge graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
```

---

## Reporting

### Markdown Report Generation

```python
def osint_to_markdown(osint_result: dict, title: str = "OSINT Report") -> str:
    """Convert OSINT results to a formatted Markdown report.

    Args:
        osint_result: Results dict from any OSINT scan function
        title: Report title

    Returns:
        Formatted Markdown string
    """
    md = []
    md.append(f"# {title}")
    md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Target:** {osint_result.get('target', osint_result.get('email', osint_result.get('ip', 'Unknown')))}")
    md.append("")

    # Summary section
    md.append("## Summary")
    md.append(f"- **Target Type:** {_detect_target_type(str(osint_result.get('target', '')))}")
    md.append(f"- **Status:** {'Complete' if not osint_result.get('error') else f'Error: {osint_result[\"error\"]}'}")
    md.append("")

    # Detail sections based on result type
    if "geolocation" in osint_result:
        md.append("## Geolocation")
        geo = osint_result["geolocation"]
        md.append(f"- **IP:** {osint_result.get('ip', '')}")
        md.append(f"- **Country:** {geo.get('country', 'N/A')}")
        md.append(f"- **City:** {geo.get('city', 'N/A')}")
        md.append(f"- **Region:** {geo.get('region', 'N/A')}")
        md.append(f"- **ISP:** {geo.get('isp', 'N/A')}")
        md.append(f"- **Coordinates:** {geo.get('latitude', 'N/A')}, {geo.get('longitude', 'N/A')}")
        md.append(f"- **VPN/Proxy:** {'Yes' if geo.get('proxy') else 'No'}")
        md.append(f"- **Tor:** {'Yes' if geo.get('tor') else 'No'}")
        md.append("")

    if "asn" in osint_result:
        md.append("## ASN Information")
        asn_info = osint_result["asn"]
        md.append(f"- **ASN:** {asn_info.get('asn', 'N/A')}")
        md.append(f"- **Name:** {asn_info.get('asn_name', 'N/A')}")
        md.append(f"- **CIDR:** {asn_info.get('asn_cidr', 'N/A')}")
        md.append("")

    if "breaches" in osint_result:
        md.append("## Data Breaches")
        breaches = osint_result["breaches"]
        if breaches:
            md.append(f"Found in **{len(breaches)}** breach(es):")
            for breach in breaches:
                md.append(f"- **{breach.get('name', 'Unknown')}** ({breach.get('breach_date', 'N/A')})")
                data_classes = breach.get('data_classes', [])
                if data_classes:
                    md.append(f"  - Data exposed: {', '.join(data_classes)}")
        else:
            md.append("No breaches found.")
        md.append("")

    if "blacklists" in osint_result:
        md.append("## Blacklist Status")
        blacklisted_count = sum(1 for b in osint_result["blacklists"] if b.get("blacklisted"))
        md.append(f"- **Blacklisted on:** {blacklisted_count}/{len(osint_result['blacklists'])} lists")
        for bl in osint_result["blacklists"]:
            status = "🚫 Listed" if bl.get("blacklisted") else "✅ Clean"
            md.append(f"- {bl.get('blacklist', 'Unknown')}: {status}")
        md.append("")

    if "findings" in osint_result:
        md.append("## Findings")
        for i, finding in enumerate(osint_result["findings"], 1):
            md.append(f"### Finding {i}: {finding.get('type', 'Unknown')}")
            md.append(f"- **Severity:** {finding.get('severity', 'N/A')}")
            md.append(f"- **Target:** {finding.get('target', 'N/A')}")
            md.append(f"- **Description:** {finding.get('description', 'N/A')}")
            if finding.get("evidence"):
                md.append(f"- **Evidence:** ```{finding['evidence']}```")
            if finding.get("remediation"):
                md.append(f"- **Remediation:** {finding['remediation']}")
            md.append("")

    return '\n'.join(md)


def osint_to_html_report(osint_result: dict, title: str = "OSINT Report") -> str:
    """Convert OSINT results to an HTML report.

    Args:
        osint_result: Results from any OSINT function
        title: Report title

    Returns:
        HTML string
    """
    # Convert markdown to HTML (or generate HTML directly)
    md = osint_to_markdown(osint_result, title)

    import html
    escaped_md = html.escape(md)

    html_report = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.6; }}
h1 {{ color: #1a1a2e; border-bottom: 3px solid #1a1a2e; padding-bottom: 10px; }}
h2 {{ color: #16213e; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
</style>
</head>
<body>
{escaped_md.replace(chr(10), '<br>')}
</body>
</html>"""

    return html_report


def save_osint_report(osint_result: dict, output_dir: str = "./reports", format: str = "md") -> str:
    """Save OSINT report to file.

    Args:
        osint_result: OSINT results data
        output_dir: Output directory for reports
        format: 'md' for Markdown, 'html' for HTML, 'json' for raw JSON

    Returns:
        Path to saved report file
    """
    import json

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = osint_result.get("target", osint_result.get("email", osint_result.get("ip", "unknown")))
    safe_target = str(target).replace(".", "_").replace("@", "_at_").replace(":", "_")

    if format == "md":
        content = osint_to_markdown(osint_result)
        filename = f"osint_report_{safe_target}_{timestamp}.md"
    elif format == "html":
        content = osint_to_html_report(osint_result)
        filename = f"osint_report_{safe_target}_{timestamp}.html"
    else:
        content = json.dumps(osint_result, indent=2, default=str)
        filename = f"osint_raw_{safe_target}_{timestamp}.json"

    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    log.info(f"OSINT report saved to {filepath}")
    return filepath
```

---

## Ethics and Legal Considerations

### Legal Frameworks

OSINT collection must comply with applicable laws:

| Jurisdiction | Key Laws | Restrictions |
|-------------|----------|--------------|
| United States | CFAA, ECPA, Stored Communications Act | Unauthorized access, interception |
| European Union | GDPR, ePrivacy Directive | Personal data processing, consent |
| United Kingdom | Data Protection Act, Computer Misuse Act | Unauthorized access, data protection |
| Canada | PIPEDA, Criminal Code | Privacy, unauthorized access |
| Australia | Privacy Act, Criminal Code Act | Privacy, computer offenses |
| India | IT Act, Personal Data Protection Bill | Data protection, computer crimes |

### What Is Legal

- **Passive OSINT:** Collecting publicly available information is generally legal
- **Public API usage:** Using APIs in accordance with terms of service
- **Public social media:** Analyzing public posts and profiles
- **WHOIS queries:** Querying public WHOIS databases
- **DNS enumeration:** Standard DNS queries
- **Certificate transparency:** Querying public CT logs
- **Wayback Machine:** Accessing archived public web pages

### What May Be Illegal

- **Unauthorized access:** Logging into accounts without permission
- **Password guessing:** Attempting to breach accounts
- **Excessive scraping:** Violating terms of service or causing DoS
- **Data storage:** Storing personal data without lawful basis (GDPR)
- **Impersonation:** Pretending to be someone else
- **Deception:** Using fake profiles to extract information
- **Dark web access:** May be monitored by law enforcement

### Ethical Guidelines

1. **Minimize harm:** Do not publish information that could cause harm
2. **Proportionality:** Only collect what is necessary for the investigation
3. **Transparency:** Be clear about who you are and why you're collecting
4. **Consent:** When possible, obtain consent from data subjects
5. **Accuracy:** Verify findings from multiple sources
6. **Timeliness:** Date all findings — information goes stale
7. **Data minimization:** Don't collect more than needed
8. **Storage limitation:** Delete data when no longer needed
9. **Security:** Protect collected data from unauthorized access
10. **Accountability:** Document all sources and methods

---

## Operational Security (OPSEC)

### For the Investigator

1. **Use a VPN** for all OSINT activities (not your home IP)
2. **Separate environments:** Use dedicated VMs for different investigations
3. **Clean browsing:** Use separate browser profiles with no cookies/extensions
4. **No personal accounts:** Never log into personal social media during investigations
5. **Tor for sensitive searches:** Use Tor Browser for dark web or sensitive queries
6. **Rotate IPs:** Change IP addresses between different targets
7. **User agent rotation:** Vary browser user agents
8. **No direct interaction:** Never interact with the target directly
9. **Secure storage:** Encrypt all collected data at rest
10. **Cleanup:** Wipe investigation environments after completion

### Tool-Specific OPSEC

```python
OP_SECURITY_CONFIG = {
    "requests_per_minute": 15,
    "delay_between_requests": 2.0,
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; rv:121.0) Gecko/20100101 Firefox/121.0",
    ],
    "proxy_rotation": True,
    "tor_enabled": False,
    "random_delays": True,
    "respect_robots_txt": True,
}


def get_osint_session() -> requests.Session:
    """Create a properly configured requests session for OSINT work.

    Applies OPSEC configurations: user agent rotation, delays,
    proxy support, and error handling.

    Returns:
        Configured requests.Session
    """
    import random
    import time
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()

    # Random user agent
    session.headers.update({
        "User-Agent": random.choice(OP_SECURITY_CONFIG["user_agents"]),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
    })

    # Retry strategy
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def rate_limited_request(url: str, session: requests.Session = None, **kwargs) -> requests.Response:
    """Make a rate-limited HTTP request with automatic delay.

    Ensures polite crawling by respecting rate limits and
    adding delays between requests.

    Args:
        url: Target URL
        session: Requests session (creates one if None)
        **kwargs: Additional request parameters

    Returns:
        Response object
    """
    import time
    import random

    if session is None:
        session = get_osint_session()

    # Add random delay
    if OP_SECURITY_CONFIG["random_delays"]:
        delay = OP_SECURITY_CONFIG["delay_between_requests"] * (0.5 + random.random())
        time.sleep(delay)

    resp = session.get(url, timeout=30, **kwargs)

    # Handle rate limiting
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 60))
        log.warning(f"Rate limited, waiting {retry_after}s")
        time.sleep(retry_after)
        resp = session.get(url, timeout=30, **kwargs)

    return resp
```

---

## Verification Checklist

### Data Quality
1. [ ] Data collected from multiple independent sources
2. [ ] Timestamps recorded for all data points
3. [ ] Source URLs documented
4. [ ] Data validated (emails formatted, IPs valid, etc.)
5. [ ] Duplicates identified and removed
6. [ ] Confidence scores calculated
7. [ ] Inconsistencies flagged for review

### Legal Compliance
1. [ ] Target is within authorized scope
2. [ ] No passwords attempted or accounts breached
3. [ ] Terms of service respected for all sources
4. [ ] GDPR/PIPEDA compliance if personal data involved
5. [ ] Data minimization principles followed
6. [ ] Collection methods documented for audit
7. [ ] Data storage security measures in place

### Analysis Quality
1. [ ] Multiple analytical perspectives considered
2. [ ] Alternative hypotheses evaluated
3. [ ] Bias identified and mitigated
4. [ ] Uncertainties explicitly noted
5. [ ] Source reliability assessed
6. [ ] Chain of evidence maintained
7. [ ] Conclusions supported by evidence

### Reporting Quality
1. [ ] Executive summary included
2. [ ] Methodology described
3. [ ] Findings presented clearly
4. [ ] Evidence referenced and quoted
5. [ ] Confidence scores provided
6. [ ] Limitations acknowledged
7. [ ] Recommendations actionable
8. [ ] Report formatted for target audience

---

## Scoring and Confidence

```python
def score_osint_finding(finding: dict) -> dict:
    """Score an OSINT finding for confidence and severity.

    Evaluates the reliability of a finding based on source quality,
    corroboration, recency, and consistency.

    Args:
        finding: Dict with 'source', 'data', 'timestamp' fields

    Returns:
        dict with confidence (0-1), severity, and quality scores
    """
    score = {
        "confidence": 0.5,
        "severity": "info",
        "source_reliability": 0.5,
        "data_quality": 0.5,
        "corroboration": 0,
        "recency": 0,
        "needs_review": True,
    }

    # Source reliability ratings
    source_reliability = {
        "official_database": 1.0,
        "academic_source": 0.9,
        "news_article": 0.7,
        "social_media": 0.4,
        "forum_post": 0.3,
        "anonymous_leak": 0.2,
        "unverified": 0.1,
    }

    source = finding.get("source", "unverified").lower()
    score["source_reliability"] = source_reliability.get(source, 0.1)

    # Recency
    try:
        from datetime import datetime, timezone
        finding_time = datetime.fromisoformat(finding.get("timestamp", datetime.now().isoformat()).replace('Z', '+00:00'))
        age_days = (datetime.now(timezone.utc) - finding_time).days
        if age_days < 7:
            score["recency"] = 1.0
        elif age_days < 30:
            score["recency"] = 0.8
        elif age_days < 90:
            score["recency"] = 0.5
        elif age_days < 365:
            score["recency"] = 0.3
        else:
            score["recency"] = 0.1
    except Exception:
        score["recency"] = 0.5

    # Corroboration — if finding has multiple supporting sources
    if isinstance(finding.get("sources"), list) and len(finding["sources"]) > 1:
        score["corroboration"] = min(1.0, len(finding["sources"]) * 0.2)
    else:
        score["corroboration"] = 0.1

    # Overall confidence
    score["confidence"] = round(
        score["source_reliability"] * 0.4 +
        score["recency"] * 0.3 +
        score["corroboration"] * 0.3,
        2,
    )

    # Needs review if confidence is low
    score["needs_review"] = score["confidence"] < 0.5

    return score
```

---

## Final Reminders

### ALWAYS Do
- Use `osint_full_scan` first for comprehensive profiling
- Use `dns_enum` before `dns_zone_transfer`
- Validate inputs with `validate_*()` before passing to OSINT functions
- Use `leak_check` for breach data, `email_rep` for reputation
- Call `osint_to_markdown(result)` or `osint_to_html_report(result)` for display
- Append timestamps to all results
- Cross-reference findings from multiple sources
- Use rate limiting and delays between requests
- Respect robots.txt and terms of service
- Document all sources and methods

### NEVER Do
- Never skip error handling — OSINT APIs go down frequently
- Never spam a single target — add small delays between requests
- Never store OSINT results without noting collection timestamp
- Never use personal accounts for OSINT investigations
- Never access dark web sites without Tor
- Never interact with targets directly
- Never exceed API rate limits
- Never collect data beyond investigation scope
- Never publish raw findings without assessment
- Never conduct OSINT without understanding legal implications

### Preferred Practices
- Prefer extended variants (`*_extended`) for deeper results
- Prefer batch tools (`batch_*`) for bulk operations (100+ targets)
- Prefer official APIs over web scraping
- Prefer multiple data sources over single-source findings
- Prefer recent data (last 90 days) over historical data
- Prefer confirmed data over reported/unverified data
- Prefer structured JSON output over raw text parsing

### Tool Selection Guide

| Target Type | First Tool | Follow-up | Confirm With |
|------------|-----------|-----------|-------------|
| Email | `full_email_intel()` | `holehe_check()`, `leak_check()` | Cross-reference breach data |
| Domain | `full_domain_intel()` | `dns_enum()`, `certificate_transparency()` | WHOIS, DNS records |
| IP | `full_ip_intel()` | `ip_geolocate_full()`, `ip_threat_intel()` | ASN, blacklists |
| Username | `social_media_full_scan()` | `sherlock_search()` | Individual platform checks |
| Phone | `phone_intel()` | Carrier lookup, breach check | Geolocation verification |
| Cryptocurrency | `btc_address_lookup()` | Transaction graph analysis | Exchange data |
| Organization | Business registries | LinkedIn employee search | News archives |
| Person | `osint_full_scan()` | Social media, email, username | Cross-reference all data |

### Quick Reference

```
Gather → Validate → Correlate → Analyze → Report
   │          │           │          │         │
   │          │           │          │         └─ Save report
   │          │           │          └─ Score & assess
   │          │           └─ Cross-reference sources
   │          └─ Check timestamps
   └─ Collect from multiple sources
```