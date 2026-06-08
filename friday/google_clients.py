"""
Google API client wrappers — makes every granted OAuth scope actually usable.
All functions use the unified google_oauth module for auth.
"""
from __future__ import annotations

import base64
import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from friday.google_oauth import call_api, get_access_token
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Google Drive
# ═══════════════════════════════════════════════════════════════════

def drive_list(folder_id: str = "root", page_size: int = 20) -> list[dict]:
    """List files and folders in a Drive folder."""
    params = {
        "q": f"'{folder_id}' in parents and trashed=false",
        "pageSize": min(page_size, 100),
        "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink)",
    }
    data = call_api("https://www.googleapis.com/drive/v3/files", params=params)
    if not data:
        return []
    return data.get("files", [])


def drive_search(query: str, page_size: int = 20) -> list[dict]:
    """Search Drive for files matching query."""
    params = {
        "q": f"name contains '{query}' and trashed=false",
        "pageSize": min(page_size, 100),
        "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink)",
    }
    data = call_api("https://www.googleapis.com/drive/v3/files", params=params)
    if not data:
        return []
    return data.get("files", [])


def drive_upload(file_path: str, mime_type: Optional[str] = None,
                 parent_folder_id: Optional[str] = None) -> dict:
    """Upload a file to Google Drive."""
    import requests
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    metadata: dict[str, Any] = {"name": path.name}
    if parent_folder_id:
        metadata["parents"] = [parent_folder_id]
    if not mime_type:
        import mimetypes
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    try:
        from requests_toolbelt import MultipartEncoder
        encoder = MultipartEncoder(
            fields={
                "metadata": json.dumps(metadata),
                "file": (path.name, path.read_bytes(), mime_type),
            }
        )
        r = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            data=encoder,
            headers={"Authorization": f"Bearer {token}", "Content-Type": encoder.content_type},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning("Drive upload failed: %s", exc)
        # Fallback to simple upload
        try:
            r = requests.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=media",
                data=path.read_bytes(),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": mime_type,
                },
                timeout=60,
            )
            r.raise_for_status()
            file_id = r.json().get("id")
            # Set metadata
            requests.patch(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"name": path.name, "parents": [parent_folder_id]} if parent_folder_id else {"name": path.name},
                timeout=15,
            )
            return {"id": file_id, "name": path.name}
        except Exception as exc2:
            return {"error": f"Upload failed: {exc2}"}


def drive_download(file_id: str, output_path: str) -> dict:
    """Download a file from Google Drive."""
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    meta = call_api(f"https://www.googleapis.com/drive/v3/files/{file_id}",
                     params={"fields": "name,mimeType"})
    if not meta:
        return {"error": "File not found"}
    out = Path(output_path)
    if out.is_dir():
        out = out / meta.get("name", "downloaded_file")
    try:
        r = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        r.raise_for_status()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)
        return {"path": str(out), "size": len(r.content), "mimeType": meta.get("mimeType")}
    except Exception as exc:
        return {"error": str(exc)}


def drive_create_folder(name: str, parent_folder_id: Optional[str] = None) -> dict:
    """Create a folder in Google Drive."""
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_folder_id:
        body["parents"] = [parent_folder_id]
    return call_api("https://www.googleapis.com/drive/v3/files", method="POST",
                     json_body=body) or {"error": "Failed to create folder"}


def drive_delete(file_id: str) -> dict:
    """Move a file to Drive trash."""
    result = call_api(f"https://www.googleapis.com/drive/v3/files/{file_id}",
                       method="DELETE")
    return {"ok": result is None}  # DELETE returns 204 No Content on success


# ═══════════════════════════════════════════════════════════════════
#  Google Sheets
# ═══════════════════════════════════════════════════════════════════

def sheets_create(title: str, sheets: Optional[list[str]] = None) -> dict:
    """Create a new Google Sheet."""
    body: dict = {"properties": {"title": title}}
    if sheets:
        body["sheets"] = [{"properties": {"title": s}} for s in sheets]
    return call_api("https://sheets.googleapis.com/v4/spreadsheets",
                     method="POST", json_body=body) or {"error": "Failed to create sheet"}


def sheets_read(spreadsheet_id: str, range_name: str = "Sheet1") -> list[list[str]]:
    """Read values from a sheet range."""
    data = call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"
    )
    if not data:
        return []
    return data.get("values", [])


def sheets_write(spreadsheet_id: str, range_name: str, values: list[list[str]]) -> dict:
    """Write values to a sheet range."""
    body = {"values": values}
    result = call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}?valueInputOption=USER_ENTERED",
        method="PUT", json_body=body,
    )
    return result or {"error": "Write failed"}


def sheets_append(spreadsheet_id: str, range_name: str, values: list[list[str]]) -> dict:
    """Append rows to a sheet."""
    body = {"values": values}
    result = call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS",
        method="POST", json_body=body,
    )
    return result or {"error": "Append failed"}


def sheets_list(spreadsheet_id: str) -> list[dict]:
    """List all sheets in a spreadsheet."""
    data = call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?fields=sheets.properties"
    )
    if not data:
        return []
    return [s["properties"] for s in data.get("sheets", [])]


# ═══════════════════════════════════════════════════════════════════
#  Google Docs
# ═══════════════════════════════════════════════════════════════════

def docs_create(title: str, content: str = "") -> dict:
    """Create a new Google Doc."""
    body = {
        "title": title,
    }
    doc = call_api("https://docs.googleapis.com/v1/documents", method="POST", json_body=body)
    if not doc or "error" in doc:
        return doc or {"error": "Failed to create doc"}
    if content:
        _docs_append_text(doc.get("documentId", ""), content)
    return doc


def docs_read(document_id: str) -> dict:
    """Read a Google Doc's content."""
    data = call_api(f"https://docs.googleapis.com/v1/documents/{document_id}")
    if not data:
        return {"error": "Doc not found"}
    body = data.get("body", {})
    text = _docs_extract_text(body.get("content", []))
    return {
        "documentId": document_id,
        "title": data.get("title", ""),
        "text": text,
    }


def docs_append_text(document_id: str, text: str) -> dict:
    """Append text to the end of a Google Doc."""
    return _docs_append_text(document_id, text)


def _docs_extract_text(elements: list[dict]) -> str:
    """Extract plain text from Docs API structural elements."""
    texts = []
    for el in elements:
        if "paragraph" in el:
            for pe in el["paragraph"].get("elements", []):
                if "textRun" in pe:
                    texts.append(pe["textRun"].get("content", ""))
        if "table" in el:
            for row in el["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    texts.append(_docs_extract_text(cell.get("content", [])))
        if "tableOfContents" in el:
            texts.append(_docs_extract_text(el["tableOfContents"].get("content", [])))
    return "".join(texts)


def _docs_append_text(document_id: str, text: str) -> dict:
    """Internal: batchUpdate to insert text at end of doc."""
    result = call_api(
        f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
        method="POST",
        json_body={
            "requests": [{
                "insertText": {
                    "location": {"index": 1},
                    "text": text,
                }
            }]
        },
    )
    return result or {"error": "Append failed"}


# ═══════════════════════════════════════════════════════════════════
#  Google Slides
# ═══════════════════════════════════════════════════════════════════

def slides_create(title: str) -> dict:
    """Create a new Google Slides presentation."""
    body = {"title": title}
    return call_api("https://slides.googleapis.com/v1/presentations",
                     method="POST", json_body=body) or {"error": "Failed to create slides"}


def slides_read(presentation_id: str) -> dict:
    """Read slide metadata and content."""
    data = call_api(f"https://slides.googleapis.com/v1/presentations/{presentation_id}")
    if not data:
        return {"error": "Presentation not found"}
    slides_list = []
    for slide in data.get("slides", []):
        slide_info = {"objectId": slide.get("objectId"), "title": "", "text": ""}
        for pe in slide.get("pageElements", []):
            shape = pe.get("shape", {})
            text = shape.get("text", {})
            for te in text.get("textElements", []):
                if "textRun" in te:
                    slide_info["text"] += te["textRun"].get("content", "")
        slides_list.append(slide_info)
    return {
        "presentationId": presentation_id,
        "title": data.get("title", ""),
        "slides": slides_list,
    }


def slides_add_slide(presentation_id: str, title: str = "", body: str = "") -> dict:
    """Add a slide with optional title and body to a presentation."""
    requests_list = [{
        "createSlide": {
            "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
        }
    }]
    result = call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST",
        json_body={"requests": requests_list},
    )
    if not result:
        return {"error": "Failed to add slide"}
    new_slide_id = None
    for reply in result.get("replies", []):
        if "createSlide" in reply:
            new_slide_id = reply["createSlide"].get("objectId")
    if title and new_slide_id:
        _slides_replace_text(presentation_id, new_slide_id, title, body)
    return result


