"""
Auto-registry for all new FRIDAY tool modules.
Generates FunctionDeclarations and TOOL_MAP entries for live.py.
"""
from __future__ import annotations

import asyncio
from typing import Any

# ── Tool Module Descriptors ──
# Format: (module_path, function_name, description, parameters_schema, required_params)

TOOL_DESCRIPTORS: list[tuple[str, str, str, dict | None, list[str] | None]] = [
    # ── Voice & Audio ──
    ("friday.tools.voice_tools", "list_audio_devices", "List available audio input/output devices", None, None),
    ("friday.tools.voice_tools", "record_audio", "Record audio from microphone", {"duration": {"type": "NUMBER", "description": "Recording duration in seconds (default 5)"}}, None),
    ("friday.tools.voice_tools", "transcribe_audio", "Transcribe audio file to text using Whisper or other STT", {"path": {"type": "STRING", "description": "Path to audio file"}, "engine": {"type": "STRING", "description": "STT engine: whisper, groq (default whisper)"}}, ["path"]),
    ("friday.tools.voice_tools", "speak_text", "Convert text to speech and play it", {"text": {"type": "STRING", "description": "Text to speak"}, "engine": {"type": "STRING", "description": "TTS engine: gtts, edge, pyttsx3 (default gtts)"}, "voice": {"type": "STRING", "description": "Voice name (edge-tts only)"}}, ["text"]),
    ("friday.tools.voice_tools", "list_tts_voices", "List available TTS voices", {"engine": {"type": "STRING", "description": "TTS engine: edge (default edge)"}}, None),
    ("friday.tools.voice_tools", "analyze_audio", "Analyze an audio file for tempo, spectral content, RMS energy", {"audio_path": {"type": "STRING", "description": "Path to audio file"}}, ["audio_path"]),
    ("friday.tools.voice_tools", "get_audio_metadata", "Get metadata from audio file (mutagen)", {"audio_path": {"type": "STRING", "description": "Path to audio file"}}, ["audio_path"]),
    ("friday.tools.voice_tools", "convert_audio", "Convert audio file between formats (pydub)", {"input_path": {"type": "STRING", "description": "Path to input audio"}, "output_format": {"type": "STRING", "description": "Output format: wav, mp3, ogg (default wav)"}}, ["input_path"]),
    ("friday.tools.voice_tools", "merge_audio", "Merge two audio files into one", {"file1": {"type": "STRING", "description": "First audio file"}, "file2": {"type": "STRING", "description": "Second audio file"}}, ["file1", "file2"]),

    # ── System Control ──
    ("friday.tools.system_tools", "get_processes", "List running processes sorted by CPU or memory", {"sort_by": {"type": "STRING", "description": "Sort by: cpu, memory_percent (default cpu)"}}, None),
    ("friday.tools.system_tools", "kill_process", "Kill a process by PID", {"pid": {"type": "INTEGER", "description": "Process ID to kill"}}, ["pid"]),
    ("friday.tools.system_tools", "get_volume", "Get current system volume level", None, None),
    ("friday.tools.system_tools", "set_volume", "Set system volume percentage", {"percent": {"type": "INTEGER", "description": "Volume level 0-100"}}, ["percent"]),
    ("friday.tools.system_tools", "mute_audio", "Mute or unmute system audio", {"muted": {"type": "BOOLEAN", "description": "True to mute, False to unmute (default True)"}}, None),
    ("friday.tools.system_tools", "get_brightness", "Get screen brightness level", None, None),
    ("friday.tools.system_tools", "set_brightness", "Set screen brightness percentage", {"percent": {"type": "INTEGER", "description": "Brightness level 0-100"}}, ["percent"]),
    ("friday.tools.system_tools", "take_screenshot", "Take a screenshot of the current screen", {"monitor": {"type": "INTEGER", "description": "Monitor index (default 0)"}}, None),
    ("friday.tools.system_tools", "list_windows", "List all open application windows", None, None),
    ("friday.tools.system_tools", "focus_window", "Focus/bring window to foreground by title", {"title": {"type": "STRING", "description": "Window title to focus"}}, ["title"]),
    ("friday.tools.system_tools", "mouse_click", "Click mouse at coordinates", {"x": {"type": "INTEGER", "description": "X coordinate"}, "y": {"type": "INTEGER", "description": "Y coordinate"}, "button": {"type": "STRING", "description": "Button: left, right, middle (default left)"}}, None),
    ("friday.tools.system_tools", "mouse_move", "Move mouse to coordinates", {"x": {"type": "INTEGER", "description": "X coordinate"}, "y": {"type": "INTEGER", "description": "Y coordinate"}}, ["x", "y"]),
    ("friday.tools.system_tools", "get_mouse_position", "Get current mouse cursor position", None, None),
    ("friday.tools.system_tools", "type_text_auto", "Type text using keyboard automation", {"text": {"type": "STRING", "description": "Text to type"}, "interval": {"type": "NUMBER", "description": "Delay between keystrokes in seconds (default 0.05)"}}, ["text"]),
    ("friday.tools.system_tools", "play_system_sound", "Play a Windows system sound", {"sound": {"type": "STRING", "description": "Sound name: default, beep, asterisk, exclamation (default default)"}}, None),
    ("friday.tools.system_tools", "read_registry", "Read a Windows Registry key or value", {"key_path": {"type": "STRING", "description": "Registry path (e.g. HKLM\\Software\\Microsoft)"}, "value_name": {"type": "STRING", "description": "Specific value name (optional)"}}, ["key_path"]),

    # ── OSINT & Reconnaissance ──
    ("friday.tools.osint_advanced_tools", "shodan_search", "Search Shodan for internet-connected devices", {"query": {"type": "STRING", "description": "Shodan search query"}, "limit": {"type": "INTEGER", "description": "Max results (default 10)"}}, ["query"]),
    ("friday.tools.osint_advanced_tools", "shodan_host", "Get Shodan info for a specific IP", {"ip": {"type": "STRING", "description": "IP address to lookup"}}, ["ip"]),
    ("friday.tools.osint_advanced_tools", "censys_search", "Search Censys certificate/host intelligence", {"query": {"type": "STRING", "description": "Censys search query"}, "limit": {"type": "INTEGER", "description": "Max results (default 10)"}}, ["query"]),
    ("friday.tools.osint_advanced_tools", "whois_lookup", "Perform WHOIS lookup on a domain", {"domain": {"type": "STRING", "description": "Domain name (e.g. example.com)"}}, ["domain"]),
    ("friday.tools.osint_advanced_tools", "harvester_enum", "Run theHarvester for email/subdomain enumeration", {"domain": {"type": "STRING", "description": "Target domain"}, "sources": {"type": "STRING", "description": "Sources: all, google,bing,yahoo (default all)"}}, ["domain"]),
    ("friday.tools.osint_advanced_tools", "subfinder_enum", "Discover subdomains using subfinder", {"domain": {"type": "STRING", "description": "Target domain"}}, ["domain"]),
    ("friday.tools.osint_advanced_tools", "nuclei_scan", "Run Nuclei vulnerability scanner on a target", {"target": {"type": "STRING", "description": "Target URL or IP"}, "severity": {"type": "STRING", "description": "Minimum severity: info, low, medium, high, critical (default medium)"}}, ["target"]),
    ("friday.tools.osint_advanced_tools", "ping_host", "Ping a host to check if it's alive", {"host": {"type": "STRING", "description": "Hostname or IP"}, "count": {"type": "INTEGER", "description": "Number of pings (default 3)"}}, ["host"]),
    ("friday.tools.osint_advanced_tools", "port_scan", "Scan common ports on a host", {"host": {"type": "STRING", "description": "Hostname or IP"}, "ports": {"type": "ARRAY", "items": {"type": "INTEGER"}, "description": "Custom port list (optional)"}}, ["host"]),
    ("friday.tools.osint_advanced_tools", "nmap_scan", "Run an Nmap scan against a host", {"host": {"type": "STRING", "description": "Target host"}, "arguments": {"type": "STRING", "description": "Nmap arguments (default: -sV -F)"}}, ["host"]),
    ("friday.tools.osint_advanced_tools", "geoip_lookup", "Lookup geolocation data for an IP address", {"ip": {"type": "STRING", "description": "IP address"}}, ["ip"]),
    ("friday.tools.osint_advanced_tools", "hunter_email_search", "Search for email addresses associated with a domain", {"domain": {"type": "STRING", "description": "Domain name"}}, ["domain"]),
    ("friday.tools.osint_advanced_tools", "clearbit_company", "Lookup company info via Clearbit", {"domain": {"type": "STRING", "description": "Company domain"}}, ["domain"]),
    ("friday.tools.osint_advanced_tools", "clearbit_person", "Lookup person info via Clearbit by email", {"email": {"type": "STRING", "description": "Email address"}}, ["email"]),

    # ── Web Scraping ──
    ("friday.tools.scraping_tools", "fetch_page", "Fetch a web page content", {"url": {"type": "STRING", "description": "Page URL"}, "use_cloudscraper": {"type": "BOOLEAN", "description": "Use cloudscraper for Cloudflare sites (default False)"}}, ["url"]),
    ("friday.tools.scraping_tools", "extract_html", "Extract structured data from HTML", {"html": {"type": "STRING", "description": "HTML content"}, "format": {"type": "STRING", "description": "Output format: text, links, images, metadata, all (default text)"}}, ["html"]),
    ("friday.tools.scraping_tools", "extract_article", "Extract article content from a URL", {"url": {"type": "STRING", "description": "Article URL"}}, ["url"]),
    ("friday.tools.scraping_tools", "html_to_markdown", "Convert HTML to Markdown", {"html": {"type": "STRING", "description": "HTML content"}}, ["html"]),
    ("friday.tools.scraping_tools", "parse_feed", "Parse an RSS/Atom feed", {"feed_url": {"type": "STRING", "description": "Feed URL"}, "limit": {"type": "INTEGER", "description": "Max entries (default 10)"}}, ["feed_url"]),
    ("friday.tools.scraping_tools", "xpath_extract", "Extract data from HTML using XPath", {"html": {"type": "STRING", "description": "HTML content"}, "expression": {"type": "STRING", "description": "XPath expression"}}, ["html", "expression"]),

    # ── Social Media ──
    ("friday.tools.social_tools", "twitter_user_info", "Get Twitter/X user profile info", {"username": {"type": "STRING", "description": "Twitter username"}}, ["username"]),
    ("friday.tools.social_tools", "twitter_search", "Search recent tweets", {"query": {"type": "STRING", "description": "Search query"}, "max_results": {"type": "INTEGER", "description": "Max tweets (default 10)"}}, ["query"]),
    ("friday.tools.social_tools", "reddit_hot", "Get hot posts from a subreddit", {"subreddit": {"type": "STRING", "description": "Subreddit name (default all)"}, "limit": {"type": "INTEGER", "description": "Max posts (default 10)"}}, None),
    ("friday.tools.social_tools", "reddit_search", "Search Reddit across all subreddits", {"query": {"type": "STRING", "description": "Search query"}, "limit": {"type": "INTEGER", "description": "Max results (default 10)"}}, ["query"]),
    ("friday.tools.social_tools", "instagram_user_info", "Get Instagram user profile info", {"username": {"type": "STRING", "description": "Instagram username"}}, ["username"]),
    ("friday.tools.social_tools", "youtube_info", "Get YouTube video metadata", {"url": {"type": "STRING", "description": "YouTube video URL"}}, ["url"]),
    ("friday.tools.social_tools", "youtube_download", "Download a YouTube video", {"url": {"type": "STRING", "description": "YouTube video URL"}}, ["url"]),
    ("friday.tools.social_tools", "spotify_search", "Search Spotify for tracks, albums, or artists", {"query": {"type": "STRING", "description": "Search query"}, "search_type": {"type": "STRING", "description": "Type: track, album, artist (default track)"}, "limit": {"type": "INTEGER", "description": "Max results (default 10)"}}, ["query"]),
    ("friday.tools.social_tools", "flickr_search", "Search Flickr photos by tags", {"tags": {"type": "STRING", "description": "Comma-separated tags"}, "per_page": {"type": "INTEGER", "description": "Results per page (default 10)"}}, ["tags"]),

    # ── Document Processing ──
    ("friday.tools.doc_tools", "read_docx", "Read a Word document", {"path": {"type": "STRING", "description": "Path to .docx file"}}, ["path"]),
    ("friday.tools.doc_tools", "create_docx", "Create a Word document with optional sections: headings, paragraphs, bullet lists, numbered lists, tables (with rows), charts, and code blocks. Use 'sections' for rich content, 'content' for plain text.", {"content": {"type": "STRING", "description": "Plain text content (alternative to sections)"}, "sections": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"type": {"type": "STRING", "description": "Section type: heading, paragraph, bullet_list, numbered_list, table, chart, divider, code"}, "text": {"type": "STRING", "description": "Text content"}, "level": {"type": "INTEGER", "description": "Heading level for heading type (1-3)"}, "items": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List items for bullet_list/numbered_list"}, "rows": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "STRING"}}, "description": "Table rows"}, "chart_type": {"type": "STRING", "description": "Chart type: bar, hbar, grouped_bar, stacked_bar, line, multi_line, area, pie, donut, scatter, bubble, histogram, box, violin, heatmap, radar, candlestick, kmeans, contour, 3d_scatter, 3d_surface, 3d_bar"}, "data": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Chart data"}, "data2": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Secondary chart data (for grouped/stacked bars, multi-line, bubble Y, scatter Y, box/violin series 2, histogram bins, 3d_scatter Z)"}, "data3": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Tertiary chart data (bubble sizes, box/violin series 3, K-means n_clusters[0], 3d_surface Z)"}, "labels": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Axis/pie labels"}, "title": {"type": "STRING", "description": "Chart title"}, "xlabel": {"type": "STRING", "description": "X axis label"}, "ylabel": {"type": "STRING", "description": "Y axis label"}}}, "description": "Rich content sections"}}, None),
    ("friday.tools.doc_tools", "read_excel", "Read an Excel workbook", {"path": {"type": "STRING", "description": "Path to .xlsx file"}, "sheet": {"type": "STRING", "description": "Sheet name (default first sheet)"}}, ["path"]),
    ("friday.tools.doc_tools", "create_excel", "Create an Excel spreadsheet from data", {"data": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "STRING"}}, "description": "2D array of data rows (each row is an array of cell values)"}, "headers": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Column headers (optional)"}}, ["data"]),
    ("friday.tools.doc_tools", "create_xlsx_chart", "Create an Excel workbook with data sheets and embedded chart image sheets supporting all chart types", {"sections": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"type": {"type": "STRING", "description": "Section type: data (spreadsheet data) or chart (embedded chart image)"}, "name": {"type": "STRING", "description": "Sheet name"}, "headers": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Column headers (for data type)"}, "rows": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "STRING"}}, "description": "Data rows (for data type)"}, "chart_type": {"type": "STRING", "description": "Chart type (for chart type)"}, "data": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Chart data"}, "data2": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Secondary chart data"}, "data3": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Tertiary chart data"}, "labels": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Chart labels"}, "title": {"type": "STRING", "description": "Chart title"}, "xlabel": {"type": "STRING", "description": "X axis label"}, "ylabel": {"type": "STRING", "description": "Y axis label"}}}, "description": "Sections for data sheets and chart sheets"}}, ["sections"]),
    ("friday.tools.doc_tools", "analyze_csv", "Analyze a CSV file with pandas", {"path": {"type": "STRING", "description": "Path to CSV file"}}, ["path"]),
    ("friday.tools.doc_tools", "read_pdf", "Extract text from a PDF", {"path": {"type": "STRING", "description": "Path to PDF file"}}, ["path"]),
    ("friday.tools.doc_tools", "create_pdf", "Generate a rich PDF document with sections: headings, paragraphs, tables, 20+ chart types (bar, grouped_bar, stacked_bar, line, multi_line, area, pie, donut, scatter, bubble, histogram, box, violin, heatmap, radar, candlestick, kmeans, contour, 3d_scatter, 3d_surface, 3d_bar), bullet lists, numbered lists, dividers, code blocks, images, captions. Supports up to 100+ pages. IMPORTANT: Before calling this tool, first use read_file('friday/skills/pdf/SKILL.md') to learn the proper usage patterns and conventions.", {"sections": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"type": {"type": "STRING", "description": "section type: heading, paragraph, table, chart, bullets, numbered, divider, code, image"}, "text": {"type": "STRING", "description": "Text content for heading/paragraph/code"}, "level": {"type": "INTEGER", "description": "Heading level: 1, 2, or 3"}, "items": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Bullet/numbered items"}, "headers": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Table column headers"}, "rows": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "STRING"}}, "description": "Table data rows"}, "caption": {"type": "STRING", "description": "Table caption"}, "chart_type": {"type": "STRING", "description": "Chart type: bar, hbar, grouped_bar, stacked_bar, line, multi_line, area, pie, donut, scatter, bubble, histogram, box, violin, heatmap, radar, candlestick, kmeans, contour, 3d_scatter, 3d_surface, 3d_bar"}, "data": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Chart data values (for kmeans: X coordinates)"}, "data2": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Secondary data series (for grouped_bar/stacked_bar/multi_line/area/bubble Y/scatter Y/box violin series 2/histogram bins/candlestick OHLC/3d_scatter Z/kmeans Y)"}, "data3": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Tertiary data series (bubble sizes, box/violin series 3, kmeans n_clusters[0], 3d_surface Z matrix)"}, "labels": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Chart axis/pie labels"}, "title": {"type": "STRING", "description": "Chart/section title"}, "xlabel": {"type": "STRING", "description": "Chart X axis label"}, "ylabel": {"type": "STRING", "description": "Chart Y axis label"}, "path": {"type": "STRING", "description": "Image path (for image type)"}}}, "description": "List of content sections to include in the PDF"}, "title": {"type": "STRING", "description": "Document title (default Friday Report)"}}, ["sections"]),
    ("friday.tools.doc_tools", "read_pptx", "Read a PowerPoint presentation", {"path": {"type": "STRING", "description": "Path to .pptx file"}}, ["path"]),
    ("friday.tools.doc_tools", "create_pptx", "Create a PowerPoint presentation with text slides and chart slides supporting all chart types (bar, line, pie, scatter, area, candlestick, kmeans, 3d, etc)", {"title": {"type": "STRING", "description": "Presentation title"}, "slides": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"title": {"type": "STRING", "description": "Slide title"}, "content": {"type": "STRING", "description": "Slide content (for content type)"}, "type": {"type": "STRING", "description": "Slide type: content or chart"}, "chart_type": {"type": "STRING", "description": "Chart type for chart slides"}, "data": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Chart data"}, "data2": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Secondary chart data"}, "data3": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Tertiary chart data"}, "labels": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Chart labels"}, "xlabel": {"type": "STRING", "description": "X axis label"}, "ylabel": {"type": "STRING", "description": "Y axis label"}, "notes": {"type": "STRING", "description": "Speaker notes"}}}, "description": "List of slides"}}, ["title", "slides"]),

    # ── Advanced Vision ──
    ("friday.tools.vision_advanced_tools", "ocr_image", "Extract text from image using OCR", {"image_path": {"type": "STRING", "description": "Path to image file"}, "engine": {"type": "STRING", "description": "OCR engine: tesseract, easyocr (default tesseract)"}}, ["image_path"]),
    ("friday.tools.vision_advanced_tools", "detect_objects", "Detect objects in image using YOLO", {"image_path": {"type": "STRING", "description": "Path to image"}, "model": {"type": "STRING", "description": "YOLO model (default yolov8n)"}}, ["image_path"]),
    ("friday.tools.vision_advanced_tools", "detect_faces", "Detect faces in an image", {"image_path": {"type": "STRING", "description": "Path to image file"}}, ["image_path"]),
    ("friday.tools.vision_advanced_tools", "pose_detection", "Detect human pose landmarks in image (MediaPipe)", {"image_path": {"type": "STRING", "description": "Path to image file"}}, ["image_path"]),
    ("friday.tools.vision_advanced_tools", "hand_detection", "Detect hand landmarks in image (MediaPipe)", {"image_path": {"type": "STRING", "description": "Path to image file"}}, ["image_path"]),
    ("friday.tools.vision_advanced_tools", "image_enhance", "Apply image enhancement filters", {"image_path": {"type": "STRING", "description": "Path to image"}, "operation": {"type": "STRING", "description": "Operation: enhance_contrast, enhance_brightness, grayscale, blur, sharpen, emboss"}, "factor": {"type": "NUMBER", "description": "Enhancement factor (default 1.5)"}}, ["image_path", "operation"]),
    ("friday.tools.vision_advanced_tools", "image_analysis", "Get detailed image analysis (format, size, channels, histogram)", {"image_path": {"type": "STRING", "description": "Path to image file"}}, ["image_path"]),
    ("friday.tools.vision_advanced_tools", "resize_image", "Resize an image to specified dimensions", {"image_path": {"type": "STRING", "description": "Path to image"}, "width": {"type": "INTEGER", "description": "New width"}, "height": {"type": "INTEGER", "description": "New height"}}, ["image_path", "width", "height"]),

    # ── NLP & ML ──
    ("friday.tools.nlp_tools", "sentiment_analysis", "Analyze sentiment of text", {"text": {"type": "STRING", "description": "Text to analyze"}}, ["text"]),
    ("friday.tools.nlp_tools", "extract_entities", "Extract named entities from text", {"text": {"type": "STRING", "description": "Text to analyze"}}, ["text"]),
    ("friday.tools.nlp_tools", "summarize_text", "Summarize a long text passage", {"text": {"type": "STRING", "description": "Text to summarize"}, "ratio": {"type": "NUMBER", "description": "Summary ratio (default 0.3)"}}, ["text"]),
    ("friday.tools.nlp_tools", "classify_text", "Classify text into categories (zero-shot)", {"text": {"type": "STRING", "description": "Text to classify"}, "labels": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List of category labels (optional)"}}, ["text"]),
    ("friday.tools.nlp_tools", "compute_embeddings", "Compute semantic embeddings for texts", {"texts": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List of texts to embed"}}, ["texts"]),

    # ── Security & Encryption ──
    ("friday.tools.security_tools", "generate_fernet_key", "Generate a Fernet encryption key", None, None),
    ("friday.tools.security_tools", "encrypt_text", "Encrypt text using Fernet symmetric encryption", {"plaintext": {"type": "STRING", "description": "Text to encrypt"}, "key": {"type": "STRING", "description": "Fernet key"}}, ["plaintext", "key"]),
    ("friday.tools.security_tools", "decrypt_text", "Decrypt Fernet-encrypted text", {"ciphertext": {"type": "STRING", "description": "Encrypted text"}, "key": {"type": "STRING", "description": "Fernet key"}}, ["ciphertext", "key"]),
    ("friday.tools.security_tools", "hash_text", "Hash text using specified algorithm", {"text": {"type": "STRING", "description": "Text to hash"}, "algorithm": {"type": "STRING", "description": "Algorithm: md5, sha1, sha256, sha512, blake2b (default sha256)"}}, ["text"]),
    ("friday.tools.security_tools", "bcrypt_hash", "Hash a password using bcrypt", {"password": {"type": "STRING", "description": "Password to hash"}}, ["password"]),
    ("friday.tools.security_tools", "bcrypt_verify", "Verify password against bcrypt hash", {"password": {"type": "STRING", "description": "Password to check"}, "hash_str": {"type": "STRING", "description": "Bcrypt hash"}}, ["password", "hash_str"]),
    ("friday.tools.security_tools", "jwt_encode", "Create a JWT token", {"payload": {"type": "OBJECT", "description": "JWT payload key-value pairs"}, "secret": {"type": "STRING", "description": "JWT secret key"}, "algorithm": {"type": "STRING", "description": "Algorithm: HS256, HS384, HS512 (default HS256)"}}, ["payload", "secret"]),
    ("friday.tools.security_tools", "jwt_decode", "Decode and verify a JWT token", {"token": {"type": "STRING", "description": "JWT token"}, "secret": {"type": "STRING", "description": "JWT secret key"}}, ["token", "secret"]),
    ("friday.tools.security_tools", "generate_totp_secret", "Generate a TOTP 2FA secret key", None, None),
    ("friday.tools.security_tools", "verify_totp", "Verify a TOTP 2-factor authentication code", {"secret": {"type": "STRING", "description": "TOTP secret"}, "token": {"type": "STRING", "description": "TOTP code to verify"}}, ["secret", "token"]),

    # ── Memory & Database ──
    ("friday.tools.memory_tools", "chroma_create_collection", "Create a ChromaDB collection", {"name": {"type": "STRING", "description": "Collection name"}}, ["name"]),
    ("friday.tools.memory_tools", "chroma_add", "Add documents to ChromaDB collection", {"collection": {"type": "STRING", "description": "Collection name"}, "texts": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Document texts"}, "ids": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Document IDs"}}, ["collection", "texts", "ids"]),
    ("friday.tools.memory_tools", "chroma_query", "Query ChromaDB for similar documents", {"collection": {"type": "STRING", "description": "Collection name"}, "query_text": {"type": "STRING", "description": "Search query"}, "n_results": {"type": "INTEGER", "description": "Number of results (default 5)"}}, ["collection", "query_text"]),
    ("friday.tools.memory_tools", "redis_set", "Store a value in Redis with optional TTL", {"key": {"type": "STRING", "description": "Redis key"}, "value": {"type": "STRING", "description": "Value to store"}, "ttl": {"type": "INTEGER", "description": "TTL in seconds (optional)"}}, ["key", "value"]),
    ("friday.tools.memory_tools", "redis_get", "Retrieve a value from Redis", {"key": {"type": "STRING", "description": "Redis key"}}, ["key"]),
    ("friday.tools.memory_tools", "redis_delete", "Delete a key from Redis", {"key": {"type": "STRING", "description": "Redis key"}}, ["key"]),
    ("friday.tools.memory_tools", "mongo_find", "Find documents in MongoDB", {"db": {"type": "STRING", "description": "Database name"}, "collection": {"type": "STRING", "description": "Collection name"}, "query": {"type": "OBJECT", "description": "MongoDB query filter (optional)"}}, ["db", "collection"]),

    # ── Knowledge Graph ──
    ("friday.tools.knowledge_tools", "neo4j_run_query", "Run a Cypher query on Neo4j", {"query": {"type": "STRING", "description": "Cypher query"}, "params": {"type": "OBJECT", "description": "Query parameters (optional)"}}, ["query"]),
    ("friday.tools.knowledge_tools", "neo4j_create_entity", "Create an entity node in Neo4j", {"label": {"type": "STRING", "description": "Node label"}, "properties": {"type": "OBJECT", "description": "Node properties"}}, ["label", "properties"]),
    ("friday.tools.knowledge_tools", "neo4j_find_entities", "Find entities by label in Neo4j", {"label": {"type": "STRING", "description": "Node label"}, "limit": {"type": "INTEGER", "description": "Max results (default 50)"}}, ["label"]),
    ("friday.tools.knowledge_tools", "analyze_graph", "Analyze a knowledge graph using NetworkX (centrality, communities)", {"nodes": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"id": {"type": "STRING", "description": "Node ID"}, "label": {"type": "STRING", "description": "Node display label"}}}, "description": "List of node objects"}, "edges": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"source": {"type": "STRING", "description": "Source node ID"}, "target": {"type": "STRING", "description": "Target node ID"}, "label": {"type": "STRING", "description": "Edge label"}}}, "description": "List of edge objects"}}, ["nodes", "edges"]),
    ("friday.tools.knowledge_tools", "create_graph_visualization", "Create an interactive HTML knowledge graph visualization (PyVis)", {"nodes": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"id": {"type": "STRING", "description": "Node ID"}, "label": {"type": "STRING", "description": "Node display label"}}}, "description": "List of node objects"}, "edges": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"source": {"type": "STRING", "description": "Source node ID"}, "target": {"type": "STRING", "description": "Target node ID"}, "label": {"type": "STRING", "description": "Edge label"}}}, "description": "List of edge objects"}}, ["nodes", "edges"]),

    # ── Google Drive ──
    ("friday.google_clients", "drive_list", "List files and folders in Google Drive", {"folder_id": {"type": "STRING", "description": "Folder ID (default root)"}, "page_size": {"type": "INTEGER", "description": "Max files to return (default 20)"}}, None),
    ("friday.google_clients", "drive_search", "Search Google Drive by filename", {"query": {"type": "STRING", "description": "Filename or keyword search"}, "page_size": {"type": "INTEGER", "description": "Max results (default 20)"}}, ["query"]),
    ("friday.google_clients", "drive_upload", "Upload a local file to Google Drive", {"file_path": {"type": "STRING", "description": "Path to local file"}, "parent_folder_id": {"type": "STRING", "description": "Optional Drive folder ID to upload into"}}, ["file_path"]),
    ("friday.google_clients", "drive_download", "Download a file from Google Drive to local", {"file_id": {"type": "STRING", "description": "Drive file ID"}, "output_path": {"type": "STRING", "description": "Local output path"}}, ["file_id", "output_path"]),
    ("friday.google_clients", "drive_create_folder", "Create a folder in Google Drive", {"name": {"type": "STRING", "description": "Folder name"}, "parent_folder_id": {"type": "STRING", "description": "Optional parent folder ID"}}, ["name"]),
    ("friday.google_clients", "drive_delete", "Move a Drive file or folder to trash", {"file_id": {"type": "STRING", "description": "File or folder ID to delete"}}, ["file_id"]),

    # ── Google Sheets ──
    ("friday.google_clients", "sheets_create", "Create a new Google Sheet", {"title": {"type": "STRING", "description": "Sheet title"}}, ["title"]),
    ("friday.google_clients", "sheets_read", "Read values from a Google Sheet range", {"spreadsheet_id": {"type": "STRING", "description": "Spreadsheet ID"}, "range_name": {"type": "STRING", "description": "Range like Sheet1 or Sheet1!A1:C10 (default Sheet1)"}}, ["spreadsheet_id"]),
    ("friday.google_clients", "sheets_write", "Write values to a Google Sheet range", {"spreadsheet_id": {"type": "STRING", "description": "Spreadsheet ID"}, "range_name": {"type": "STRING", "description": "Range e.g. Sheet1!A1"}, "values": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "STRING"}}, "description": "2D array of cell values"}}, ["spreadsheet_id", "range_name", "values"]),
    ("friday.google_clients", "sheets_append", "Append rows to a Google Sheet", {"spreadsheet_id": {"type": "STRING", "description": "Spreadsheet ID"}, "range_name": {"type": "STRING", "description": "Range e.g. Sheet1!A1"}, "values": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "STRING"}}, "description": "2D array of rows to append"}}, ["spreadsheet_id", "range_name", "values"]),
    ("friday.google_clients", "sheets_list", "List all sheets/tabs in a spreadsheet", {"spreadsheet_id": {"type": "STRING", "description": "Spreadsheet ID"}}, ["spreadsheet_id"]),

    # ── Google Docs ──
    ("friday.google_clients", "docs_create", "Create a new Google Doc", {"title": {"type": "STRING", "description": "Document title"}, "content": {"type": "STRING", "description": "Optional initial content"}}, ["title"]),
    ("friday.google_clients", "docs_read", "Read a Google Doc's content", {"document_id": {"type": "STRING", "description": "Document ID"}}, ["document_id"]),
    ("friday.google_clients", "docs_append_text", "Append text to a Google Doc", {"document_id": {"type": "STRING", "description": "Document ID"}, "text": {"type": "STRING", "description": "Text to append"}}, ["document_id", "text"]),

    # ── Google Slides ──
    ("friday.google_clients", "slides_create", "Create a new Google Slides presentation", {"title": {"type": "STRING", "description": "Presentation title"}}, ["title"]),
    ("friday.google_clients", "slides_read", "Read Google Slides presentation content", {"presentation_id": {"type": "STRING", "description": "Presentation ID"}}, ["presentation_id"]),
    ("friday.google_clients", "slides_add_slide", "Add a slide to a Google Slides presentation", {"presentation_id": {"type": "STRING", "description": "Presentation ID"}, "title": {"type": "STRING", "description": "Optional slide title"}, "body": {"type": "STRING", "description": "Optional slide body text"}}, ["presentation_id"]),

    # ── Google People / Contacts ──
    ("friday.google_clients", "people_list", "List Google Contacts", {"page_size": {"type": "INTEGER", "description": "Max contacts (default 20)"}}, None),
    ("friday.google_clients", "people_search", "Search Google Contacts by name or email", {"query": {"type": "STRING", "description": "Search query"}, "page_size": {"type": "INTEGER", "description": "Max results (default 20)"}}, ["query"]),
    ("friday.google_clients", "people_create_contact", "Create a new Google Contact", {"name": {"type": "STRING", "description": "Contact name"}, "email": {"type": "STRING", "description": "Optional email"}, "phone": {"type": "STRING", "description": "Optional phone number"}}, ["name"]),
    ("friday.google_clients", "people_list_directories", "List available contact directories", None, None),

    # ── Google Maps ──
    ("friday.google_clients", "maps_geocode", "Geocode an address to lat/lng coordinates", {"address": {"type": "STRING", "description": "Street address or place name"}}, ["address"]),
    ("friday.google_clients", "maps_reverse_geocode", "Reverse geocode lat/lng to street address", {"lat": {"type": "NUMBER", "description": "Latitude"}, "lng": {"type": "NUMBER", "description": "Longitude"}}, ["lat", "lng"]),
    ("friday.google_clients", "maps_places_search", "Search for places using Google Places API", {"query": {"type": "STRING", "description": "Search query like 'coffee near Times Square'"}, "location": {"type": "STRING", "description": "Optional bias: lat,lng"}, "radius": {"type": "INTEGER", "description": "Search radius in meters (default 5000)"}}, ["query"]),
    ("friday.google_clients", "maps_directions", "Get driving/walking/transit directions", {"origin": {"type": "STRING", "description": "Starting address"}, "destination": {"type": "STRING", "description": "Destination address"}, "mode": {"type": "STRING", "description": "Travel mode: driving, walking, bicycling, transit (default driving)"}}, ["origin", "destination"]),
    ("friday.google_clients", "maps_elevation", "Get elevation data for locations", {"locations": {"type": "STRING", "description": "Comma-separated lat,lng pairs e.g. 40.71,-74.00|34.05,-118.24"}}, ["locations"]),

    # ── Google Cloud Platform ──
    ("friday.google_clients", "bigquery_query", "Run a BigQuery SQL query and return results", {"sql": {"type": "STRING", "description": "SQL query to execute"}}, ["sql"]),
    ("friday.google_clients", "storage_list", "List objects in a Cloud Storage bucket", {"bucket": {"type": "STRING", "description": "Bucket name"}, "prefix": {"type": "STRING", "description": "Optional path prefix filter"}}, ["bucket"]),
    ("friday.google_clients", "storage_upload", "Upload a file to Cloud Storage bucket", {"bucket": {"type": "STRING", "description": "Bucket name"}, "file_path": {"type": "STRING", "description": "Local file path"}, "dest_path": {"type": "STRING", "description": "Optional destination path in bucket"}}, ["bucket", "file_path"]),
    ("friday.google_clients", "vision_annotate", "Analyze an image with Cloud Vision API (labels, text, faces, safety)", {"image_path": {"type": "STRING", "description": "Path to image file"}}, ["image_path"]),
    ("friday.google_clients", "translate_text", "Translate text between languages", {"text": {"type": "STRING", "description": "Text to translate"}, "target_language": {"type": "STRING", "description": "Target language code e.g. es, fr, ja (default en)"}, "source_language": {"type": "STRING", "description": "Optional source language code"}}, ["text"]),
    ("friday.google_clients", "translate_detect_language", "Detect the language of a text", {"text": {"type": "STRING", "description": "Text to analyze"}}, ["text"]),
    ("friday.google_clients", "tts_synthesize", "Convert text to speech audio file (Google Cloud TTS)", {"text": {"type": "STRING", "description": "Text to speak"}, "language": {"type": "STRING", "description": "Language code (default en-US)"}, "voice_name": {"type": "STRING", "description": "Voice name (default en-US-Wavenet-D)"}, "output_path": {"type": "STRING", "description": "Output file path (default output.mp3)"}}, ["text"]),
    ("friday.google_clients", "stt_transcribe", "Transcribe audio file to text (Google Cloud STT)", {"audio_path": {"type": "STRING", "description": "Path to audio file"}, "language": {"type": "STRING", "description": "Language code (default en-US)"}}, ["audio_path"]),

    # ── Firebase Firestore ──
    ("friday.google_clients", "firestore_get", "Get a Firestore document by ID", {"collection": {"type": "STRING", "description": "Collection name"}, "document_id": {"type": "STRING", "description": "Document ID"}}, ["collection", "document_id"]),
    ("friday.google_clients", "firestore_query", "List all documents in a Firestore collection", {"collection": {"type": "STRING", "description": "Collection name"}}, ["collection"]),
    ("friday.google_clients", "firestore_set", "Create or overwrite a Firestore document", {"collection": {"type": "STRING", "description": "Collection name"}, "document_id": {"type": "STRING", "description": "Document ID"}, "data": {"type": "OBJECT", "description": "Document fields as key-value pairs"}}, ["collection", "document_id", "data"]),
    ("friday.google_clients", "firestore_delete", "Delete a Firestore document", {"collection": {"type": "STRING", "description": "Collection name"}, "document_id": {"type": "STRING", "description": "Document ID"}}, ["collection", "document_id"]),

    # ── Google Books ──
    ("friday.google_clients", "books_search", "Search Google Books", {"query": {"type": "STRING", "description": "Search query"}, "max_results": {"type": "INTEGER", "description": "Max results (default 10)"}}, ["query"]),
    ("friday.google_clients", "books_get_volume", "Get detailed info about a Google Books volume", {"volume_id": {"type": "STRING", "description": "Volume ID"}}, ["volume_id"]),

    # ── YouTube Analytics (monetization) ──
    ("friday.google_clients", "youtube_analytics_advanced", "Get advanced YouTube Analytics with monetization data (revenue, CPM, ad revenue)", {"channel_id": {"type": "STRING", "description": "YouTube channel ID"}, "start_date": {"type": "STRING", "description": "Start date YYYY-MM-DD"}, "end_date": {"type": "STRING", "description": "End date YYYY-MM-DD"}}, ["channel_id", "start_date", "end_date"]),

    # ── YouTube Data API ──
    ("friday.google_clients", "youtube_search", "Search YouTube videos by query. Supports duration filter and sort order.", {"query": {"type": "STRING", "description": "Search query"}, "max_results": {"type": "INTEGER", "description": "Max results (default 10, max 50)"}, "video_duration": {"type": "STRING", "description": "Filter: any, short (<4min), medium (4-20min), long (>20min) (optional)"}, "order": {"type": "STRING", "description": "Sort: relevance, date, rating, viewCount (default relevance)"}}, ["query"]),
    ("friday.google_clients", "youtube_video_info", "Get detailed info about a YouTube video (stats, duration, tags, captions)", {"video_id": {"type": "STRING", "description": "YouTube video ID"}}, ["video_id"]),
    ("friday.google_clients", "youtube_channel_info", "Get YouTube channel details (subscribers, video count, uploads playlist ID). Provide channel_id, for_username, or omit for own channel.", {"channel_id": {"type": "STRING", "description": "Channel ID (optional)"}, "for_username": {"type": "STRING", "description": "Channel username (optional)"}}, None),
    ("friday.google_clients", "youtube_list_comments", "List top-level comments on a YouTube video", {"video_id": {"type": "STRING", "description": "Video ID"}, "max_results": {"type": "INTEGER", "description": "Max comments (default 20, max 50)"}}, ["video_id"]),
    ("friday.google_clients", "youtube_list_playlist_items", "List videos in a YouTube playlist", {"playlist_id": {"type": "STRING", "description": "Playlist ID"}, "max_results": {"type": "INTEGER", "description": "Max results (default 20, max 50)"}}, ["playlist_id"]),
    ("friday.google_clients", "youtube_list_channel_videos", "List videos uploaded by a YouTube channel", {"channel_id": {"type": "STRING", "description": "Channel ID"}, "max_results": {"type": "INTEGER", "description": "Max results (default 20, max 50)"}, "order": {"type": "STRING", "description": "Sort: date, rating, viewCount, title (default date)"}}, ["channel_id"]),

    # ── Google Tasks ──
    ("friday.google_clients", "tasks_list_tasklists", "List all task lists", None, None),
    ("friday.google_clients", "tasks_list", "List tasks from a task list", {"tasklist_id": {"type": "STRING", "description": "Task list ID (default @default)"}, "max_results": {"type": "INTEGER", "description": "Max results (default 20)"}, "show_completed": {"type": "BOOLEAN", "description": "Include completed tasks (default False)"}}, None),
    ("friday.google_clients", "tasks_create", "Create a new task in a task list", {"tasklist_id": {"type": "STRING", "description": "Task list ID (default @default)"}, "title": {"type": "STRING", "description": "Task title"}, "notes": {"type": "STRING", "description": "Optional notes"}, "due": {"type": "STRING", "description": "Optional due date ISO 8601"}}, ["title"]),
    ("friday.google_clients", "tasks_update", "Update a task (title, notes, due, or status). Set status='completed' to mark done.", {"tasklist_id": {"type": "STRING", "description": "Task list ID"}, "task_id": {"type": "STRING", "description": "Task ID to update"}, "title": {"type": "STRING", "description": "New title (optional)"}, "notes": {"type": "STRING", "description": "New notes (optional)"}, "due": {"type": "STRING", "description": "New due date ISO 8601 (optional)"}, "status": {"type": "STRING", "description": "New status: needsAction, completed (optional)"}}, ["tasklist_id", "task_id"]),
    ("friday.google_clients", "tasks_delete", "Delete a task", {"tasklist_id": {"type": "STRING", "description": "Task list ID"}, "task_id": {"type": "STRING", "description": "Task ID to delete"}}, ["tasklist_id", "task_id"]),

    # ── Google Photos ──
    ("friday.google_clients", "photos_list_albums", "List Google Photos albums", {"page_size": {"type": "INTEGER", "description": "Max albums (default 20)"}}, None),
    ("friday.google_clients", "photos_list_album_contents", "List media items in a Google Photos album", {"album_id": {"type": "STRING", "description": "Album ID"}, "page_size": {"type": "INTEGER", "description": "Max items (default 50, max 100)"}}, ["album_id"]),
    ("friday.google_clients", "photos_search_by_date", "Search Google Photos by date (year, month, day)", {"year": {"type": "INTEGER", "description": "Year e.g. 2026"}, "month": {"type": "INTEGER", "description": "Month 1-12 (optional)"}, "day": {"type": "INTEGER", "description": "Day 1-31 (optional)"}, "page_size": {"type": "INTEGER", "description": "Max results (default 50)"}}, ["year"]),
    ("friday.google_clients", "photos_create_album", "Create a new Google Photos album", {"title": {"type": "STRING", "description": "Album title"}}, ["title"]),

    # ── Google Calendar ──
    ("friday.google_clients", "calendar_list_calendars", "List all calendars the user has access to", None, None),
    ("friday.google_clients", "calendar_list_events", "List calendar events. Supports time range filtering.", {"calendar_id": {"type": "STRING", "description": "Calendar ID (default primary)"}, "max_results": {"type": "INTEGER", "description": "Max events (default 20)"}, "time_min": {"type": "STRING", "description": "Start of time range ISO 8601 (optional)"}, "time_max": {"type": "STRING", "description": "End of time range ISO 8601 (optional)"}}, None),
    ("friday.google_clients", "calendar_create_event", "Create a calendar event", {"calendar_id": {"type": "STRING", "description": "Calendar ID (default primary)"}, "summary": {"type": "STRING", "description": "Event title"}, "description": {"type": "STRING", "description": "Event description (optional)"}, "start_time": {"type": "STRING", "description": "Start time ISO 8601 e.g. 2026-06-10T14:00:00"}, "end_time": {"type": "STRING", "description": "End time ISO 8601 e.g. 2026-06-10T15:00:00"}, "timezone": {"type": "STRING", "description": "Timezone (default UTC)"}, "location": {"type": "STRING", "description": "Event location (optional)"}}, ["summary", "start_time", "end_time"]),

    # ── Google Analytics ──
    ("friday.google_clients", "analytics_get_reports", "Get Google Analytics 4 report data. Requires numeric GA4 property ID.", {"property_id": {"type": "STRING", "description": "Numeric GA4 property ID"}, "start_date": {"type": "STRING", "description": "Start date e.g. 7daysAgo, 2026-01-01 (default 7daysAgo)"}, "end_date": {"type": "STRING", "description": "End date e.g. today, 2026-06-01 (default today)"}, "metrics": {"type": "STRING", "description": "Metrics: sessions,activeUsers,newUsers,totalRevenue (default sessions)"}, "dimensions": {"type": "STRING", "description": "Dimensions: date,country,deviceCategory (default date)"}}, ["property_id"]),

    # ── Google Drive Extended ──
    ("friday.google_clients", "drive_export", "Export a Google Workspace file (Doc/Sheet/Slide) to another format like PDF, DOCX, CSV", {"file_id": {"type": "STRING", "description": "Drive file ID"}, "mime_type": {"type": "STRING", "description": "Export MIME type: application/pdf, text/csv, application/vnd.openxmlformats-officedocument.wordprocessingml.document (default application/pdf)"}}, ["file_id"]),
    ("friday.google_clients", "drive_list_comments", "List comments on a Google Drive file", {"file_id": {"type": "STRING", "description": "Drive file ID"}, "page_size": {"type": "INTEGER", "description": "Max comments (default 20)"}}, ["file_id"]),
    ("friday.google_clients", "drive_create_comment", "Add a comment to a Google Drive file", {"file_id": {"type": "STRING", "description": "Drive file ID"}, "content": {"type": "STRING", "description": "Comment text"}}, ["file_id", "content"]),
    ("friday.google_clients", "drive_list_permissions", "List sharing permissions for a Drive file", {"file_id": {"type": "STRING", "description": "Drive file ID"}}, ["file_id"]),
    ("friday.google_clients", "drive_create_permission", "Share a Drive file with someone via email", {"file_id": {"type": "STRING", "description": "Drive file ID"}, "email": {"type": "STRING", "description": "User's email address"}, "role": {"type": "STRING", "description": "Role: owner, writer, commenter, reader (default reader)"}, "send_notification": {"type": "BOOLEAN", "description": "Send notification email (default False)"}}, ["file_id", "email"]),
    ("friday.google_clients", "drive_list_revisions", "List revision history for a Drive file", {"file_id": {"type": "STRING", "description": "Drive file ID"}, "page_size": {"type": "INTEGER", "description": "Max revisions (default 20)"}}, ["file_id"]),

    # ── Google Forms ──
    ("friday.google_clients", "forms_list", "List accessible Google Forms", {"page_size": {"type": "INTEGER", "description": "Max forms (default 50)"}}, None),
    ("friday.google_clients", "forms_get", "Get the structure of a Google Form (questions, settings, title)", {"form_id": {"type": "STRING", "description": "Form ID"}}, ["form_id"]),
    ("friday.google_clients", "forms_list_responses", "List responses submitted to a Google Form", {"form_id": {"type": "STRING", "description": "Form ID"}}, ["form_id"]),

    # ── Google Slides Extended ──
    ("friday.google_clients", "slides_add_text_slide", "Add a slide with title and body text to a presentation", {"presentation_id": {"type": "STRING", "description": "Presentation ID"}, "title": {"type": "STRING", "description": "Slide title (optional)"}, "body": {"type": "STRING", "description": "Slide body text (optional)"}, "position": {"type": "INTEGER", "description": "Insertion index (optional)"}}, ["presentation_id"]),
    ("friday.google_clients", "slides_add_image", "Add an image from URL to a slide in a presentation", {"presentation_id": {"type": "STRING", "description": "Presentation ID"}, "image_url": {"type": "STRING", "description": "Public URL of the image"}, "slide_object_id": {"type": "STRING", "description": "Target slide object ID (optional, uses first slide)"}, "width_pt": {"type": "NUMBER", "description": "Image width in points (default 400)"}, "height_pt": {"type": "NUMBER", "description": "Image height in points (default 300)"}}, ["presentation_id", "image_url"]),

    # ── WiFi & Network Security ──
    ("friday.tools.wifi_tools", "wifi_list_profiles", "List saved WiFi network profiles on Windows", None, None),
    ("friday.tools.wifi_tools", "wifi_show_password", "Show password for a saved WiFi profile (requires admin)", {"ssid": {"type": "STRING", "description": "WiFi SSID/profile name"}}, ["ssid"]),
    ("friday.tools.wifi_tools", "wifi_scan", "Scan for nearby WiFi networks", None, None),
    ("friday.tools.wifi_tools", "wifi_connection_status", "Get current WiFi connection status", None, None),
    ("friday.tools.wifi_tools", "network_connections", "List active TCP/UDP network connections", None, None),
    ("friday.tools.wifi_tools", "arp_table", "Get ARP table showing IP-to-MAC mappings on local network", None, None),
    ("friday.tools.wifi_tools", "traceroute", "Trace network route to a target host", {"target": {"type": "STRING", "description": "Target hostname or IP"}, "max_hops": {"type": "INTEGER", "description": "Maximum hops (default 30)"}}, ["target"]),
    ("friday.tools.dns_tool", "dns_lookup", "Lookup DNS records for a domain", {"domain": {"type": "STRING", "description": "Domain to query"}, "record_type": {"type": "STRING", "description": "Record type: A, AAAA, MX, CNAME, NS, TXT, SOA, ANY (default A)"}}, ["domain"]),
    ("friday.tools.dns_tool", "dns_reverse_lookup", "Reverse DNS lookup for an IP address", {"ip": {"type": "STRING", "description": "IP address"}}, ["ip"]),

    # ── Workflow & Agent Orchestration ──
    ("friday.workflow", "create_and_run_workflow", "Decompose a complex task into a multi-agent pipeline and execute it. Agents collaborate and share results automatically. Example: 'Research quantum computing, find vulnerabilities in our site, and write a report'", {"task": {"type": "STRING", "description": "The complex task description to decompose and execute"}}, ["task"]),
    ("friday.workflow", "get_workflow", "Get the status and details of a running or completed workflow", {"wid": {"type": "STRING", "description": "Workflow ID"}}, ["wid"]),
    ("friday.workflow", "get_workflow_status_text", "Get a human-readable status summary of a workflow", {"wid": {"type": "STRING", "description": "Workflow ID"}}, ["wid"]),
    ("friday.agent_bus", "get_task_status", "Check the status of a specific agent task", {"task_id": {"type": "STRING", "description": "Task ID to check"}}, ["task_id"]),
    ("friday.agent_profiles", "list_agents", "List all available sub-agents and their capabilities", None, None),

    # ── Browser Automation (browser-use) ──
    ("friday.tools.browser_tool", "run_browser_task", "Execute an autonomous multi-step browser task using AI agent (navigate, click, fill forms, extract data)", {"task": {"type": "STRING", "description": "Natural language description of what to do in the browser"}, "llm_provider": {"type": "STRING", "description": "LLM provider: google, openai, anthropic, builtin (default google)"}, "llm_model": {"type": "STRING", "description": "Model name (default gemini-3.1-flash-live-preview)"}, "headless": {"type": "BOOLEAN", "description": "Run headless (no visible window) (default False)"}, "max_steps": {"type": "INTEGER", "description": "Max browser action steps (default 30)"}}, ["task"]),
    ("friday.tools.browser_tool", "browser_navigate", "Quick navigation: visit a URL and return page title and summary", {"url": {"type": "STRING", "description": "URL to navigate to"}, "headless": {"type": "BOOLEAN", "description": "Run headless (default False)"}}, ["url"]),
    ("friday.tools.browser_tool", "browser_extract_content", "Navigate to a URL and extract specific content from the page", {"url": {"type": "STRING", "description": "URL to visit"}, "instructions": {"type": "STRING", "description": "Specific extraction instructions (optional)"}}, ["url"]),
    ("friday.tools.browser_tool", "browser_search", "Search the web using a search engine and return top results", {"query": {"type": "STRING", "description": "Search query"}, "engine": {"type": "STRING", "description": "Search engine: google, bing, duckduckgo (default google)"}}, ["query"]),

    # ── Maigret OSINT Username Search ──
    ("friday.tools.maigret_tool", "run_maigret", "Search for a username across 3000+ platforms using maigret OSINT tool", {"username": {"type": "STRING", "description": "Target username to search"}, "top": {"type": "INTEGER", "description": "Number of top sites to check by traffic rank (default 500)"}, "tags": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Only check sites with these tags e.g. coding, social"}, "timeout": {"type": "INTEGER", "description": "Search timeout in seconds (default 60)"}}, ["username"]),

    # ── Holehe Email-to-Account Check ──
    ("friday.tools.holehe_tool", "run_holehe", "Check if an email is registered on 120+ online services using holehe", {"email": {"type": "STRING", "description": "Target email address to check"}, "timeout": {"type": "INTEGER", "description": "Check timeout in seconds (default 60)"}}, ["email"]),

    # ── Telegram OSINT (Telethon) ──
    ("friday.tools.telegram_osint_tool", "resolve_telegram_user", "Resolve a Telegram user by username or phone number", {"identifier": {"type": "STRING", "description": "Username (without @), phone number, or user ID"}, "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default 30)"}}, ["identifier"]),
    ("friday.tools.telegram_osint_tool", "scrape_telegram_channel", "Scrape recent messages from a public Telegram channel", {"channel_identifier": {"type": "STRING", "description": "Channel username or invite link"}, "limit": {"type": "INTEGER", "description": "Maximum messages to retrieve (default 50, max 1000)"}, "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default 60)"}}, ["channel_identifier"]),

    # ── GitHub OSINT (PyGithub) ──
    ("friday.tools.github_osint_tool", "github_user_info", "Get detailed GitHub user profile information including repos", {"username": {"type": "STRING", "description": "GitHub username"}, "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default 30)"}}, ["username"]),
    ("friday.tools.github_osint_tool", "github_search_users", "Search GitHub for users matching a query", {"query": {"type": "STRING", "description": "Search query (e.g. location:london language:python)"}, "limit": {"type": "INTEGER", "description": "Maximum results (default 10)"}, "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default 30)"}}, ["query"]),
    ("friday.tools.github_osint_tool", "github_search_repos", "Search GitHub for repositories matching a query", {"query": {"type": "STRING", "description": "Search query (e.g. machine learning language:python)"}, "limit": {"type": "INTEGER", "description": "Maximum results (default 10)"}, "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default 30)"}}, ["query"]),
    ("friday.tools.github_osint_tool", "github_commit_emails", "Extract email addresses from commit history of a repository", {"repo_full_name": {"type": "STRING", "description": "Repository full name (e.g. owner/repo)"}, "limit": {"type": "INTEGER", "description": "Maximum commits to scan (default 100)"}, "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default 30)"}}, ["repo_full_name"]),
    ("friday.tools.github_osint_tool", "github_org_repos", "List all repositories for a GitHub organization", {"org_name": {"type": "STRING", "description": "GitHub organization name"}, "limit": {"type": "INTEGER", "description": "Maximum repos to return (default 50)"}, "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default 30)"}}, ["org_name"]),

    # ── Naminter Username Enumeration ──
    ("friday.tools.naminter_tool", "run_naminter", "Search for a username across 500+ sites using WhatsMyName dataset via naminter", {"username": {"type": "STRING", "description": "Target username to search for"}, "timeout": {"type": "INTEGER", "description": "Search timeout in seconds (default 60)"}}, ["username"]),

    # ── Wappalyzer Web Technology Detection ──
    ("friday.tools.wappalyzer_tool", "detect_technologies", "Detect web technologies used by a website using Wappalyzer", {"url": {"type": "STRING", "description": "Website URL to analyze"}, "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default 30)"}}, ["url"]),

    # ── Search Tools (DuckDuckGo / Brave / Tavily) ──
    ("friday.tools.search_tools", "search_duckduckgo", "Search the web using DuckDuckGo (free, unlimited, no API key)", {"query": {"type": "STRING", "description": "Search query"}, "max_results": {"type": "INTEGER", "description": "Max results (default 10)"}, "region": {"type": "STRING", "description": "Region: wt-wt, us-en, uk-en, etc (default wt-wt)"}}, ["query"]),
    ("friday.tools.search_tools", "search_brave", "Search the web using Brave Search API (2000 free queries/month)", {"query": {"type": "STRING", "description": "Search query"}, "count": {"type": "INTEGER", "description": "Results per page (default 10, max 20)"}, "offset": {"type": "INTEGER", "description": "Pagination offset (default 0)"}}, ["query"]),
    ("friday.tools.search_tools", "search_tavily", "Search the web using Tavily AI Search API (1000 free queries/month)", {"query": {"type": "STRING", "description": "Search query"}, "max_results": {"type": "INTEGER", "description": "Max results (default 10)"}, "include_answer": {"type": "BOOLEAN", "description": "Include AI-generated answer summary (default True)"}}, ["query"]),
    ("friday.tools.search_tools", "search_auto", "Auto-select best available search engine (DuckDuckGo→Brave→Tavily fallback) and return results", {"query": {"type": "STRING", "description": "Search query"}, "max_results": {"type": "INTEGER", "description": "Max results (default 10)"}}, ["query"]),

    # ── Dev Tools (Ruff / ripgrep / ast-grep / Tree-sitter / Pyright) ──
    ("friday.tools.dev_tools", "lint_code", "Lint Python code with Ruff (800+ rules) and return diagnostics", {"file_path": {"type": "STRING", "description": "Path to Python file or directory"}, "select": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Specific rule codes to enable (optional)"}}, ["file_path"]),
    ("friday.tools.dev_tools", "format_code", "Format Python code with Ruff formatter (compatible with Black)", {"file_path": {"type": "STRING", "description": "Path to Python file or directory"}, "check": {"type": "BOOLEAN", "description": "Only check formatting, don't modify (default False)"}}, ["file_path"]),
    ("friday.tools.dev_tools", "search_code", "Search file contents using ripgrep (fast regex search)", {"pattern": {"type": "STRING", "description": "Regex pattern to search for"}, "path": {"type": "STRING", "description": "Directory or file to search (default .)"}, "glob": {"type": "STRING", "description": "File glob filter e.g. *.py"}, "max_results": {"type": "INTEGER", "description": "Max results (default 50)"}}, ["pattern"]),
    ("friday.tools.dev_tools", "search_ast", "Structural AST search using ast-grep (find code patterns by syntax)", {"pattern": {"type": "STRING", "description": "ast-grep pattern to match. Example: 'console.log($A)'"}, "path": {"type": "STRING", "description": "File or directory to search (default .)"}, "lang": {"type": "STRING", "description": "Language (default python)"}}, ["pattern"]),
    ("friday.tools.dev_tools", "parse_code", "Parse source code with Tree-sitter and extract functions, classes, imports", {"file_path": {"type": "STRING", "description": "Path to source file"}, "language": {"type": "STRING", "description": "Language: python, javascript, typescript, go, rust, java, cpp (auto-detect by extension if omitted)"}}, ["file_path"]),
    ("friday.tools.dev_tools", "type_check", "Type-check Python code with Pyright and return diagnostics", {"file_path": {"type": "STRING", "description": "Path to Python file or directory"}}, ["file_path"]),

    # ── Web Tools (Crawl4AI / curl_cffi / Trafilatura / Docling) ──
    ("friday.tools.web_tools", "crawl_page", "Crawl a web page and extract clean markdown content using Crawl4AI", {"url": {"type": "STRING", "description": "Page URL to crawl"}, "word_count_threshold": {"type": "INTEGER", "description": "Min words per block (default 10)"}}, ["url"]),
    ("friday.tools.web_tools", "fetch_with_fingerprint", "Fetch URL content using curl_cffi with browser TLS fingerprinting (bypasses Cloudflare)", {"url": {"type": "STRING", "description": "URL to fetch"}, "impersonate": {"type": "STRING", "description": "Browser to impersonate: chrome, safari, edge, firefox (default chrome)"}}, ["url"]),
    ("friday.tools.web_tools", "extract_text", "Extract clean text from HTML using Trafilatura (best F1 0.958)", {"url": {"type": "STRING", "description": "Page URL"}, "include_links": {"type": "BOOLEAN", "description": "Include links in output (default False)"}}, ["url"]),
    ("friday.tools.web_tools", "parse_document", "Parse PDF/DOCX/XLSX/PPTX documents to markdown using Docling (IBM AI document parser)", {"file_path": {"type": "STRING", "description": "Path to document file"}}, ["file_path"]),

    # ── AI Tools (Ollama / Diffusers / OpenRouter / Langfuse) ──
    ("friday.tools.ai_tools", "ollama_generate", "Generate a response from a local Ollama model", {"model": {"type": "STRING", "description": "Model name (default qwen2.5)"}, "prompt": {"type": "STRING", "description": "Input prompt"}, "system": {"type": "STRING", "description": "System prompt (optional)"}}, ["prompt"]),
    ("friday.tools.ai_tools", "ollama_list_models", "List available local Ollama models", None, None),
    ("friday.tools.ai_tools", "generate_image", "Generate an image from text prompt using Hugging Face Diffusers", {"prompt": {"type": "STRING", "description": "Text description of the image"}, "model_id": {"type": "STRING", "description": "HF model ID (default stabilityai/stable-diffusion-2-1)"}, "output_path": {"type": "STRING", "description": "Save path (generated if omitted)"}}, ["prompt"]),
    ("friday.tools.ai_tools", "openrouter_chat", "Chat with any model via OpenRouter (300+ models available)", {"model": {"type": "STRING", "description": "Model name (default google/gemini-3.1-flash-live-preview:free)"}, "messages": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"role": {"type": "STRING", "description": "user or assistant"}, "content": {"type": "STRING", "description": "Message content"}}}, "description": "Chat messages array"}, "temperature": {"type": "NUMBER", "description": "Sampling temperature (default 0.7)"}}, ["messages"]),
    ("friday.tools.ai_tools", "langfuse_trace", "Create a Langfuse trace for LLM observability", {"name": {"type": "STRING", "description": "Trace name"}, "metadata": {"type": "OBJECT", "description": "Optional metadata dict"}, "tags": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Optional tags"}}, ["name"]),

    # ── Storage / Database Tools (Supabase / Qdrant / e2b) ──
    ("friday.tools.storage_tools", "supabase_query", "Query a Supabase table and return rows", {"table": {"type": "STRING", "description": "Table name"}, "select": {"type": "STRING", "description": "Columns to select (default *)"}, "eq_column": {"type": "STRING", "description": "Optional equality filter column"}, "eq_value": {"type": "STRING", "description": "Optional equality filter value"}, "limit": {"type": "INTEGER", "description": "Max rows (default 100)"}}, ["table"]),
    ("friday.tools.storage_tools", "qdrant_search", "Search a Qdrant vector collection for similar vectors", {"collection_name": {"type": "STRING", "description": "Collection name"}, "query_vector": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Query embedding vector"}, "limit": {"type": "INTEGER", "description": "Max results (default 10)"}}, ["collection_name", "query_vector"]),
    ("friday.tools.storage_tools", "e2b_execute_code", "Execute code in a secure cloud sandbox via e2b", {"code": {"type": "STRING", "description": "Code to execute"}, "language": {"type": "STRING", "description": "Language: python, javascript, bash (default python)"}, "timeout": {"type": "INTEGER", "description": "Execution timeout (default 30)"}}, ["code"]),

    # ── SCM / DevOps Tools (pre-commit / PyDriller / LibCST / pip-audit) ──
    ("friday.tools.scm_tools", "run_precommit", "Run pre-commit hooks on staged or all files", {"all_files": {"type": "BOOLEAN", "description": "Run on all files, not just staged (default False)"}, "hook_id": {"type": "STRING", "description": "Specific hook ID to run (optional)"}}, None),
    ("friday.tools.scm_tools", "analyze_git_repo", "Analyze git repository history using PyDriller (commits, developers, churn)", {"repo_path": {"type": "STRING", "description": "Path to git repository (default .)"}, "max_commits": {"type": "INTEGER", "description": "Max commits to analyze (default 100)"}}, None),
    ("friday.tools.scm_tools", "codemod_python", "Apply automated code transformations to Python files using LibCST", {"file_path": {"type": "STRING", "description": "Path to Python file"}, "transformations": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"type": {"type": "STRING", "description": "Transform type: rename_function, rename_class, add_decorator, remove_decorator, add_import, replace_call"}, "old_name": {"type": "STRING", "description": "Old name (for rename operations)"}, "new_name": {"type": "STRING", "description": "New name (for rename operations)"}, "target": {"type": "STRING", "description": "Target function/class name"}, "decorator": {"type": "STRING", "description": "Decorator text (for add/remove decorator)"}, "import_statement": {"type": "STRING", "description": "Import to add (for add_import)"}, "old_call": {"type": "STRING", "description": "Old call pattern (for replace_call)"}, "new_call": {"type": "STRING", "description": "New call pattern (for replace_call)"}}}, "description": "List of transformation operations"}}, ["file_path", "transformations"]),
    ("friday.tools.scm_tools", "audit_dependencies", "Audit Python project dependencies for known CVEs using pip-audit", {"project_path": {"type": "STRING", "description": "Path to project directory (default .)"}, "requirements_file": {"type": "STRING", "description": "Path to requirements file (optional)"}}, None),

    # ── Google Cloud Natural Language ──
    ("friday.google_clients", "nlp_extract_entities", "Extract entities (people, places, orgs, events, products) from text using Cloud NLP", {"text": {"type": "STRING", "description": "Text to analyze"}}, ["text"]),
    ("friday.google_clients", "nlp_analyze_sentiment", "Analyze sentiment of text — returns score (-1 to 1) and magnitude", {"text": {"type": "STRING", "description": "Text to analyze"}}, ["text"]),
    ("friday.google_clients", "nlp_classify_content", "Classify text into content categories (e.g. /Technology & Computing)", {"text": {"type": "STRING", "description": "Text to classify"}}, ["text"]),
    ("friday.google_clients", "nlp_analyze_syntax", "Analyze syntax — tokens with part-of-speech tags and dependency parse", {"text": {"type": "STRING", "description": "Text to analyze"}}, ["text"]),

    # ── Google People / Contacts — Extended ──
    ("friday.google_clients", "people_get", "Get detailed contact info (addresses, birthdays, organizations, relations, skills, events)", {"resource_name": {"type": "STRING", "description": "Resource name e.g. people/12345"}}, ["resource_name"]),
    ("friday.google_clients", "people_update_contact", "Update a contact's name, email, or phone", {"resource_name": {"type": "STRING", "description": "Resource name e.g. people/12345"}, "name": {"type": "STRING", "description": "New name (optional)"}, "email": {"type": "STRING", "description": "New email (optional)"}, "phone": {"type": "STRING", "description": "New phone (optional)"}}, ["resource_name"]),
    ("friday.google_clients", "people_delete_contact", "Delete a contact", {"resource_name": {"type": "STRING", "description": "Resource name to delete"}}, ["resource_name"]),

    # ── Google Photos — Extended ──
    ("friday.google_clients", "photos_get_media_item", "Get a single photo/video with full EXIF metadata (camera make/model, GPS, aperture, ISO, flash)", {"media_item_id": {"type": "STRING", "description": "Media item ID"}}, ["media_item_id"]),

    # ── Google Maps — Place Details ──
    ("friday.google_clients", "maps_place_details", "Get place details including photos, reviews, opening hours, price level, phone, website", {"place_id": {"type": "STRING", "description": "Google Place ID"}}, ["place_id"]),

    # ── Google Docs — Advanced editing ──
    ("friday.google_clients", "docs_batch_update", "Apply multiple updates to a Google Doc (insertText, insertInlineImage, updateTextStyle, etc.)", {"document_id": {"type": "STRING", "description": "Document ID"}, "requests_list": {"type": "ARRAY", "items": {"type": "OBJECT"}, "description": "List of update requests"}}, ["document_id", "requests_list"]),
    ("friday.google_clients", "docs_insert_image", "Insert an inline image at a position in a Google Doc", {"document_id": {"type": "STRING", "description": "Document ID"}, "image_url": {"type": "STRING", "description": "Public URL of image"}, "index": {"type": "INTEGER", "description": "Insertion position index (default 0)"}}, ["document_id", "image_url"]),

    # ── Google Forms — Creator ──
    ("friday.google_clients", "forms_create", "Create a Google Form with questions. Supports SHORT_ANSWER, PARAGRAPH, MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN, LINEAR_SCALE, DATE, TIME.", {"title": {"type": "STRING", "description": "Form title"}, "description": {"type": "STRING", "description": "Form description (optional)"}, "questions": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"title": {"type": "STRING", "description": "Question text"}, "type": {"type": "STRING", "description": "Question type: SHORT_ANSWER, PARAGRAPH, MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN, LINEAR_SCALE, DATE, TIME"}, "options": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Choice options (for choice types or scale labels)"}, "required": {"type": "BOOLEAN", "description": "Whether question is required"}}}, "description": "List of questions (optional)"}, "collect_email": {"type": "BOOLEAN", "description": "Collect respondent email (default False)"}}, ["title"]),

    # ── Google Search Console ──
    ("friday.google_clients", "searchconsole_list_sites", "List sites verified in Google Search Console", None, None),
    ("friday.google_clients", "searchconsole_query", "Get Search Analytics data (clicks, impressions, CTR, position) for a verified site", {"site_url": {"type": "STRING", "description": "Verified site URL"}, "start_date": {"type": "STRING", "description": "Start date (default 7daysAgo)"}, "end_date": {"type": "STRING", "description": "End date (default today)"}, "dimension": {"type": "STRING", "description": "Dimension: query, page, country, device, date (default query)"}, "row_limit": {"type": "INTEGER", "description": "Max rows (default 10)"}}, ["site_url"]),

    # ── Browser-Use Bridge (AI-native web browsing) ──
    ("friday.browser_use_bridge", "browser_use_navigate", "Full autonomous browser agent via browser-use. Give a natural language task — the AI handles navigation, clicks, forms, extraction, multi-step planning.", {"task": {"type": "STRING", "description": "Natural language task"}, "max_steps": {"type": "INTEGER", "description": "Max action steps (default 20)"}}, ["task"]),
    ("friday.browser_use_bridge", "browser_use_extract", "Extract structured information from web pages using browser-use AI agent.", {"task": {"type": "STRING", "description": "Navigation + what to extract"}, "instruction": {"type": "STRING", "description": "Extraction guidance"}}, ["task"]),
    ("friday.browser_use_bridge", "browser_use_click", "Click an element on the page by CSS selector or visible text.", {"selector": {"type": "STRING", "description": "CSS selector"}, "text": {"type": "STRING", "description": "Visible text to click"}}, None),
    ("friday.browser_use_bridge", "browser_use_type", "Type text into an input field.", {"selector": {"type": "STRING", "description": "CSS selector"}, "text": {"type": "STRING", "description": "Text to type"}, "clear_first": {"type": "BOOLEAN", "description": "Clear field first (default true)"}}, ["selector", "text"]),
    ("friday.browser_use_bridge", "browser_use_extract_text", "Extract visible text from the page or element.", {"selector": {"type": "STRING", "description": "CSS selector (default body)"}}, None),
    ("friday.browser_use_bridge", "browser_use_extract_html", "Extract full HTML of the current page.", None, None),
    ("friday.browser_use_bridge", "browser_use_extract_links", "Extract all links from the current page.", None, None),
    ("friday.browser_use_bridge", "browser_use_screenshot", "Take a screenshot of the current page (returns base64 PNG).", {"full_page": {"type": "BOOLEAN", "description": "Full page capture (default false)"}}, None),
    ("friday.browser_use_bridge", "browser_use_scroll", "Scroll the page up or down.", {"direction": {"type": "STRING", "description": "down or up (default down)"}, "amount": {"type": "INTEGER", "description": "Pixels (default 500)"}}, None),
    ("friday.browser_use_bridge", "browser_use_evaluate", "Run JavaScript in the page context.", {"script": {"type": "STRING", "description": "JavaScript code"}}, ["script"]),
    ("friday.browser_use_bridge", "browser_use_get_dom_state", "Get DOM state: URL, title, viewport, link/button/input counts.", None, None),
    ("friday.browser_use_bridge", "browser_use_get_url", "Get the current page URL.", None, None),
    ("friday.browser_use_bridge", "browser_use_get_title", "Get the current page title.", None, None),
    ("friday.browser_use_bridge", "browser_use_list_tabs", "List all open browser tabs.", None, None),
    ("friday.browser_use_bridge", "browser_use_new_tab", "Open a new tab with optional URL.", {"url": {"type": "STRING", "description": "URL to open (default about:blank)"}}, None),
    ("friday.browser_use_bridge", "browser_use_close_tab", "Close the current browser tab.", None, None),
    ("friday.browser_use_bridge", "browser_use_go_back", "Navigate back in browser history.", None, None),
    ("friday.browser_use_bridge", "browser_use_go_forward", "Navigate forward in browser history.", None, None),
    ("friday.browser_use_bridge", "browser_use_status", "Show browser-use bridge status.", None, None),
    ("friday.browser_use_bridge", "browser_use_clear", "Close browser and clear session.", None, None),
    ("friday.browser_use_bridge", "browser_use_reconnect", "Force-reconnect the browser.", None, None),

    # ── Cookbook (Hardware Scanner + Model Recommendations) ──
    ("friday.cookbook", "cookbook_scan", "Scan local hardware (GPU, VRAM, RAM) and show system specs.", {"force": {"type": "BOOLEAN", "description": "Re-scan instead of cache"}}, None),
    ("friday.cookbook", "cookbook_recommend", "Recommend the best local AI models based on detected GPU/VRAM.", None, None),
    ("friday.cookbook", "cookbook_ollama_check", "Check if Ollama is installed and list local models.", None, None),

    # ── Proactive Copilot (Desktop-aware suggestions) ──
    ("friday.proactive_copilot", "proactive_suggest", "Get a proactive suggestion based on desktop context (active window, clipboard, files).", {"force": {"type": "BOOLEAN", "description": "Bypass cooldown"}}, None),
    ("friday.proactive_copilot", "proactive_status", "Show proactive copilot status.", None, None),
    ("friday.proactive_copilot", "proactive_copilot_enable", "Enable or disable the proactive copilot.", {"enabled": {"type": "BOOLEAN", "description": "True to enable, False to disable"}}, None),
    ("friday.proactive_copilot", "proactive_context", "Get current desktop context: active window, clipboard, recent files.", None, None),

    # ── Agent Heartbeat Protocol ──
    ("friday.agent_heartbeat", "agent_heartbeat_status", "Get real-time status of all agents via heartbeat protocol.", None, None),
    ("friday.agent_heartbeat", "agent_heartbeat_get", "Get heartbeat for a specific agent.", {"agent_id": {"type": "STRING", "description": "Agent ID"}}, ["agent_id"]),
    ("friday.agent_heartbeat", "agent_heartbeat_add_trigger", "Add cross-agent trigger: when source_role finds keyword, spawn task for target_agent.", {"trigger_id": {"type": "STRING", "description": "Unique trigger ID"}, "source_role": {"type": "STRING", "description": "Source agent role (researcher, coder, security, general)"}, "keyword": {"type": "STRING", "description": "Keyword to match in agent findings"}, "target_agent": {"type": "STRING", "description": "Target agent name"}, "target_task_template": {"type": "STRING", "description": "Task template with {finding} and {source_agent} placeholders"}}, ["trigger_id", "source_role", "keyword", "target_agent", "target_task_template"]),
    ("friday.agent_heartbeat", "agent_heartbeat_remove_trigger", "Remove a cross-agent trigger.", {"trigger_id": {"type": "STRING", "description": "Trigger ID to remove"}}, ["trigger_id"]),
    ("friday.agent_heartbeat", "agent_heartbeat_list_triggers", "List all registered cross-agent triggers.", None, None),
    ("friday.agent_heartbeat", "agent_heartbeat_route_finding", "Manually route a finding from one agent as a task for another.", {"source_agent_id": {"type": "STRING", "description": "Source agent"}, "finding": {"type": "STRING", "description": "The finding"}, "target_agent_id": {"type": "STRING", "description": "Target agent"}, "task_description": {"type": "STRING", "description": "Task for target"}}, ["source_agent_id", "finding", "target_agent_id", "task_description"]),
    ("friday.agent_heartbeat", "heartbeat_daemon_start", "Start the background heartbeat daemon that tracks all agents.", None, None),
    ("friday.agent_heartbeat", "heartbeat_daemon_stop", "Stop the background heartbeat daemon.", None, None),

    # ── Paperclip Adapter ──
    ("friday.paperclip_adapter", "paperclip_adapter_start", "Start FRIDAY as a Paperclip-compatible agent in background thread.", {"agent_id": {"type": "STRING", "description": "Agent ID (default friday-agent)"}, "company": {"type": "STRING", "description": "Company name (default default)"}, "role": {"type": "STRING", "description": "Agent role (default general)"}}, None),
    ("friday.paperclip_adapter", "paperclip_adapter_stop", "Stop the Paperclip adapter.", None, None),
    ("friday.paperclip_adapter", "paperclip_adapter_status", "Check if the Paperclip adapter is running.", None, None),
    ("friday.paperclip_adapter", "paperclip_adapter_register", "Register FRIDAY as a Paperclip agent with capabilities.", {"company": {"type": "STRING", "description": "Company name"}, "role": {"type": "STRING", "description": "Role"}, "display_name": {"type": "STRING", "description": "Display name (default FRIDAY AI)"}}, None),
    ("friday.paperclip_adapter", "paperclip_adapter_submit_task", "Submit a task directly to the Paperclip adapter.", {"description": {"type": "STRING", "description": "Task description"}, "task_type": {"type": "STRING", "description": "Task type (research, deep_research, code, security, browse, scan, suggest, general)"}}, ["description"]),
]


def build_new_tools(types_module) -> list:
    """Generate types.FunctionDeclaration list for all new tools."""
    declarations = []
    for module_path, func_name, desc, params_schema, required in TOOL_DESCRIPTORS:
        schema = None
        if params_schema:
            schema = types_module.Schema(type="OBJECT", properties=params_schema, required=required or [])
        declarations.append(
            types_module.FunctionDeclaration(name=func_name, description=desc, parameters=schema)
        )
    # Merge osint_extra tools (481 functions, dynamically introspected)
    try:
        from friday.tools.osint_extra_bridge import build_osint_extra_tools
        declarations.extend(build_osint_extra_tools(types_module))
    except Exception:
        pass
    return declarations


def build_new_tool_map() -> dict[str, Any]:
    """Build a dict mapping tool names to their functions by lazy-importing modules."""
    tool_map = {}
    for module_path, func_name, _, _, _ in TOOL_DESCRIPTORS:
        tool_map[func_name] = _LazyToolFunc(module_path, func_name)
    # Merge osint_extra tool map
    try:
        from friday.tools.osint_extra_bridge import build_osint_extra_tool_map
        tool_map.update(build_osint_extra_tool_map())
    except Exception:
        pass
    return tool_map


class _LazyToolFunc:
    """Lazily imports and calls the actual function when invoked.
    Handles both sync and async functions transparently."""
    def __init__(self, module_path: str, func_name: str):
        self._module_path = module_path
        self._func_name = func_name
        self._func = None

    def _load(self):
        if self._func is None:
            import importlib
            mod = importlib.import_module(self._module_path)
            self._func = getattr(mod, self._func_name)

    def __call__(self, **kwargs):
        self._load()
        try:
            result = self._func(**kwargs)
        except TypeError as e:
            # Some tools expect positional args or different patterns
            try:
                result = self._func(**{k: v for k, v in kwargs.items() if v is not None})
            except Exception:
                result = self._func(kwargs)
        if result is not None and hasattr(result, '__await__'):
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, result)
                return future.result(timeout=300)
        return result
