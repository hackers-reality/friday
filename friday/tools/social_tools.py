"""
Social Media & Media tools
Libraries: tweepy, praw, instagrapi, yt-dlp, spotipy, flickrapi, discogs-client
"""
import asyncio
import json
import os
import subprocess
import tempfile
from typing import Any

# ── Twitter/X (tweepy) ──
HAS_TWEEPY = False
try:
    import tweepy
    HAS_TWEEPY = True
except ImportError:
    pass


async def twitter_user_info(username: str) -> dict[str, Any]:
    bearer = os.environ.get("TWITTER_BEARER_TOKEN") or os.environ.get("TWITTER_API_KEY")
    if not bearer:
        return {"error": "TWITTER_BEARER_TOKEN not set"}
    if not HAS_TWEEPY:
        return {"error": "tweepy not installed"}
    try:
        client = tweepy.Client(bearer_token=bearer if os.environ.get("TWITTER_BEARER_TOKEN") else None,
                                consumer_key=os.environ.get("TWITTER_API_KEY"),
                                consumer_secret=os.environ.get("TWITTER_API_SECRET"))
        user = await asyncio.get_event_loop().run_in_executor(None, lambda: client.get_user(username=username, user_fields=["description", "public_metrics", "location", "profile_image_url"]))
        if user.data:
            d = user.data
            return {"id": d.id, "name": d.name, "username": d.username, "description": d.description,
                    "followers": d.public_metrics.get("followers_count"), "following": d.public_metrics.get("following_count"),
                    "tweets": d.public_metrics.get("tweet_count"), "location": d.location, "image": d.profile_image_url}
        return {"error": "User not found"}
    except Exception as e:
        return {"error": str(e)}


async def twitter_search(query: str, max_results: int = 10) -> dict[str, Any]:
    bearer = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer:
        return {"error": "TWITTER_BEARER_TOKEN not set"}
    if not HAS_TWEEPY:
        return {"error": "tweepy not installed"}
    try:
        client = tweepy.Client(bearer_token=bearer)
        tweets = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.search_recent_tweets(query=query, max_results=max_results, tweet_fields=["created_at", "public_metrics"]))
        return {"query": query, "tweets": [{"id": t.id, "text": t.text[:500], "created_at": str(t.created_at),
                "likes": t.public_metrics.get("like_count"), "retweets": t.public_metrics.get("retweet_count")}
                for t in (tweets.data or [])]}
    except Exception as e:
        return {"error": str(e)}


# ── Reddit (praw) ──
HAS_PRAW = False
try:
    import praw
    HAS_PRAW = True
except ImportError:
    pass


async def reddit_hot(subreddit: str = "all", limit: int = 10) -> dict[str, Any]:
    if not HAS_PRAW:
        return {"error": "praw not installed"}
    try:
        reddit = praw.Reddit(client_id=os.environ.get("REDDIT_CLIENT_ID"),
                             client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
                             user_agent="FRIDAY:v1.0 (by /u/friday_bot)")
        posts = []
        for post in reddit.subreddit(subreddit).hot(limit=limit):
            posts.append({"id": post.id, "title": post.title, "score": post.score,
                         "author": str(post.author), "url": post.url, "comments": post.num_comments,
                         "created": str(post.created), "selftext": (post.selftext or "")[:500]})
        return {"subreddit": subreddit, "posts": posts}
    except Exception as e:
        return {"error": str(e)}


async def reddit_search(query: str, limit: int = 10) -> dict[str, Any]:
    if not HAS_PRAW:
        return {"error": "praw not installed"}
    try:
        reddit = praw.Reddit(client_id=os.environ.get("REDDIT_CLIENT_ID"),
                             client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
                             user_agent="FRIDAY:v1.0")
        posts = []
        for post in reddit.subreddit("all").search(query, limit=limit):
            posts.append({"id": post.id, "title": post.title, "score": post.score,
                         "subreddit": post.subreddit.display_name, "url": post.url,
                         "selftext": (post.selftext or "")[:500]})
        return {"query": query, "posts": posts}
    except Exception as e:
        return {"error": str(e)}


# ── Instagram (instagrapi) ──
HAS_INSTAGRAPI = False
try:
    from instagrapi import Client
    HAS_INSTAGRAPI = True
except ImportError:
    pass


async def instagram_user_info(username: str) -> dict[str, Any]:
    if not HAS_INSTAGRAPI:
        return {"error": "instagrapi not installed"}
    if not os.environ.get("INSTAGRAM_USER") or not os.environ.get("INSTAGRAM_PASS"):
        return {"error": "INSTAGRAM_USER/PASS not set"}
    try:
        cl = Client()
        await asyncio.get_event_loop().run_in_executor(None, lambda: cl.login(os.environ["INSTAGRAM_USER"], os.environ["INSTAGRAM_PASS"]))
        user_id = await asyncio.get_event_loop().run_in_executor(None, lambda: cl.user_id_from_username(username))
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: cl.user_info(user_id))
        return {"username": info.username, "full_name": info.full_name, "biography": info.biography,
                "followers": info.follower_count, "following": info.following_count,
                "media_count": info.media_count, "is_private": info.is_private,
                "profile_pic": info.profile_pic_url_hd}
    except Exception as e:
        return {"error": str(e)}


# ── YouTube (yt-dlp) ──
YTDLP_PATH = os.environ.get("YTDLP_PATH", "yt-dlp")