def _slides_replace_text(presentation_id: str, slide_id: str,
                         title: str, body: str) -> dict:
    """Replace placeholder text in a slide."""
    requests_list = []
    if title:
        requests_list.append({
            "insertText": {
                "objectId": slide_id,
                "insertionIndex": 0,
                "text": title,
            }
        })
    if body:
        requests_list.append({
            "insertText": {
                "objectId": slide_id,
                "insertionIndex": len(title),
                "text": f"\n{body}",
            }
        })
    if requests_list:
        return call_api(
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
            method="POST",
            json_body={"requests": requests_list},
        ) or {}
    return {}


# ═══════════════════════════════════════════════════════════════════
#  Google People / Contacts
# ═══════════════════════════════════════════════════════════════════

def people_list(page_size: int = 20) -> list[dict]:
    """List authenticated user's contacts."""
    params = {
        "pageSize": min(page_size, 100),
        "personFields": "names,emailAddresses,phoneNumbers,photos,organizations",
    }
    data = call_api("https://people.googleapis.com/v1/people/me/connections",
                     params=params)
    if not data:
        return []
    return data.get("connections", [])


def people_search(query: str, page_size: int = 20) -> list[dict]:
    """Search contacts by name or email."""
    # People API search is limited; we list and filter client-side
    all_contacts = people_list(100)
    query_lower = query.lower()
    results = []
    for c in all_contacts:
        names = [n.get("displayName", "").lower() for n in c.get("names", [])]
        emails = [e.get("value", "").lower() for e in c.get("emailAddresses", [])]
        if any(query_lower in n for n in names) or any(query_lower in e for e in emails):
            results.append(c)
    return results[:page_size]


def people_create_contact(name: str, email: Optional[str] = None,
                          phone: Optional[str] = None) -> dict:
    """Create a new contact."""
    body: dict = {"names": [{"givenName": name}]}
    if email:
        body["emailAddresses"] = [{"value": email}]
    if phone:
        body["phoneNumbers"] = [{"value": phone}]
    return call_api("https://people.googleapis.com/v1/people:createContact",
                     method="POST", json_body=body) or {"error": "Failed to create contact"}


# ═══════════════════════════════════════════════════════════════════
#  Google Maps (Geocoding, Places, Directions, Elevation)
# ═══════════════════════════════════════════════════════════════════

def maps_geocode(address: str) -> list[dict]:
    """Geocode an address to lat/lng."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    data = call_api(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": address, "key": api_key},
    )
    if not data:
        return []
    return data.get("results", [])


def maps_reverse_geocode(lat: float, lng: float) -> list[dict]:
    """Reverse geocode lat/lng to address."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    data = call_api(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"latlng": f"{lat},{lng}", "key": api_key},
    )
    if not data:
        return []
    return data.get("results", [])


def maps_places_search(query: str, location: Optional[str] = None,
                       radius: int = 5000) -> list[dict]:
    """Search for places using Google Places API."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    params: dict = {"query": query, "key": api_key}
    if location:
        params["location"] = location
        params["radius"] = radius
    data = call_api(
        "https://maps.googleapis.com/maps/api/place/textsearch/json",
        params=params,
    )
    if not data:
        return []
    return data.get("results", [])


def maps_directions(origin: str, destination: str, mode: str = "driving") -> list[dict]:
    """Get directions between two points."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    data = call_api(
        "https://maps.googleapis.com/maps/api/directions/json",
        params={
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "key": api_key,
        },
    )
    if not data:
        return []
    return data.get("routes", [])


def maps_elevation(locations: str) -> list[dict]:
    """Get elevation data for locations (comma-separated lat,lng pairs)."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    data = call_api(
        "https://maps.googleapis.com/maps/api/elevation/json",
        params={"locations": locations, "key": api_key},
    )
    if not data:
        return []
    return data.get("results", [])


# ═══════════════════════════════════════════════════════════════════
#  Google Cloud Platform (BigQuery, Cloud Storage, Vision, Translate, TTS, STT)
# ═══════════════════════════════════════════════════════════════════

def bigquery_query(sql: str, project_id: Optional[str] = None) -> list[dict]:
    """Run a BigQuery SQL query and return results."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    body = {
        "query": sql,
        "useLegacySql": False,
    }
    if pid:
        body["requestId"] = pid
    data = call_api(
        f"https://bigquery.googleapis.com/bigquery/v2/projects/{pid or 'none'}/queries",
        method="POST", json_body=body, timeout=30,
    )
    if not data:
        return []
    rows = []
    for row in data.get("rows", []):
        rows.append({f["name"]: f.get("v", "") for f in data.get("schema", {}).get("fields", [])})
        # Map values from row
        for i, cell in enumerate(row.get("f", [])):
            fields = data.get("schema", {}).get("fields", [])
            if i < len(fields):
                rows[-1][fields[i]["name"]] = cell.get("v", "")
    return rows


def storage_list(bucket: str, prefix: str = "") -> list[dict]:
    """List objects in a Cloud Storage bucket."""
    params: dict = {"bucket": bucket}
    if prefix:
        params["prefix"] = prefix
    data = call_api(
        "https://storage.googleapis.com/storage/v1/b",
        params={"project": os.getenv("GOOGLE_CLOUD_PROJECT", "")},
    )
    if not data:
        return []
    # List objects in specific bucket
    objects = call_api(
        f"https://storage.googleapis.com/storage/v1/b/{bucket}/o",
        params={"prefix": prefix},
    )
    if not objects:
        return []
    return objects.get("items", [])


