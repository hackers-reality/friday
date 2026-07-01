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

def _maps_request(url: str, params: dict) -> list[dict]:
    """Direct Maps API request (Maps uses API key, not OAuth)."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY not set. Get it from https://console.cloud.google.com/apis/credentials"}]
    params["key"] = api_key
    import requests as _req
    try:
        r = _req.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception as exc:
        return [{"error": f"Maps API error: {exc}"}]


def maps_geocode(address: str) -> list[dict]:
    """Geocode an address to lat/lng."""
    return _maps_request(
        "https://maps.googleapis.com/maps/api/geocode/json",
        {"address": address},
    )


def maps_reverse_geocode(lat: float, lng: float) -> list[dict]:
    """Reverse geocode lat/lng to address."""
    return _maps_request(
        "https://maps.googleapis.com/maps/api/geocode/json",
        {"latlng": f"{lat},{lng}"},
    )


def maps_places_search(query: str, location: Optional[str] = None,
                       radius: int = 5000) -> list[dict]:
    """Search for places using Google Places API."""
    params: dict = {"query": query}
    if location:
        params["location"] = location
        params["radius"] = radius
    return _maps_request(
        "https://maps.googleapis.com/maps/api/place/textsearch/json",
        params,
    )


def maps_directions(origin: str, destination: str, mode: str = "driving") -> list[dict]:
    """Get directions between two points."""
    return _maps_request(
        "https://maps.googleapis.com/maps/api/directions/json",
        {"origin": origin, "destination": destination, "mode": mode},
    )


def maps_elevation(locations: str) -> list[dict]:
    """Get elevation data for locations (comma-separated lat,lng pairs)."""
    return _maps_request(
        "https://maps.googleapis.com/maps/api/elevation/json",
        {"locations": locations},
    )


# ═══════════════════════════════════════════════════════════════════
#  Google Cloud Platform (BigQuery, Cloud Storage, Vision, Translate, TTS, STT)
# ═══════════════════════════════════════════════════════════════════

def bigquery_query(sql: str, project_id: Optional[str] = None) -> list[dict]:
    """Run a BigQuery SQL query and return results."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    if not pid:
        return [{"error": "No project_id provided and GOOGLE_CLOUD_PROJECT not set"}]
    body = {
        "query": sql,
        "useLegacySql": False,
    }
    if pid:
        body["requestId"] = pid
    data = call_api(
        f"https://bigquery.googleapis.com/bigquery/v2/projects/{pid}/queries",
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
    """Search YouTube by scraping HTML (no API key required)."""
    import httpx, re, html as html_mod
    sort_map = {"relevance": "", "date": "&sp=CAI%3D", "viewCount": "&sp=CAM%3D", "rating": "&sp=CAE%3D"}
    sort_suffix = sort_map.get(order, "")
    dur_map = {"short": "&sp=EgQQARgB", "medium": "&sp=EgQQARgC", "long": "&sp=EgQQARgD"}
    dur_suffix = dur_map.get(video_duration, "")
    url = f"https://www.youtube.com/results?search_query={httpx.utils.quote(query)}{sort_suffix}{dur_suffix}"
    try:
        resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code != 200:
            return []
        # Extract initial data from ytInitialData
        match = re.search(r'ytInitialData\s*=\s*({.*?});', resp.text, re.DOTALL)
        if not match:
            return []
        import json
        data = json.loads(match.group(1))
        results = []
        contents = (data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {})
                    .get("sectionListRenderer", {}).get("contents", []))
        for section in contents:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                vren = item.get("videoRenderer", {})
                if not vren:
                    continue
                vid = vren.get("videoId", "")
                title_runs = vren.get("title", {}).get("runs", [])
                title = "".join(r.get("text", "") for r in title_runs)
                desc_runs = vren.get("detailedMetadataSnippets", [{}])[0].get("snippetText", {}).get("runs", [])
                desc = "".join(r.get("text", "") for r in desc_runs)
                channel = vren.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                published = vren.get("publishedTimeText", {}).get("simpleText", "")
                thumb = ""
                thumbs = vren.get("thumbnail", {}).get("thumbnails", [])
                if thumbs:
                    thumb = thumbs[-1].get("url", "")
                results.append({
                    "videoId": vid,
                    "title": title,
                    "description": html_mod.unescape(desc)[:300],
                    "channelTitle": channel,
                    "publishedAt": published,
                    "thumbnail": thumb,
                })
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


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
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
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


