"""
MedGemma API Client — Unified
Sends images to MedGemma model deployed on Modal.
Includes ZIP smart-routing, series detection, batch processing, and JSON report saving.

All images are sent as base64-encoded data inline in the JSON request.
DICOM files (.dcm) are automatically converted to JPEG with appropriate windowing before analysis.

Cold start handling:
  Before the first analysis, the script checks if the server is ready. If the Modal
  container is cold-starting, progress feedback is shown until the server responds.

Modal config: --limit-mm-per-prompt image=85 (max 85 images per request)

Usage:
  python3 scripts/medgemma_api.py images/xray.jpeg              # single image
  python3 scripts/medgemma_api.py scan.dcm                      # single DICOM
  python3 scripts/medgemma_api.py images/d0.jpg images/d1.jpg   # multiple images
  python3 scripts/medgemma_api.py archive.zip                   # ZIP archive (JPEG, DICOM, or mixed)

Note: On Windows, use `python` instead of `python3` if `python3` is not available.
"""

import base64
import json
import os
import shutil
import sys
import time
import zipfile
import urllib.request
import urllib.error
import ssl
import datetime
from pathlib import Path

# UTF-8 output for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _load_env():
    """Load .env file from the project root (no external deps)."""
    # Walk up from script dir to find .env
    for parent in [Path(__file__).resolve().parent.parent, Path.cwd()]:
        env_file = parent / ".env"
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
            break


_load_env()

ENDPOINT = os.environ.get("MEDGEMMA_ENDPOINT", "")
MODEL = os.environ.get("MEDGEMMA_MODEL", "google/medgemma-1.5-4b-it")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".dcm", ".dicom"}
_MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".bmp": "image/bmp",
    ".tiff": "image/tiff", ".tif": "image/tiff",
    ".dcm": "image/jpeg", ".dicom": "image/jpeg",  # converted to JPEG before sending
}

# DICOM support — lazy import to avoid hard dependency
_dicom_utils = None


def _get_dicom_utils():
    """Lazy-import dicom_utils module."""
    global _dicom_utils
    if _dicom_utils is None:
        from pathlib import Path as _P
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "dicom_utils", _P(__file__).resolve().parent / "dicom_utils.py"
        )
        _dicom_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_dicom_utils)
    return _dicom_utils

MAX_IMAGES_PER_REQUEST = 85  # Modal vLLM config: --limit-mm-per-prompt image=85


# ---------------------------------------------------------------------------
# SSL context
# ---------------------------------------------------------------------------

