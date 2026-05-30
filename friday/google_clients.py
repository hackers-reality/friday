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
#  Google Classroom
# ═══════════════════════════════════════════════════════════════════

def classroom_list_courses(page_size: int = 50) -> list[dict]:
    """List Google Classroom courses."""
    data = call_api(
        "https://classroom.googleapis.com/v1/courses",
        params={"pageSize": min(page_size, 100)},
    )
    if not data:
        return []
    return data.get("courses", [])


def classroom_list_coursework(course_id: str, page_size: int = 20) -> list[dict]:
    """List coursework/assignments for a course."""
    data = call_api(
        f"https://classroom.googleapis.com/v1/courses/{course_id}/courseWork",
        params={"pageSize": min(page_size, 100)},
    )
    if not data:
        return []
    return data.get("courseWork", [])


def classroom_list_students(course_id: str) -> list[dict]:
    """List students enrolled in a course."""
    data = call_api(
        f"https://classroom.googleapis.com/v1/courses/{course_id}/students"
    )
    if not data:
        return []
    return data.get("students", [])


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
#  YouTube Analytics — Monetary extension
# ═══════════════════════════════════════════════════════════════════

def youtube_analytics_advanced(channel_id: str, start_date: str, end_date: str) -> list[dict]:
    """Get advanced YouTube Analytics including monetization data."""
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
