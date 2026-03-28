# Med-Rehber

Medical image analysis and general medical assistant project.

## Language Preference

At the start of every conversation, check `reports/user_config.md`.

- If the file exists and contains a `language:` field → use that language for all interactions.
- If the file does not exist:
  1. Ask:
     ```
     🌐 Please choose your language / Lütfen dilinizi seçin:

     1. 🇬🇧 English
     2. 🇹🇷 Türkçe
     ```
  2. Save the choice to `reports/user_config.md`:
     ```
     language: en
     ```
     (or `language: tr`)
  3. Confirm in the chosen language and proceed.

**All subsequent communication, reports, and analysis output MUST be in the user's chosen language.**

## First-Run Check

After setting the language, check if the `.env` file exists. If it doesn't:
1. Tell the user (in their chosen language): "Welcome! This looks like your first time. Shall we set things up together?"
2. If they agree, read `skills/setup-skill.md` and start the setup wizard
3. Do not perform any analysis until setup is complete

If the user says "setup", "install", "kurulum", "get started", "start setup" → read and apply `skills/setup-skill.md`.
If the user says "help", "yardım" → read the HELP COMMAND section from `.agents/skills/medgemma-setup/SKILL.md`.
If the user says "test", "connection test", "bağlantı testi" → run a test analysis with a sample image.
If the user says "settings", "ayarlar" → show the contents of `.env`.

## Skill Routing

| User says / provides | Skill to apply |
|----------------------|----------------|
| "setup", "install", "kurulum", "get started" | `skills/setup-skill.md` |
| Medical images (X-ray, CT, MRI, DICOM files) | `skills/radiology-skill.md` |
| `.dcm` file, ZIP with DICOM, "analyze this scan" | `skills/radiology-skill.md` |
| Lab results, blood work, medications, symptoms | `skills/medical-assistant-skill.md` |
| Drug interactions, medical report text | `skills/medical-assistant-skill.md` |

## Patient Intake

Only AFTER setup is complete and `.env` exists. Before any analysis, collect the following from the user (ask one at a time, in their language):

1. **Who is this report for?** (themselves / a relative / general information)
2. **Age and gender**
3. **Complaint/reason** — "Why was this test done?"
4. **Known medical conditions** (if any)
5. **Current medications** (if any)

Save this to `reports/patient_info.md`. On subsequent analyses, read this file — do not ask again.
Always use the filename `patient_info.md` (in English) regardless of the user's language preference.

If emergency signs are present → stop intake, recommend calling emergency services (112 in Turkey, or local number).

## MedGemma Pipeline

For image analysis, use `scripts/medgemma_api.py`:

```bash
python3 scripts/medgemma_api.py images/xray.jpeg              # single image
python3 scripts/medgemma_api.py scan.dcm                      # single DICOM
python3 scripts/medgemma_api.py images/d0.jpg images/d1.jpg   # multiple images
python3 scripts/medgemma_api.py archive.zip                   # ZIP archive (JPEG, DICOM, or mixed)
```

DICOM files (.dcm) are automatically converted to JPEG with appropriate windowing before analysis.
All images are sent as base64-encoded data inline in the request.

**Cold start handling:** On first request, the script sends a single readiness check with a long timeout (no polling). If the Modal container is cold-starting, progress messages are shown locally while waiting. Typically takes 1-3 minutes.

Each series is independent: ≤85 images → single request, >85 → batched in groups of 85.
MedGemma outputs in English → translate findings into the user's chosen language in plain, simple terms.

## Modal Deployment

The MedGemma server runs on Modal. Deploy script: `scripts/modal_medgemma.py`.

```bash
modal deploy scripts/modal_medgemma.py
```

This creates:
- `medgemma-vllm` app with vLLM + MedGemma model
- `medgemma-hf-cache` volume for model weights (avoids re-download)
- `vllm-cache` volume for compilation cache (faster subsequent cold starts)

## Report Saving

The script automatically saves raw JSON results (e.g., `reports/xray_20260327_143022.json`).
You should additionally write a human-readable report as `reports/YYYY-MM-DD_short-description_report.md` using the findings from the JSON output.

## Language & Style

Use simple, plain language that anyone can understand — in the user's chosen language.
If medical terms are needed, explain them in parentheses.