# ═══════════════════════════════════════════════════════════════════
#  YouTube — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def youtube_upload_video(file_path: str, title: str, description: str = "",
                         tags: Optional[list[str]] = None,
                         privacy_status: str = "private") -> dict:
    """Upload a video file to YouTube. privacy_status: public, private, unlisted."""
    import requests
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    # Step 1: Create resumable upload session
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
        },
        "status": {"privacyStatus": privacy_status},
    }
    try:
        r = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Upload-Content-Type": "video/*",
            },
            json=body,
            timeout=15,
        )
        r.raise_for_status()
        upload_url = r.headers.get("Location")
        if not upload_url:
            return {"error": "No upload URL returned"}
        # Step 2: Upload the file bytes
        file_size = path.stat().st_size
        r2 = requests.put(
            upload_url,
            data=path.read_bytes(),
            headers={
                "Content-Length": str(file_size),
                "Content-Type": "video/*",
            },
            timeout=300,
        )
        r2.raise_for_status()
        return {"videoId": r2.json().get("id"), "title": title, "status": privacy_status}
    except Exception as exc:
        logger.warning("YouTube upload failed: %s", exc)
        return {"error": str(exc)}


def youtube_update_video(video_id: str, **kwargs) -> dict:
    """Update video metadata. Kwargs: title, description, tags (list), categoryId, privacyStatus."""
    if not video_id:
        return {"error": "video_id is required"}
    snippet: dict[str, Any] = {}
    status: dict[str, Any] = {}
    for key, val in kwargs.items():
        if key == "privacyStatus":
            status["privacyStatus"] = val
        elif key == "tags":
            snippet["tags"] = val
        else:
            snippet[key] = val
    body: dict[str, Any] = {"id": video_id}
    if snippet:
        body["snippet"] = snippet
    if status:
        body["status"] = status
    parts = []
    if snippet:
        parts.append("snippet")
    if status:
        parts.append("status")
    data = call_api(
        f"https://www.googleapis.com/youtube/v3/videos?part={','.join(parts)}",
        method="PUT", json_body=body,
    )
    if not data or not data.get("items"):
        return {"error": "Failed to update video"}
    return {"videoId": video_id, "updated": True, "title": data["items"][0].get("snippet", {}).get("title")}


def youtube_delete_video(video_id: str) -> dict:
    """Delete a YouTube video."""
    if not video_id:
        return {"error": "video_id is required"}
    result = call_api(
        f"https://www.googleapis.com/youtube/v3/videos?id={video_id}",
        method="DELETE",
    )
    return {"ok": result is None, "videoId": video_id}


def youtube_set_thumbnail(video_id: str, image_path: str) -> dict:
    """Set video thumbnail from an image file."""
    import requests
    path = Path(image_path)
    if not path.exists():
        return {"error": f"File not found: {image_path}"}
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    try:
        r = requests.post(
            f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "image/*",
            },
            data=path.read_bytes(),
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        if items:
            return {"videoId": video_id, "thumbnail": items[0].get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url")}
        return {"videoId": video_id, "thumbnail": "set"}
    except Exception as exc:
        return {"error": str(exc)}


def youtube_rate_video(video_id: str, rating: str = "like") -> dict:
    """Rate a video. rating: like, dislike, none."""
    if rating not in ("like", "dislike", "none"):
        return {"error": "rating must be 'like', 'dislike', or 'none'"}
    result = call_api(
        "https://www.googleapis.com/youtube/v3/videos/rate",
        method="POST",
        json_body={"id": video_id, "rating": rating},
    )
    return {"ok": result is None, "videoId": video_id, "rating": rating}


def youtube_get_captions(video_id: str) -> list[dict]:
    """List caption tracks for a video."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/captions",
        params={"part": "snippet", "videoId": video_id},
    )
    if not data:
        return []
    return [{
        "id": item["id"],
        "language": item.get("snippet", {}).get("language", ""),
        "name": item.get("snippet", {}).get("name", ""),
        "trackKind": item.get("snippet", {}).get("trackKind", ""),
        "audioTrackType": item.get("snippet", {}).get("audioTrackType", ""),
    } for item in data.get("items", [])]


def youtube_download_caption(caption_id: str, fmt: str = "srt") -> str:
    """Download caption content in srt, sbv, or vtt format."""
    import requests
    token = get_access_token()
    if not token:
        return ""
    try:
        r = requests.get(
            f"https://www.googleapis.com/youtube/v3/captions/{caption_id}",
            params={"tfmt": fmt, "part": "id"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.text
    except Exception as exc:
        logger.warning("YouTube download caption failed: %s", exc)
        return ""


def youtube_subscribe(channel_id: str) -> dict:
    """Subscribe to a channel."""
    if not channel_id:
        return {"error": "channel_id is required"}
    result = call_api(
        "https://www.googleapis.com/youtube/v3/subscriptions",
        method="POST",
        json_body={"snippet": {"resourceId": {"kind": "youtube#channel", "channelId": channel_id}}},
    )
    if not result:
        return {"error": "Failed to subscribe"}
    return {"subscriptionId": result.get("id"), "channelId": channel_id, "subscribed": True}


def youtube_unsubscribe(subscription_id: str) -> dict:
    """Unsubscribe from a channel using subscription ID."""
    if not subscription_id:
        return {"error": "subscription_id is required"}
    result = call_api(
        f"https://www.googleapis.com/youtube/v3/subscriptions?id={subscription_id}",
        method="DELETE",
    )
    return {"ok": result is None, "subscriptionId": subscription_id}


def youtube_list_subscriptions(page_size: int = 20) -> list[dict]:
    """List authenticated user's subscriptions."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/subscriptions",
        params={"part": "snippet", "mine": "true", "maxResults": min(page_size, 50)},
    )
    if not data:
        return []
    return [{
        "subscriptionId": item["id"],
        "channelId": item.get("snippet", {}).get("resourceId", {}).get("channelId", ""),
        "title": item.get("snippet", {}).get("title", ""),
        "description": (item.get("snippet", {}).get("description") or "")[:300],
        "channelUrl": f"https://www.youtube.com/channel/{item.get('snippet', {}).get('resourceId', {}).get('channelId', '')}",
    } for item in data.get("items", [])]


def youtube_create_playlist(title: str, description: str = "",
                            privacy_status: str = "private") -> dict:
    """Create a YouTube playlist."""
    body = {
        "snippet": {"title": title, "description": description},
        "status": {"privacyStatus": privacy_status},
    }
    data = call_api(
        "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create playlist"}
    return {"playlistId": data.get("id"), "title": title, "privacyStatus": privacy_status}


def youtube_update_playlist(playlist_id: str, title: Optional[str] = None,
                            description: Optional[str] = None,
                            privacy_status: Optional[str] = None) -> dict:
    """Update playlist metadata."""
    if not playlist_id:
        return {"error": "playlist_id is required"}
    snippet: dict[str, Any] = {}
    if title is not None:
        snippet["title"] = title
    if description is not None:
        snippet["description"] = description
    status: dict[str, Any] = {}
    if privacy_status is not None:
        status["privacyStatus"] = privacy_status
    body: dict[str, Any] = {"id": playlist_id}
    if snippet:
        body["snippet"] = snippet
    if status:
        body["status"] = status
    data = call_api(
        "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status",
        method="PUT", json_body=body,
    )
    if not data:
        return {"error": "Failed to update playlist"}
    return {"playlistId": playlist_id, "updated": True}


def youtube_delete_playlist(playlist_id: str) -> dict:
    """Delete a YouTube playlist."""
    if not playlist_id:
        return {"error": "playlist_id is required"}
    result = call_api(
        f"https://www.googleapis.com/youtube/v3/playlists?id={playlist_id}",
        method="DELETE",
    )
    return {"ok": result is None, "playlistId": playlist_id}


def youtube_add_video_to_playlist(playlist_id: str, video_id: str,
                                  position: Optional[int] = None) -> dict:
    """Add a video to a playlist. Optionally specify position."""
    if not playlist_id or not video_id:
        return {"error": "playlist_id and video_id are required"}
    body: dict = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    if position is not None:
        body["snippet"]["position"] = position
    data = call_api(
        "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to add video to playlist"}
    return {"playlistItemId": data.get("id"), "playlistId": playlist_id, "videoId": video_id}


def youtube_remove_video_from_playlist(playlist_item_id: str) -> dict:
    """Remove a video from a playlist using the playlist item ID."""
    if not playlist_item_id:
        return {"error": "playlist_item_id is required"}
    result = call_api(
        f"https://www.googleapis.com/youtube/v3/playlistItems?id={playlist_item_id}",
        method="DELETE",
    )
    return {"ok": result is None, "playlistItemId": playlist_item_id}


def youtube_moderate_comment(comment_id: str, action: str = "delete") -> dict:
    """Moderate a comment. action: approve, reject, delete (reject/deletes the comment)."""
    if not comment_id:
        return {"error": "comment_id is required"}
    if action == "delete":
        result = call_api(
            f"https://www.googleapis.com/youtube/v3/comments?id={comment_id}",
            method="DELETE",
        )
        return {"ok": result is None, "commentId": comment_id, "action": "delete"}
    data = call_api(
        f"https://www.googleapis.com/youtube/v3/comments/setModerationStatus?id={comment_id}&moderationStatus={action}",
        method="POST", json_body={},
    )
    return {"ok": data is True or data is None, "commentId": comment_id, "action": action}


def youtube_reply_to_comment(parent_id: str, text: str) -> dict:
    """Reply to a comment thread. parent_id is the top-level comment thread ID."""
    if not parent_id or not text:
        return {"error": "parent_id and text are required"}
    body = {
        "snippet": {
            "parentId": parent_id,
            "textOriginal": text,
        }
    }
    data = call_api(
        "https://www.googleapis.com/youtube/v3/comments?part=snippet",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to post reply"}
    return {"commentId": data.get("id"), "parentId": parent_id, "text": text}


def youtube_list_replies(comment_id: str, max_results: int = 20) -> list[dict]:
    """List replies to a comment (comment thread ID or comment ID)."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/comments",
        params={"part": "snippet", "parentId": comment_id, "maxResults": min(max_results, 50)},
    )
    if not data:
        return []
    return [{
        "commentId": item["id"],
        "author": item.get("snippet", {}).get("authorDisplayName", ""),
        "textDisplay": item.get("snippet", {}).get("textDisplay", ""),
        "likeCount": item.get("snippet", {}).get("likeCount", 0),
        "publishedAt": item.get("snippet", {}).get("publishedAt", ""),
    } for item in data.get("items", [])]


def youtube_get_channel_analytics(channel_id: str, start_date: str = "30daysAgo",
                                  end_date: str = "today",
                                  metrics: str = "views,likes,subscribersGained",
                                  dimensions: str = "day") -> list[dict]:
    """Get YouTube Analytics for a channel. Returns list of rows with headers."""
    token = get_access_token()
    if not token:
        return []
    import requests
    params = {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": metrics,
        "dimensions": dimensions,
        "filters": f"channel=={channel_id}",
    }
    try:
        r = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        rows_raw = data.get("rows", [])
        col_headers = [c.get("name", "") for c in data.get("columnHeaders", [])]
        return [dict(zip(col_headers, row)) for row in rows_raw]
    except Exception as exc:
        logger.warning("YouTube channel analytics failed: %s", exc)
        return []


def youtube_search_channels(query: str, max_results: int = 10) -> list[dict]:
    """Search for YouTube channels."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/search",
        params={"part": "snippet", "q": query, "type": "channel", "maxResults": min(max_results, 50)},
    )
    if not data:
        return []
    return [{
        "channelId": item.get("id", {}).get("channelId", ""),
        "title": item.get("snippet", {}).get("title", ""),
        "description": (item.get("snippet", {}).get("description") or "")[:300],
        "publishedAt": item.get("snippet", {}).get("publishedAt", ""),
        "thumbnail": item.get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url", ""),
    } for item in data.get("items", [])]


def youtube_list_my_videos(max_results: int = 20, order: str = "date") -> list[dict]:
    """List authenticated user's uploaded videos."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/search",
        params={"part": "snippet", "forMine": "true", "type": "video",
                "maxResults": min(max_results, 50), "order": order},
    )
    if not data:
        return []
    return [{
        "videoId": item.get("id", {}).get("videoId", ""),
        "title": item.get("snippet", {}).get("title", ""),
        "description": (item.get("snippet", {}).get("description") or "")[:300],
        "publishedAt": item.get("snippet", {}).get("publishedAt", ""),
        "thumbnail": item.get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url", ""),
    } for item in data.get("items", [])]


def youtube_create_broadcast(title: str, description: str = "",
                             start_time: str = "",
                             privacy_status: str = "private") -> dict:
    """Create a YouTube live broadcast. start_time: ISO 8601 datetime."""
    if not start_time:
        start_time = datetime.utcnow().isoformat() + "Z"
    body = {
        "snippet": {"title": title, "description": description, "scheduledStartTime": start_time},
        "status": {"privacyStatus": privacy_status},
        "contentDetails": {"enableAutoStart": True, "enableAutoStop": True},
    }
    data = call_api(
        "https://www.googleapis.com/youtube/v3/liveBroadcasts?part=snippet,status,contentDetails",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create broadcast"}
    return {
        "broadcastId": data.get("id"),
        "title": title,
        "status": data.get("status", {}).get("lifeCycleStatus", ""),
        "boundStreamId": data.get("contentDetails", {}).get("boundStreamId", ""),
    }


def youtube_bind_broadcast(broadcast_id: str, stream_id: str) -> dict:
    """Bind a live broadcast to a live stream."""
    if not broadcast_id or not stream_id:
        return {"error": "broadcast_id and stream_id are required"}
    data = call_api(
        "https://www.googleapis.com/youtube/v3/liveBroadcasts/bind",
        method="POST",
        params={"part": "id,contentDetails", "id": broadcast_id, "streamId": stream_id},
    )
    if not data:
        return {"error": "Failed to bind broadcast"}
    return {"broadcastId": broadcast_id, "streamId": stream_id, "bound": True}


def youtube_transition_broadcast(broadcast_id: str, status: str = "live") -> dict:
    """Change broadcast status. status: testing, live, complete."""
    valid = ("testing", "live", "complete")
    if status not in valid:
        return {"error": f"status must be one of {valid}"}
    data = call_api(
        f"https://www.googleapis.com/youtube/v3/liveBroadcasts/transition?part=status&id={broadcast_id}&broadcastStatus={status}",
        method="POST",
    )
    if not data:
        return {"error": "Failed to transition broadcast"}
    return {"broadcastId": broadcast_id, "status": status, "lifeCycleStatus": data.get("status", {}).get("lifeCycleStatus", "")}


def youtube_create_stream(title: str, fmt: str = "720p") -> dict:
    """Create a live stream. fmt: 480p, 720p, 1080p."""
    cdn = {"resolution": fmt, "frameRate": "30fps", "ingestionType": "rtmp"}
    body = {
        "snippet": {"title": title},
        "cdn": cdn,
        "contentDetails": {"isReusable": True},
    }
    data = call_api(
        "https://www.googleapis.com/youtube/v3/liveStreams?part=snippet,cdn,contentDetails",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create stream"}
    cdn_info = data.get("cdn", {})
    ingestion = cdn_info.get("ingestionInfo", {})
    return {
        "streamId": data.get("id"),
        "title": title,
        "ingestionAddress": ingestion.get("ingestionAddress", ""),
        "streamName": ingestion.get("streamName", ""),
        "resolution": fmt,
    }


def youtube_get_video_categories(region_code: str = "US") -> list[dict]:
    """List video categories for a region."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/videoCategories",
        params={"part": "snippet", "regionCode": region_code},
    )
    if not data:
        return []
    return [{
        "categoryId": item.get("id", ""),
        "title": item.get("snippet", {}).get("title", ""),
        "assignable": item.get("snippet", {}).get("assignable", False),
    } for item in data.get("items", [])]


def youtube_list_playlists(channel_id: str, max_results: int = 20) -> list[dict]:
    """List playlists for a channel."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/playlists",
        params={"part": "snippet", "channelId": channel_id, "maxResults": min(max_results, 50)},
    )
    if not data:
        return []
    return [{
        "playlistId": item["id"],
        "title": item.get("snippet", {}).get("title", ""),
        "description": (item.get("snippet", {}).get("description") or "")[:300],
        "itemCount": item.get("snippet", {}).get("itemCount", 0),
        "publishedAt": item.get("snippet", {}).get("publishedAt", ""),
        "thumbnail": item.get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url", ""),
    } for item in data.get("items", [])]


def youtube_get_channel_sections(channel_id: str) -> list[dict]:
    """Get channel sections for a YouTube channel."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/channelSections",
        params={"part": "snippet,contentDetails", "channelId": channel_id},
    )
    if not data:
        return []
    return [{
        "sectionId": item["id"],
        "type": item.get("snippet", {}).get("type", ""),
        "title": item.get("snippet", {}).get("title", ""),
        "playlistIds": item.get("contentDetails", {}).get("playlists", []),
        "channelIds": item.get("contentDetails", {}).get("channels", []),
    } for item in data.get("items", [])]


def youtube_report_abuse(video_id: str, reason: str = "harassment") -> dict:
    """Report a video for abuse."""
    if not video_id:
        return {"error": "video_id is required"}
    result = call_api(
        "https://www.googleapis.com/youtube/v3/videos/reportAbuse",
        method="POST",
        json_body={"videoId": video_id, "reasonId": reason},
    )
    return {"ok": result is None, "videoId": video_id, "reason": reason}


def youtube_get_video_rating(video_id: str) -> dict:
    """Get authenticated user's rating for a video."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/videos/getRating",
        params={"id": video_id},
    )
    if not data:
        return {"error": "Failed to get rating"}
    items = data.get("items", [])
    if items:
        return {"videoId": video_id, "rating": items[0].get("rating", "none")}
    return {"videoId": video_id, "rating": "none"}


def youtube_get_trascript(video_id: str, language: str = "en") -> str:
    """Get video captions/transcript as plain text. Fetches caption track, downloads, parses."""
    import requests
    # Find caption track for requested language
    captions = youtube_get_captions(video_id)
    caption_id = None
    for cap in captions:
        if cap.get("language", "").startswith(language):
            caption_id = cap["id"]
            break
    if not caption_id and captions:
        caption_id = captions[0]["id"]
    if not caption_id:
        return ""
    # Download in srt format and strip timestamps
    raw = youtube_download_caption(caption_id, "srt")
    if not raw:
        return ""
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        lines.append(line)
    return " ".join(lines)


def youtube_channel_search(channel_id: str, query: str, max_results: int = 20) -> list[dict]:
    """Search within a channel's videos."""
    data = call_api(
        "https://www.googleapis.com/youtube/v3/search",
        params={"part": "snippet", "channelId": channel_id, "q": query,
                "type": "video", "maxResults": min(max_results, 50)},
    )
    if not data:
        return []
    return [{
        "videoId": item.get("id", {}).get("videoId", ""),
        "title": item.get("snippet", {}).get("title", ""),
        "description": (item.get("snippet", {}).get("description") or "")[:300],
        "publishedAt": item.get("snippet", {}).get("publishedAt", ""),
        "thumbnail": item.get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url", ""),
    } for item in data.get("items", [])]


# ═══════════════════════════════════════════════════════════════════
#  Sheets — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def sheets_insert_rows(spreadsheet_id: str, sheet_id: int, start_index: int, num_rows: int = 1) -> dict:
    """Insert rows at a specific index in a sheet."""
    body = {
        "requests": [{
            "insertDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_index,
                    "endIndex": start_index + num_rows,
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to insert rows"}


def sheets_delete_rows(spreadsheet_id: str, sheet_id: int, start_index: int, end_index: int) -> dict:
    """Delete rows from a sheet."""
    body = {
        "requests": [{
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_index,
                    "endIndex": end_index,
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to delete rows"}


def sheets_insert_columns(spreadsheet_id: str, sheet_id: int, start_index: int, num_columns: int = 1) -> dict:
    """Insert columns at a specific index in a sheet."""
    body = {
        "requests": [{
            "insertDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_index,
                    "endIndex": start_index + num_columns,
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to insert columns"}


def sheets_delete_columns(spreadsheet_id: str, sheet_id: int, start_index: int, end_index: int) -> dict:
    """Delete columns from a sheet."""
    body = {
        "requests": [{
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_index,
                    "endIndex": end_index,
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to delete columns"}


def sheets_update_cell(spreadsheet_id: str, sheet_name: str, row: int, col: int, value: str) -> dict:
    """Update a single cell value in a sheet."""
    body = {
        "requests": [{
            "updateCells": {
                "range": {
                    "sheetId": sheet_name,
                    "startRowIndex": row,
                    "startColumnIndex": col,
                    "endRowIndex": row + 1,
                    "endColumnIndex": col + 1,
                },
                "rows": [{"values": [{"userEnteredValue": {"stringValue": value}}]}],
                "fields": "userEnteredValue",
            }
        }]
    }
    result = call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    )
    if not result:
        return {"error": "Failed to update cell"}
    return result


def sheets_format_range(spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int,
                        start_col: int, end_col: int, bold: Optional[bool] = None,
                        italic: Optional[bool] = None, font_size: Optional[int] = None,
                        background_color: Optional[dict] = None,
                        text_color: Optional[dict] = None,
                        horizontal_alignment: Optional[str] = None) -> dict:
    """Apply formatting to a cell range."""
    cell_format: dict[str, Any] = {}
    if bold is not None:
        cell_format["textFormat"] = cell_format.get("textFormat", {})
        cell_format["textFormat"]["bold"] = bold
    if italic is not None:
        cell_format["textFormat"] = cell_format.get("textFormat", {})
        cell_format["textFormat"]["italic"] = italic
    if font_size is not None:
        cell_format["textFormat"] = cell_format.get("textFormat", {})
        cell_format["textFormat"]["fontSize"] = font_size
    if background_color is not None:
        cell_format["backgroundColor"] = background_color
    if text_color is not None:
        cell_format["textFormat"] = cell_format.get("textFormat", {})
        cell_format["textFormat"]["foregroundColor"] = text_color
    if horizontal_alignment is not None:
        cell_format["horizontalAlignment"] = horizontal_alignment
    body = {
        "requests": [{
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col,
                },
                "cell": {"userEnteredFormat": cell_format},
                "fields": "userEnteredFormat",
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to format range"}


def sheets_add_sheet(spreadsheet_id: str, title: str) -> dict:
    """Add a new sheet tab to a spreadsheet."""
    body = {
        "requests": [{
            "addSheet": {
                "properties": {"title": title}
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to add sheet"}


def sheets_delete_sheet(spreadsheet_id: str, sheet_id: int) -> dict:
    """Delete a sheet tab from a spreadsheet."""
    body = {
        "requests": [{
            "deleteSheet": {
                "sheetId": sheet_id
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to delete sheet"}


def sheets_clear(spreadsheet_id: str, range_name: str) -> dict:
    """Clear cell values in a range."""
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}:clear",
        method="POST", json_body={},
    ) or {"error": "Failed to clear range"}


def sheets_get_columns(spreadsheet_id: str, sheet_name: str = "Sheet1") -> list[dict]:
    """List column metadata for a sheet using includeGridData."""
    token = get_access_token()
    if not token:
        return []
    import requests
    try:
        r = requests.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
            params={"ranges": sheet_name, "includeGridData": "true"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        sheets_data = data.get("sheets", [])
        if not sheets_data:
            return []
        grid_data = sheets_data[0].get("data", [])
        if not grid_data:
            return []
        columns = []
        for i, col_meta in enumerate(grid_data[0].get("columnMetadata", [])):
            columns.append({
                "index": i,
                "size": col_meta.get("pixelSize", 0),
            })
        return columns
    except Exception as exc:
        logger.warning("sheets_get_columns failed: %s", exc)
        return []


def sheets_find_replace(spreadsheet_id: str, find: str, replacement: str,
                        sheet_id: int, all_sheets: bool = False) -> dict:
    """Find and replace text across a sheet range."""
    body = {
        "requests": [{
            "findReplace": {
                "find": find,
                "replacement": replacement,
                "allSheets": all_sheets,
            }
        }]
    }
    if not all_sheets:
        body["requests"][0]["findReplace"]["sheetId"] = sheet_id
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to find/replace"}


def sheets_auto_resize(spreadsheet_id: str, sheet_id: int,
                       start_index: int = 0, end_index: int = 26) -> dict:
    """Auto-resize columns in a sheet."""
    body = {
        "requests": [{
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_index,
                    "endIndex": end_index,
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to auto-resize columns"}


def sheets_protect_range(spreadsheet_id: str, sheet_id: int,
                         start_row: int, end_row: int,
                         start_col: int, end_col: int,
                         description: str = "") -> dict:
    """Add a protected range to a sheet."""
    body = {
        "requests": [{
            "addProtectedRange": {
                "protectedRange": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
                    },
                    "description": description,
                    "warningOnly": True,
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to protect range"}


def sheets_create_chart(spreadsheet_id: str, sheet_id: int, title: str,
                        chart_type: str = "COLUMN", range_sheet_id: Optional[int] = None,
                        start_row: int = 0, end_row: int = 10,
                        start_col: int = 0, end_col: int = 5) -> dict:
    """Insert a chart into a sheet."""
    body = {
        "requests": [{
            "addChart": {
                "chart": {
                    "spec": {
                        "title": title,
                        "basicChart": {
                            "chartType": chart_type,
                            "legendPosition": "BOTTOM_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "X Axis"},
                                {"position": "LEFT_AXIS", "title": "Y Axis"},
                            ],
                            "domains": [{
                                "domain": {
                                    "sourceRange": {
                                        "sources": [{
                                            "sheetId": range_sheet_id or sheet_id,
                                            "startRowIndex": start_row,
                                            "endRowIndex": end_row,
                                            "startColumnIndex": start_col,
                                            "endColumnIndex": start_col + 1,
                                        }]
                                    }
                                }
                            }],
                            "series": [{
                                "series": {
                                    "sourceRange": {
                                        "sources": [{
                                            "sheetId": range_sheet_id or sheet_id,
                                            "startRowIndex": start_row,
                                            "endRowIndex": end_row,
                                            "startColumnIndex": start_col + 1,
                                            "endColumnIndex": end_col,
                                        }]
                                    }
                                },
                                "targetAxis": "LEFT_AXIS",
                            }],
                        },
                    },
                    "position": {
                        "newSheet": True
                    }
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to create chart"}


def sheets_merge_cells(spreadsheet_id: str, sheet_id: int,
                       start_row: int, end_row: int,
                       start_col: int, end_col: int) -> dict:
    """Merge cells in a range."""
    body = {
        "requests": [{
            "mergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col,
                },
                "mergeType": "MERGE_ALL",
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to merge cells"}


def sheets_unmerge_cells(spreadsheet_id: str, sheet_id: int,
                         start_row: int, end_row: int,
                         start_col: int, end_col: int) -> dict:
    """Unmerge cells in a range."""
    body = {
        "requests": [{
            "unmergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col,
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to unmerge cells"}


def sheets_set_data_validation(spreadsheet_id: str, sheet_id: int,
                               start_row: int, end_row: int,
                               start_col: int, end_col: int,
                               condition_type: str = "ONE_OF_LIST",
                               values: Optional[list[str]] = None,
                               strict: bool = True,
                               input_message: str = "") -> dict:
    """Set data validation on a range."""
    condition = {"type": condition_type}
    if values:
        condition["values"] = [{"userEnteredValue": v} for v in values]
    body = {
        "requests": [{
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col,
                },
                "rule": {
                    "condition": condition,
                    "strict": strict,
                    "inputMessage": input_message,
                    "showCustomUi": True if input_message else False,
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to set data validation"}


def sheets_move_sheet(spreadsheet_id: str, sheet_id: int, destination_index: int) -> dict:
    """Move/reorder a sheet tab to a new position."""
    body = {
        "requests": [{
            "moveSheet": {
                "sheetId": sheet_id,
                "destinationIndex": destination_index,
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to move sheet"}


def sheets_duplicate_sheet(spreadsheet_id: str, sheet_id: int,
                           insert_sheet_index: Optional[int] = None,
                           new_sheet_name: Optional[str] = None) -> dict:
    """Duplicate a sheet tab."""
    duplicate = {"sourceSheetId": sheet_id}
    if insert_sheet_index is not None:
        duplicate["insertSheetIndex"] = insert_sheet_index
    if new_sheet_name is not None:
        duplicate["newSheetName"] = new_sheet_name
    body = {
        "requests": [{"duplicateSheet": duplicate}]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to duplicate sheet"}


def sheets_get_named_ranges(spreadsheet_id: str) -> list[dict]:
    """List all named ranges in a spreadsheet."""
    data = call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
        params={"fields": "namedRanges"},
    )
    if not data:
        return []
    return data.get("namedRanges", [])


def sheets_add_named_range(spreadsheet_id: str, name: str,
                           sheet_id: int, start_row: int, end_row: int,
                           start_col: int, end_col: int) -> dict:
    """Add a named range to a spreadsheet."""
    body = {
        "requests": [{
            "addNamedRange": {
                "namedRange": {
                    "name": name,
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
                    }
                }
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to add named range"}


def sheets_delete_named_range(spreadsheet_id: str, named_range_id: str) -> dict:
    """Delete a named range from a spreadsheet."""
    body = {
        "requests": [{
            "deleteNamedRange": {
                "namedRangeId": named_range_id,
            }
        }]
    }
    return call_api(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to delete named range"}


# ═══════════════════════════════════════════════════════════════════
#  Docs — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def docs_insert_table(document_id: str, rows: int, cols: int, index: int = 0) -> dict:
    """Insert a table at a specific index in a document."""
    return docs_batch_update(document_id, [{
        "insertTable": {
            "rows": rows,
            "columns": cols,
            "location": {"index": index},
        }
    }])


def docs_delete_table_row(document_id: str, table_start_index: int, row_index: int) -> dict:
    """Delete a table row from a document."""
    return docs_batch_update(document_id, [{
        "deleteTableRow": {
            "tableCellLocation": {
                "tableStartLocation": {"index": table_start_index},
                "rowIndex": row_index,
                "columnIndex": 0,
            }
        }
    }])


def docs_insert_page_break(document_id: str, index: int = 0) -> dict:
    """Insert a page break at a specific index."""
    return docs_batch_update(document_id, [{
        "insertPageBreak": {
            "location": {"index": index},
        }
    }])


def docs_insert_header(document_id: str, text: str) -> dict:
    """Insert a header on a document."""
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.post(
            f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "requests": [
                    {"createHeader": {"type": "DEFAULT", "sectionBreakLocation": {"index": 0}}},
                    {"insertText": {"location": {"index": 1}, "text": text}},
                ]
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def docs_insert_footer(document_id: str, text: str) -> dict:
    """Insert a footer on a document."""
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.post(
            f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "requests": [
                    {"createFooter": {"type": "DEFAULT", "sectionBreakLocation": {"index": 0}}},
                    {"insertText": {"location": {"index": 1}, "text": text}},
                ]
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def docs_replace_all_text(document_id: str, find_text: str, replace_text: str) -> dict:
    """Find and replace text across an entire document."""
    return docs_batch_update(document_id, [{
        "replaceAllText": {
            "containsText": {"text": find_text, "matchCase": True},
            "replaceText": replace_text,
        }
    }])


def docs_update_text_style(document_id: str, index: int, length: int,
                           bold: Optional[bool] = None,
                           italic: Optional[bool] = None,
                           underline: Optional[bool] = None,
                           font_size: Optional[int] = None,
                           foreground_color: Optional[dict] = None) -> dict:
    """Update text style at a specific range."""
    text_style: dict[str, Any] = {}
    if bold is not None:
        text_style["bold"] = bold
    if italic is not None:
        text_style["italic"] = italic
    if underline is not None:
        text_style["underline"] = underline
    if font_size is not None:
        text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
    if foreground_color is not None:
        text_style["foregroundColor"] = foreground_color
    return docs_batch_update(document_id, [{
        "updateTextStyle": {
            "range": {"startIndex": index, "endIndex": index + length},
            "textStyle": text_style,
            "fields": ",".join(text_style.keys()),
        }
    }])


def docs_update_paragraph_style(document_id: str, index: int, length: int,
                                alignment: Optional[str] = None,
                                line_spacing: Optional[float] = None,
                                indent_start: Optional[dict] = None,
                                indent_end: Optional[dict] = None,
                                space_before: Optional[dict] = None,
                                space_after: Optional[dict] = None) -> dict:
    """Update paragraph style at a specific range."""
    paragraph_style: dict[str, Any] = {}
    fields = []
    if alignment is not None:
        paragraph_style["alignment"] = alignment
        fields.append("alignment")
    if line_spacing is not None:
        paragraph_style["lineSpacing"] = line_spacing
        fields.append("lineSpacing")
    if indent_start is not None:
        paragraph_style["indentStart"] = indent_start
        fields.append("indentStart")
    if indent_end is not None:
        paragraph_style["indentEnd"] = indent_end
        fields.append("indentEnd")
    if space_before is not None:
        paragraph_style["spaceBefore"] = space_before
        fields.append("spaceBefore")
    if space_after is not None:
        paragraph_style["spaceAfter"] = space_after
        fields.append("spaceAfter")
    if not paragraph_style:
        return {"error": "No paragraph style options provided"}
    return docs_batch_update(document_id, [{
        "updateParagraphStyle": {
            "range": {"startIndex": index, "endIndex": index + length},
            "paragraphStyle": paragraph_style,
            "fields": ",".join(fields),
        }
    }])


def docs_get_document(document_id: str) -> dict:
    """Get a document with full content including tables, images, headers, footers."""
    data = call_api(
        f"https://docs.googleapis.com/v1/documents/{document_id}",
        params={"suggestionsViewMode": "PREVIEW_WITHOUT_SUGGESTIONS"},
    )
    if not data:
        return {"error": "Doc not found"}
    return {
        "documentId": data.get("documentId"),
        "title": data.get("title"),
        "body": data.get("body"),
        "headers": data.get("headers"),
        "footers": data.get("footers"),
        "inlineObjects": data.get("inlineObjects"),
        "positionedObjects": data.get("positionedObjects"),
        "lists": data.get("lists"),
        "namedRanges": data.get("namedRanges"),
        "namedStyles": data.get("namedStyles"),
        "suggestionsViewMode": data.get("suggestionsViewMode"),
    }


def docs_create_positioned_image(document_id: str, image_url: str,
                                 left_pt: float = 0, top_pt: float = 0,
                                 width_pt: float = 200, height_pt: float = 200) -> dict:
    """Insert a positioned (floating) image into a document."""
    return docs_batch_update(document_id, [{
        "createPositionedImage": {
            "uri": image_url,
            "left": {"magnitude": left_pt, "unit": "PT"},
            "top": {"magnitude": top_pt, "unit": "PT"},
            "width": {"magnitude": width_pt, "unit": "PT"},
            "height": {"magnitude": height_pt, "unit": "PT"},
        }
    }])


def docs_delete_header(document_id: str) -> dict:
    """Delete the default header from a document."""
    return docs_batch_update(document_id, [{
        "deleteHeader": {"type": "DEFAULT"}
    }])


def docs_delete_footer(document_id: str) -> dict:
    """Delete the default footer from a document."""
    return docs_batch_update(document_id, [{
        "deleteFooter": {"type": "DEFAULT"}
    }])


def docs_update_document_title(document_id: str, title: str) -> dict:
    """Update the document title using the Drive API (PATCH to rename)."""
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.patch(
            f"https://www.googleapis.com/drive/v3/files/{document_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"name": title},
            timeout=10,
        )
        r.raise_for_status()
        return {"documentId": document_id, "title": title, "updated": True}
    except Exception as exc:
        return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════════
#  Slides — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def slides_delete_slide(presentation_id: str, slide_object_id: str) -> dict:
    """Delete a slide from a presentation."""
    body = {
        "requests": [{
            "deleteObject": {"objectId": slide_object_id}
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to delete slide"}


def slides_duplicate_slide(presentation_id: str, slide_object_id: str,
                           insertion_index: Optional[int] = None) -> dict:
    """Duplicate a slide at a specified position."""
    duplicate = {"objectId": slide_object_id}
    if insertion_index is not None:
        duplicate["insertionIndex"] = insertion_index
    body = {
        "requests": [{"duplicateObject": duplicate}]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to duplicate slide"}


def slides_move_slide(presentation_id: str, slide_object_id: str,
                      insertion_index: int) -> dict:
    """Move a slide to a different position."""
    body = {
        "requests": [{
            "updateSlidesPosition": {
                "slideObjectIds": [slide_object_id],
                "insertionIndex": insertion_index,
            }
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to move slide"}


def slides_update_slide_background(presentation_id: str, slide_object_id: str,
                                   solid_color: Optional[dict] = None,
                                   image_url: Optional[str] = None) -> dict:
    """Set a slide background to a solid color or image."""
    page_element = {"pageBackgroundFill": {}}
    if solid_color:
        page_element["pageBackgroundFill"] = {
            "solidFill": {"color": solid_color}
        }
    elif image_url:
        page_element["pageBackgroundFill"] = {
            "stretchedPictureFill": {"contentUrl": image_url}
        }
    else:
        return {"error": "Provide either solid_color or image_url"}
    body = {
        "requests": [{
            "updatePageProperties": {
                "objectId": slide_object_id,
                "pageProperties": page_element,
                "fields": "pageBackgroundFill",
            }
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to update slide background"}


def slides_insert_table(presentation_id: str, slide_id: str,
                        rows: int, cols: int,
                        left_pt: float = 50, top_pt: float = 50,
                        width_pt: float = 400, height_pt: float = 200) -> dict:
    """Insert a table on a slide."""
    body = {
        "requests": [{
            "createTable": {
                "objectId": f"tbl_{int(import_time())}",
                "rows": rows,
                "columns": cols,
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": width_pt, "unit": "PT"},
                        "height": {"magnitude": height_pt, "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": left_pt, "translateY": top_pt,
                        "unit": "PT",
                    },
                }
            }
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to insert table"}


def slides_insert_shape(presentation_id: str, slide_id: str,
                        shape_type: str = "RECTANGLE",
                        left_pt: float = 50, top_pt: float = 50,
                        width_pt: float = 200, height_pt: float = 100) -> dict:
    """Insert a shape (rectangle, ellipse, triangle, etc.) on a slide."""
    body = {
        "requests": [{
            "createShape": {
                "objectId": f"shape_{int(import_time())}",
                "shapeType": shape_type,
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": width_pt, "unit": "PT"},
                        "height": {"magnitude": height_pt, "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": left_pt, "translateY": top_pt,
                        "unit": "PT",
                    },
                }
            }
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to insert shape"}


def slides_insert_line(presentation_id: str, slide_id: str,
                       left_pt: float = 50, top_pt: float = 50,
                       width_pt: float = 200, height_pt: float = 0) -> dict:
    """Insert a line/arrow on a slide."""
    body = {
        "requests": [{
            "createLine": {
                "objectId": f"line_{int(import_time())}",
                "lineCategory": "STRAIGHT",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": width_pt, "unit": "PT"},
                        "height": {"magnitude": height_pt, "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": left_pt, "translateY": top_pt,
                        "unit": "PT",
                    },
                }
            }
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to insert line"}


def slides_update_text(presentation_id: str, object_id: str, text: str) -> dict:
    """Update an existing text box or shape content."""
    body = {
        "requests": [{
            "insertText": {
                "objectId": object_id,
                "insertionIndex": 0,
                "text": text,
            }
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to update text"}


def slides_get_page_thumbnails(presentation_id: str,
                               page_object_id: Optional[str] = None) -> list[dict]:
    """Get page thumbnails for a presentation."""
    token = get_access_token()
    if not token:
        return []
    import requests
    url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}/pages/{page_object_id}/pageThumbnails" if page_object_id else f"https://slides.googleapis.com/v1/presentations/{presentation_id}/pages/*/pageThumbnails"
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        thumbs = []
        for item in data.get("items", []):
            thumbs.append({
                "pageId": item.get("pageId"),
                "thumbnailUrl": item.get("thumbnailUrl"),
                "width": item.get("width"),
                "height": item.get("height"),
            })
        return thumbs
    except Exception as exc:
        logger.warning("slides_get_page_thumbnails failed: %s", exc)
        return []