def _ssl_ctx() -> ssl.SSLContext:
    if os.environ.get("MEDGEMMA_VERIFY_SSL", "true").lower() in ("0", "false", "no"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()


# ---------------------------------------------------------------------------
# Cold start detection and server readiness
# ---------------------------------------------------------------------------

_server_warm = False


def _ensure_server_ready() -> bool:
    """
    Wait for the MedGemma server to be ready. Handles cold starts gracefully.

    Strategy: Send ONE request with a long timeout instead of polling.
    Modal automatically boots the container on the first request — we just wait.
    Polling every N seconds floods Modal's queue with Pending requests, which can
    prevent the container from ever starting. One request = one queue entry.
    """
    global _server_warm
    if _server_warm:
        return True

    if not ENDPOINT:
        print("[SERVER] ERROR: No endpoint configured.")
        return False

    # Derive /v1/models URL from the chat completions endpoint
    if "/v1/" in ENDPOINT:
        url = ENDPOINT.split("/v1/")[0] + "/v1/models"
    else:
        url = ENDPOINT

    print("[SERVER] Checking MedGemma server status...")

    # Modal cold start handling:
    # - First request triggers container boot and queues (1 queue entry only)
    # - Modal returns HTTP 303 redirect after ~150s if the container is still starting
    # - We follow the redirect URL (which waits for the same container) up to max_wait
    # - Progress messages are printed locally based on elapsed time
    import threading

    max_wait = 600  # 10 minutes total
    start = time.time()
    cold_start = False

    # Background thread for progress display
    stop_progress = threading.Event()

    def _progress_printer():
        time.sleep(5)
        if stop_progress.is_set():
            return
        nonlocal cold_start
        cold_start = True
        print("[SERVER] Server is starting up (cold start)...")
        print("[SERVER] The AI model is loading into GPU memory. This typically takes 2-5 minutes.")
        while not stop_progress.is_set():
            stop_progress.wait(timeout=30)
            if stop_progress.is_set():
                return
            elapsed = int(time.time() - start)
            mins, secs = divmod(elapsed, 60)
            print(f"[SERVER] Waiting... {mins}m {secs:02d}s elapsed")

    progress_thread = threading.Thread(target=_progress_printer, daemon=True)
    progress_thread.start()

    # Disable automatic redirect following — we handle 303 manually
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if code == 303:
                return None  # Don't auto-follow; we'll handle it
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=_ssl_ctx()))
    current_url = url

    try:
        while time.time() - start < max_wait:
            remaining = max(30, int(max_wait - (time.time() - start)))
            req = urllib.request.Request(current_url, method="GET")
            try:
                with opener.open(req, timeout=remaining) as resp:
                    if resp.status == 200:
                        stop_progress.set()
                        progress_thread.join(timeout=2)
                        elapsed = int(time.time() - start)
                        if cold_start:
                            mins, secs = divmod(elapsed, 60)
                            print(f"[SERVER] Server is ready! (cold start took {mins}m {secs:02d}s)")
                        else:
                            print("[SERVER] Server is ready.")
                        _server_warm = True
                        return True
            except urllib.error.HTTPError as e:
                if e.code == 303:
                    # Modal redirect during cold start — follow the new URL
                    redirect_url = e.headers.get("Location")
                    if redirect_url:
                        current_url = redirect_url
                    continue
                if e.code == 502:
                    # Proxy is up but vLLM is still loading — retry
                    time.sleep(5)
                    continue
                raise
            except urllib.error.URLError:
                # Connection failed, retry after short pause
                time.sleep(5)
                continue

        # Timeout reached
        stop_progress.set()
        progress_thread.join(timeout=2)
        print(f"[SERVER] Server did not respond within {max_wait // 60} minutes.")
        print("[SERVER] Check your deployment: modal app list")
        return False
    except Exception as e:
        stop_progress.set()
        progress_thread.join(timeout=2)
        print(f"[SERVER] Connection error: {e}")
        print("[SERVER] Check your deployment: modal app list")
        return False


# ---------------------------------------------------------------------------
# API call — sends payload to the endpoint
# ---------------------------------------------------------------------------

