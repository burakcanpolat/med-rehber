"""
DICOM image processing utilities for Med-Rehber.

Handles reading, metadata extraction, windowing, JPEG conversion,
slice sorting/selection, and series grouping for DICOM medical images.

Dependencies: pydicom, numpy, Pillow (PIL).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Union

import numpy as np
import pydicom
from pydicom.dataset import Dataset
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DICOM_EXTENSIONS = {".dcm", ".dicom"}

_DICOM_MAGIC = b"DICM"
_DICOM_MAGIC_OFFSET = 128

# CT window presets: body_part_key -> list of (name, window_width, window_level)
_CT_WINDOW_PRESETS: dict[str, list[tuple[str, float, float]]] = {
    "CHEST": [
        ("soft_tissue", 400, 40),
        ("lung", 1500, -600),
        ("bone", 2000, 300),
    ],
    "HEAD": [
        ("brain", 80, 40),
        ("soft_tissue", 400, 40),
    ],
    "BRAIN": [
        ("brain", 80, 40),
        ("soft_tissue", 400, 40),
    ],
    "ABDOMEN": [
        ("soft_tissue", 400, 50),
        ("bone", 2000, 300),
    ],
}

_CT_DEFAULT_PRESETS: list[tuple[str, float, float]] = [
    ("soft_tissue", 400, 40),
    ("lung", 1500, -600),
    ("bone", 2000, 300),
]


# ---------------------------------------------------------------------------
# 1. is_dicom
# ---------------------------------------------------------------------------

def is_dicom(path: Path) -> bool:
    """Check whether *path* is a DICOM file by extension or magic bytes."""
    path = Path(path)

    # Extension check
    if path.suffix.lower() in DICOM_EXTENSIONS:
        return True

    # Magic-bytes check
    try:
        with open(path, "rb") as fh:
            fh.seek(_DICOM_MAGIC_OFFSET)
            return fh.read(4) == _DICOM_MAGIC
    except (OSError, IOError):
        return False


# ---------------------------------------------------------------------------
# 2. read_dicom
# ---------------------------------------------------------------------------

def read_dicom(path: Path) -> Dataset:
    """Read a DICOM file, handling compressed transfer syntaxes.

    Uses ``force=True`` for maximum compatibility.  If pixel data is
    compressed and the initial ``pixel_array`` access fails, a
    decompression attempt is made via ``pydicom.pixels.decompress``.
    """
    path = Path(path)
    ds = pydicom.dcmread(path, force=True)

    # Ensure file_meta exists (force=True may skip it)
    if not hasattr(ds, "file_meta"):
        ds.file_meta = pydicom.Dataset()

    # Attempt to access pixel data so compressed issues surface early.
    if "PixelData" in ds:
        try:
            _ = ds.pixel_array
        except Exception:
            # Try pydicom built-in decompression
            try:
                from pydicom.pixels import decompress
                decompress(ds)
                _ = ds.pixel_array
            except Exception as exc:
                raise RuntimeError(
                    f"Cannot decode pixel data for {path.name}. "
                    f"Transfer Syntax may require additional codec libraries. "
                    f"Original error: {exc}"
                ) from exc

    return ds


# ---------------------------------------------------------------------------
# 3. extract_metadata
# ---------------------------------------------------------------------------

def _to_float(value: object) -> Union[float, None]:
    """Convert a DICOM DSfloat / MultiValue to a plain float."""
    if value is None:
        return None
    # MultiValue → take the first element
    if isinstance(value, (list, pydicom.multival.MultiValue)):
        if len(value) == 0:
            return None
        value = value[0]
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_metadata(ds: Dataset) -> dict:
    """Extract clinically relevant metadata from a pydicom Dataset."""
    patient_name = ds.get("PatientName", None)
    patient_name_str = str(patient_name) if patient_name is not None else None

    return {
        "modality": ds.get("Modality", None),
        "body_part": ds.get("BodyPartExamined", None),
        "patient_age": ds.get("PatientAge", None),
        "patient_sex": ds.get("PatientSex", None),
        "patient_name": patient_name_str,
        "study_description": ds.get("StudyDescription", None),
        "series_description": ds.get("SeriesDescription", None),
        "study_date": ds.get("StudyDate", None),
        "rows": ds.get("Rows", None),
        "columns": ds.get("Columns", None),
        "bits_allocated": ds.get("BitsAllocated", None),
        "bits_stored": ds.get("BitsStored", None),
        "samples_per_pixel": ds.get("SamplesPerPixel", None),
        "photometric_interpretation": ds.get("PhotometricInterpretation", None),
        "window_center": _to_float(ds.get("WindowCenter", None)),
        "window_width": _to_float(ds.get("WindowWidth", None)),
        "rescale_slope": _to_float(ds.get("RescaleSlope", None)),
        "rescale_intercept": _to_float(ds.get("RescaleIntercept", None)),
        "number_of_frames": ds.get("NumberOfFrames", None),
        "slice_location": _to_float(ds.get("SliceLocation", None)),
        "instance_number": ds.get("InstanceNumber", None),
        "series_instance_uid": ds.get("SeriesInstanceUID", None),
    }


# ---------------------------------------------------------------------------
# 4. apply_window
# ---------------------------------------------------------------------------

def apply_window(hu_array: np.ndarray, ww: float, wl: float) -> np.ndarray:
    """Apply CT windowing to a Hounsfield-unit array.

    Clips to ``[wl - ww/2, wl + ww/2]`` and normalises to ``[0, 255]`` uint8.
    """
    lower = wl - ww / 2.0
    upper = wl + ww / 2.0
    arr = np.clip(hu_array, lower, upper)
    # Avoid division by zero if ww == 0
    if ww == 0:
        return np.zeros_like(hu_array, dtype=np.uint8)
    arr = ((arr - lower) / (upper - lower) * 255.0)
    return arr.astype(np.uint8)


# ---------------------------------------------------------------------------
# 5. get_window_presets
# ---------------------------------------------------------------------------

def get_window_presets(
    modality: str, body_part: str
) -> list[tuple[str, float, float]]:
    """Return window presets ``(name, ww, wl)`` for a given modality/body part.

    Only CT modality has meaningful HU-based presets.  MRI, CR/DX, and US
    return an empty list (they use different normalisation strategies).
    """
    if modality is None:
        return []

    modality_upper = modality.strip().upper()
    if modality_upper != "CT":
        return []

    body_upper = (body_part or "").strip().upper()
    return list(_CT_WINDOW_PRESETS.get(body_upper, _CT_DEFAULT_PRESETS))


# ---------------------------------------------------------------------------
# 6. dicom_to_jpeg_bytes
# ---------------------------------------------------------------------------

def _percentile_normalize(arr: np.ndarray) -> np.ndarray:
    """Normalise using 1st–99th percentile clipping → uint8."""
    p1 = np.percentile(arr, 1)
    p99 = np.percentile(arr, 99)
    if p99 == p1:
        return np.zeros_like(arr, dtype=np.uint8)
    clipped = np.clip(arr, p1, p99)
    scaled = (clipped - p1) / (p99 - p1) * 255.0
    return scaled.astype(np.uint8)


def _normalize_to_uint8(arr: np.ndarray) -> np.ndarray:
    """Simple min-max normalisation → uint8."""
    mn, mx = float(arr.min()), float(arr.max())
    if mx == mn:
        return np.zeros_like(arr, dtype=np.uint8)
    return ((arr - mn) / (mx - mn) * 255.0).astype(np.uint8)


def dicom_to_jpeg_bytes(
    path: Path,
    ww: Union[float, None] = None,
    wl: Union[float, None] = None,
    quality: int = 92,
) -> bytes:
    """Convert a DICOM file to JPEG bytes.

    Parameters
    ----------
    path : Path
        Path to the DICOM file.
    ww, wl : float or None
        Explicit window width / level.  If ``None``, automatic windowing is used.
    quality : int
        JPEG compression quality (1–100).
    """
    ds = read_dicom(Path(path))
    meta = extract_metadata(ds)
    spp = meta["samples_per_pixel"] or 1
    photometric = meta["photometric_interpretation"] or ""
    modality = (meta["modality"] or "").strip().upper()

    arr = ds.pixel_array  # already validated in read_dicom

    # --- Colour images (SamplesPerPixel == 3) ---
    if spp == 3:
        if arr.ndim == 3 and arr.shape[2] == 3:
            # Convert colour space to RGB if needed
            if photometric and photometric.upper() not in ("RGB",):
                try:
                    from pydicom.pixels import convert_color_space
                    arr = convert_color_space(arr, photometric, "RGB")
                except Exception:
                    pass  # best-effort; already in a usable format
            img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
        else:
            img = Image.fromarray(arr.astype(np.uint8))
    # --- Greyscale images ---
    else:
        # Handle multi-frame: take first frame
        if arr.ndim == 3 and spp == 1:
            arr = arr[0]

        arr = arr.astype(np.float64)

        # Apply modality LUT (RescaleSlope / RescaleIntercept)
        has_rescale = meta["rescale_slope"] is not None
        if has_rescale:
            try:
                from pydicom.pixels import apply_modality_lut
                arr = apply_modality_lut(arr, ds).astype(np.float64)
            except Exception:
                slope = meta["rescale_slope"] or 1.0
                intercept = meta["rescale_intercept"] or 0.0
                arr = arr * slope + intercept

        # Windowing / normalisation
        if ww is not None and wl is not None:
            arr = apply_window(arr, ww, wl)
        elif has_rescale:
            # Use VOI LUT from DICOM tags
            try:
                from pydicom.pixels import apply_voi_lut
                arr = apply_voi_lut(arr, ds, index=0).astype(np.float64)
                arr = _normalize_to_uint8(arr)
            except Exception:
                arr = _normalize_to_uint8(arr)
        else:
            # MRI and others without RescaleSlope: percentile normalisation
            arr = _percentile_normalize(arr)

        # Ensure uint8
        if arr.dtype != np.uint8:
            arr = _normalize_to_uint8(arr)

        # MONOCHROME1 → invert
        if "MONOCHROME1" in photometric.upper():
            arr = 255 - arr

        img = Image.fromarray(arr, mode="L").convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 7. dicom_to_multi_window
# ---------------------------------------------------------------------------

def dicom_to_multi_window(
    path: Path, quality: int = 92
) -> list[tuple[str, bytes]]:
    """Convert a DICOM to JPEG bytes for each relevant window preset.

    For CT: one JPEG per preset window (soft_tissue, lung, bone, etc.).
    For non-CT: a single JPEG with default/automatic windowing.

    Reads the DICOM file once and reuses the pixel array for all windows.
    """
    path = Path(path)
    ds = read_dicom(path)
    meta = extract_metadata(ds)
    modality = (meta["modality"] or "").strip().upper()
    body_part = meta["body_part"] or ""

    presets = get_window_presets(modality, body_part)

    if not presets:
        # Non-CT: single image with default windowing
        label = modality if modality else "default"
        jpeg = dicom_to_jpeg_bytes(path, quality=quality)
        return [(label, jpeg)]

    # CT multi-window: read pixel data once, apply each window
    arr = ds.pixel_array.astype(np.float64)

    # Apply modality LUT (RescaleSlope/Intercept → HU for CT)
    has_rescale = meta["rescale_slope"] is not None
    if has_rescale:
        try:
            from pydicom.pixels import apply_modality_lut
            arr = apply_modality_lut(arr, ds).astype(np.float64)
        except Exception:
            slope = meta["rescale_slope"] or 1.0
            intercept = meta["rescale_intercept"] or 0.0
            arr = arr * slope + intercept

    # Handle multi-frame: take first frame
    spp = meta["samples_per_pixel"] or 1
    if arr.ndim == 3 and spp == 1:
        arr = arr[0]

    photometric = (meta["photometric_interpretation"] or "").upper()

    results: list[tuple[str, bytes]] = []
    for name, ww, wl in presets:
        windowed = apply_window(arr, ww, wl)
        # MONOCHROME1 → invert
        if "MONOCHROME1" in photometric:
            windowed = 255 - windowed
        img = Image.fromarray(windowed, mode="L").convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        results.append((name, buf.getvalue()))

    return results


# ---------------------------------------------------------------------------
# 8. build_dicom_prompt_context
# ---------------------------------------------------------------------------

def build_dicom_prompt_context(metadata: dict) -> str:
    """Format DICOM metadata into a text block for inclusion in LLM prompts."""
    modality = metadata.get("modality") or "Unknown"
    body_part = metadata.get("body_part") or "Unknown"
    series_desc = metadata.get("series_description") or "N/A"
    study_desc = metadata.get("study_description") or ""
    rows = metadata.get("rows")
    cols = metadata.get("columns")
    wc = metadata.get("window_center")
    ww = metadata.get("window_width")

    parts = [
        f"[DICOM Info] Modality: {modality} | Body Part: {body_part} | Series: {series_desc}",
    ]

    if study_desc:
        parts.append(f"Study: {study_desc}")

    if rows and cols:
        parts.append(f"Matrix: {rows}x{cols}")

    if wc is not None and ww is not None:
        parts.append(f"Windows: WC={wc}, WW={ww}")
    else:
        parts.append("Windows: default (VOI LUT from DICOM tags)")

    bits = metadata.get("bits_stored")
    if bits:
        parts.append(f"Bit depth: {bits}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 9. sort_dicom_by_position
# ---------------------------------------------------------------------------

def sort_dicom_by_position(paths: list[Path]) -> list[Path]:
    """Sort DICOM files by SliceLocation, falling back to InstanceNumber.

    Files that cannot be read or lack both attributes keep their original
    relative order.
    """
    keyed: list[tuple[float, int, Path]] = []

    for idx, p in enumerate(paths):
        try:
            ds = pydicom.dcmread(p, force=True, stop_before_pixels=True)
        except Exception:
            keyed.append((float("inf"), idx, p))
            continue

        slice_loc = ds.get("SliceLocation", None)
        if slice_loc is not None:
            try:
                keyed.append((float(slice_loc), idx, p))
                continue
            except (TypeError, ValueError):
                pass

        inst_num = ds.get("InstanceNumber", None)
        if inst_num is not None:
            try:
                keyed.append((float(inst_num), idx, p))
                continue
            except (TypeError, ValueError):
                pass

        # Neither available — preserve original order via sentinel
        keyed.append((float("inf"), idx, p))

    keyed.sort(key=lambda t: (t[0], t[1]))
    return [t[2] for t in keyed]


# ---------------------------------------------------------------------------
# 10. select_slices
# ---------------------------------------------------------------------------

def select_slices(
    paths: list[Path], max_slices: int, *, presorted: bool = False
) -> list[Path]:
    """Uniformly sample slices, always including first and last.

    The input is sorted by position unless *presorted* is ``True``.
    If the number of slices is already within *max_slices*, all are returned.
    """
    if max_slices < 1:
        return []

    sorted_paths = paths if presorted else sort_dicom_by_position(paths)
    n = len(sorted_paths)

    if n <= max_slices:
        return sorted_paths

    if max_slices == 1:
        return [sorted_paths[n // 2]]

    # Always include first and last; fill the rest evenly
    indices = set()
    indices.add(0)
    indices.add(n - 1)
    for i in range(1, max_slices - 1):
        idx = int(round(i * (n - 1) / (max_slices - 1)))
        indices.add(idx)

    return [sorted_paths[i] for i in sorted(indices)]


# ---------------------------------------------------------------------------
# 11. group_by_series
# ---------------------------------------------------------------------------

def group_by_series(paths: list[Path]) -> dict[str, list[Path]]:
    """Group DICOM files by SeriesInstanceUID.

    The dictionary key is the SeriesDescription when available,
    otherwise ``series_N`` (N = 1, 2, ...).
    """
    uid_to_paths: dict[str, list[Path]] = {}
    uid_to_desc: dict[str, str] = {}

    for p in paths:
        try:
            ds = pydicom.dcmread(p, force=True, stop_before_pixels=True)
        except Exception:
            uid = "__unreadable__"
            uid_to_paths.setdefault(uid, []).append(p)
            continue

        uid = str(ds.get("SeriesInstanceUID", "__no_uid__"))
        uid_to_paths.setdefault(uid, []).append(p)

        if uid not in uid_to_desc:
            desc = ds.get("SeriesDescription", None)
            if desc:
                uid_to_desc[uid] = str(desc)

    # Build result dict with human-readable keys
    result: dict[str, list[Path]] = {}
    counter = 0
    for uid, file_paths in uid_to_paths.items():
        if uid in uid_to_desc:
            key = uid_to_desc[uid]
        else:
            counter += 1
            key = f"series_{counter}"

        # Handle duplicate series description keys
        base_key = key
        dedup = 2
        while key in result:
            key = f"{base_key}_{dedup}"
            dedup += 1

        result[key] = file_paths

    return result