async def youtube_info(url: str) -> dict[str, Any]:
    try:
        proc = await asyncio.create_subprocess_exec(
            YTDLP_PATH, "--dump-json", url,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        data = json.loads(stdout.decode())
        return {"title": data.get("title"), "duration": data.get("duration"), "view_count": data.get("view_count"),
                "like_count": data.get("like_count"), "channel": data.get("channel"),
                "description": (data.get("description") or "")[:1000],
                "tags": data.get("tags", [])[:20], "categories": data.get("categories"),
                "formats": [{"id": f.get("format_id"), "ext": f.get("ext"), "resolution": f.get("resolution"),
                            "filesize": f.get("filesize")} for f in (data.get("formats") or [])[:10]]}
    except FileNotFoundError:
        return {"error": "yt-dlp not installed. Install: pip install yt-dlp"}
    except Exception as e:
        return {"error": str(e)}


async def youtube_download(url: str, output_dir: str | None = None) -> dict[str, Any]:
    out = output_dir or tempfile.gettempdir()
    try:
        proc = await asyncio.create_subprocess_exec(
            YTDLP_PATH, url, "-o", os.path.join(out, "%(title)s.%(ext)s"),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        return {"url": url, "output_dir": out, "status": "downloading" if proc.returncode == 0 else "failed"}
    except FileNotFoundError:
        return {"error": "yt-dlp not installed"}
    except Exception as e:
        return {"error": str(e)}


# ── Spotify (spotipy) ──
HAS_SPOTIPY = False
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    HAS_SPOTIPY = True
except ImportError:
    pass


async def spotify_search(query: str, search_type: str = "track", limit: int = 10) -> dict[str, Any]:
    if not HAS_SPOTIPY:
        return {"error": "spotipy not installed"}
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not cid or not secret:
        return {"error": "SPOTIFY_CLIENT_ID/SECRET not set"}
    try:
        auth = SpotifyClientCredentials(client_id=cid, client_secret=secret)
        sp = spotipy.Spotify(auth_manager=auth)
        results = await asyncio.get_event_loop().run_in_executor(
            None, lambda: sp.search(q=query, type=search_type, limit=limit))
        items = results.get(f"{search_type}s", {}).get("items", [])
        return {"query": query, "type": search_type,
                "results": [{"id": i.get("id"), "name": i.get("name"), "artist": ", ".join(a["name"] for a in i.get("artists", [])),
                            "album": i.get("album", {}).get("name"), "popularity": i.get("popularity"),
                            "url": i.get("external_urls", {}).get("spotify")} for i in items]}
    except Exception as e:
        return {"error": str(e)}


async def spotify_playlist(playlist_id: str) -> dict[str, Any]:
    if not HAS_SPOTIPY:
        return {"error": "spotipy not installed"}
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not cid or not secret:
        return {"error": "Spotify credentials not set"}
    try:
        auth = SpotifyClientCredentials(client_id=cid, client_secret=secret)
        sp = spotipy.Spotify(auth_manager=auth)
        results = await asyncio.get_event_loop().run_in_executor(None, lambda: sp.playlist(playlist_id))
        tracks = results.get("tracks", {}).get("items", [])
        return {"name": results.get("name"), "description": results.get("description"),
                "owner": results.get("owner", {}).get("display_name"), "followers": results.get("followers", {}).get("total"),
                "tracks": [{"name": t.get("track", {}).get("name"), "artist": ", ".join(a["name"] for a in (t.get("track", {}).get("artists") or [])),
                           "album": t.get("track", {}).get("album", {}).get("name")} for t in tracks if t.get("track")]}
    except Exception as e:
        return {"error": str(e)}


# ── Flickr ──
async def flickr_search(tags: str, per_page: int = 10) -> dict[str, Any]:
    api_key = os.environ.get("FLICKR_API_KEY")
    if not api_key:
        return {"error": "FLICKR_API_KEY not set"}
    try:
        import flickrapi
        flickr = flickrapi.FlickrAPI(api_key, cache=True)
        photos = await asyncio.get_event_loop().run_in_executor(
            None, lambda: flickr.photos.search(tags=tags, per_page=per_page)["photos"]["photo"])
        return {"tags": tags, "photos": [{"id": p["id"], "title": p["title"], "owner": p["owner"],
                "url": f"https://www.flickr.com/photos/{p['owner']}/{p['id']}"} for p in photos]}
    except ImportError:
        return {"error": "flickrapi not installed"}
    except Exception as e:
        return {"error": str(e)}


# ── Discogs ──
async def discogs_search(query: str, search_type: str = "release") -> dict[str, Any]:
    token = os.environ.get("DISCOGS_TOKEN")
    if not token:
        return {"error": "DISCOGS_TOKEN not set"}
    try:
        import requests
        headers = {"Authorization": f"Discogs token={token}", "User-Agent": "FRIDAY/1.0"}
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(f"https://api.discogs.com/database/search?q={query}&type={search_type}",
                                        headers=headers, timeout=15))
        data = r.json()
        return {"query": query, "type": search_type, "total": data.get("pagination", {}).get("items", 0),
                "results": [{"id": i["id"], "title": i["title"], "type": i["type"],
                            "year": i.get("year"), "country": i.get("country"),
                            "format": i.get("format", [])} for i in data.get("results", [])[:20]]}
    except Exception as e:
        return {"error": str(e)}