def _api_call(content: list[dict], max_tokens: int = 1024, timeout: int = 300) -> str:
    """Send a chat completion request to the MedGemma endpoint."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }).encode()

    req = urllib.request.Request(
        ENDPOINT, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as resp:
            result = json.loads(resp.read().decode())
            choices = result.get("choices")
            if not choices:
                return f"ERROR: Unexpected API response (no choices): {json.dumps(result)[:500]}"
            return choices[0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:1000]
        except Exception:
            pass
        return f"ERROR: MedGemma HTTP {e.code}: {body or e.reason}"
    except urllib.error.URLError as e:
        if "timed out" in str(e):
            return "ERROR: MedGemma request timed out."
        return f"ERROR: MedGemma connection error: {e}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return f"ERROR: MedGemma malformed response: {e}"
    except Exception as e:
        return f"ERROR: MedGemma API error: {e}"


# ---------------------------------------------------------------------------
# Image content builder — base64
# ---------------------------------------------------------------------------

def _image_content(image_path: Path) -> dict:
    """Build an image_url content block using base64 encoding.

    DICOM files are converted to JPEG before encoding.
    """
    if image_path.suffix.lower() in (".dcm", ".dicom"):
        du = _get_dicom_utils()
        jpeg_bytes = du.dicom_to_jpeg_bytes(image_path)
        b64 = base64.b64encode(jpeg_bytes).decode()
        return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}

    mime = _MIME_MAP.get(image_path.suffix.lower(), "image/png")
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def _dicom_multi_window_content(image_path: Path) -> list[dict]:
    """Build multiple image_url content blocks for CT multi-window rendering.

    For CT: returns one image per window preset (soft_tissue, lung, bone).
    For non-CT (MRI, X-ray, etc.): returns a single image with default windowing.
    """
    du = _get_dicom_utils()
    windows = du.dicom_to_multi_window(image_path)
    content = []
    for _name, jpeg_bytes in windows:
        b64 = base64.b64encode(jpeg_bytes).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    return content


def _is_dicom(path: Path) -> bool:
    """Check if a file is DICOM format (extension or magic bytes)."""
    if path.suffix.lower() in (".dcm", ".dicom"):
        return True
    # Magic bytes fallback for extensionless DICOM files
    try:
        with open(path, "rb") as fh:
            fh.seek(128)
            return fh.read(4) == b"DICM"
    except (OSError, IOError):
        return False


def _get_dicom_metadata_text(image_path: Path) -> str:
    """Extract DICOM metadata and format as prompt context text."""
    du = _get_dicom_utils()
    ds = du.read_dicom(image_path)
    meta = du.extract_metadata(ds)
    return du.build_dicom_prompt_context(meta)


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def analyze_image(image_path: str | Path,
                  prompt: str = "Analyze this medical image. Provide detailed findings.") -> str:
    """Analyze a single image with MedGemma.

    DICOM files get multi-window rendering (for CT) and metadata-enriched prompts.
    """
    path = Path(image_path)
    if not path.exists():
        return f"ERROR: File not found: {image_path}"

    if _is_dicom(path):
        # Enrich prompt with DICOM metadata
        try:
            meta_text = _get_dicom_metadata_text(path)
            enriched_prompt = f"{prompt}\n\n{meta_text}"
        except Exception:
            enriched_prompt = prompt

        # Multi-window content (CT: multiple images, MRI/XR: single)
        try:
            image_blocks = _dicom_multi_window_content(path)
        except Exception:
            image_blocks = [_image_content(path)]

        content: list[dict] = [{"type": "text", "text": enriched_prompt}]
        content.extend(image_blocks)
        return _api_call(content, max_tokens=1024, timeout=300)

    content = [{"type": "text", "text": prompt}, _image_content(path)]
    return _api_call(content, max_tokens=1024, timeout=300)


def analyze_multiple(image_paths: list[str | Path],
                     prompt: str = "Compare these medical images. Analyze progression.") -> str:
    """Send multiple images to MedGemma in a single request (max 85).

    DICOM files are converted to JPEG. For series of DICOM files, metadata
    from the first file is included in the prompt.
    """
    paths = [Path(p) for p in image_paths]

    # Check if any/all are DICOM — enrich prompt with metadata from first DICOM
    dicom_paths = [p for p in paths if _is_dicom(p)]
    if dicom_paths:
        try:
            meta_text = _get_dicom_metadata_text(dicom_paths[0])
            prompt = f"{prompt}\n\n{meta_text}"
        except Exception:
            pass

    # For DICOM series: use single-window to stay within 85-image limit
    # (multi-window would multiply image count by 2-3x)
    content: list[dict] = [{"type": "text", "text": prompt}]

    total = len(paths)
    if total > MAX_IMAGES_PER_REQUEST:
        return f"ERROR: Too many images ({total}). Maximum is {MAX_IMAGES_PER_REQUEST} per request. Use analyze_series() for batching."

    for path in paths:
        if not path.exists():
            return f"ERROR: File not found: {path}"
        content.append(_image_content(path))

    return _api_call(content, max_tokens=2048, timeout=600)


# ---------------------------------------------------------------------------
# ZIP extraction
# ---------------------------------------------------------------------------

def extract_zip(zip_path: str | Path) -> tuple[list[Path], Path]:
    """Extract image files from a ZIP to images/temp/{zip_name}/."""
    zip_path = Path(zip_path)
    out = Path("images") / "temp" / zip_path.stem
    out.mkdir(parents=True, exist_ok=True)

    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        out_resolved = out.resolve()
        total_size = 0
        max_extract_size = 2 * 1024 * 1024 * 1024  # 2 GB limit
        for info in zf.infolist():
            name = info.filename
            if Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            if name.startswith("__MACOSX"):
                continue
            # ZIP bomb protection
            total_size += info.file_size
            if total_size > max_extract_size:
                print("ERROR: ZIP extraction exceeds 2 GB limit. Possible zip bomb.")
                break
            # ZIP slip protection: validate and write manually
            target = (out / name).resolve()
            if not str(target).startswith(str(out_resolved) + os.sep):
                print(f"WARNING: Skipping suspicious path: {name}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(name))
            extracted.append(target)

    extracted.sort()
    print(f"[ZIP] {len(extracted)} images extracted -> {out}")
    return extracted, out


# ---------------------------------------------------------------------------
# Series detection
# ---------------------------------------------------------------------------

def detect_series(image_paths: list[Path], extraction_root: Path) -> dict[str, list[Path]]:
    """
    Group images by series.
    - For DICOM files without subdirs: group by SeriesInstanceUID
    - If subdirectories exist: each subdirectory = one series
    - If no subdirectories (non-DICOM): all files = single series
    """
    subdirs: dict[str, list[Path]] = {}
    flat: list[Path] = []
    extraction_root = Path(extraction_root).resolve()

    for p in image_paths:
        rel = p.resolve().relative_to(extraction_root)
        parts = rel.parts
        if len(parts) > 1:
            series_name = parts[0]
            subdirs.setdefault(series_name, []).append(p)
        else:
            flat.append(p)

    if subdirs:
        if flat:
            subdirs["_other"] = sorted(flat)
        return {k: sorted(v) for k, v in subdirs.items()}

    # For flat DICOM files: try grouping by SeriesInstanceUID
    flat_dicom = [p for p in image_paths if _is_dicom(p)]
    if flat_dicom and len(flat_dicom) == len(image_paths):
        try:
            du = _get_dicom_utils()
            groups = du.group_by_series(flat_dicom)
            if groups:
                return groups
        except Exception:
            pass

    return {"all_images": sorted(image_paths)}


# ---------------------------------------------------------------------------
# Series analysis — each series is independent
# ---------------------------------------------------------------------------

def analyze_series(series_name: str, images: list[Path]) -> dict:
    """
    Analyze a single series.
    - DICOM files are sorted by slice position before analysis
    - <=85 images -> send all in a single request
    - >85 images -> smart slice selection for DICOM, batching for regular images
    """
    total = len(images)

    # Sort DICOM files by slice position for correct anatomical order
    has_dicom = any(_is_dicom(p) for p in images)
    if has_dicom:
        try:
            du = _get_dicom_utils()
            images = du.sort_dicom_by_position(images)
        except Exception:
            pass

    print(f"\n{'='*60}")
    print(f"  SERIES: {series_name} ({total} images{'  [DICOM]' if has_dicom else ''})")
    print(f"{'='*60}")

    series_result = {
        "series_name": series_name,
        "total_images": total,
        "batches": [],
    }

    # For large DICOM series: use smart slice selection instead of batching
    if has_dicom and total > MAX_IMAGES_PER_REQUEST:
        try:
            du = _get_dicom_utils()
            selected = du.select_slices(images, MAX_IMAGES_PER_REQUEST, presorted=True)
            print(f"  -> DICOM series: selected {len(selected)} of {total} slices (uniform sampling)")
            prompt = (
                f"These are {len(selected)} representative slices (uniformly sampled from {total} total) "
                f"of a medical imaging series. "
                "Analyze the complete series: describe the imaging modality, body region, "
                "and all notable findings. Note any changes across slices."
            )
            answer = analyze_multiple(selected, prompt)
            print(f"  -> Result: {answer[:200]}...")
            series_result["batches"].append({
                "batch": 1,
                "image_count": len(selected),
                "total_in_series": total,
                "sampling": f"{len(selected)} of {total} (uniform)",
                "images": [p.name for p in selected],
                "analysis": answer,
            })
            return series_result
        except Exception:
            pass  # Fall through to standard batching

    if total <= MAX_IMAGES_PER_REQUEST:
        print(f"  -> Sending {total} images in a single request...")
        prompt = (
            f"These are {total} consecutive medical imaging slices from the same series. "
            "Analyze the complete series: describe the imaging modality, body region, "
            "and all notable findings across the entire series. "
            "Note any progression or changes between slices."
        )
        answer = analyze_multiple(images, prompt)
        print(f"  -> Result: {answer[:200]}...")
        series_result["batches"].append({
            "batch": 1,
            "image_count": total,
            "images": [p.name for p in images],
            "analysis": answer,
        })
    else:
        batches = [images[i:i + MAX_IMAGES_PER_REQUEST]
                   for i in range(0, total, MAX_IMAGES_PER_REQUEST)]
        print(f"  -> {len(batches)} batches (groups of {MAX_IMAGES_PER_REQUEST})")

        for idx, batch in enumerate(batches, 1):
            print(f"\n  [BATCH {idx}/{len(batches)}] {len(batch)} images...")
            prompt = (
                f"These are medical imaging slices {(idx-1)*MAX_IMAGES_PER_REQUEST + 1}"
                f"-{(idx-1)*MAX_IMAGES_PER_REQUEST + len(batch)} "
                f"from a series of {total} total slices. "
                "Describe the imaging modality, body region, and key findings in this segment."
            )
            answer = analyze_multiple(batch, prompt)
            print(f"  -> Result: {answer[:200]}...")
            series_result["batches"].append({
                "batch": idx,
                "image_count": len(batch),
                "images": [p.name for p in batch],
                "analysis": answer,
            })

    return series_result


# ---------------------------------------------------------------------------
# Report saving
# ---------------------------------------------------------------------------

def save_report(data: dict, label: str = "report") -> Path:
    """Save results as timestamped JSON under reports/."""
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    out = reports_dir / f"{safe_label}_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[REPORT] Saved: {out}")
    return out


# ---------------------------------------------------------------------------
# Smart ZIP dispatcher
# ---------------------------------------------------------------------------

def process_zip(zip_path: str | Path) -> dict:
    """Extract ZIP, split into series, analyze each series independently."""
    zip_path = Path(zip_path)
    if not zip_path.exists():
        print(f"ERROR: ZIP file not found: {zip_path}")
        return {}

    images, extraction_root = extract_zip(zip_path)
    total = len(images)

    if total == 0:
        print("ERROR: No image files found in ZIP.")
        return {}

    zip_label = Path(zip_path).stem

    # Detect series
    series_map = detect_series(images, extraction_root)
    print(f"\n[PLAN] {total} images, {len(series_map)} series:")
    for name, imgs in series_map.items():
        batches_needed = (len(imgs) + MAX_IMAGES_PER_REQUEST - 1) // MAX_IMAGES_PER_REQUEST
        mode = "single request" if len(imgs) <= MAX_IMAGES_PER_REQUEST else f"{batches_needed} batches"
        print(f"  - {name}: {len(imgs)} images ({mode})")

    # Analyze each series independently
    results = {
        "zip_file": str(zip_path),
        "total_images": total,
        "total_series": len(series_map),
        "series": {},
    }

    try:
        for series_name, series_images in series_map.items():
            series_result = analyze_series(series_name, series_images)
            results["series"][series_name] = series_result

        save_report(results, label=zip_label)
    finally:
        # Always clean up extracted files, even if analysis fails
        if extraction_root.exists():
            shutil.rmtree(extraction_root, ignore_errors=True)

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _print_usage():
    print("Usage:")
    print("  python3 scripts/medgemma_api.py images/xray.jpeg              # single image")
    print("  python3 scripts/medgemma_api.py scan.dcm                      # single DICOM")
    print("  python3 scripts/medgemma_api.py images/d0.jpg images/d1.jpg   # multiple images")
    print("  python3 scripts/medgemma_api.py archive.zip                   # ZIP archive (JPEG, DICOM, or mixed)")


if __name__ == "__main__":
    # Handle --help before anything else (works even without .env)
    if "--help" in sys.argv or "-h" in sys.argv:
        _print_usage()
        sys.exit(0)

    if not ENDPOINT:
        print("ERROR: MEDGEMMA_ENDPOINT is not set.")
        print("Please create a .env file with your Modal endpoint URL.")
        print("See .env.example for details.")
        sys.exit(1)

    args = sys.argv[1:]

    if len(args) < 1:
        _print_usage()
        sys.exit(1)

    # Validate file extensions
    for arg in args:
        if not arg.lower().endswith(".zip"):
            ext = Path(arg).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                print(f"ERROR: Unsupported file type: {ext or '(none)'}")
                print(f"Supported: {', '.join(sorted(IMAGE_EXTENSIONS))}")
                sys.exit(1)

    # Ensure server is ready (handles cold start with progress feedback)
    if not _ensure_server_ready():
        print("ERROR: MedGemma server is not available. Cannot proceed.")
        sys.exit(1)

    input_path = args[0]

    if input_path.lower().endswith(".zip"):
        process_zip(input_path)
    else:
        paths = args
        if len(paths) == 1:
            print(f"[SINGLE IMAGE] {paths[0]}")
            result = analyze_image(paths[0])
            print(result)
            save_report({"mode": "single", "image": paths[0], "analysis": result},
                        label=Path(paths[0]).stem)
        else:
            print(f"[MULTIPLE IMAGES] {len(paths)} files")
            result = analyze_multiple(paths)
            print(result)
            save_report({"mode": "multiple", "images": paths, "analysis": result},
                        label="multi_image")