def slides_list(max_results: int = 20) -> list[dict]:
    """List presentations from Drive with Slides MIME type."""
    data = call_api(
        "https://www.googleapis.com/drive/v3/files",
        params={
            "q": "mimeType='application/vnd.google-apps.presentation' and trashed=false",
            "pageSize": min(max_results, 100),
            "fields": "files(id,name,createdTime,modifiedTime,webViewLink)",
        },
    )
    if not data:
        return []
    return [{
        "presentationId": f["id"],
        "title": f.get("name"),
        "createdTime": f.get("createdTime"),
        "modifiedTime": f.get("modifiedTime"),
        "url": f.get("webViewLink"),
    } for f in data.get("files", [])]


def slides_refresh_presentation(presentation_id: str) -> dict:
    """Reload presentation data fresh from the API."""
    data = call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}",
    )
    if not data:
        return {"error": "Presentation not found"}
    return data


def slides_add_video(presentation_id: str, slide_id: str, video_url: str,
                     left_pt: float = 50, top_pt: float = 50,
                     width_pt: float = 400, height_pt: float = 300) -> dict:
    """Add a YouTube video to a slide."""
    body = {
        "requests": [{
            "createVideo": {
                "objectId": f"vid_{int(import_time())}",
                "source": "YOUTUBE",
                "id": video_url,
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": width_pt, "unit": "PT"},
                        "height": {"magnitude": height_pt, "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": left_pt, "translateY": top_pt,
                        "unit": "PT",
                    },
                }
            }
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to add video"}


def slides_add_word_art(presentation_id: str, slide_id: str, text: str,
                        left_pt: float = 50, top_pt: float = 50,
                        width_pt: float = 300, height_pt: float = 100) -> dict:
    """Add WordArt text to a slide."""
    body = {
        "requests": [{
            "createShape": {
                "objectId": f"wordart_{int(import_time())}",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": width_pt, "unit": "PT"},
                        "height": {"magnitude": height_pt, "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": left_pt, "translateY": top_pt,
                        "unit": "PT",
                    },
                },
            }
        }, {
            "insertText": {
                "objectId": f"wordart_{int(import_time())}",
                "insertionIndex": 0,
                "text": text,
            }
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to add WordArt"}


def slides_update_page_element_transform(presentation_id: str, page_element_id: str,
                                         translate_x: float, translate_y: float,
                                         scale_x: float = 1, scale_y: float = 1,
                                         width_pt: Optional[float] = None,
                                         height_pt: Optional[float] = None) -> dict:
    """Update the position and size of a page element."""
    transform = {
        "scaleX": scale_x,
        "scaleY": scale_y,
        "translateX": translate_x,
        "translateY": translate_y,
        "unit": "PT",
    }
    update = {
        "objectId": page_element_id,
        "elementProperties": {
            "transform": transform,
        },
        "fields": "transform",
    }
    if width_pt is not None and height_pt is not None:
        update["elementProperties"]["size"] = {
            "width": {"magnitude": width_pt, "unit": "PT"},
            "height": {"magnitude": height_pt, "unit": "PT"},
        }
        update["fields"] = "transform,size"
    body = {
        "requests": [{
            "updatePageElementTransform": update
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to update element transform"}


def slides_group_objects(presentation_id: str, slide_id: str,
                         object_ids: list[str]) -> dict:
    """Group multiple page elements together."""
    body = {
        "requests": [{
            "groupObjects": {
                "childrenObjectIds": object_ids,
                "objectId": f"group_{int(import_time())}",
            }
        }]
    }
    return call_api(
        f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
        method="POST", json_body=body,
    ) or {"error": "Failed to group objects"}


# ═══════════════════════════════════════════════════════════════════
#  Calendar — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def calendar_update_event(calendar_id: str = "primary", event_id: str = "",
                           summary: Optional[str] = None,
                           description: Optional[str] = None,
                           start_time: Optional[str] = None,
                           end_time: Optional[str] = None,
                           location: Optional[str] = None,
                           timezone: str = "UTC") -> dict:
    """Update an existing calendar event. Omitted fields are left unchanged."""
    if not event_id:
        return {"error": "event_id is required"}
    body: dict[str, Any] = {}
    if summary is not None:
        body["summary"] = summary
    if description is not None:
        body["description"] = description
    if start_time is not None:
        body["start"] = {"dateTime": start_time, "timeZone": timezone}
    if end_time is not None:
        body["end"] = {"dateTime": end_time, "timeZone": timezone}
    if location is not None:
        body["location"] = location
    if not body:
        return {"error": "Nothing to update"}
    data = call_api(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
        method="PATCH", json_body=body,
    )
    if not data:
        return {"error": "Failed to update event"}
    return {
        "id": data.get("id"),
        "summary": data.get("summary"),
        "htmlLink": data.get("htmlLink"),
        "start": data.get("start"),
        "end": data.get("end"),
    }


def calendar_delete_event(calendar_id: str = "primary", event_id: str = "") -> dict:
    """Delete a calendar event."""
    if not event_id:
        return {"error": "event_id is required"}
    result = call_api(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
        method="DELETE",
    )
    return {"ok": result is None, "eventId": event_id}


def calendar_get_event(calendar_id: str = "primary", event_id: str = "") -> dict:
    """Get a single calendar event with full details."""
    if not event_id:
        return {"error": "event_id is required"}
    data = call_api(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
    )
    if not data:
        return {"error": "Event not found"}
    return {
        "id": data.get("id"),
        "summary": data.get("summary"),
        "description": (data.get("description") or "")[:500],
        "start": data.get("start", {}),
        "end": data.get("end", {}),
        "location": data.get("location"),
        "status": data.get("status"),
        "creator": data.get("creator", {}).get("email"),
        "htmlLink": data.get("htmlLink"),
        "reminders": data.get("reminders", {}),
        "attendees": [{"email": a.get("email"), "responseStatus": a.get("responseStatus")}
                      for a in (data.get("attendees") or [])],
        "recurrence": data.get("recurrence", []),
    }


def calendar_freebusy(calendar_id: str = "primary",
                       time_min: str = "", time_max: str = "",
                       timezone: str = "UTC") -> list[dict]:
    """Check busy time slots for a calendar within a time range."""
    if not time_min or not time_max:
        return [{"error": "time_min and time_max are required (ISO 8601)"}]
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": timezone,
        "items": [{"id": calendar_id}],
    }
    data = call_api(
        "https://www.googleapis.com/calendar/v3/freeBusy",
        method="POST", json_body=body,
    )
    if not data:
        return []
    cal_map = data.get("calendars", {})
    cal_data = cal_map.get(calendar_id, {})
    return [{
        "start": b.get("start"),
        "end": b.get("end"),
    } for b in cal_data.get("busy", [])]


def calendar_quick_add(calendar_id: str = "primary", text: str = "") -> dict:
    """Quickly create an event using natural language text."""
    if not text:
        return {"error": "text is required (e.g. 'Meeting at 3pm tomorrow')"}
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.post(
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/quickAdd"
            "?conferenceDataVersion=0&sendNotifications=true",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"text": text},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "id": data.get("id"),
            "summary": data.get("summary"),
            "htmlLink": data.get("htmlLink"),
            "start": data.get("start"),
            "end": data.get("end"),
        }
    except Exception as exc:
        return {"error": str(exc)}


def calendar_import_event(calendar_id: str = "primary", summary: str = "Imported event",
                           description: str = "",
                           start_time: str = "", end_time: str = "",
                           timezone: str = "UTC",
                           location: Optional[str] = None) -> dict:
    """Import an event to a secondary calendar (bypasses default reminders)."""
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
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/import"
        "?supportsAttachments=true",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to import event"}
    return {
        "id": data.get("id"),
        "summary": data.get("summary"),
        "htmlLink": data.get("htmlLink"),
        "start": data.get("start"),
        "end": data.get("end"),
    }


def calendar_list_acl(calendar_id: str = "primary") -> list[dict]:
    """List ACL (access control) rules for a calendar."""
    data = call_api(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/acl",
    )
    if not data:
        return []
    return [{
        "id": r.get("id"),
        "scope": r.get("scope", {}).get("type"),
        "scopeValue": r.get("scope", {}).get("value", ""),
        "role": r.get("role"),
    } for r in data.get("items", [])]


def calendar_move_event(event_id: str = "", destination_calendar_id: str = "",
                         source_calendar_id: str = "primary") -> dict:
    """Move an event from one calendar to another."""
    if not event_id or not destination_calendar_id:
        return {"error": "event_id and destination_calendar_id are required"}
    data = call_api(
        f"https://www.googleapis.com/calendar/v3/calendars/{source_calendar_id}/events/{event_id}",
        method="PATCH",
        json_body={"calendarId": destination_calendar_id},
    )
    if not data:
        return {"error": "Failed to move event"}
    return {
        "id": data.get("id"),
        "summary": data.get("summary"),
        "newCalendarId": destination_calendar_id,
        "htmlLink": data.get("htmlLink"),
    }


def calendar_get_colors() -> dict:
    """Get color definitions for calendars and events."""
    data = call_api("https://www.googleapis.com/calendar/v3/colors")
    if not data:
        return {}
    return {
        "calendar": {k: {"background": v.get("background"), "foreground": v.get("foreground")}
                     for k, v in (data.get("calendar", {}) or {}).items()},
        "event": {k: {"background": v.get("background"), "foreground": v.get("foreground")}
                  for k, v in (data.get("event", {}) or {}).items()},
        "kind": data.get("kind"),
        "updated": data.get("updated"),
    }


def calendar_list_colors() -> dict:
    """Alias for calendar_get_colors."""
    return calendar_get_colors()


def calendar_set_reminder(calendar_id: str = "primary",
                           reminders: Optional[list[dict]] = None) -> dict:
    """Set default reminders on a calendar. reminders: list of {'method': 'popup'|'email', 'minutes': int}."""
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    body = {
        "reminders": {
            "overrides": reminders or [{"method": "popup", "minutes": 30}],
            "useDefault": False,
        }
    }
    try:
        r = requests.patch(
            f"https://www.googleapis.com/calendar/v3/users/me/calendarList/{calendar_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "calendarId": calendar_id,
            "defaultReminders": data.get("defaultReminders", []),
        }
    except Exception as exc:
        return {"error": str(exc)}


def calendar_watch(calendar_id: str = "primary", channel_id: str = "",
                    webhook_url: str = "", token: str = "") -> dict:
    """Start watching for changes to a calendar via push notifications."""
    if not channel_id or not webhook_url:
        return {"error": "channel_id and webhook_url are required"}
    body = {
        "id": channel_id,
        "type": "web_hook",
        "address": webhook_url,
    }
    if token:
        body["token"] = token
    data = call_api(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/watch",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to start watch"}
    return {
        "resourceId": data.get("resourceId"),
        "expiration": data.get("expiration"),
        "channelId": channel_id,
    }


def calendar_stop_watch(channel_id: str = "", resource_id: str = "") -> dict:
    """Stop watching for changes by closing the notification channel."""
    if not channel_id or not resource_id:
        return {"error": "channel_id and resource_id are required"}
    result = call_api(
        "https://www.googleapis.com/calendar/v3/channels/stop",
        method="POST",
        json_body={"id": channel_id, "resourceId": resource_id},
    )
    return {"ok": result is None}


# ═══════════════════════════════════════════════════════════════════
#  Google Drive — Extended (copy, move, trash, labels, watch, IDs)
# ═══════════════════════════════════════════════════════════════════


def drive_copy(file_id: str = "", new_name: str = "",
                parent_folder_id: Optional[str] = None) -> dict:
    """Copy a Drive file with an optional new name and destination folder."""
    if not file_id:
        return {"error": "file_id is required"}
    body: dict[str, Any] = {}
    if new_name:
        body["name"] = new_name
    if parent_folder_id:
        body["parents"] = [parent_folder_id]
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/copy",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to copy file"}
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "mimeType": data.get("mimeType"),
        "webViewLink": data.get("webViewLink"),
    }


def drive_move(file_id: str = "", new_parent_id: str = "",
                old_parent_id: Optional[str] = None) -> dict:
    """Move a file to a different folder."""
    if not file_id or not new_parent_id:
        return {"error": "file_id and new_parent_id are required"}
    params: dict[str, str] = {
        "addParents": new_parent_id,
    }
    if old_parent_id:
        params["removeParents"] = old_parent_id
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        method="PATCH",
        params=params,
        json_body={},
    )
    if not data:
        return {"error": "Failed to move file"}
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "parents": data.get("parents", []),
    }