def storage_upload(bucket: str, file_path: str, dest_path: Optional[str] = None) -> dict:
    """Upload a file to Cloud Storage."""
    import requests
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    dest = dest_path or path.name
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    try:
        r = requests.post(
            f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o?uploadType=media&name={dest}",
            data=path.read_bytes(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def vision_annotate(image_path: str, features: Optional[list[str]] = None) -> dict:
    """Annotate an image using Cloud Vision API."""
    import requests
    path = Path(image_path)
    if not path.exists():
        return {"error": f"File not found: {image_path}"}
    image_data = base64.b64encode(path.read_bytes()).decode()
    if not features:
        features = ["LABEL_DETECTION", "TEXT_DETECTION", "SAFE_SEARCH_DETECTION"]
    body = {
        "requests": [{
            "image": {"content": image_data},
            "features": [{"type": f, "maxResults": 20} for f in features],
        }]
    }
    data = call_api(
        "https://vision.googleapis.com/v1/images:annotate",
        method="POST", json_body=body, timeout=30,
    )
    if not data:
        return {}
    responses = data.get("responses", [])
    if not responses:
        return {}
    return responses[0]


def translate_text(text: str, target_language: str = "en",
                   source_language: Optional[str] = None) -> dict:
    """Translate text using Google Cloud Translation API."""
    body: dict = {
        "q": text,
        "target": target_language,
    }
    if source_language:
        body["source"] = source_language
    data = call_api(
        "https://translation.googleapis.com/language/translate/v2",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Translation failed"}
    translations = data.get("data", {}).get("translations", [])
    if translations:
        return translations[0]
    return {}


def translate_detect_language(text: str) -> list[dict]:
    """Detect the language of text using Translation API."""
    data = call_api(
        "https://translation.googleapis.com/language/translate/v2/detect",
        method="POST", json_body={"q": text},
    )
    if not data:
        return []
    return data.get("data", {}).get("detections", [])


def tts_synthesize(text: str, language: str = "en-US",
                   voice_name: str = "en-US-Wavenet-D",
                   output_path: str = "output.mp3") -> dict:
    """Convert text to speech using Cloud Text-to-Speech API."""
    body = {
        "input": {"text": text},
        "voice": {"languageCode": language, "name": voice_name},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.0},
    }
    data = call_api(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        method="POST", json_body=body, timeout=30,
    )
    if not data:
        return {"error": "TTS synthesis failed"}
    audio_content = data.get("audioContent", "")
    if audio_content:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(base64.b64decode(audio_content))
        return {"path": str(out), "size": len(audio_content), "format": "MP3"}
    return data


def stt_transcribe(audio_path: str, language: str = "en-US") -> dict:
    """Transcribe speech to text using Cloud Speech-to-Text API."""
    import requests
    path = Path(audio_path)
    if not path.exists():
        return {"error": f"File not found: {audio_path}"}
    audio_data = base64.b64encode(path.read_bytes()).decode()
    body = {
        "config": {
            "languageCode": language,
            "encoding": "MP3" if path.suffix.lower() == ".mp3" else "LINEAR16",
        },
        "audio": {"content": audio_data},
    }
    data = call_api(
        "https://speech.googleapis.com/v1/speech:recognize",
        method="POST", json_body=body, timeout=60,
    )
    if not data:
        return {"error": "Transcription failed"}
    results = data.get("results", [])
    transcriptions = []
    for r in results:
        for alt in r.get("alternatives", []):
            transcriptions.append({
                "transcript": alt.get("transcript", ""),
                "confidence": alt.get("confidence", 0),
            })
    return {"transcriptions": transcriptions, "total_results": len(results)}


# ═══════════════════════════════════════════════════════════════════
#  Firebase (Firestore)
# ═══════════════════════════════════════════════════════════════════

def firestore_get(collection: str, document_id: str, project_id: Optional[str] = None) -> dict:
    """Get a Firestore document by ID."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/{collection}/{document_id}"
    )
    if not data:
        return {"error": "Document not found"}
    if "error" in data:
        return data
    fields = data.get("fields", {})
    return {
        "id": data.get("name", "").split("/")[-1],
        "fields": _firestore_decode_fields(fields),
        "createTime": data.get("createTime"),
        "updateTime": data.get("updateTime"),
    }


def firestore_query(collection: str, project_id: Optional[str] = None) -> list[dict]:
    """List all documents in a Firestore collection (simple query)."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/{collection}"
    )
    if not data:
        return []
    docs = []
    for doc in data.get("documents", []):
        fields = doc.get("fields", {})
        docs.append({
            "id": doc.get("name", "").split("/")[-1],
            "fields": _firestore_decode_fields(fields),
            "createTime": doc.get("createTime"),
            "updateTime": doc.get("updateTime"),
        })
    return docs


def firestore_set(collection: str, document_id: str, data_dict: dict,
                  project_id: Optional[str] = None) -> dict:
    """Create or overwrite a Firestore document."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    body = {"fields": _firestore_encode_fields(data_dict)}
    result = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/{collection}?documentId={document_id}",
        method="POST", json_body=body,
    )
    return result or {"error": "Failed to set document"}


def firestore_delete(collection: str, document_id: str,
                     project_id: Optional[str] = None) -> dict:
    """Delete a Firestore document."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    result = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/{collection}/{document_id}",
        method="DELETE",
    )
    return {"ok": result is None}


def _firestore_decode_fields(fields: dict) -> dict:
    """Decode Firestore Value objects back to plain types."""
    result = {}
    type_map = {
        "stringValue": str,
        "integerValue": lambda x: int(x) if x else 0,
        "doubleValue": float,
        "booleanValue": bool,
        "timestampValue": str,
        "referenceValue": str,
        "geoPointValue": str,
    }
    for key, value in fields.items():
        for type_key, converter in type_map.items():
            if type_key in value:
                result[key] = converter(value[type_key])
                break
            if "mapValue" in value:
                result[key] = _firestore_decode_fields(value["mapValue"].get("fields", {}))
                break
            if "arrayValue" in value:
                result[key] = [_firestore_decode_fields({"item": v})["item"]
                              for v in value["arrayValue"].get("values", [])]
                break
    return result


def _firestore_encode_fields(data: dict) -> dict:
    """Encode plain types to Firestore Value objects."""
    fields = {}
    for key, value in data.items():
        if isinstance(value, str):
            fields[key] = {"stringValue": value}
        elif isinstance(value, bool):
            fields[key] = {"booleanValue": value}
        elif isinstance(value, int):
            fields[key] = {"integerValue": str(value)}
        elif isinstance(value, float):
            fields[key] = {"doubleValue": value}
        elif isinstance(value, dict):
            fields[key] = {"mapValue": {"fields": _firestore_encode_fields(value)}}
        elif isinstance(value, list):
            fields[key] = {
                "arrayValue": {
                    "values": [_firestore_encode_fields({"": v})[""] for v in value]
                }
            }
        else:
            fields[key] = {"stringValue": str(value)}
    return fields


# ═══════════════════════════════════════════════════════════════════
#  Google Books
# ═══════════════════════════════════════════════════════════════════

def books_search(query: str, max_results: int = 10) -> list[dict]:
    """Search Google Books."""
    data = call_api(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": query, "maxResults": min(max_results, 40)},
    )
    if not data:
        return []
    items = data.get("items", [])
    results = []
    for item in items:
        vol = item.get("volumeInfo", {})
        results.append({
            "id": item.get("id"),
            "title": vol.get("title"),
            "authors": vol.get("authors", []),
            "description": (vol.get("description") or "")[:500],
            "categories": vol.get("categories", []),
            "pageCount": vol.get("pageCount"),
            "publishedDate": vol.get("publishedDate"),
            "publisher": vol.get("publisher"),
            "thumbnail": vol.get("imageLinks", {}).get("thumbnail"),
        })
    return results


def books_get_volume(volume_id: str) -> dict:
    """Get detailed info about a specific book."""
    data = call_api(f"https://www.googleapis.com/books/v1/volumes/{volume_id}")
    if not data:
        return {"error": "Volume not found"}
    vol = data.get("volumeInfo", {})
    return {
        "id": data.get("id"),
        "title": vol.get("title"),
        "authors": vol.get("authors", []),
        "description": (vol.get("description") or "")[:1000],
        "categories": vol.get("categories", []),
        "pageCount": vol.get("pageCount"),
        "publishedDate": vol.get("publishedDate"),
        "publisher": vol.get("publisher"),
        "language": vol.get("language"),
        "isbn": [i.get("identifier") for i in (vol.get("industryIdentifiers") or [])],
        "thumbnail": vol.get("imageLinks", {}).get("thumbnail"),
        "previewLink": vol.get("previewLink"),
        "infoLink": vol.get("infoLink"),
    }


# ═══════════════════════════════════════════════════════════════════
#  YouTube Data API v3 — Full channel
# ═══════════════════════════════════════════════════════════════════

def youtube_search(query: str, max_results: int = 10, video_duration: Optional[str] = None,
                   order: str = "relevance") -> list[dict]:
    """Search YouTube videos. duration: any, short, medium, long. order: relevance, date, rating, viewCount."""
    params = {
        "part": "snippet",
        "q": query,
        "maxResults": min(max_results, 50),
        "type": "video",
        "order": order,
    }
    if video_duration:
        params["videoDuration"] = video_duration
    data = call_api("https://www.googleapis.com/youtube/v3/search", params=params)
    if not data:
        return []
    results = []
    for item in data.get("items", []):
        vid = item.get("id", {})
        snip = item.get("snippet", {})
        results.append({
            "videoId": vid.get("videoId"),
            "title": snip.get("title"),
            "description": (snip.get("description") or "")[:300],
            "channelId": snip.get("channelId"),
            "channelTitle": snip.get("channelTitle"),
            "publishedAt": snip.get("publishedAt"),
            "thumbnail": snip.get("thumbnails", {}).get("high", {}).get("url"),
        })
    return results


