"""
MedGemma API Client — Unified
Modal üzerinde deploy edilmiş MedGemma modeline görüntü gönderir.
ZIP smart-routing, series detection, batch processing ve JSON rapor kaydını içerir.

Modal config: --limit-mm-per-prompt image=85 (tek istekte max 85 görüntü)
"""

import base64
import json
import sys
import zipfile
import urllib.request
import ssl
import datetime
from pathlib import Path

# Windows'ta UTF-8 çıktı için
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ENDPOINT = "https://burakcanpolat--medgemma-vllm-serve.modal.run/v1/chat/completions"
MODEL = "google/medgemma-1.5-4b-it"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

MAX_IMAGES_PER_REQUEST = 85  # Modal vLLM config: --limit-mm-per-prompt image=85


# ---------------------------------------------------------------------------
# SSL context
# ---------------------------------------------------------------------------

def _ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def analyze_image(image_path: str | Path,
                  prompt: str = "Analyze this medical image. Provide detailed findings.") -> str:
    """Tek bir görüntüyü MedGemma ile analiz eder."""
    path = Path(image_path)
    if not path.exists():
        return f"HATA: Dosya bulunamadi: {image_path}"

    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode()

    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
        ]}],
        "max_tokens": 1024,
        "temperature": 0,
    }).encode()

    req = urllib.request.Request(
        ENDPOINT, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=300, context=_ssl_ctx()) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"HATA: MedGemma API hatasi: {e}"


def analyze_multiple(image_paths: list[str | Path],
                     prompt: str = "Compare these medical images. Analyze progression.") -> str:
    """Birden fazla görüntüyü tek istekte MedGemma'ya gönderir (max 85)."""
    content: list[dict] = [{"type": "text", "text": prompt}]

    for p in image_paths:
        path = Path(p)
        if not path.exists():
            return f"HATA: Dosya bulunamadi: {p}"
        mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        b64 = base64.b64encode(path.read_bytes()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 2048,
        "temperature": 0,
    }).encode()

    req = urllib.request.Request(
        ENDPOINT, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=600, context=_ssl_ctx()) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"HATA: MedGemma API hatasi: {e}"


# ---------------------------------------------------------------------------
# ZIP extraction
# ---------------------------------------------------------------------------

def extract_zip(zip_path: str | Path) -> tuple[list[Path], Path]:
    """ZIP dosyasini images/temp/{zip_name}/ altina cikarir."""
    zip_path = Path(zip_path)
    out = Path("images") / "temp" / zip_path.stem
    out.mkdir(parents=True, exist_ok=True)

    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if Path(name).suffix.lower() in IMAGE_EXTENSIONS and not name.startswith("__MACOSX"):
                zf.extract(name, out)
                extracted.append(out / name)

    extracted.sort()
    print(f"[ZIP] {len(extracted)} goruntu cikarildi -> {out}")
    return extracted, out


# ---------------------------------------------------------------------------
# Series detection
# ---------------------------------------------------------------------------

def detect_series(image_paths: list[Path], extraction_root: Path) -> dict[str, list[Path]]:
    """
    Görüntüleri seriye göre gruplar.
    - Alt klasörler varsa: her alt klasör = bir seri
    - Alt klasör yoksa: tüm dosyalar tek seri
    """
    subdirs: dict[str, list[Path]] = {}
    flat: list[Path] = []

    for p in image_paths:
        rel = p.relative_to(extraction_root)
        parts = rel.parts
        if len(parts) > 1:
            series_name = parts[0]
            subdirs.setdefault(series_name, []).append(p)
        else:
            flat.append(p)

    if subdirs:
        # Flat dosyalar varsa onları da ayrı seri olarak ekle
        if flat:
            subdirs["_diger"] = sorted(flat)
        return {k: sorted(v) for k, v in subdirs.items()}

    # Alt klasör yok → tek seri
    return {"tum_gorseller": sorted(image_paths)}


# ---------------------------------------------------------------------------
# Seri analizi — her seri kendi içinde bağımsız
# ---------------------------------------------------------------------------