def drive_trash(file_id: str = "") -> dict:
    """Move a file to the Drive trash."""
    if not file_id:
        return {"error": "file_id is required"}
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        method="PATCH",
        json_body={"trashed": True},
    )
    if not data:
        return {"error": "Failed to trash file"}
    return {"id": data.get("id"), "name": data.get("name"), "trashed": True}


def drive_untrash(file_id: str = "") -> dict:
    """Restore a file from the Drive trash."""
    if not file_id:
        return {"error": "file_id is required"}
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        method="PATCH",
        json_body={"trashed": False},
    )
    if not data:
        return {"error": "Failed to untrash file"}
    return {"id": data.get("id"), "name": data.get("name"), "trashed": False}


def drive_update(file_id: str = "", name: Optional[str] = None,
                  description: Optional[str] = None) -> dict:
    """Update file metadata (name, description)."""
    if not file_id:
        return {"error": "file_id is required"}
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if not body:
        return {"error": "Nothing to update"}
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        method="PATCH", json_body=body,
    )
    if not data:
        return {"error": "Failed to update file"}
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "description": (data.get("description") or "")[:300],
        "modifiedTime": data.get("modifiedTime"),
    }


def drive_empty_trash() -> dict:
    """Permanently empty the Drive trash."""
    result = call_api(
        "https://www.googleapis.com/drive/v3/files/trash",
        method="DELETE",
    )
    return {"ok": result is None}


def drive_about() -> dict:
    """Get storage quota, usage, and max upload size."""
    data = call_api(
        "https://www.googleapis.com/drive/v3/about",
        params={"fields": "storageQuota,maxUploadSize,user,importFormats,exportFormats"},
    )
    if not data:
        return {"error": "Failed to get Drive info"}
    quota = data.get("storageQuota", {})
    return {
        "user": {
            "email": data.get("user", {}).get("emailAddress", ""),
            "name": data.get("user", {}).get("displayName", ""),
        },
        "storageQuota": {
            "limit": int(quota.get("limit", 0)),
            "usage": int(quota.get("usage", 0)),
            "usageInDrive": int(quota.get("usageInDrive", 0)),
            "usageInDriveTrash": int(quota.get("usageInDriveTrash", 0)),
        },
        "maxUploadSize": int(data.get("maxUploadSize", 0)),
    }


def drive_list_starred(page_size: int = 20) -> list[dict]:
    """List starred files in Drive."""
    data = call_api(
        "https://www.googleapis.com/drive/v3/files",
        params={
            "q": "starred=true and trashed=false",
            "pageSize": min(page_size, 100),
            "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,starred)",
        },
    )
    if not data:
        return []
    return [{
        "id": f.get("id"),
        "name": f.get("name"),
        "mimeType": f.get("mimeType"),
        "size": f.get("size"),
        "createdTime": f.get("createdTime"),
        "modifiedTime": f.get("modifiedTime"),
        "webViewLink": f.get("webViewLink"),
        "starred": f.get("starred", False),
    } for f in data.get("files", [])]


def drive_create_shortcut(file_id: str = "", name: str = "",
                           parent_folder_id: Optional[str] = None) -> dict:
    """Create a shortcut to a Drive file."""
    if not file_id:
        return {"error": "file_id is required"}
    body: dict[str, Any] = {
        "name": name or f"Shortcut to {file_id}",
        "mimeType": "application/vnd.google-apps.shortcut",
        "shortcutDetails": {
            "targetId": file_id,
        },
    }
    if parent_folder_id:
        body["parents"] = [parent_folder_id]
    data = call_api(
        "https://www.googleapis.com/drive/v3/files",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create shortcut"}
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "targetId": file_id,
        "webViewLink": data.get("webViewLink"),
    }


def drive_list_labels(file_id: Optional[str] = None, page_size: int = 20) -> list[dict]:
    """List Drive labels. If file_id is provided, list labels on that file."""
    if file_id:
        data = call_api(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/labels",
            params={"pageSize": min(page_size, 100)},
        )
        if not data:
            return []
        return data.get("labels", [])
    data = call_api(
        "https://www.googleapis.com/drive/v3/labels",
        params={"pageSize": min(page_size, 100)},
    )
    if not data:
        return []
    return data.get("labels", [])


def drive_add_label(file_id: str = "", label_id: str = "",
                     fields: Optional[dict[str, Any]] = None) -> dict:
    """Apply a label to a Drive file with optional field values."""
    if not file_id or not label_id:
        return {"error": "file_id and label_id are required"}
    body = {
        "labelModifications": [{
            "labelId": label_id,
            "setFieldValues": fields or {},
        }],
    }
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/modifyLabels",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to add label"}
    return {
        "kind": data.get("kind"),
        "labelIds": [m.get("labelId") for m in (data.get("labelModifications") or [])],
    }


def drive_watch(file_id: str = "", channel_id: str = "",
                 webhook_url: str = "", token: str = "") -> dict:
    """Start watching for changes to a Drive file via push notifications."""
    if not file_id or not channel_id or not webhook_url:
        return {"error": "file_id, channel_id, and webhook_url are required"}
    body = {
        "id": channel_id,
        "type": "web_hook",
        "address": webhook_url,
    }
    if token:
        body["token"] = token
    data = call_api(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/watch",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to start watch"}
    return {
        "resourceId": data.get("resourceId"),
        "expiration": data.get("expiration"),
        "channelId": channel_id,
    }


def drive_generate_ids(count: int = 10, space: str = "drive") -> list[str]:
    """Generate Drive file IDs for pre-allocation."""
    data = call_api(
        "https://www.googleapis.com/drive/v3/files/generateIds",
        params={"count": min(max(count, 1), 1000), "space": space},
    )
    if not data:
        return []
    return data.get("ids", [])


# ═══════════════════════════════════════════════════════════════════
#  Gmail API
# ═══════════════════════════════════════════════════════════════════


def gmail_list_drafts(max_results: int = 20, q: str = "") -> list[dict]:
    """List draft emails. q: search query."""
    params: dict[str, Any] = {
        "maxResults": min(max_results, 100),
    }
    if q:
        params["q"] = q
    data = call_api(
        "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
        params=params,
    )
    if not data:
        return []
    return [{
        "id": d.get("id"),
        "messageId": d.get("message", {}).get("id"),
        "threadId": d.get("message", {}).get("threadId"),
    } for d in data.get("drafts", [])]


def gmail_read_draft(draft_id: str = "") -> dict:
    """Read a draft's full content including message details."""
    if not draft_id:
        return {"error": "draft_id is required"}
    data = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}",
        params={"format": "full"},
    )
    if not data:
        return {"error": "Draft not found"}
    msg = data.get("message", {})
    headers = {h.get("name", "").lower(): h.get("value", "") for h in (msg.get("payload", {}) or {}).get("headers", [])}
    return {
        "draftId": data.get("id"),
        "messageId": msg.get("id"),
        "threadId": msg.get("threadId"),
        "to": headers.get("to", ""),
        "from": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "body": msg.get("snippet", ""),
    }


def gmail_trash_message(message_id: str = "") -> dict:
    """Trash (soft delete) a message."""
    if not message_id:
        return {"error": "message_id is required"}
    data = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/trash",
        method="POST",
    )
    if not data:
        return {"error": "Failed to trash message"}
    return {"id": data.get("id"), "threadId": data.get("threadId"), "trashed": True}


def gmail_untrash_message(message_id: str = "") -> dict:
    """Untrash a previously trashed message."""
    if not message_id:
        return {"error": "message_id is required"}
    data = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/untrash",
        method="POST",
    )
    if not data:
        return {"error": "Failed to untrash message"}
    return {"id": data.get("id"), "threadId": data.get("threadId"), "trashed": False}


def gmail_delete_message(message_id: str = "") -> dict:
    """Permanently delete a message."""
    if not message_id:
        return {"error": "message_id is required"}
    result = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
        method="DELETE",
    )
    return {"ok": result is None, "messageId": message_id}


def gmail_list_labels() -> list[dict]:
    """List all Gmail labels for the authenticated user."""
    data = call_api("https://gmail.googleapis.com/gmail/v1/users/me/labels")
    if not data:
        return []
    return [{
        "id": l.get("id"),
        "name": l.get("name"),
        "type": l.get("type"),
        "labelListVisibility": l.get("labelListVisibility", ""),
        "messageListVisibility": l.get("messageListVisibility", ""),
        "messagesTotal": l.get("messagesTotal", 0),
        "messagesUnread": l.get("messagesUnread", 0),
        "threadsTotal": l.get("threadsTotal", 0),
        "threadsUnread": l.get("threadsUnread", 0),
    } for l in data.get("labels", [])]


def gmail_create_label(name: str = "",
                        label_list_visibility: str = "labelShow",
                        message_list_visibility: str = "show") -> dict:
    """Create a new Gmail label."""
    if not name:
        return {"error": "name is required"}
    body = {
        "name": name,
        "labelListVisibility": label_list_visibility,
        "messageListVisibility": message_list_visibility,
    }
    data = call_api(
        "https://gmail.googleapis.com/gmail/v1/users/me/labels",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create label"}
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "type": data.get("type"),
    }


def gmail_update_label(label_id: str = "", name: Optional[str] = None,
                        visibility: Optional[str] = None) -> dict:
    """Update a Gmail label's properties."""
    if not label_id:
        return {"error": "label_id is required"}
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if visibility is not None:
        body["messageListVisibility"] = visibility
        body["labelListVisibility"] = visibility
    if not body:
        return {"error": "Nothing to update"}
    data = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/labels/{label_id}",
        method="PUT", json_body=body,
    )
    if not data:
        return {"error": "Failed to update label"}
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "labelListVisibility": data.get("labelListVisibility"),
        "messageListVisibility": data.get("messageListVisibility"),
    }