def youtube_video_info(video_id: str) -> dict:
    """Get detailed info about a YouTube video (stats, content details, snippet)."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "snippet,contentDetails,statistics", "id": video_id},
    )
    if not data or not data.get("items"):
        return {"error": "Video not found"}
    item = data["items"][0]
    snip = item.get("snippet", {})
    stats = item.get("statistics", {})
    cd = item.get("contentDetails", {})
    return {
        "videoId": item["id"],
        "title": snip.get("title"),
        "description": (snip.get("description") or "")[:1000],
        "channelId": snip.get("channelId"),
        "channelTitle": snip.get("channelTitle"),
        "publishedAt": snip.get("publishedAt"),
        "tags": snip.get("tags", []),
        "categoryId": snip.get("categoryId"),
        "duration": cd.get("duration"),
        "definition": cd.get("definition"),
        "caption": cd.get("caption", "false") == "true",
        "viewCount": stats.get("viewCount"),
        "likeCount": stats.get("likeCount"),
        "commentCount": stats.get("commentCount"),
        "thumbnail": snip.get("thumbnails", {}).get("maxres", {}).get("url")
                      or snip.get("thumbnails", {}).get("high", {}).get("url"),
    }


def youtube_channel_info(channel_id: Optional[str] = None,
                         for_username: Optional[str] = None) -> dict:
    """Get YouTube channel details. Provide channel_id OR for_username."""
    params: dict[str, Any] = {"part": "snippet,contentDetails,statistics"}
    if channel_id:
        params["id"] = channel_id
    elif for_username:
        params["forUsername"] = for_username
    else:
        # Use authenticated user's channel
        params["mine"] = "true"
    data = call_api("https://www.googleapis.com/youtube/v3/channels", params=params)
    if not data or not data.get("items"):
        return {"error": "Channel not found"}
    item = data["items"][0]
    snip = item.get("snippet", {})
    stats = item.get("statistics", {})
    cd = item.get("contentDetails", {})
    return {
        "channelId": item["id"],
        "title": snip.get("title"),
        "description": (snip.get("description") or "")[:500],
        "customUrl": snip.get("customUrl"),
        "publishedAt": snip.get("publishedAt"),
        "country": snip.get("country"),
        "thumbnail": snip.get("thumbnails", {}).get("high", {}).get("url"),
        "subscriberCount": stats.get("subscriberCount", "0"),
        "videoCount": stats.get("videoCount", "0"),
        "viewCount": stats.get("viewCount", "0"),
        "playlistId": cd.get("relatedPlaylists", {}).get("uploads"),
    }


def youtube_list_comments(video_id: str, max_results: int = 20) -> list[dict]:
    """List top-level comments on a YouTube video."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/commentThreads",
        params={"part": "snippet", "videoId": video_id, "maxResults": min(max_results, 50),
                "order": "relevance"},
    )
    if not data:
        return []
    results = []
    for item in data.get("items", []):
        top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        results.append({
            "commentId": item.get("id"),
            "author": top.get("authorDisplayName"),
            "channelId": top.get("authorChannelId", {}).get("value"),
            "textDisplay": top.get("textDisplay"),
            "likeCount": top.get("likeCount"),
            "publishedAt": top.get("publishedAt"),
            "totalReplyCount": item.get("snippet", {}).get("totalReplyCount", 0),
        })
    return results


def youtube_list_playlist_items(playlist_id: str, max_results: int = 20) -> list[dict]:
    """List videos in a YouTube playlist."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        params={"part": "snippet,contentDetails", "playlistId": playlist_id,
                "maxResults": min(max_results, 50)},
    )
    if not data:
        return []
    results = []
    for item in data.get("items", []):
        snip = item.get("snippet", {})
        results.append({
            "videoId": snip.get("resourceId", {}).get("videoId") or item.get("contentDetails", {}).get("videoId"),
            "title": snip.get("title"),
            "channelId": snip.get("videoOwnerChannelId") or snip.get("channelId"),
            "channelTitle": snip.get("videoOwnerChannelTitle") or snip.get("channelTitle"),
            "position": snip.get("position"),
            "publishedAt": snip.get("publishedAt"),
            "thumbnail": snip.get("thumbnails", {}).get("high", {}).get("url"),
        })
    return results


def youtube_list_channel_videos(channel_id: str, max_results: int = 20,
                                order: str = "date") -> list[dict]:
    """List videos uploaded by a channel. order: date, rating, viewCount, title."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/search",
        params={"part": "snippet", "channelId": channel_id, "maxResults": min(max_results, 50),
                "order": order, "type": "video"},
    )
    if not data:
        return []
    results = []
    for item in data.get("items", []):
        snip = item.get("snippet", {})
        results.append({
            "videoId": item.get("id", {}).get("videoId"),
            "title": snip.get("title"),
            "description": (snip.get("description") or "")[:300],
            "publishedAt": snip.get("publishedAt"),
            "thumbnail": snip.get("thumbnails", {}).get("high", {}).get("url"),
        })
    return results


def youtube_analytics_advanced(channel_id: str, start_date: str, end_date: str) -> list[dict]:
    """Get advanced YouTube Analytics including monetization data (revenue, CPM, ad revenue)."""
    token = get_access_token()
    if not token:
        return []
    import requests
    params = {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedRevenue,estimatedAdRevenue,averageViewDuration,impressions,"
                    "cpm,estimatedCpm,playlistStarts,comments,likes,dislikes,shares",
        "dimensions": "day",
        "filters": f"channel=={channel_id}",
    }
    try:
        r = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code == 403:
            return []
        r.raise_for_status()
        data = r.json()
        rows_raw = data.get("rows", [])
        col_headers = [c.get("name", "") for c in data.get("columnHeaders", [])]
        return [dict(zip(col_headers, row)) for row in rows_raw]
    except Exception as exc:
        logger.warning("YouTube Analytics advanced failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════
#  Google Tasks
# ═══════════════════════════════════════════════════════════════════

def tasks_list_tasklists(max_results: int = 20) -> list[dict]:
    """List all task lists."""
    data = call_api(
        "https://tasks.googleapis.com/tasks/v1/users/@me/lists",
        params={"maxResults": min(max_results, 100)},
    )
    if not data:
        return []
    return [{"id": i["id"], "title": i.get("title"), "updated": i.get("updated")}
            for i in data.get("items", [])]


def tasks_list(tasklist_id: str = "@default", max_results: int = 20,
               show_completed: bool = False) -> list[dict]:
    """List tasks from a task list."""
    params: dict[str, Any] = {
        "maxResults": min(max_results, 100),
        "showCompleted": str(show_completed).lower(),
    }
    data = call_api(
        f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist_id}/tasks",
        params=params,
    )
    if not data:
        return []
    results = []
    for item in data.get("items", []):
        results.append({
            "id": item["id"],
            "title": item.get("title"),
            "notes": item.get("notes"),
            "due": item.get("due"),
            "status": item.get("status"),
            "updated": item.get("updated"),
            "position": item.get("position"),
        })
    return results


def tasks_create(tasklist_id: str = "@default", title: str = "New task",
                 notes: str = "", due: Optional[str] = None) -> dict:
    """Create a task. due: ISO 8601 date or datetime."""
    body: dict[str, Any] = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        body["due"] = due
    data = call_api(
        f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist_id}/tasks",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create task"}
    return {"id": data.get("id"), "title": data.get("title"), "status": data.get("status"),
            "due": data.get("due"), "notes": data.get("notes"), "selfLink": data.get("selfLink")}


def tasks_update(tasklist_id: str, task_id: str, title: Optional[str] = None,
                 notes: Optional[str] = None, due: Optional[str] = None,
                 status: Optional[str] = None) -> dict:
    """Update a task. Set status to 'completed' to mark done."""
    if not task_id:
        return {"error": "task_id is required"}
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if notes is not None:
        body["notes"] = notes
    if due is not None:
        body["due"] = due
    if status is not None:
        body["status"] = status
    if not body:
        return {"error": "Nothing to update"}
    data = call_api(
        f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist_id}/tasks/{task_id}",
        method="PUT", json_body=body,
    )
    if not data:
        return {"error": "Failed to update task"}
    return {"id": data.get("id"), "title": data.get("title"), "status": data.get("status"),
            "due": data.get("due")}


def tasks_delete(tasklist_id: str, task_id: str) -> dict:
    """Delete a task."""
    if not task_id:
        return {"error": "task_id is required"}
    import requests as req
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    try:
        r = req.delete(
            f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist_id}/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        return {"success": True, "deleted": task_id}
    except Exception as exc:
        return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════════