def analyze_series(series_name: str, images: list[Path]) -> dict:
    """
    Tek bir seriyi analiz eder.
    - ≤85 görüntü → hepsini tek istekte gönder (Modal max: 85)
    - >85 görüntü → 85'lik batch'lere böl
    """
    total = len(images)
    print(f"\n{'='*60}")
    print(f"  SERİ: {series_name} ({total} goruntu)")
    print(f"{'='*60}")

    series_result = {
        "series_name": series_name,
        "total_images": total,
        "batches": [],
    }

    if total <= MAX_IMAGES_PER_REQUEST:
        # Tek istekte hepsini gönder
        print(f"  -> Tek istekte {total} goruntu gonderiliyor...")
        prompt = (
            f"These are {total} consecutive medical imaging slices from the same series. "
            "Analyze the complete series: describe the imaging modality, body region, "
            "and all notable findings across the entire series. "
            "Note any progression or changes between slices."
        )
        answer = analyze_multiple(images, prompt)
        print(f"  -> Sonuc: {answer[:200]}...")
        series_result["batches"].append({
            "batch": 1,
            "image_count": total,
            "images": [p.name for p in images],
            "analysis": answer,
        })
    else:
        # 85'lik batch'lere böl
        batches = [images[i:i + MAX_IMAGES_PER_REQUEST]
                   for i in range(0, total, MAX_IMAGES_PER_REQUEST)]
        print(f"  -> {len(batches)} batch ({MAX_IMAGES_PER_REQUEST}'lik gruplar)")

        for idx, batch in enumerate(batches, 1):
            print(f"\n  [BATCH {idx}/{len(batches)}] {len(batch)} goruntu...")
            prompt = (
                f"These are medical imaging slices {(idx-1)*MAX_IMAGES_PER_REQUEST + 1}"
                f"-{(idx-1)*MAX_IMAGES_PER_REQUEST + len(batch)} "
                f"from a series of {total} total slices. "
                "Describe the imaging modality, body region, and key findings in this segment."
            )
            answer = analyze_multiple(batch, prompt)
            print(f"  -> Sonuc: {answer[:160]}...")
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
    """Sonuçları reports/ altına zaman damgalı JSON olarak kaydeder."""
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    out = reports_dir / f"{safe_label}_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[RAPOR] Kaydedildi: {out}")
    return out


# ---------------------------------------------------------------------------
# Smart ZIP dispatcher
# ---------------------------------------------------------------------------

def process_zip(zip_path: str | Path) -> dict:
    """
    ZIP'i çıkart, serilere ayır, her seriyi bağımsız analiz et.
    Her seri kendi içinde: ≤85 → tek istek, >85 → 85'lik batch'ler.
    """
    images, extraction_root = extract_zip(zip_path)
    total = len(images)

    if total == 0:
        print("HATA: ZIP icinde goruntu dosyasi bulunamadi.")
        return {}

    zip_label = Path(zip_path).stem

    # Serilere ayır
    series_map = detect_series(images, extraction_root)
    print(f"\n[PLAN] {total} goruntu, {len(series_map)} seri tespit edildi:")
    for name, imgs in series_map.items():
        batches_needed = (len(imgs) + MAX_IMAGES_PER_REQUEST - 1) // MAX_IMAGES_PER_REQUEST
        mode = "tek istek" if len(imgs) <= MAX_IMAGES_PER_REQUEST else f"{batches_needed} batch"
        print(f"  - {name}: {len(imgs)} goruntu ({mode})")

    # Her seriyi bağımsız analiz et
    results = {
        "zip_file": str(zip_path),
        "total_images": total,
        "total_series": len(series_map),
        "series": {},
    }

    for series_name, series_images in series_map.items():
        series_result = analyze_series(series_name, series_images)
        results["series"][series_name] = series_result

    save_report(results, label=zip_label)
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanim:")
        print("  python medgemma_api.py goruntu.jpeg")
        print("  python medgemma_api.py goruntu1.jpg goruntu2.jpg goruntu3.jpg")
        print("  python medgemma_api.py gorseller.zip")
        sys.exit(1)

    input_path = sys.argv[1]

    if input_path.lower().endswith(".zip"):
        process_zip(input_path)
    else:
        paths = sys.argv[1:]
        if len(paths) == 1:
            print(f"[TEK GORUNTU] {paths[0]}")
            result = analyze_image(paths[0])
            print(result)
            save_report({"mode": "single", "image": paths[0], "analysis": result},
                        label=Path(paths[0]).stem)
        else:
            print(f"[COKLU GORUNTU] {len(paths)} dosya")
            result = analyze_multiple(paths)
            print(result)
            save_report({"mode": "multiple", "images": paths, "analysis": result},
                        label="multi_image")