def gmail_delete_label(label_id: str = "") -> dict:
    """Delete a Gmail label."""
    if not label_id:
        return {"error": "label_id is required"}
    result = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/labels/{label_id}",
        method="DELETE",
    )
    return {"ok": result is None, "labelId": label_id}


def gmail_modify_message(message_id: str = "",
                          add_label_ids: Optional[list[str]] = None,
                          remove_label_ids: Optional[list[str]] = None) -> dict:
    """Modify message labels (add/remove)."""
    if not message_id:
        return {"error": "message_id is required"}
    body: dict[str, Any] = {}
    if add_label_ids:
        body["addLabelIds"] = add_label_ids
    if remove_label_ids:
        body["removeLabelIds"] = remove_label_ids
    if not body:
        return {"error": "Specify add_label_ids and/or remove_label_ids"}
    data = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to modify message"}
    return {
        "id": data.get("id"),
        "threadId": data.get("threadId"),
        "labelIds": data.get("labelIds", []),
    }


def gmail_get_message(message_id: str = "", format: str = "full") -> dict:
    """Get a full message with payload. format: minimal, full, raw, metadata."""
    if not message_id:
        return {"error": "message_id is required"}
    valid_formats = ("minimal", "full", "raw", "metadata")
    if format not in valid_formats:
        format = "full"
    data = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
        params={"format": format},
    )
    if not data:
        return {"error": "Message not found"}
    headers = {h.get("name", "").lower(): h.get("value", "") for h in (data.get("payload", {}) or {}).get("headers", [])}
    return {
        "id": data.get("id"),
        "threadId": data.get("threadId"),
        "labelIds": data.get("labelIds", []),
        "snippet": data.get("snippet", ""),
        "to": headers.get("to", ""),
        "from": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "sizeEstimate": data.get("sizeEstimate", 0),
        "internalDate": data.get("internalDate", ""),
        "payload": data.get("payload"),
    }


def gmail_get_attachment(message_id: str = "", attachment_id: str = "") -> dict:
    """Get attachment data from a message."""
    if not message_id or not attachment_id:
        return {"error": "message_id and attachment_id are required"}
    data = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}",
    )
    if not data:
        return {"error": "Attachment not found"}
    return {
        "attachmentId": data.get("attachmentId"),
        "size": data.get("size", 0),
        "data": data.get("data", ""),
        "mimeType": "",  # Not returned by API, caller should know from message payload
    }


def gmail_get_profile() -> dict:
    """Get the authenticated user's Gmail profile."""
    data = call_api("https://gmail.googleapis.com/gmail/v1/users/me/profile")
    if not data:
        return {"error": "Failed to get profile"}
    return {
        "emailAddress": data.get("emailAddress", ""),
        "messagesTotal": data.get("messagesTotal", 0),
        "threadsTotal": data.get("threadsTotal", 0),
        "historyId": data.get("historyId", ""),
    }


def gmail_list_filters() -> list[dict]:
    """List Gmail filters for the authenticated user."""
    data = call_api("https://gmail.googleapis.com/gmail/v1/users/me/settings/filters")
    if not data:
        return []
    return [{
        "id": f.get("id"),
        "criteria": f.get("criteria", {}),
        "action": f.get("action", {}),
    } for f in data.get("filter", [])]


def gmail_create_filter(criteria: Optional[dict[str, Any]] = None,
                         action: Optional[dict[str, Any]] = None) -> dict:
    """Create a Gmail filter with criteria and action."""
    body: dict[str, Any] = {}
    if criteria:
        body["criteria"] = criteria
    if action:
        body["action"] = action
    if not body:
        return {"error": "criteria and/or action are required"}
    data = call_api(
        "https://gmail.googleapis.com/gmail/v1/users/me/settings/filters",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create filter"}
    return {
        "id": data.get("id"),
        "criteria": data.get("criteria", {}),
        "action": data.get("action", {}),
    }


def gmail_delete_filter(filter_id: str = "") -> dict:
    """Delete a Gmail filter."""
    if not filter_id:
        return {"error": "filter_id is required"}
    result = call_api(
        f"https://gmail.googleapis.com/gmail/v1/users/me/settings/filters/{filter_id}",
        method="DELETE",
    )
    return {"ok": result is None, "filterId": filter_id}


def gmail_auto_forward(email: str = "", disposition: str = "leaveInInbox") -> dict:
    """Set up auto-forwarding to another email address."""
    if not email:
        return {"error": "email is required"}
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    # Step 1: Add forwarding address
    try:
        r1 = requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/settings/forwardingAddresses",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"forwardingEmail": email},
            timeout=10,
        )
        if r1.status_code == 409:
            pass  # Already exists
        elif r1.status_code != 200:
            r1.raise_for_status()
    except Exception as exc:
        return {"error": f"Failed to add forwarding address: {exc}"}
    # Step 2: Enable auto-forwarding
    try:
        r2 = requests.put(
            "https://gmail.googleapis.com/gmail/v1/users/me/settings/autoForwarding",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "enabled": True,
                "emailAddress": email,
                "disposition": disposition,
            },
            timeout=10,
        )
        r2.raise_for_status()
        data = r2.json()
        return {
            "enabled": data.get("enabled", False),
            "emailAddress": data.get("emailAddress", ""),
            "disposition": data.get("disposition", ""),
        }
    except Exception as exc:
        return {"error": str(exc)}


def gmail_get_auto_forwarding() -> dict:
    """Get auto-forwarding settings."""
    data = call_api("https://gmail.googleapis.com/gmail/v1/users/me/settings/autoForwarding")
    if not data:
        return {"error": "Failed to get forwarding settings"}
    return {
        "enabled": data.get("enabled", False),
        "emailAddress": data.get("emailAddress", ""),
        "disposition": data.get("disposition", ""),
    }


def gmail_get_delegated_accounts() -> list[dict]:
    """List delegated accounts (delegates) for the authenticated user."""
    data = call_api(
        "https://gmail.googleapis.com/gmail/v1/users/me/settings/delegates",
    )
    if not data:
        return []
    return [{
        "emailAddress": d.get("delegateEmail", ""),
        "verificationStatus": d.get("verificationStatus", ""),
    } for d in data.get("delegates", [])]


def gmail_send_raw(raw_base64: str = "") -> dict:
    """Send a raw MIME message (base64-urlsafe encoded)."""
    if not raw_base64:
        return {"error": "raw_base64 is required (base64-urlsafe encoded MIME message)"}
    data = call_api(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        method="POST",
        json_body={"raw": raw_base64},
    )
    if not data:
        return {"error": "Failed to send message"}
    return {
        "id": data.get("id"),
        "threadId": data.get("threadId"),
        "labelIds": data.get("labelIds", []),
    }


def gmail_import_message(raw_base64: str = "",
                          internal_date_source: str = "dateHeader",
                          never_mark_spam: bool = True,
                          process_for_calendar: bool = True) -> dict:
    """Import a message into the mailbox (like send but doesn't deliver externally)."""
    if not raw_base64:
        return {"error": "raw_base64 is required"}
    body: dict[str, Any] = {
        "raw": raw_base64,
    }
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/import"
            f"?internalDateSource={internal_date_source}"
            f"&neverMarkSpam={str(never_mark_spam).lower()}"
            f"&processForCalendar={str(process_for_calendar).lower()}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "labelIds": data.get("labelIds", []),
        }
    except Exception as exc:
        return {"error": str(exc)}


def gmail_batch_delete(message_ids: Optional[list[str]] = None) -> dict:
    """Batch delete messages by IDs."""
    if not message_ids:
        return {"error": "message_ids list is required"}
    result = call_api(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/batchDelete",
        method="POST",
        json_body={"ids": message_ids},
    )
    return {"ok": result is None, "deletedCount": len(message_ids)}


def gmail_search(query: str = "", max_results: int = 20,
                  include_spam_trash: bool = False) -> list[dict]:
    """Search messages with advanced query syntax."""
    params: dict[str, Any] = {
        "q": query,
        "maxResults": min(max_results, 100),
        "includeSpamTrash": str(include_spam_trash).lower(),
    }
    data = call_api(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        params=params,
    )
    if not data:
        return []
    msg_ids = [m.get("id") for m in data.get("messages", [])]
    results = []
    for msg_id in msg_ids:
        msg = gmail_get_message(msg_id, format="metadata")
        if "error" not in msg:
            results.append(msg)
    return results


def gmail_list_messages_paged(page_token: str = "", max_results: int = 20,
                                q: str = "") -> dict:
    """List messages with pagination support."""
    params: dict[str, Any] = {
        "maxResults": min(max_results, 100),
    }
    if page_token:
        params["pageToken"] = page_token
    if q:
        params["q"] = q
    data = call_api(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        params=params,
    )
    if not data:
        return {"messages": [], "nextPageToken": ""}
    return {
        "messages": [{"id": m.get("id"), "threadId": m.get("threadId")}
                     for m in data.get("messages", [])],
        "nextPageToken": data.get("nextPageToken", ""),
        "resultSizeEstimate": data.get("resultSizeEstimate", 0),
    }


# ═══════════════════════════════════════════════════════════════════
#  Analytics — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def analytics_list_accounts() -> list[dict]:
    """List all Google Analytics accounts."""
    data = call_api("https://analyticsadmin.googleapis.com/v1beta/accounts")
    if not data:
        return []
    return data.get("accounts", [])


def analytics_list_properties(account_id: str = "") -> list[dict]:
    """List properties for an Analytics account."""
    if not account_id:
        return [{"error": "account_id is required"}]
    data = call_api(
        "https://analyticsadmin.googleapis.com/v1beta/properties",
        params={"filter": f"parent:accounts/{account_id}"},
    )
    if not data:
        return []
    return data.get("properties", [])


def analytics_get_realtime(property_id: str = "", metrics: Optional[list[str]] = None,
                           dimensions: Optional[list[str]] = None) -> list[dict]:
    """Get real-time Analytics data for a property."""
    if not property_id:
        return [{"error": "property_id is required"}]
    import requests
    token = get_access_token()
    if not token:
        return []
    body: dict = {}
    if metrics:
        body["metrics"] = [{"name": m} for m in metrics]
    if dimensions:
        body["dimensions"] = [{"name": d} for d in dimensions]
    try:
        r = requests.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runRealtimeReport",
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
        logger.warning("Analytics realtime failed: %s", exc)
        return []


def analytics_run_report_expanded(property_id: str = "",
                                  metrics: Optional[list[str]] = None,
                                  dimensions: Optional[list[str]] = None,
                                  date_ranges: Optional[list[dict]] = None,
                                  dimension_filter: Optional[dict] = None,
                                  order_by: Optional[list[dict]] = None,
                                  limit: int = 1000,
                                  offset: int = 0) -> list[dict]:
    """Run a full GA4 report with advanced options."""
    if not property_id:
        return [{"error": "property_id is required"}]
    import requests
    token = get_access_token()
    if not token:
        return []
    body: dict = {
        "dateRanges": date_ranges or [{"startDate": "7daysAgo", "endDate": "today"}],
        "limit": limit,
        "offset": offset,
    }
    if metrics:
        body["metrics"] = [{"name": m} for m in metrics]
    if dimensions:
        body["dimensions"] = [{"name": d} for d in dimensions]
    if dimension_filter:
        body["dimensionFilter"] = dimension_filter
    if order_by:
        body["orderBys"] = order_by
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
        logger.warning("Analytics report expanded failed: %s", exc)
        return []


def analytics_batch_run_reports(property_id: str = "",
                                requests_list: Optional[list[dict]] = None) -> list[dict]:
    """Run multiple Analytics reports in one request."""
    if not property_id or not requests_list:
        return [{"error": "property_id and requests_list are required"}]
    import requests
    token = get_access_token()
    if not token:
        return []
    body = {
        "property": f"properties/{property_id}",
        "requests": requests_list,
    }
    try:
        r = requests.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:batchRunReports",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("reports", [])
    except Exception as exc:
        logger.warning("Analytics batch reports failed: %s", exc)
        return []


def analytics_get_metadata(property_id: str = "") -> dict:
    """Get GA4 column metadata for a property."""
    if not property_id:
        return {"error": "property_id is required"}
    data = call_api(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}/metadata"
    )
    if not data:
        return {}
    return data