#  Google Photos Library API
# ═══════════════════════════════════════════════════════════════════

def photos_list_albums(page_size: int = 20) -> list[dict]:
    """List Google Photos albums."""
    token = get_access_token()
    if not token:
        return []
    import requests
    try:
        r = requests.get(
            "https://photoslibrary.googleapis.com/v1/albums",
            params={"pageSize": min(page_size, 50)},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return [{
            "id": a["id"],
            "title": a.get("title"),
            "mediaItemsCount": a.get("mediaItemsCount", "0"),
            "coverPhotoUrl": a.get("coverPhotoBaseUrl", "") + "=w200-h200",
            "productUrl": a.get("productUrl"),
        } for a in data.get("albums", [])]
    except Exception as exc:
        logger.warning("Photos list albums failed: %s", exc)
        return []


def photos_list_album_contents(album_id: str, page_size: int = 50) -> list[dict]:
    """List media items in a Google Photos album."""
    token = get_access_token()
    if not token:
        return []
    import requests
    try:
        r = requests.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:search",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"albumId": album_id, "pageSize": min(page_size, 100)},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return [{
            "id": m["id"],
            "filename": m.get("filename"),
            "mimeType": m.get("mimeType"),
            "creationTime": m.get("mediaMetadata", {}).get("creationTime"),
            "width": m.get("mediaMetadata", {}).get("width"),
            "height": m.get("mediaMetadata", {}).get("height"),
            "description": m.get("description", ""),
            "productUrl": m.get("productUrl"),
            "baseUrl": m.get("baseUrl"),
        } for m in data.get("mediaItems", [])]
    except Exception as exc:
        logger.warning("Photos list contents failed: %s", exc)
        return []


def photos_search_by_date(year: int, month: Optional[int] = None,
                          day: Optional[int] = None, page_size: int = 50) -> list[dict]:
    """Search Google Photos by date. Returns matching media items."""
    token = get_access_token()
    if not token:
        return []
    import requests
    filters: dict = {}
    date_filter: dict = {"year": year}
    if month:
        date_filter["month"] = month
    if day:
        date_filter["day"] = day
    filters["dateFilter"] = {"dates": [date_filter]}
    try:
        r = requests.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:search",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"pageSize": min(page_size, 100), "filters": filters},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return [{
            "id": m["id"],
            "filename": m.get("filename"),
            "mimeType": m.get("mimeType"),
            "creationTime": m.get("mediaMetadata", {}).get("creationTime"),
            "productUrl": m.get("productUrl"),
            "baseUrl": m.get("baseUrl"),
        } for m in data.get("mediaItems", [])]
    except Exception as exc:
        logger.warning("Photos search failed: %s", exc)
        return []


def photos_create_album(title: str) -> dict:
    """Create a new Google Photos album."""
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.post(
            "https://photoslibrary.googleapis.com/v1/albums",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"album": {"title": title}},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return {"id": data["id"], "title": data.get("title"), "productUrl": data.get("productUrl")}
    except Exception as exc:
        return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════════
#  Google Calendar
# ═══════════════════════════════════════════════════════════════════

def calendar_list_calendars() -> list[dict]:
    """List all calendars the user has access to."""
    data = call_api(
        "https://www.googleapis.com/calendar/v3/users/me/calendarList",
        params={"minAccessRole": "reader"},
    )
    if not data:
        return []
    return [{
        "id": c["id"],
        "summary": c.get("summary"),
        "description": (c.get("description") or "")[:200],
        "timeZone": c.get("timeZone"),
        "accessRole": c.get("accessRole"),
        "primary": c.get("primary", False),
    } for c in data.get("items", [])]


def calendar_list_events(calendar_id: str = "primary", max_results: int = 20,
                         time_min: Optional[str] = None,
                         time_max: Optional[str] = None) -> list[dict]:
    """List calendar events. time_min/time_max: ISO 8601 e.g. '2026-06-01T00:00:00Z'."""
    params: dict[str, Any] = {
        "calendarId": calendar_id,
        "maxResults": min(max_results, 250),
        "singleEvents": "true",
        "orderBy": "startTime",
    }
    if time_min:
        params["timeMin"] = time_min
    if time_max:
        params["timeMax"] = time_max
    data = call_api(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
        params=params,
    )
    if not data:
        return []
    results = []
    for item in data.get("items", []):
        results.append({
            "id": item["id"],
            "summary": item.get("summary"),
            "description": (item.get("description") or "")[:300],
            "start": item.get("start", {}),
            "end": item.get("end", {}),
            "location": item.get("location"),
            "status": item.get("status"),
            "creator": item.get("creator", {}).get("email"),
            "htmlLink": item.get("htmlLink"),
            "reminders": item.get("reminders", {}),
        })
    return results


def calendar_create_event(calendar_id: str = "primary", summary: str = "New event",
                          description: str = "",
                          start_time: str = "", end_time: str = "",
                          timezone: str = "UTC",
                          location: Optional[str] = None) -> dict:
    """Create a calendar event. start_time/end_time: ISO 8601 e.g. '2026-06-10T14:00:00'."""
    if not start_time or not end_time:
        return {"error": "start_time and end_time are required (ISO 8601 format)"}
    body: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": timezone},
        "end": {"dateTime": end_time, "timeZone": timezone},
    }
    if location:
        body["location"] = location
    data = call_api(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create event"}
    return {
        "id": data.get("id"),
        "summary": data.get("summary"),
        "htmlLink": data.get("htmlLink"),
        "start": data.get("start"),
        "end": data.get("end"),
    }


# ═══════════════════════════════════════════════════════════════════
#  Google Analytics Data API
# ═══════════════════════════════════════════════════════════════════

def analytics_get_reports(property_id: str = "", start_date: str = "7daysAgo",
                          end_date: str = "today", metrics: str = "sessions",
                          dimensions: str = "date") -> list[dict]:
    """
    Get Google Analytics 4 report data.
    property_id: numeric GA4 property ID (without 'properties/' prefix).
    metrics: comma-separated e.g. 'sessions,activeUsers,newUsers,totalRevenue'
    dimensions: comma-separated e.g. 'date,country,deviceCategory'
    """
    token = get_access_token()
    if not token:
        return []
    if not property_id:
        return [{"error": "property_id is required (numeric GA4 ID)"}]
    import requests
    body = {
        "property": f"properties/{property_id}",
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "metrics": [{"name": m.strip()} for m in metrics.split(",")],
        "dimensions": [{"name": d.strip()} for d in dimensions.split(",")],
    }
    try:
        r = requests.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        dim_headers = [h.get("name", "") for h in data.get("dimensionHeaders", [])]
        met_headers = [h.get("name", "") for h in data.get("metricHeaders", [])]
        all_headers = dim_headers + met_headers
        results = []
        for row in data.get("rows", []):
            dim_vals = [d.get("value", "") for d in row.get("dimensionValues", [])]
            met_vals = [m.get("value", "") for m in row.get("metricValues", [])]
            results.append(dict(zip(all_headers, dim_vals + met_vals)))
        return results
    except Exception as exc:
        logger.warning("Analytics report failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════
#  Google Drive — Extended (export, comments, permissions)
# ═══════════════════════════════════════════════════════════════════

def drive_export(file_id: str, mime_type: str = "application/pdf") -> dict:
    """
    Export a Google Workspace file (Doc, Sheet, Slide) to another format.
    Common mime types:
      - Docs: application/pdf, text/plain, application/vnd.openxmlformats-officedocument.wordprocessingml.document
      - Sheets: application/pdf, text/csv, application/x-vnd.oasis.opendocument.spreadsheet
      - Slides: application/pdf, text/plain, application/vnd.openxmlformats-officedocument.presentationml.presentation
    Returns a dict with 'file_path' to the downloaded export.
    """
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    import tempfile
    try:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
        r = requests.get(
            url,
            params={"mimeType": mime_type},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            stream=True,
        )
        r.raise_for_status()
        ext_map = {
            "application/pdf": ".pdf",
            "text/plain": ".txt",
            "text/csv": ".csv",
            "application/zip": ".zip",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
            "application/rtf": ".rtf",
            "text/html": ".html",
        }
        ext = ext_map.get(mime_type, ".bin")
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        for chunk in r.iter_content(chunk_size=8192):
            tmp.write(chunk)
        tmp.close()
        return {"file_path": tmp.name, "mime_type": mime_type, "size": r.headers.get("Content-Length", "unknown")}
    except Exception as exc:
        return {"error": str(exc)}


def drive_list_comments(file_id: str, page_size: int = 20) -> list[dict]:
    """List comments on a Google Drive file."""
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/comments",
        params={"pageSize": min(page_size, 100), "fields": "comments(id,author,content,createdTime,modifiedTime,quotedFileContent,resolved)"},
    )
    if not data:
        return []
    return [{
        "id": c["id"],
        "author": c.get("author", {}).get("displayName", ""),
        "authorEmail": c.get("author", {}).get("emailAddress", ""),
        "content": c.get("content", ""),
        "createdTime": c.get("createdTime"),
        "modifiedTime": c.get("modifiedTime"),
        "resolved": c.get("resolved", False),
        "quotedContent": c.get("quotedFileContent", {}).get("value", ""),
    } for c in data.get("comments", [])]


def drive_create_comment(file_id: str, content: str) -> dict:
    """Add a comment to a Google Drive file."""
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/comments",
        method="POST", json_body={"content": content},
    )
    if not data:
        return {"error": "Failed to create comment"}
    return {
        "id": data.get("id"),
        "content": data.get("content"),
        "author": data.get("author", {}).get("displayName", ""),
        "createdTime": data.get("createdTime"),
    }


def drive_list_permissions(file_id: str) -> list[dict]:
    """List sharing permissions for a Drive file."""
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
        params={"fields": "permissions(id,type,role,emailAddress,displayName,domain,allowFileDiscovery,expirationTime)"},
    )
    if not data:
        return []
    return [{
        "id": p["id"],
        "type": p.get("type"),
        "role": p.get("role"),
        "emailAddress": p.get("emailAddress", ""),
        "displayName": p.get("displayName", ""),
        "domain": p.get("domain", ""),
        "allowFileDiscovery": p.get("allowFileDiscovery", True),
        "expirationTime": p.get("expirationTime"),
    } for p in data.get("permissions", [])]


def drive_create_permission(file_id: str, email: str, role: str = "reader",
                            send_notification: bool = False) -> dict:
    """Share a Drive file with someone. role: owner, writer, commenter, reader."""
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
        method="POST",
        params={"sendNotificationEmail": str(send_notification).lower()},
        json_body={"type": "user", "role": role, "emailAddress": email},
    )
    if not data:
        return {"error": "Failed to share file"}
    return {
        "id": data.get("id"),
        "role": data.get("role"),
        "type": data.get("type"),
        "emailAddress": data.get("emailAddress"),
    }


def drive_list_revisions(file_id: str, page_size: int = 20) -> list[dict]:
    """List revision history for a Drive file."""
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/revisions",
        params={"pageSize": min(page_size, 100), "fields": "revisions(id,modifiedTime,lastModifyingUser,size,keepForever,exportLinks)"},
    )
    if not data:
        return []
    return [{
        "id": r["id"],
        "modifiedTime": r.get("modifiedTime"),
        "modifierName": r.get("lastModifyingUser", {}).get("displayName", ""),
        "size": r.get("size"),
        "keepForever": r.get("keepForever", False),
    } for r in data.get("revisions", [])]


# ═══════════════════════════════════════════════════════════════════
#  Google Forms
# ═══════════════════════════════════════════════════════════════════

def forms_list(page_size: int = 50) -> list[dict]:
    """List accessible Google Forms. Uses Drive API to find form files."""
    data = call_api(
        "https://www.googleapis.com/drive/v3/files",
        params={"q": "mimeType='application/vnd.google-apps.form' and trashed=false",
                "pageSize": min(page_size, 100),
                "fields": "files(id,name,createdTime,modifiedTime,webViewLink)"},
    )
    if not data:
        return []
    return [{
        "formId": f["id"],
        "title": f.get("name"),
        "createdTime": f.get("createdTime"),
        "modifiedTime": f.get("modifiedTime"),
        "url": f.get("webViewLink"),
    } for f in data.get("files", [])]


def forms_get(form_id: str) -> dict:
    """Get the structure of a Google Form (questions, settings, title)."""
    data = call_api(
        f"https://forms.googleapis.com/v1/forms/{form_id}",
    )
    if not data:
        return {"error": "Form not found"}
    info = data.get("info", {})
    items = []
    for item in data.get("items", []):
        q = item.get("questionItem", {}).get("question", {})
        items.append({
            "itemId": item.get("itemId"),
            "title": item.get("title", ""),
            "questionType": list(q.get("choiceQuestion", {}).keys()) or list(q.keys()),
            "required": q.get("required", False),
            "choices": [c.get("value") for c in q.get("choiceQuestion", {}).get("options", [])]
                       if "choiceQuestion" in q else [],
        })
    return {
        "formId": data.get("formId"),
        "title": info.get("title", ""),
        "description": info.get("description", ""),
        "documentTitle": info.get("documentTitle", ""),
        "items": items,
        "respondentUri": info.get("respondentUri", ""),
        "settings": {s.get("key"): s.get("value") for s in info.get("settings", [])},
    }


def forms_list_responses(form_id: str) -> list[dict]:
    """List responses submitted to a Google Form."""
    data = call_api(
        f"https://forms.googleapis.com/v1/forms/{form_id}/responses",
    )
    if not data:
        return []
    results = []
    for resp in data.get("responses", []):
        answers = {}
        for q_id, ans in resp.get("answers", {}).items():
            text_ans = ans.get("textAnswers", {}).get("answers", [{}])
            answers[q_id] = [a.get("value", "") for a in text_ans]
        results.append({
            "responseId": resp.get("responseId"),
            "createTime": resp.get("createTime"),
            "lastSubmittedTime": resp.get("lastSubmittedTime"),
            "answers": answers,
        })
    return results


# ═══════════════════════════════════════════════════════════════════
#  Google Slides — Extended
# ═══════════════════════════════════════════════════════════════════

def slides_add_text_slide(presentation_id: str, title: str = "",
                          body: str = "", position: Optional[int] = None) -> dict:
    """Add a slide with a title and body text box to a presentation."""
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    requests_list = []
    layout_req = {
        "createSlide": {
            "objectId": f"slide_{int(import_time())}",
        }
    }
    if position is not None:
        layout_req["createSlide"]["insertionIndex"] = position
    if title:
        layout_req["createSlide"]["placeholderIdMappings"] = [{"layoutPlaceholder": {"type": "TITLE", "index": 0},
                                                                "objectId": f"title_{int(import_time())}"}]
    requests_list.append(layout_req)
    if title:
        requests_list.append({
            "insertText": {"objectId": f"title_{int(import_time())}", "text": title}
        })
    if body:
        slide_id = layout_req["createSlide"]["objectId"]
        box_id = f"bodybox_{int(import_time())}"
        requests_list.append({
            "createShape": {
                "objectId": box_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": {"magnitude": 600, "unit": "PT"},
                             "height": {"magnitude": 300, "unit": "PT"}},
                    "transform": {"scaleX": 1, "scaleY": 1, "translateX": 50, "translateY": 150, "unit": "PT"},
                }
            }
        })
        requests_list.append({
            "insertText": {"objectId": box_id, "text": body}
        })
    try:
        r = requests.post(
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"requests": requests_list},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def import_time():
    """Microsecond timestamp for unique IDs."""
    import time
    return time.time() * 1000000