# ═══════════════════════════════════════════════════════════════════
#  Search Console — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def searchconsole_inspect_url(site_url: str = "", inspection_url: str = "") -> dict:
    """Inspect a URL in the Google Index."""
    if not site_url or not inspection_url:
        return {"error": "site_url and inspection_url are required"}
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    try:
        r = requests.post(
            "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"siteUrl": site_url, "inspectionUrl": inspection_url},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def searchconsole_list_sitemaps(site_url: str = "") -> list[dict]:
    """List sitemaps for a verified site."""
    if not site_url:
        return [{"error": "site_url is required"}]
    data = call_api(
        f"https://searchconsole.googleapis.com/v1/sites/{site_url}/sitemaps"
    )
    if not data:
        return []
    return data.get("sitemap", [])


def searchconsole_submit_sitemap(site_url: str = "", sitemap_url: str = "") -> dict:
    """Submit a sitemap for a site."""
    if not site_url or not sitemap_url:
        return {"error": "site_url and sitemap_url are required"}
    result = call_api(
        f"https://searchconsole.googleapis.com/v1/sites/{site_url}/sitemaps/{sitemap_url}",
        method="PUT",
    )
    return {"ok": result is None, "siteUrl": site_url, "sitemapUrl": sitemap_url}


def searchconsole_remove_sitemap(site_url: str = "", sitemap_url: str = "") -> dict:
    """Delete a sitemap."""
    if not site_url or not sitemap_url:
        return {"error": "site_url and sitemap_url are required"}
    result = call_api(
        f"https://searchconsole.googleapis.com/v1/sites/{site_url}/sitemaps/{sitemap_url}",
        method="DELETE",
    )
    return {"ok": result is None, "siteUrl": site_url, "sitemapUrl": sitemap_url}


def searchconsole_crawl_errors_counts(site_url: str = "", category: str = "notFound",
                                      platform: str = "web") -> list[dict]:
    """Get crawl error counts for a site."""
    if not site_url:
        return [{"error": "site_url is required"}]
    import requests
    token = get_access_token()
    if not token:
        return []
    try:
        r = requests.get(
            f"https://searchconsole.googleapis.com/v1/sites/{site_url}/crawlErrorsCountsQuery",
            params={"category": category, "platform": platform},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("countPerTypes", [])
    except Exception as exc:
        logger.warning("Search Console crawl errors counts failed: %s", exc)
        return []


def searchconsole_crawl_errors_samples(site_url: str = "", category: str = "notFound",
                                        platform: str = "web") -> list[dict]:
    """Get crawl error samples for a site."""
    if not site_url:
        return [{"error": "site_url is required"}]
    import requests
    token = get_access_token()
    if not token:
        return []
    try:
        r = requests.get(
            f"https://searchconsole.googleapis.com/v1/sites/{site_url}/crawlErrorsSamplesQuery",
            params={"category": category, "platform": platform},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("crawlErrorSample", [])
    except Exception as exc:
        logger.warning("Search Console crawl error samples failed: %s", exc)
        return []


def searchconsole_mark_crawl_error_fixed(site_url: str = "", category: str = "notFound",
                                          platform: str = "web") -> dict:
    """Mark a crawl error as fixed."""
    if not site_url:
        return {"error": "site_url is required"}
    result = call_api(
        f"https://searchconsole.googleapis.com/v1/sites/{site_url}/crawlErrorsSamplesQuery",
        method="DELETE",
        params={"category": category, "platform": platform},
    )
    return {"ok": result is None, "siteUrl": site_url, "category": category, "platform": platform}


def searchconsole_test_robots_txt(site_url: str = "", url_to_test: str = "") -> dict:
    """Test if a URL is blocked by robots.txt."""
    if not site_url or not url_to_test:
        return {"error": "site_url and url_to_test are required"}
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    try:
        r = requests.get(
            "https://searchconsole.googleapis.com/v1/urlTestingTools/site:testRobotsTxt",
            params={"siteUrl": site_url, "urlToTest": url_to_test},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════════
#  Maps — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def _maps_request_raw(url: str, params: dict) -> dict:
    """Direct Maps API request returning full JSON response (not just results)."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set"}
    params["key"] = api_key
    import requests as _req
    try:
        r = _req.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": f"Maps API error: {exc}"}


def _maps_request_post(url: str, body: dict) -> dict:
    """Direct Maps API POST request using API key."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set"}
    import requests as _req
    try:
        r = _req.post(
            url,
            params={"key": api_key},
            json=body,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": f"Maps API error: {exc}"}


def maps_nearby_search(location: str = "", radius: int = 1500,
                        type: str = "", keyword: str = "") -> list[dict]:
    """Find places nearby a location."""
    params: dict = {"location": location, "radius": radius}
    if type:
        params["type"] = type
    if keyword:
        params["keyword"] = keyword
    import os as _os
    api_key = _os.getenv("GOOGLE_MAPS_API_KEY") or _os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY not set"}]
    params["key"] = api_key
    import requests as _req
    try:
        r = _req.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", [])
    except Exception as exc:
        return [{"error": f"Maps API error: {exc}"}]


def maps_text_search(query: str = "", location: str = "") -> list[dict]:
    """Text search for places."""
    params: dict = {"query": query}
    if location:
        params["location"] = location
    import os as _os
    api_key = _os.getenv("GOOGLE_MAPS_API_KEY") or _os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY not set"}]
    params["key"] = api_key
    import requests as _req
    try:
        r = _req.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", [])
    except Exception as exc:
        return [{"error": f"Maps API error: {exc}"}]


def maps_find_place(input: str = "", inputtype: str = "textquery",
                     fields: str = "formatted_address,name,geometry") -> dict:
    """Find a place by text or phone number input."""
    params = {"input": input, "inputtype": inputtype, "fields": fields}
    import os as _os
    api_key = _os.getenv("GOOGLE_MAPS_API_KEY") or _os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set"}
    params["key"] = api_key
    import requests as _req
    try:
        r = _req.get(
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        candidates = data.get("candidates", [])
        if candidates:
            return candidates[0]
        return {}
    except Exception as exc:
        return {"error": f"Maps API error: {exc}"}


def maps_autocomplete(input: str = "", types: str = "",
                       components: str = "") -> list[dict]:
    """Get place autocomplete predictions."""
    params: dict = {"input": input}
    if types:
        params["types"] = types
    if components:
        params["components"] = components
    import os as _os
    api_key = _os.getenv("GOOGLE_MAPS_API_KEY") or _os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY not set"}]
    params["key"] = api_key
    import requests as _req
    try:
        r = _req.get(
            "https://maps.googleapis.com/maps/api/place/autocomplete/json",
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("predictions", [])
    except Exception as exc:
        return [{"error": f"Maps API error: {exc}"}]


def maps_query_autocomplete(input: str = "", offset: int = 0,
                             location: str = "", radius: int = 0) -> list[dict]:
    """Get query autocomplete suggestions."""
    params: dict = {"input": input}
    if offset:
        params["offset"] = offset
    if location:
        params["location"] = location
    if radius:
        params["radius"] = radius
    import os as _os
    api_key = _os.getenv("GOOGLE_MAPS_API_KEY") or _os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY not set"}]
    params["key"] = api_key
    import requests as _req
    try:
        r = _req.get(
            "https://maps.googleapis.com/maps/api/place/queryautocomplete/json",
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("predictions", [])
    except Exception as exc:
        return [{"error": f"Maps API error: {exc}"}]


def maps_distance_matrix(origins: str = "", destinations: str = "",
                          mode: str = "driving", units: str = "metric") -> dict:
    """Compute travel distance and time matrix."""
    params = {
        "origins": origins,
        "destinations": destinations,
        "mode": mode,
        "units": units,
    }
    import os as _os
    api_key = _os.getenv("GOOGLE_MAPS_API_KEY") or _os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set"}
    params["key"] = api_key
    import requests as _req
    try:
        r = _req.get(
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": f"Maps API error: {exc}"}


def maps_roads_nearest_roads(points: str = "") -> list[dict]:
    """Find nearest road segments to GPS points."""
    if not points:
        return [{"error": "points are required (lat,lng|lat,lng)"}]
    import os as _os
    api_key = _os.getenv("GOOGLE_MAPS_API_KEY") or _os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY not set"}]
    import requests as _req
    try:
        r = _req.get(
            "https://roads.googleapis.com/v1/nearestRoads",
            params={"points": points, "key": api_key},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("snappedPoints", [])
    except Exception as exc:
        return [{"error": f"Roads API error: {exc}"}]


def maps_roads_snap_to_roads(points: str = "", interpolate: bool = True) -> dict:
    """Snap GPS points to roads."""
    if not points:
        return {"error": "points are required"}
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set"}
    import requests as _req
    try:
        r = _req.post(
            "https://roads.googleapis.com/v1/snapToRoads",
            params={"key": api_key},
            json={"path": points, "interpolate": interpolate},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": f"Roads API error: {exc}"}


def maps_timezone(location: str = "", timestamp: int = 0) -> dict:
    """Get timezone for coordinates. Uses GOOGLE_MAPS_API_KEY."""
    if not location:
        return {"error": "location is required (lat,lng)"}
    if not timestamp:
        import time
        timestamp = int(time.time())
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set"}
    import requests as _req
    try:
        r = _req.get(
            "https://maps.googleapis.com/maps/api/timezone/json",
            params={"location": location, "timestamp": timestamp, "key": api_key},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": f"TimeZone API error: {exc}"}


# ═══════════════════════════════════════════════════════════════════
#  Maps — Free Directions (no API key required)
# ═══════════════════════════════════════════════════════════════════


def maps_geocode_free(address: str) -> dict:
    """Geocode an address using the free Nominatim (OpenStreetMap) API.
    No API key needed. Rate-limited to 1 req/sec.
    Returns lat/lng or error.

    Gets up to 5 results and picks the most detailed city-level result.
    Falls back to ', India' or ', city, India' for ambiguous names.
    """
    import requests, time
    def _score(entry):
        dn = entry.get("display_name", "")
        parts = dn.split(",")
        cls = entry.get("class", "")
        # Prefer place=city/town/village, penalize administrative boundaries
        score = len(parts) * 10
        if "India" in dn: score += 50
        if cls in ("place",): score += 30
        for kw in ("city", "town", "village"): 
            if kw in dn.lower(): score += 20
        return score
    try:
        # Try original query with limit=5
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 5},
            headers={"User-Agent": "FRIDAY-Assistant/1.0"}, timeout=10,
        )
        r.raise_for_status()
        data = r.json() or []
        best = max(data, key=_score) if data else None
        # Fallback: try with ', India' if no good result
        if (not best or "India" not in best.get("display_name", "")) and "," not in address:
            for suffix in (", India", ", city, India"):
                time.sleep(1)
                r2 = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": f"{address}{suffix}", "format": "json", "limit": 5},
                    headers={"User-Agent": "FRIDAY-Assistant/1.0"}, timeout=10,
                )
                r2.raise_for_status()
                data2 = r2.json() or []
                if data2:
                    best2 = max(data2, key=_score)
                    if best2 and _score(best2) > _score(best):
                        best = best2
        if not best:
            return {"error": f"Address not found: {address}"}
        return {"lat": float(best["lat"]), "lng": float(best["lon"]),
                "display_name": best.get("display_name", "")}
    except Exception as exc:
        return {"error": f"Nominatim geocoding error: {exc}"}


def maps_get_eta(origin_lat: float, origin_lng: float,
                 dest_lat: float, dest_lng: float,
                 waypoints: Optional[list[dict]] = None) -> dict:
    """Get ETA using free OSRM routing API. No API key needed.
    Returns duration (seconds), distance (meters), and text summary.

    OSRM provides free-flow (no traffic) estimates. A distance-based
    speed correction is applied for more realistic ETAs:
      - <30 km → capped at 40 km/h (city traffic)
      - >=30 km → capped at 55 km/h (highway with traffic)
    """
    import requests
    coords = f"{origin_lng},{origin_lat};"
    if waypoints:
        for wp in waypoints:
            coords += f"{wp['lng']},{wp['lat']};"
    coords += f"{dest_lng},{dest_lat}"
    try:
        r = requests.get(
            f"https://router.project-osrm.org/route/v1/driving/{coords}",
            params={"overview": "false", "alternatives": "false", "steps": "false"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("routes"):
            return {"error": "No route found"}
        route = data["routes"][0]
        duration_sec = route.get("duration", 0)
        distance_m = route.get("distance", 0)
        dist_km = distance_m / 1000
        speed_kmh = dist_km / (duration_sec / 3600) if duration_sec > 0 else 0
        max_speed = 55 if dist_km >= 30 else 40
        if speed_kmh > max_speed:
            duration_sec = dist_km / max_speed * 3600
        hours = int(duration_sec // 3600)
        mins = int((duration_sec % 3600) // 60)
        if hours > 0:
            duration_text = f"{hours}h {mins}min"
        else:
            duration_text = f"{mins}min"
        if distance_m >= 1000:
            dist_text = f"{dist_km:.1f} km"
        else:
            dist_text = f"{int(distance_m)} m"
        return {
            "duration_seconds": duration_sec,
            "duration_text": duration_text,
            "distance_meters": distance_m,
            "distance_text": dist_text,
            "osrm_raw_speed_kmh": round(speed_kmh, 1),
        }
    except Exception as exc:
        return {"error": f"OSRM routing error: {exc}"}


def maps_open_directions(origin: str, destination: str,
                         waypoints: Optional[list[str]] = None,
                         travelmode: str = "driving",
                         origin_name: str = "",
                         destination_name: str = "") -> dict:
    """
    Open Google Maps with directions from origin to destination.
    FREE — no API key needed. Uses Google Maps URI scheme.

    origin/destination can be:
      - "home" or "work" (looked up from memory)
      - "lat,lng" coordinates
      - Any address string

    waypoints: optional list of addresses for stops (max 10).
    travelmode: driving, walking, bicycling, transit.

    Returns dict with:
      - url: Google Maps directions URL (open this in browser)
      - eta: ETA info from OSRM (or error string)
      - origin_coords, dest_coords: resolved coordinates
    """
    from urllib.parse import quote

    # Try to resolve "home" and "work" from memory
    def _resolve_label(label: str) -> str:
        label_lower = label.lower().strip()
        if label_lower in ("home", "my home", "my place", "house"):
            try:
                from friday.tools_flat import memory_retrieve
                r = memory_retrieve("home_address")
                if r and "error" not in str(r).lower():
                    return str(r)
            except Exception:
                pass
            return "Home"
        if label_lower in ("work", "office", "my office", "my work"):
            try:
                from friday.tools_flat import memory_retrieve
                r = memory_retrieve("work_address")
                if r and "error" not in str(r).lower():
                    return str(r)
            except Exception:
                pass
            return "Work"
        return label

    origin = _resolve_label(origin)
    destination = _resolve_label(destination)

    resolved_waypoints = []
    if waypoints:
        for wp in waypoints:
            resolved_waypoints.append(_resolve_label(wp))

    # Geocode origin and destination (free Nominatim)
    origin_coords = None
    dest_coords = None

    # Check if already lat,lng
    def _is_coords(val: str) -> bool:
        import re
        return bool(re.match(r'^-?\d+\.?\d*,-?\d+\.?\d*$', val.strip()))

    if not _is_coords(origin):
        geo = maps_geocode_free(origin)
        if "error" not in geo:
            origin_coords = f"{geo['lat']},{geo['lng']}"
    else:
        origin_coords = origin

    if not _is_coords(destination):
        geo = maps_geocode_free(destination)
        if "error" not in geo:
            dest_coords = f"{geo['lat']},{geo['lng']}"
    else:
        dest_coords = destination

    # Build Google Maps URL
    import urllib.parse
    def _enc(s):
        return urllib.parse.quote(s.replace(", ", ",").replace(" ", "+"))
    origin_enc = _enc(origin)
    dest_enc = _enc(destination)
    url = f"https://www.google.com/maps/dir/{origin_enc}/{dest_enc}/data=!3m"
    if resolved_waypoints:
        wp_enc = "/".join(_enc(w) for w in resolved_waypoints)
        url = f"https://www.google.com/maps/dir/{origin_enc}/{wp_enc}/{dest_enc}/data=!3m"

    # Get ETA from OSRM if we have coordinates
    eta = None
    if origin_coords and dest_coords:
        olat, olng = origin_coords.split(",")
        dlat, dlng = dest_coords.split(",")
        wp_list = None
        if resolved_waypoints:
            wp_list = []
            for wp in resolved_waypoints:
                g = maps_geocode_free(wp)
                if "error" not in g:
                    wp_list.append({"lat": g["lat"], "lng": g["lng"]})
        eta = maps_get_eta(float(olat), float(olng), float(dlat), float(dlng), wp_list)

    result = {
        "url": url,
        "eta": eta or {"error": "Could not calculate ETA"},
        "origin": origin,
        "destination": destination,
        "travelmode": travelmode,
        "waypoints": resolved_waypoints or [],
    }
    if origin_coords:
        result["origin_coords"] = origin_coords
    if dest_coords:
        result["dest_coords"] = dest_coords

    return result


# ═══════════════════════════════════════════════════════════════════
#  Vision — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def _vision_annotate_single(image_path: str, feature_type: str, max_results: int = 20) -> dict:
    """Internal: run a single Vision API annotation."""
    path = Path(image_path)
    if not path.exists():
        return {"error": f"File not found: {image_path}"}
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    image_data = base64.b64encode(path.read_bytes()).decode()
    body = {
        "requests": [{
            "image": {"content": image_data},
            "features": [{"type": feature_type, "maxResults": max_results}],
        }]
    }
    try:
        r = requests.post(
            "https://vision.googleapis.com/v1/images:annotate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        responses = data.get("responses", [])
        if responses:
            return responses[0]
        return {}
    except Exception as exc:
        return {"error": str(exc)}


def vision_detect_text_full(image_path: str = "") -> dict:
    """Full OCR with DOCUMENT_TEXT_DETECTION."""
    return _vision_annotate_single(image_path, "DOCUMENT_TEXT_DETECTION")


def vision_detect_faces(image_path: str = "") -> dict:
    """Detect faces in an image."""
    return _vision_annotate_single(image_path, "FACE_DETECTION")


def vision_detect_labels(image_path: str = "") -> dict:
    """Detect labels in an image."""
    return _vision_annotate_single(image_path, "LABEL_DETECTION")


def vision_detect_landmarks(image_path: str = "") -> dict:
    """Detect landmarks in an image."""
    return _vision_annotate_single(image_path, "LANDMARK_DETECTION")


def vision_detect_logos(image_path: str = "") -> dict:
    """Detect logos in an image."""
    return _vision_annotate_single(image_path, "LOGO_DETECTION")


def vision_detect_objects(image_path: str = "") -> dict:
    """Object localization in an image."""
    return _vision_annotate_single(image_path, "OBJECT_LOCALIZATION")


def vision_detect_web(image_path: str = "") -> dict:
    """Web detection (similar images, web entities, pages)."""
    return _vision_annotate_single(image_path, "WEB_DETECTION")


def vision_detect_safe_search(image_path: str = "") -> dict:
    """Safe search detection."""
    return _vision_annotate_single(image_path, "SAFE_SEARCH_DETECTION")


def vision_detect_text(image_path: str = "") -> dict:
    """Simple TEXT_DETECTION."""
    return _vision_annotate_single(image_path, "TEXT_DETECTION")


def vision_detect_document(image_path: str = "") -> dict:
    """Full document OCR with DOCUMENT_TEXT_DETECTION."""
    return _vision_annotate_single(image_path, "DOCUMENT_TEXT_DETECTION")


def vision_detect_image_properties(image_path: str = "") -> dict:
    """Get image properties (dominant colors)."""
    return _vision_annotate_single(image_path, "IMAGE_PROPERTIES")


def vision_detect_crop_hints(image_path: str = "") -> dict:
    """Get crop hints for an image."""
    return _vision_annotate_single(image_path, "CROP_HINTS")


def vision_async_batch_annotate(image_path: str = "",
                                 features: Optional[list[str]] = None,
                                 output_uri: str = "",
                                 bucket: str = "") -> dict:
    """Batch async annotation for multiple features, writes results to GCS."""
    if not image_path or not output_uri:
        return {"error": "image_path and output_uri are required"}
    path = Path(image_path)
    if not path.exists():
        return {"error": f"File not found: {image_path}"}
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    image_data = base64.b64encode(path.read_bytes()).decode()
    if not features:
        features = ["LABEL_DETECTION", "TEXT_DETECTION"]
    body = {
        "requests": [{
            "inputConfig": {
                "gcsSource": {"uri": output_uri},
                "mimeType": "image/jpeg",
            },
            "features": [{"type": f, "maxResults": 20} for f in features],
            "outputConfig": {
                "gcsDestination": {"uri": output_uri},
                "batchSize": 1,
            },
        }]
    }
    try:
        r = requests.post(
            "https://vision.googleapis.com/v1/images:asyncBatchAnnotate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════════
#  Translate — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def translate_list_languages(target_language: str = "") -> list[dict]:
    """List supported translation languages."""
    params: dict = {}
    if target_language:
        params["target"] = target_language
    data = call_api(
        "https://translation.googleapis.com/language/translate/v2/languages",
        params=params,
    )
    if not data:
        return []
    return data.get("data", {}).get("languages", [])


def translate_batch_translate(texts: Optional[list[str]] = None,
                               target_language: str = "en",
                               source_language: str = "") -> dict:
    """Batch translate multiple texts."""
    if not texts:
        return {"error": "texts list is required"}
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    body: dict = {
        "q": texts,
        "target": target_language,
    }
    if source_language:
        body["source"] = source_language
    try:
        r = requests.post(
            "https://translation.googleapis.com/language/translate/v2",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def translate_get_supported_glossaries() -> list[dict]:
    """List available glossaries for Cloud Translation."""
    data = call_api(
        "https://translation.googleapis.com/v3/projects/-/locations/global/glossaries"
    )
    if not data:
        return []
    return data.get("glossaries", [])


# ═══════════════════════════════════════════════════════════════════
#  TTS — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def tts_list_voices(language_code: str = "") -> list[dict]:
    """List available TTS voices with language codes."""
    params: dict = {}
    if language_code:
        params["languageCode"] = language_code
    data = call_api(
        "https://texttospeech.googleapis.com/v1/voices",
        params=params,
    )
    if not data:
        return []
    return data.get("voices", [])


def tts_synthesize_long_audio(text: str = "", voice_name: str = "",
                               output_bucket: str = "") -> dict:
    """Long-form audio synthesis (async) writing to GCS."""
    if not text or not voice_name or not output_bucket:
        return {"error": "text, voice_name, and output_bucket are required"}
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    body = {
        "input": {"text": text},
        "voice": {"name": voice_name, "languageCode": voice_name.split("-")[0] + "-" + voice_name.split("-")[1] if "-" in voice_name else "en-US"},
        "audioConfig": {"audioEncoding": "LINEAR16"},
        "outputGcsUri": output_bucket,
    }
    try:
        r = requests.post(
            "https://texttospeech.googleapis.com/v1/text:synthesizeLongAudio",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════════
#  Cloud Storage — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def storage_list_buckets(project_id: str = "") -> list[dict]:
    """List all Cloud Storage buckets for a project."""
    if not project_id:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        "https://storage.googleapis.com/storage/v1/b",
        params={"project": project_id},
    )
    if not data:
        return []
    return data.get("items", [])


def storage_create_bucket(name: str = "", project_id: str = "",
                           location: str = "US", storage_class: str = "STANDARD") -> dict:
    """Create a new Cloud Storage bucket."""
    if not name:
        return {"error": "name is required"}
    if not project_id:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    body = {
        "name": name,
        "location": location,
        "storageClass": storage_class,
    }
    try:
        r = requests.post(
            f"https://storage.googleapis.com/storage/v1/b?project={project_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def storage_delete_bucket(name: str = "") -> dict:
    """Delete a Cloud Storage bucket."""
    if not name:
        return {"error": "name is required"}
    result = call_api(
        f"https://storage.googleapis.com/storage/v1/b/{name}",
        method="DELETE",
    )
    return {"ok": result is None, "bucket": name}


def storage_delete_file(bucket: str = "", path: str = "") -> dict:
    """Delete an object in a bucket."""
    if not bucket or not path:
        return {"error": "bucket and path are required"}
    result = call_api(
        f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{path}",
        method="DELETE",
    )
    return {"ok": result is None, "bucket": bucket, "path": path}


def storage_get_file(bucket: str = "", path: str = "") -> dict:
    """Get object metadata from Cloud Storage."""
    if not bucket or not path:
        return {"error": "bucket and path are required"}
    data = call_api(
        f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{path}"
    )
    if not data:
        return {"error": "Object not found"}
    return data


def storage_copy_file(source_bucket: str = "", source_path: str = "",
                       dest_bucket: str = "", dest_path: str = "") -> dict:
    """Copy an object within or between buckets."""
    if not source_bucket or not source_path or not dest_bucket or not dest_path:
        return {"error": "source_bucket, source_path, dest_bucket, and dest_path are required"}
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    try:
        r = requests.post(
            f"https://storage.googleapis.com/storage/v1/b/{source_bucket}/o/{source_path}/copyTo/b/{dest_bucket}/o/{dest_path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def storage_move_file(bucket: str = "", source_path: str = "",
                       dest_path: str = "") -> dict:
    """Rename/move an object within a bucket (copy + delete source)."""
    if not bucket or not source_path or not dest_path:
        return {"error": "bucket, source_path, and dest_path are required"}
    # Copy to new location
    copy_result = storage_copy_file(
        source_bucket=bucket, source_path=source_path,
        dest_bucket=bucket, dest_path=dest_path,
    )
    if "error" in copy_result:
        return copy_result
    # Delete source
    delete_result = storage_delete_file(bucket=bucket, path=source_path)
    return {
        "copy": copy_result,
        "sourceDeleted": delete_result.get("ok", False),
        "bucket": bucket,
        "sourcePath": source_path,
        "destPath": dest_path,
    }


# ═══════════════════════════════════════════════════════════════════
#  People — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def people_create_group(group_name: str) -> dict:
    """Create a contact group."""
    body = {"contactGroup": {"name": group_name}}
    data = call_api(
        "https://people.googleapis.com/v1/contactGroups",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create group"}
    return {"groupResourceName": data.get("resourceName"), "groupName": data.get("name")}


def people_list_groups() -> list[dict]:
    """List contact groups."""
    data = call_api("https://people.googleapis.com/v1/contactGroups")
    if not data:
        return []
    return [{
        "resourceName": g.get("resourceName"),
        "name": g.get("name"),
        "groupType": g.get("groupType"),
        "memberCount": g.get("memberCount", 0),
    } for g in data.get("contactGroups", [])]


def people_delete_group(resource_name: str) -> dict:
    """Delete a contact group by resource name."""
    if not resource_name:
        return {"error": "resource_name is required"}
    result = call_api(
        f"https://people.googleapis.com/v1/{resource_name}",
        method="DELETE",
    )
    return {"ok": result is None, "deleted": resource_name}


def people_update_group(resource_name: str, new_name: str) -> dict:
    """Update a contact group's name."""
    if not resource_name or not new_name:
        return {"error": "resource_name and new_name are required"}
    body = {"contactGroup": {"name": new_name}}
    data = call_api(
        f"https://people.googleapis.com/v1/{resource_name}",
        method="PUT", json_body=body,
    )
    if not data:
        return {"error": "Failed to update group"}
    return {"resourceName": data.get("resourceName"), "name": data.get("name")}


def people_search_directory(query: str, page_size: int = 20) -> list[dict]:
    """Search all directories for people matching query."""
    params = {
        "query": query,
        "pageSize": min(page_size, 100),
        "readMask": "names,emailAddresses,phoneNumbers,photos",
    }
    data = call_api(
        "https://people.googleapis.com/v1/people:searchDirectoryPeople",
        params=params,
    )
    if not data:
        return []
    return [{
        "resourceName": p.get("resourceName"),
        "name": (p.get("names") or [{}])[0].get("displayName", ""),
        "email": (p.get("emailAddresses") or [{}])[0].get("value", ""),
        "phone": (p.get("phoneNumbers") or [{}])[0].get("value", ""),
        "photo": (p.get("photos") or [{}])[0].get("url", ""),
    } for p in data.get("people", [])]


def people_list_connections(resource_name: str = "people/me", page_size: int = 20) -> list[dict]:
    """List connections for a person resource."""
    params = {
        "pageSize": min(page_size, 100),
        "personFields": "names,emailAddresses,phoneNumbers,photos",
    }
    data = call_api(
        f"https://people.googleapis.com/v1/{resource_name}/connections",
        params=params,
    )
    if not data:
        return []
    return [{
        "resourceName": c.get("resourceName"),
        "name": (c.get("names") or [{}])[0].get("displayName", ""),
        "email": (c.get("emailAddresses") or [{}])[0].get("value", ""),
        "phone": (c.get("phoneNumbers") or [{}])[0].get("value", ""),
    } for c in data.get("connections", [])]


def people_get_batch_get(resource_names: list[str]) -> list[dict]:
    """Get multiple people by resource names."""
    if not resource_names:
        return []
    params = {
        "resourceNames": resource_names,
        "personFields": "names,emailAddresses,phoneNumbers,photos",
    }
    data = call_api(
        "https://people.googleapis.com/v1/people:batchGet",
        params=params,
    )
    if not data:
        return []
    results = []
    for resp in data.get("responses", []):
        p = resp.get("person", {})
        results.append({
            "resourceName": p.get("resourceName"),
            "name": (p.get("names") or [{}])[0].get("displayName", ""),
            "email": (p.get("emailAddresses") or [{}])[0].get("value", ""),
        })
    return results


def people_list_contact_groups(page_size: int = 20) -> list[dict]:
    """List contact groups with pagination."""
    data = call_api(
        "https://people.googleapis.com/v1/contactGroups",
        params={"pageSize": min(page_size, 100)},
    )
    if not data:
        return []
    return [{
        "resourceName": g.get("resourceName"),
        "name": g.get("name"),
        "groupType": g.get("groupType"),
        "memberCount": g.get("memberCount", 0),
    } for g in data.get("contactGroups", [])]


def people_copy_other_contact_to_my_contacts(resource_name: str) -> dict:
    """Copy a person from 'Other contacts' to 'My contacts'."""
    if not resource_name:
        return {"error": "resource_name is required"}
    data = call_api(
        f"https://people.googleapis.com/v1/{resource_name}:copyOtherContactToMyContactsGroup",
        method="POST",
    )
    if not data:
        return {"error": "Failed to copy contact"}
    return {"resourceName": data.get("resourceName"), "copied": True}


# ═══════════════════════════════════════════════════════════════════
#  Tasks — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def tasks_create_tasklist(title: str) -> dict:
    """Create a new task list."""
    data = call_api(
        "https://tasks.googleapis.com/tasks/v1/users/@me/lists",
        method="POST", json_body={"title": title},
    )
    if not data:
        return {"error": "Failed to create task list"}
    return {"id": data.get("id"), "title": data.get("title"), "updated": data.get("updated")}


def tasks_update_tasklist(tasklist_id: str, title: str) -> dict:
    """Update a task list title."""
    if not tasklist_id or not title:
        return {"error": "tasklist_id and title are required"}
    data = call_api(
        f"https://tasks.googleapis.com/tasks/v1/users/@me/lists/{tasklist_id}",
        method="PUT", json_body={"title": title},
    )
    if not data:
        return {"error": "Failed to update task list"}
    return {"id": data.get("id"), "title": data.get("title")}


def tasks_delete_tasklist(tasklist_id: str) -> dict:
    """Delete a task list."""
    if not tasklist_id:
        return {"error": "tasklist_id is required"}
    result = call_api(
        f"https://tasks.googleapis.com/tasks/v1/users/@me/lists/{tasklist_id}",
        method="DELETE",
    )
    return {"ok": result is None, "deleted": tasklist_id}


def tasks_move(task_id: str, source_list_id: str, dest_list_id: str,
               parent: Optional[str] = None) -> dict:
    """Move a task to a different position or list."""
    if not task_id or not source_list_id or not dest_list_id:
        return {"error": "task_id, source_list_id, and dest_list_id are required"}
    body: dict[str, Any] = {}
    if parent:
        body["parent"] = parent
    data = call_api(
        f"https://tasks.googleapis.com/tasks/v1/lists/{source_list_id}/tasks/{task_id}/move"
        f"?destinationTasklist={dest_list_id}",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to move task"}
    return {"id": data.get("id"), "title": data.get("title"), "destListId": dest_list_id}


def tasks_clear_completed(tasklist_id: str) -> dict:
    """Clear completed tasks from a task list."""
    if not tasklist_id:
        return {"error": "tasklist_id is required"}
    import requests
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    try:
        r = requests.post(
            f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist_id}/clear",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        return {"success": True, "cleared": tasklist_id}
    except Exception as exc:
        return {"error": str(exc)}


def tasks_get(tasklist_id: str, task_id: str) -> dict:
    """Get a single task by ID."""
    if not tasklist_id or not task_id:
        return {"error": "tasklist_id and task_id are required"}
    data = call_api(
        f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist_id}/tasks/{task_id}",
    )
    if not data:
        return {"error": "Task not found"}
    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "notes": data.get("notes"),
        "due": data.get("due"),
        "status": data.get("status"),
        "updated": data.get("updated"),
        "position": data.get("position"),
        "selfLink": data.get("selfLink"),
    }


# ═══════════════════════════════════════════════════════════════════
#  Photos — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def photos_upload(file_path: str, album_id: Optional[str] = None,
                  description: Optional[str] = None) -> dict:
    """Upload a media item from a local file to Google Photos."""
    import requests
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    try:
        # Step 1: Upload raw bytes to get upload token
        upload_url = "https://photoslibrary.googleapis.com/v1/uploads"
        file_bytes = path.read_bytes()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
            "X-Goog-Upload-File-Name": path.name,
            "X-Goog-Upload-Protocol": "raw",
        }
        r = requests.post(upload_url, data=file_bytes, headers=headers, timeout=60)
        r.raise_for_status()
        upload_token = r.text.strip()
        if not upload_token:
            return {"error": "No upload token returned"}
        # Step 2: Create media item with batchCreate
        new_media_item = {"simpleMediaItem": {"uploadToken": upload_token}}
        if description:
            new_media_item["description"] = description
        create_body: dict[str, Any] = {"newMediaItems": [new_media_item]}
        if album_id:
            create_body["albumId"] = album_id
        r2 = requests.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=create_body,
            timeout=30,
        )
        r2.raise_for_status()
        result = r2.json()
        items = result.get("newMediaItemResults", [])
        if items:
            return items[0].get("mediaItem", {})
        return {"uploadToken": upload_token}
    except Exception as exc:
        return {"error": str(exc)}


def photos_add_to_album(album_id: str, media_item_ids: list[str]) -> dict:
    """Add media items to an album."""
    if not album_id or not media_item_ids:
        return {"error": "album_id and media_item_ids are required"}
    result = call_api(
        "https://photoslibrary.googleapis.com/v1/albums/batchAddMediaItems",
        method="POST",
        json_body={"albumId": album_id, "mediaItemIds": media_item_ids},
    )
    return {"ok": result is None, "albumId": album_id, "addedCount": len(media_item_ids)}


def photos_remove_from_album(album_id: str, media_item_ids: list[str]) -> dict:
    """Remove media items from an album."""
    if not album_id or not media_item_ids:
        return {"error": "album_id and media_item_ids are required"}
    result = call_api(
        "https://photoslibrary.googleapis.com/v1/albums/batchRemoveMediaItems",
        method="POST",
        json_body={"albumId": album_id, "mediaItemIds": media_item_ids},
    )
    return {"ok": result is None, "albumId": album_id, "removedCount": len(media_item_ids)}


def photos_search_by_content(include_archived: bool = False,
                              category: Optional[str] = None,
                              date_filter: Optional[list[dict]] = None,
                              page_size: int = 50) -> list[dict]:
    """Search media items by content filters (categories, dates)."""
    token = get_access_token()
    if not token:
        return []
    import requests
    filters: dict = {}
    if include_archived:
        filters["includeArchivedMedia"] = include_archived
    if category:
        filters["contentFilter"] = {"includedContentCategories": [category]}
    if date_filter:
        filters["dateFilter"] = {"dates": date_filter}
    body: dict[str, Any] = {"pageSize": min(page_size, 100), "filters": filters}
    try:
        r = requests.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:search",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=15,
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
        logger.warning("Photos search by content failed: %s", exc)
        return []


def photos_get_album(album_id: str) -> dict:
    """Get album details."""
    if not album_id:
        return {"error": "album_id is required"}
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.get(
            f"https://photoslibrary.googleapis.com/v1/albums/{album_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "id": data["id"],
            "title": data.get("title"),
            "productUrl": data.get("productUrl"),
            "mediaItemsCount": data.get("mediaItemsCount", "0"),
            "coverPhotoUrl": data.get("coverPhotoBaseUrl", "") + "=w200-h200",
            "isWriteable": data.get("isWriteable", False),
            "shareInfo": data.get("shareInfo"),
        }
    except Exception as exc:
        return {"error": str(exc)}


def photos_list_shared_albums(page_size: int = 20) -> list[dict]:
    """List albums shared with the user."""
    token = get_access_token()
    if not token:
        return []
    import requests
    try:
        r = requests.get(
            "https://photoslibrary.googleapis.com/v1/sharedAlbums",
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
            "shareInfo": a.get("shareInfo"),
        } for a in data.get("sharedAlbums", [])]
    except Exception as exc:
        logger.warning("Photos list shared albums failed: %s", exc)
        return []


def photos_leave_shared_album(share_token: str) -> dict:
    """Leave a shared album."""
    if not share_token:
        return {"error": "share_token is required"}
    result = call_api(
        "https://photoslibrary.googleapis.com/v1/albums:leaveSharedAlbum",
        method="POST",
        json_body={"shareToken": share_token},
    )
    return {"ok": result is None, "left": True}


def photos_share_album(album_id: str, is_collaborative: bool = False,
                       is_commentable: bool = False) -> dict:
    """Create share info for an album."""
    if not album_id:
        return {"error": "album_id is required"}
    body: dict[str, Any] = {
        "sharedAlbumOptions": {
            "isCollaborative": is_collaborative,
            "isCommentable": is_commentable,
        }
    }
    data = call_api(
        f"https://photoslibrary.googleapis.com/v1/albums/{album_id}:share",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to share album"}
    return {"albumId": album_id, "shareInfo": data.get("shareInfo")}


def photos_unshare_album(album_id: str) -> dict:
    """Stop sharing an album."""
    if not album_id:
        return {"error": "album_id is required"}
    result = call_api(
        f"https://photoslibrary.googleapis.com/v1/albums/{album_id}:unshare",
        method="POST",
    )
    return {"ok": result is None, "unshared": True}


def photos_get_media_item_metadata(media_item_id: str) -> dict:
    """Get a single media item with full metadata."""
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
#  Books — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def books_list_bookshelves() -> list[dict]:
    """List bookshelves for the authenticated user."""
    data = call_api("https://www.googleapis.com/books/v1/mylibrary/bookshelves")
    if not data:
        return []
    return [{
        "id": s.get("id"),
        "title": s.get("title"),
        "volumeCount": s.get("volumeCount", 0),
        "updated": s.get("updated"),
    } for s in data.get("items", [])]


def books_get_bookshelf(shelf_id: str, max_results: int = 10) -> list[dict]:
    """List volumes in a bookshelf."""
    if not shelf_id:
        return []
    data = call_api(
        f"https://www.googleapis.com/books/v1/mylibrary/bookshelves/{shelf_id}/volumes",
        params={"maxResults": min(max_results, 40)},
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
        })
    return results


def books_add_to_bookshelf(shelf_id: str, volume_id: str) -> dict:
    """Add a volume to a bookshelf."""
    if not shelf_id or not volume_id:
        return {"error": "shelf_id and volume_id are required"}
    result = call_api(
        f"https://www.googleapis.com/books/v1/mylibrary/bookshelves/{shelf_id}/addVolume",
        method="POST",
        json_body={"volumeId": volume_id},
    )
    return {"ok": result is None, "shelfId": shelf_id, "volumeId": volume_id}


def books_remove_from_bookshelf(shelf_id: str, volume_id: str) -> dict:
    """Remove a volume from a bookshelf."""
    if not shelf_id or not volume_id:
        return {"error": "shelf_id and volume_id are required"}
    result = call_api(
        f"https://www.googleapis.com/books/v1/mylibrary/bookshelves/{shelf_id}/removeVolume",
        method="POST",
        json_body={"volumeId": volume_id},
    )
    return {"ok": result is None, "shelfId": shelf_id, "volumeId": volume_id}


def books_clear_bookshelf(shelf_id: str) -> dict:
    """Clear all volumes in a bookshelf."""
    if not shelf_id:
        return {"error": "shelf_id is required"}
    result = call_api(
        f"https://www.googleapis.com/books/v1/mylibrary/bookshelves/{shelf_id}/clearVolumes",
        method="POST",
    )
    return {"ok": result is None, "cleared": shelf_id}


def books_move_volume(shelf_id: str, volume_id: str, new_position: int) -> dict:
    """Move a volume within a bookshelf to a new position."""
    if not shelf_id or not volume_id:
        return {"error": "shelf_id and volume_id are required"}
    result = call_api(
        f"https://www.googleapis.com/books/v1/mylibrary/bookshelves/{shelf_id}/moveVolume",
        method="POST",
        json_body={"volumeId": volume_id, "volumePosition": new_position},
    )
    return {"ok": result is None, "shelfId": shelf_id, "volumeId": volume_id, "newPosition": new_position}


def books_get_reading_position(volume_id: str) -> dict:
    """Get reading progress for a volume."""
    if not volume_id:
        return {"error": "volume_id is required"}
    token = get_access_token()
    if not token:
        return {"error": "No OAuth token"}
    import requests
    try:
        r = requests.get(
            "https://www.googleapis.com/books/v1/mylibrary/readingpositions",
            params={"volumeId": volume_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "volumeId": volume_id,
            "position": data.get("position"),
            "updated": data.get("updated"),
        }
    except Exception as exc:
        return {"error": str(exc)}


def books_set_reading_position(volume_id: str, position: str, timestamp: str = "") -> dict:
    """Set reading position for a volume."""
    if not volume_id or not position:
        return {"error": "volume_id and position are required"}
    body: dict[str, Any] = {
        "volumeId": volume_id,
        "position": position,
    }
    if timestamp:
        body["timestamp"] = timestamp
    result = call_api(
        "https://www.googleapis.com/books/v1/mylibrary/readingpositions",
        method="POST", json_body=body,
    )
    return {"ok": result is None, "volumeId": volume_id, "position": position}


def books_list_annotations() -> list[dict]:
    """List user's book annotations and highlights."""
    data = call_api("https://www.googleapis.com/books/v1/mylibrary/annotations")
    if not data:
        return []
    return [{
        "id": a.get("id"),
        "volumeId": a.get("volumeId"),
        "content": a.get("content"),
        "selectedText": a.get("selectedText"),
        "layerSummary": a.get("layerSummary"),
    } for a in data.get("items", [])]


def books_create_annotation(volume_id: str, content: str,
                            selected_text: Optional[str] = None) -> dict:
    """Create an annotation or highlight for a volume."""
    if not volume_id or not content:
        return {"error": "volume_id and content are required"}
    body: dict[str, Any] = {
        "volumeId": volume_id,
        "content": content,
    }
    if selected_text:
        body["selectedText"] = selected_text
    data = call_api(
        "https://www.googleapis.com/books/v1/mylibrary/annotations",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to create annotation"}
    return {"id": data.get("id"), "volumeId": data.get("volumeId"), "content": data.get("content")}


def books_delete_annotation(annotation_id: str) -> dict:
    """Delete an annotation."""
    if not annotation_id:
        return {"error": "annotation_id is required"}
    result = call_api(
        f"https://www.googleapis.com/books/v1/mylibrary/annotations/{annotation_id}",
        method="DELETE",
    )
    return {"ok": result is None, "deleted": annotation_id}


def books_get_volume_recommended(max_results: int = 10) -> list[dict]:
    """Get recommended volumes for the user."""
    data = call_api(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": ":recommended", "maxResults": min(max_results, 40)},
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
        })
    return results


def books_search_by_subject(subject: str, max_results: int = 10) -> list[dict]:
    """Search books by subject."""
    if not subject:
        return []
    data = call_api(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": f"subject:{subject}", "maxResults": min(max_results, 40)},
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
        })
    return results


def books_list_volumes(shelf_id: str) -> list[dict]:
    """List volumes in a bookshelf by shelf ID."""
    if not shelf_id:
        return []
    data = call_api(
        f"https://www.googleapis.com/books/v1/mylibrary/bookshelves/{shelf_id}/volumes",
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
            "publisher": vol.get("publisher"),
            "publishedDate": vol.get("publishedDate"),
        })
    return results


def books_get_volume_annotations(volume_id: str) -> list[dict]:
    """List annotations for a specific volume."""
    if not volume_id:
        return []
    data = call_api(
        "https://www.googleapis.com/books/v1/mylibrary/annotations",
        params={"volumeId": volume_id},
    )
    if not data:
        return []
    return [{
        "id": a.get("id"),
        "content": a.get("content"),
        "selectedText": a.get("selectedText"),
        "layerSummary": a.get("layerSummary"),
    } for a in data.get("items", [])]


# ═══════════════════════════════════════════════════════════════════
#  Firebase / Firestore — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def firestore_list_collections(project_id: Optional[str] = None) -> list[dict]:
    """List collection IDs in the Firestore database."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents:listCollectionIds",
        method="POST", json_body={},
    )
    if not data:
        return []
    return [{"collectionId": cid} for cid in data.get("collectionIds", [])]


def firestore_list_documents(collection: str, page_size: int = 20,
                              project_id: Optional[str] = None) -> list[dict]:
    """List documents in a collection with their fields."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/{collection}",
        params={"pageSize": min(page_size, 300)},
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


def firestore_update_document(collection: str, document_id: str,
                               update_fields: dict,
                               project_id: Optional[str] = None) -> dict:
    """Update specific fields in a Firestore document."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    body = {"fields": _firestore_encode_fields(update_fields)}
    data = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/{collection}/{document_id}",
        params={"updateMask.fieldPaths": list(update_fields.keys())},
        method="PATCH", json_body=body,
    )
    if not data:
        return {"error": "Failed to update document"}
    return {"id": data.get("name", "").split("/")[-1], "fields": _firestore_decode_fields(data.get("fields", {}))}


def firestore_create_document(collection: str, data_dict: dict,
                               project_id: Optional[str] = None) -> dict:
    """Create a Firestore document with auto-generated ID."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    body = {"fields": _firestore_encode_fields(data_dict)}
    result = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/{collection}",
        method="POST", json_body=body,
    )
    if not result:
        return {"error": "Failed to create document"}
    return {"id": result.get("name", "").split("/")[-1], "fields": _firestore_decode_fields(result.get("fields", {}))}


def firestore_run_query(collection: str, structured_query: dict,
                         project_id: Optional[str] = None) -> list[dict]:
    """Run a structured Firestore query."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    body = {
        "structuredQuery": structured_query,
    }
    data = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents:runQuery",
        method="POST", json_body=body, timeout=30,
    )
    if not data:
        return []
    results = []
    for item in data:
        doc = item.get("document", {})
        if doc:
            results.append({
                "id": doc.get("name", "").split("/")[-1],
                "fields": _firestore_decode_fields(doc.get("fields", {})),
            })
    return results


def firestore_batch_get(document_paths: list[str],
                         project_id: Optional[str] = None) -> list[dict]:
    """Batch get multiple Firestore documents."""
    if not document_paths:
        return []
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    body = {"documents": document_paths}
    data = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents:batchGet",
        method="POST", json_body=body,
    )
    if not data:
        return []
    results = []
    for item in data.get("found", []):
        results.append({
            "id": item.get("name", "").split("/")[-1],
            "fields": _firestore_decode_fields(item.get("fields", {})),
        })
    return results


def firestore_begin_transaction(project_id: Optional[str] = None) -> dict:
    """Start a Firestore transaction."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents:beginTransaction",
        method="POST", json_body={},
    )
    if not data:
        return {"error": "Failed to begin transaction"}
    return {"transaction": data.get("transaction")}


def firestore_commit(transaction: str, writes: list[dict],
                      project_id: Optional[str] = None) -> dict:
    """Commit a Firestore transaction with writes."""
    if not transaction:
        return {"error": "transaction is required"}
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    body = {
        "transaction": transaction,
        "writes": writes,
    }
    data = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents:commit",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to commit transaction"}
    return {"commitTime": data.get("commitTime"), "writeResults": data.get("writeResults", [])}


def firestore_rollback(transaction: str, project_id: Optional[str] = None) -> dict:
    """Rollback a Firestore transaction."""
    if not transaction:
        return {"error": "transaction is required"}
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    result = call_api(
        f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents:rollback",
        method="POST", json_body={"transaction": transaction},
    )
    return {"ok": result is None}


# ═══════════════════════════════════════════════════════════════════
#  BigQuery — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def bigquery_list_datasets(project_id: Optional[str] = None) -> list[dict]:
    """List datasets in a BigQuery project."""
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        f"https://bigquery.googleapis.com/bigquery/v2/projects/{pid}/datasets",
    )
    if not data:
        return []
    return [{
        "id": d.get("datasetReference", {}).get("datasetId", ""),
        "friendlyName": d.get("friendlyName", ""),
        "location": d.get("location", ""),
    } for d in data.get("datasets", [])]


def bigquery_list_tables(dataset_id: str, project_id: Optional[str] = None) -> list[dict]:
    """List tables in a BigQuery dataset."""
    if not dataset_id:
        return []
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        f"https://bigquery.googleapis.com/bigquery/v2/projects/{pid}/datasets/{dataset_id}/tables",
    )
    if not data:
        return []
    return [{
        "id": t.get("tableReference", {}).get("tableId", ""),
        "type": t.get("type", ""),
        "friendlyName": t.get("friendlyName", ""),
    } for t in data.get("tables", [])]


def bigquery_get_table(dataset_id: str, table_id: str,
                        project_id: Optional[str] = None) -> dict:
    """Get BigQuery table metadata."""
    if not dataset_id or not table_id:
        return {"error": "dataset_id and table_id are required"}
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        f"https://bigquery.googleapis.com/bigquery/v2/projects/{pid}/datasets/{dataset_id}/tables/{table_id}",
    )
    if not data:
        return {"error": "Table not found"}
    schema = data.get("schema", {}).get("fields", [])
    return {
        "id": data.get("id"),
        "tableType": data.get("type"),
        "friendlyName": data.get("friendlyName"),
        "description": data.get("description", ""),
        "creationTime": data.get("creationTime"),
        "lastModifiedTime": data.get("lastModifiedTime"),
        "numRows": data.get("numRows", "0"),
        "numBytes": data.get("numBytes", "0"),
        "location": data.get("location", ""),
        "schema": [{"name": f.get("name"), "type": f.get("type"), "mode": f.get("mode")} for f in schema],
    }


def bigquery_get_dataset(dataset_id: str, project_id: Optional[str] = None) -> dict:
    """Get BigQuery dataset metadata."""
    if not dataset_id:
        return {"error": "dataset_id is required"}
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    data = call_api(
        f"https://bigquery.googleapis.com/bigquery/v2/projects/{pid}/datasets/{dataset_id}",
    )
    if not data:
        return {"error": "Dataset not found"}
    return {
        "id": data.get("id"),
        "friendlyName": data.get("friendlyName"),
        "description": data.get("description", ""),
        "location": data.get("location", ""),
        "creationTime": data.get("creationTime"),
        "lastModifiedTime": data.get("lastModifiedTime"),
        "defaultTableExpirationMs": data.get("defaultTableExpirationMs"),
    }


def bigquery_insert_rows(dataset_id: str, table_id: str, rows: list[dict],
                          project_id: Optional[str] = None) -> dict:
    """Stream rows into a BigQuery table."""
    if not dataset_id or not table_id or not rows:
        return {"error": "dataset_id, table_id, and rows are required"}
    pid = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    body = {
        "rows": [{"json": row} for row in rows],
    }
    data = call_api(
        f"https://bigquery.googleapis.com/bigquery/v2/projects/{pid}/datasets/{dataset_id}/tables/{table_id}/insertAll",
        method="POST", json_body=body,
    )
    if not data:
        return {"error": "Failed to insert rows"}
    return {
        "kind": data.get("kind"),
        "insertErrors": data.get("insertErrors", []),
    }


# ═══════════════════════════════════════════════════════════════════
#  NLP — Expanded Tools
# ═══════════════════════════════════════════════════════════════════


def nlp_analyze_entity_sentiment(text: str) -> list[dict]:
    """Analyze entity sentiment in text — returns entities with sentiment scores."""
    token = get_access_token()
    if not token:
        return []
    import requests
    try:
        r = requests.post(
            "https://language.googleapis.com/v1/documents:analyzeEntitySentiment",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"document": {"type": "PLAIN_TEXT", "content": text}, "encodingType": "UTF8"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return [{
            "name": e.get("name"),
            "type": e.get("type"),
            "salience": e.get("salience"),
            "sentiment": e.get("sentiment", {}),
            "wikipedia_url": e.get("metadata", {}).get("wikipedia_url", ""),
            "mid": e.get("metadata", {}).get("mid", ""),
            "mentions": [{"text": m.get("text", {}).get("content", ""),
                          "type": m.get("type"),
                          "sentiment": m.get("sentiment", {})}
                         for m in e.get("mentions", [])],
        } for e in data.get("entities", [])]
    except Exception as exc:
        logger.warning("NLP entity sentiment analysis failed: %s", exc)
        return []