def slides_add_image(presentation_id: str, image_url: str,
                     slide_object_id: Optional[str] = None,
                     width_pt: float = 400, height_pt: float = 300) -> dict:
    """Add an image to a slide in a presentation."""
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    img_id = f"img_{int(import_time())}"
    slide_id = slide_object_id or "p"
    requests_list = [{
        "createImage": {
            "objectId": img_id,
            "url": image_url,
            "elementProperties": {
                "pageObjectId": slide_id,
                "size": {"width": {"magnitude": width_pt, "unit": "PT"},
                         "height": {"magnitude": height_pt, "unit": "PT"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": 50, "translateY": 50, "unit": "PT"},
            }
        }
    }]
    try:
        r = requests.post(
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"requests": requests_list},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════════
#  Google Cloud Natural Language API
# ═══════════════════════════════════════════════════════════════════

def nlp_extract_entities(text: str) -> list[dict]:
    """Extract entities (people, places, orgs, events, products, etc.) from text using Cloud NLP."""
    token = get_access_token()
    if not token:
        return []
    import requests
    try:
        r = requests.post(
            "https://language.googleapis.com/v1/documents:analyzeEntities",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"document": {"type": "PLAIN_TEXT", "content": text}, "encodingType": "UTF8"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        results = []
        for e in data.get("entities", []):
            results.append({
                "name": e.get("name"),
                "type": e.get("type"),
                "salience": e.get("salience"),
                "wikipedia_url": e.get("metadata", {}).get("wikipedia_url", ""),
                "mid": e.get("metadata", {}).get("mid", ""),
                "mentions": [{"text": m.get("text", {}).get("content", ""),
                              "type": m.get("type")} for m in e.get("mentions", [])],
            })
        return results
    except Exception as exc:
        logger.warning("NLP entities failed: %s", exc)
        return []


def nlp_analyze_sentiment(text: str) -> dict:
    """Analyze sentiment of text — returns score (-1 to 1) and magnitude."""
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.post(
            "https://language.googleapis.com/v1/documents:analyzeSentiment",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"document": {"type": "PLAIN_TEXT", "content": text}, "encodingType": "UTF8"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        doc = data.get("documentSentiment", {})
        sentences = []
        for s in data.get("sentences", []):
            txt = s.get("text", {}).get("content", "")
            sent = s.get("sentiment", {})
            sentences.append({"text": txt, "score": sent.get("score"), "magnitude": sent.get("magnitude")})
        return {
            "score": doc.get("score"),
            "magnitude": doc.get("magnitude"),
            "sentences": sentences,
        }
    except Exception as exc:
        return {"error": str(exc)}


def nlp_classify_content(text: str) -> list[dict]:
    """Classify text into content categories (e.g. /Technology & Computing /Arts & Entertainment)."""
    token = get_access_token()
    if not token:
        return []
    import requests
    try:
        r = requests.post(
            "https://language.googleapis.com/v1/documents:classifyText",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"document": {"type": "PLAIN_TEXT", "content": text}},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return [{"name": c.get("name"), "confidence": c.get("confidence")}
                for c in data.get("categories", [])]
    except Exception as exc:
        logger.warning("NLP classify failed: %s", exc)
        return []


def nlp_analyze_syntax(text: str) -> list[dict]:
    """Analyze syntax of text — returns tokens with part-of-speech tags, dependency parse."""
    token = get_access_token()
    if not token:
        return []
    import requests
    try:
        r = requests.post(
            "https://language.googleapis.com/v1/documents:analyzeSyntax",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"document": {"type": "PLAIN_TEXT", "content": text}, "encodingType": "UTF8"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return [{
            "text": t.get("text", {}).get("content", ""),
            "partOfSpeech": t.get("partOfSpeech", {}).get("tag"),
            "headTokenIndex": t.get("dependencyEdge", {}).get("headTokenIndex"),
            "label": t.get("dependencyEdge", {}).get("label"),
            "lemma": t.get("lemma"),
        } for t in data.get("tokens", [])]
    except Exception as exc:
        logger.warning("NLP syntax failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════
#  Google People / Contacts — Extended
# ═══════════════════════════════════════════════════════════════════

def people_get(resource_name: str) -> dict:
    """Get detailed info about a contact by resource name (e.g. 'people/12345')."""
    data = call_api(
        f"https://people.googleapis.com/v1/{resource_name}",
        params={"personFields": "names,emailAddresses,phoneNumbers,addresses,birthdays,genders,"
                                "organizations,relations,photos,biographies,events,skills,locales,urls"},
    )
    if not data:
        return {"error": "Contact not found"}
    return {
        "resourceName": data.get("resourceName"),
        "names": [n.get("displayName") for n in data.get("names", [])],
        "emails": [e.get("value") for e in data.get("emailAddresses", [])],
        "phones": [p.get("value") for p in data.get("phoneNumbers", [])],
        "addresses": [{"street": a.get("streetAddress"), "city": a.get("city"),
                        "region": a.get("region"), "country": a.get("country")}
                      for a in data.get("addresses", [])],
        "birthdays": [f"{b.get('date', {}).get('month')}/{b.get('date', {}).get('day')}/{b.get('date', {}).get('year')}"
                      for b in data.get("birthdays", []) if b.get("date")],
        "genders": [g.get("value") for g in data.get("genders", [])],
        "organizations": [{"name": o.get("name"), "title": o.get("title"),
                           "department": o.get("department")}
                          for o in data.get("organizations", [])],
        "relations": [{"person": r.get("person"), "type": r.get("type")}
                      for r in data.get("relations", [])],
        "biographies": [b.get("value") for b in data.get("biographies", [])],
        "events": [{"date": f"{e.get('date', {}).get('month')}/{e.get('date', {}).get('day')}",
                     "type": e.get("type")} for e in data.get("events", [])],
        "skills": [s.get("value") for s in data.get("skills", [])],
        "photo": (data.get("photos") or [{}])[0].get("url"),
        "urls": [u.get("value") for u in data.get("urls", [])],
    }


def people_update_contact(resource_name: str, name: Optional[str] = None,
                          email: Optional[str] = None, phone: Optional[str] = None) -> dict:
    """Update a contact's name, email, or phone."""
    if not resource_name:
        return {"error": "resource_name is required (e.g. people/12345)"}
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    body: dict = {"etag": "*"}
    fields = []
    if name:
        body["names"] = [{"givenName": name}]
        fields.append("names")
    if email:
        body["emailAddresses"] = [{"value": email}]
        fields.append("emailAddresses")
    if phone:
        body["phoneNumbers"] = [{"value": phone}]
        fields.append("phoneNumbers")
    if not body:
        return {"error": "Nothing to update"}
    try:
        r = requests.patch(
            f"https://people.googleapis.com/v1/{resource_name}:updateContact",
            params={"updatePersonFields": ",".join(fields)},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=10,
        )
        r.raise_for_status()
        return {"success": True, "resourceName": r.json().get("resourceName")}
    except Exception as exc:
        return {"error": str(exc)}


def people_delete_contact(resource_name: str) -> dict:
    """Delete a contact by resource name."""
    if not resource_name:
        return {"error": "resource_name is required"}
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.delete(
            f"https://people.googleapis.com/v1/{resource_name}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        return {"success": True, "deleted": resource_name}
    except Exception as exc:
        return {"error": str(exc)}


def people_list_directories(page_size: int = 20) -> list[dict]:
    """List available contact directories (include 'people/me' for own contacts)."""
    data = call_api(
        "https://people.googleapis.com/v1/people:listDirectoryPeople",
        params={"readMask": "names,emailAddresses", "pageSize": min(page_size, 100)},
    )
    if not data:
        return []
    return [{
        "resourceName": p.get("resourceName"),
        "name": (p.get("names") or [{}])[0].get("displayName", ""),
        "email": (p.get("emailAddresses") or [{}])[0].get("value", ""),
    } for p in data.get("people", [])]


# ═══════════════════════════════════════════════════════════════════
#  Google Photos — Enhanced with full metadata
# ═══════════════════════════════════════════════════════════════════

def photos_get_media_item(media_item_id: str) -> dict:
    """Get a single media item with full metadata (camera info, GPS, etc.)."""
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.get(
            f"https://photoslibrary.googleapis.com/v1/mediaItems/{media_item_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        item = r.json()
        meta = item.get("mediaMetadata", {})
        result = {
            "id": item["id"],
            "filename": item.get("filename"),
            "mimeType": item.get("mimeType"),
            "productUrl": item.get("productUrl"),
            "baseUrl": item.get("baseUrl"),
            "creationTime": meta.get("creationTime"),
            "width": meta.get("width"),
            "height": meta.get("height"),
        }
        # Photo-specific metadata (camera, GPS)
        photo = meta.get("photo", {})
        if photo:
            result["camera"] = {
                "make": photo.get("cameraMake", ""),
                "model": photo.get("cameraModel", ""),
                "focalLength": photo.get("focalLength"),
                "apertureFNumber": photo.get("apertureFNumber"),
                "isoEquivalent": photo.get("isoEquivalent"),
                "exposureTime": photo.get("exposureTime"),
                "flashUsed": photo.get("flashUsed", False),
            }
            gps = {
                "latitude": photo.get("latitude"),
                "longitude": photo.get("longitude"),
                "altitude": photo.get("altitude"),
            }
            if any(v is not None for v in gps.values()):
                result["gpsLocation"] = gps
        # Video-specific metadata
        video = meta.get("video", {})
        if video:
            result["video"] = {
                "fps": video.get("fps"),
                "status": video.get("status"),
            }
        return result
    except Exception as exc:
        return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════════
#  Google Maps — Place Details (photos, reviews, hours)
# ═══════════════════════════════════════════════════════════════════

def maps_place_details(place_id: str) -> dict:
    """Get details about a place including photos, reviews, opening hours, price level.
    Uses Google Maps API key (GOOGLE_MAPS_API_KEY from .env) — no OAuth needed."""
    import os
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_CLIENT_SECRET")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set in .env"}
    try:
        import requests
        r = requests.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={
                "place_id": place_id,
                "key": api_key,
                "fields": "name,formatted_address,formatted_phone_number,website,rating,"
                          "user_ratings_total,opening_hours,price_level,reviews,photos,"
                          "geometry,url,vicinity,types",
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {"error": "Maps API request failed"}
    if data.get("status") != "OK":
        return {"error": data.get("error_message", data.get("status", "Unknown error"))}
    result = data.get("result", {})
    return {
        "name": result.get("name"),
        "address": result.get("formatted_address"),
        "phone": result.get("formatted_phone_number"),
        "website": result.get("website"),
        "rating": result.get("rating"),
        "totalRatings": result.get("user_ratings_total"),
        "priceLevel": result.get("price_level"),
        "location": result.get("geometry", {}).get("location", {}),
        "types": result.get("types", []),
        "url": result.get("url"),
        "openingHours": result.get("opening_hours", {}).get("weekday_text", []),
        "reviews": [{
            "author": r.get("author_name"),
            "rating": r.get("rating"),
            "text": (r.get("text") or "")[:1000],
            "time": r.get("relative_time_description"),
        } for r in (result.get("reviews") or [])],
        "photos": [p.get("photo_reference") for p in (result.get("photos") or [])],
    }


# ═══════════════════════════════════════════════════════════════════
#  Google Docs — batchUpdate for advanced editing
# ═══════════════════════════════════════════════════════════════════

def docs_batch_update(document_id: str, requests_list: list[dict]) -> dict:
    """
    Apply multiple updates to a Google Doc.
    See https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate
    Common request types: insertText, insertInlineImage, updateTextStyle, updateParagraphStyle, createParagraphBullets.
    """
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.post(
            f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"requests": requests_list},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return {"replyIds": [r.get("insertText", {}).get("textLocation", {}).get("index")
                             for r in (data.get("replies") or [])],
                "documentId": document_id}
    except Exception as exc:
        return {"error": str(exc)}


def docs_insert_image(document_id: str, image_url: str, index: int = 0) -> dict:
    """Insert an inline image at a specific index in a Google Doc."""
    return docs_batch_update(document_id, [{
        "insertInlineImage": {
            "uri": image_url,
            "location": {"index": index},
            "objectSize": {"height": {"magnitude": 300, "unit": "PT"},
                           "width": {"magnitude": 400, "unit": "PT"}},
        }
    }])


# ═══════════════════════════════════════════════════════════════════
#  Google Forms — Create with questions
# ═══════════════════════════════════════════════════════════════════

def forms_create(title: str, description: str = "",
                 questions: Optional[list[dict]] = None,
                 collect_email: bool = False) -> dict:
    """
    Create a Google Form with questions.
    questions: list of {"title": "...", "type": "SHORT_ANSWER|PARAGRAPH|MULTIPLE_CHOICE|CHECKBOXES|DROPDOWN|LINEAR_SCALE|DATE|TIME", "options": ["..."] (for choice types), "required": True/False}
    """
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    # Step 1: Create the form
    body = {
        "info": {
            "title": title,
            "documentTitle": title,
            "description": description,
        }
    }
    if collect_email:
        body["info"]["settings"] = [{"key": "COLLECT_EMAIL_ADDRESSES", "value": "true"}]
    try:
        r = requests.post(
            "https://forms.googleapis.com/v1/forms",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=10,
        )
        r.raise_for_status()
        form_data = r.json()
        form_id = form_data.get("formId")
    except Exception as exc:
        return {"error": f"Failed to create form: {exc}"}

    # Step 2: Add questions via batchUpdate
    if questions:
        q_requests = []
        for i, q in enumerate(questions):
            q_title = q.get("title", f"Question {i+1}")
            q_type = q.get("type", "SHORT_ANSWER")
            q_required = q.get("required", False)
            q_options = q.get("options", [])
            item = {"title": q_title, "questionItem": {"question": {"required": q_required}}}
            if q_type in ("MULTIPLE_CHOICE", "CHECKBOXES", "DROPDOWN"):
                choice_type = "RADIO" if q_type == "MULTIPLE_CHOICE" else ("CHECKBOX" if q_type == "CHECKBOXES" else "DROP_DOWN")
                item["questionItem"]["question"]["choiceQuestion"] = {
                    "type": choice_type,
                    "options": [{"value": opt} for opt in q_options],
                }
            elif q_type == "LINEAR_SCALE":
                item["questionItem"]["question"]["scaleQuestion"] = {
                    "low": 1, "high": min(max(len(q_options), 2), 10) if q_options else 5,
                    "lowLabel": (q_options or ["Poor"])[0] if q_options else "",
                    "highLabel": (q_options or ["Excellent"])[-1] if q_options else "",
                }
            elif q_type in ("DATE", "TIME"):
                item["questionItem"]["question"]["dateQuestion" if q_type == "DATE" else "timeQuestion"] = {}
            else:
                item["questionItem"]["question"]["textQuestion"] = {"paragraph": q_type == "PARAGRAPH"}
            q_requests.append({"createItem": {"item": item, "location": {"index": i}}})
        try:
            r2 = requests.post(
                f"https://forms.googleapis.com/v1/forms/{form_id}:batchUpdate",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"requests": q_requests},
                timeout=10,
            )
            r2.raise_for_status()
        except Exception as exc:
            return {"formId": form_id, "error": f"Created but failed to add questions: {exc}"}

    return {
        "formId": form_id,
        "title": title,
        "responderUri": f"https://docs.google.com/forms/d/e/{form_id}/viewform",
        "editUri": f"https://docs.google.com/forms/d/{form_id}/edit",
    }


# ═══════════════════════════════════════════════════════════════════
#  Google Search Console
# ═══════════════════════════════════════════════════════════════════

def searchconsole_list_sites() -> list[dict]:
    """List sites verified in Google Search Console."""
    data = call_api("https://searchconsole.googleapis.com/v1/sites")
    if not data:
        return []
    return [{"siteUrl": s.get("siteUrl"), "permissionLevel": s.get("permissionLevel")}
            for s in data.get("siteEntry", [])]


def searchconsole_query(site_url: str, start_date: str = "7daysAgo",
                        end_date: str = "today", dimension: str = "query",
                        row_limit: int = 10) -> list[dict]:
    """
    Get Search Analytics data for a verified site.
    dimension: query, page, country, device, date
    """
    token = get_access_token()
    if not token:
        return []
    import requests
    try:
        r = requests.post(
            f"https://searchconsole.googleapis.com/v1/sites/{site_url}/searchAnalytics/query",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"startDate": start_date, "endDate": end_date,
                  "dimensions": [dimension], "rowLimit": min(row_limit, 100)},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return [{
            "keys": row.get("keys", []),
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0),
            "position": row.get("position", 0),
        } for row in data.get("rows", [])]
    except Exception as exc:
        logger.warning("Search Console query failed: %s", exc)
        return []


