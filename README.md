# Med-Rehber

Your AI guide for understanding medical results in plain language. Powered by [MedGemma](https://huggingface.co/google/medgemma-1.5-4b-it). Works with **Zed**, **Cursor**, and **Claude Code**.

> **Türkçe:** Tıbbi sonuçlarınızı herkesin anlayacağı dile çeviren AI rehberiniz. MedGemma destekli. Zed, Cursor ve Claude Code ile çalışır. [Türkçe kurulum](#turkce-kurulum)

---

## What Does It Do?

When you open this repo in an AI editor, the AI assistant will:
1. Ask you to choose your **language** (English or Turkish)
2. Collect **patient information** (age, gender, complaint)
3. Analyze images with **MedGemma**
4. Report results in **plain, simple language** in your chosen language
5. Save reports to `reports/`

## Project Structure

```
med-rehber/
├── CLAUDE.md                         ← Claude Code + Zed instructions
├── AGENTS.md                         ← Universal instructions (Cursor, Zed, Copilot)
├── .cursor/rules/medgemma.mdc        ← Cursor instructions
├── .gitattributes                    ← Cross-platform line ending rules
├── .agents/skills/                   ← Universal Skills (all editors)
│   ├── medgemma-setup/SKILL.md       ← Setup wizard skill
│   ├── medgemma-radiology/SKILL.md   ← Image analysis skill
│   └── medgemma-assistant/SKILL.md   ← Lab/drug/symptom skill
├── skills/                           ← Readable skill files
│   ├── setup-skill.md
│   ├── radiology-skill.md
│   └── medical-assistant-skill.md
├── scripts/
│   ├── medgemma_api.py               ← MedGemma API client
│   ├── dicom_utils.py                ← DICOM to JPEG conversion & metadata extraction
│   └── modal_medgemma.py             ← Modal deployment script
├── setup.sh                          ← Setup script (macOS/Linux)
├── setup.bat                         ← Setup script (Windows)
├── .zed/settings.json.example        ← Zed + OpenRouter config example
├── .env.example                      ← Environment variable template
├── LICENSE                           ← MIT License
├── images/                           ← Place your images here
├── reports/                          ← Reports are saved here
└── test/
    ├── sample-xrays.zip              ← Test images archive
    └── sample-xrays/                 ← Test images
        ├── normal/                   ← 3 normal X-rays
        ├── pneumonia/                ← 2 pneumonia X-rays
        └── temporal/                 ← 3 temporal series
```

---

## Quick Setup

No coding knowledge required. The AI assistant guides you through everything.

### Step 1: Get the project

**Option A — Download ZIP (easiest):**
Go to https://github.com/burakcanpolat/med-rehber → click the green **"Code"** button → **"Download ZIP"** → extract the folder. The extracted folder will be named `med-rehber-main` — open this folder in your editor.

**Option B — Git clone:**
```bash
git clone https://github.com/burakcanpolat/med-rehber.git
```

### Step 2: Open in an AI editor

Download one of these editors and open the med-rehber folder:

| Editor | Download | Best for |
|--------|----------|----------|
| **Zed** (recommended) | [zed.dev/download](https://zed.dev/download) | Free, fast, works with any AI model via OpenRouter |
| **Cursor** | [cursor.com](https://cursor.com) | Built-in AI, familiar VS Code interface |
| **Claude Code** | `npm install -g @anthropic-ai/claude-code` | Terminal-based, most powerful (requires [Node.js](https://nodejs.org)) |

> **Which editor should I choose?** If you've never programmed before, choose **Zed** — it's free and easy to set up. If you already use VS Code, choose **Cursor**. If you're comfortable with the command line, choose **Claude Code**.

> **Important (Zed users):** Before you can chat with the AI, you need an OpenRouter API key. Get one free at [openrouter.ai/keys](https://openrouter.ai/keys), then add it in Zed: Command Palette → `agent: open settings` → paste your key in the OpenRouter section.

### Step 3: Say "start setup"

Open the AI chat panel in your editor and type:

> **"start setup"**

The AI will guide you through everything step by step:
- Python installation
- Modal account (free, $30/month credit)
- HuggingFace token (free, for AI model access)
- MedGemma deployment
- Your first medical image analysis

### Alternative: Quick prerequisites check

If you prefer to check prerequisites before opening an editor:

**macOS / Linux:** `./setup.sh`
**Windows:** `setup.bat`

These scripts check Python and Modal CLI, then point you to an AI editor for the full setup.

---

## Detailed Setup

### Zed (Recommended)

With Zed + OpenRouter you can use **any model** (Claude, Gemini, GPT, Llama...).

**1. Install Zed**
- [zed.dev/download](https://zed.dev/download) (macOS, Linux, Windows)

**2. Get an OpenRouter API key**
- [openrouter.ai/keys](https://openrouter.ai/keys) — free account + API key

**3. Add API key to Zed**
- Open Zed → Command Palette → `agent: open settings`
- Paste your API key in the OpenRouter section
- Or: set the `OPENROUTER_API_KEY` environment variable

**4. Open the repo**
```bash
git clone https://github.com/burakcanpolat/med-rehber.git
cd med-rehber
```
Open the folder in Zed. `CLAUDE.md` is automatically loaded as AI instructions.

**5. (Optional) Model setting**
```bash
cp .zed/settings.json.example .zed/settings.json
```
Default model: Claude Sonnet 4. Edit `settings.json` to change.

**6. Start using**
Open the Agent Panel and ask:
> "Analyze the X-rays in the test folder"

---

### Cursor

**1.** Install from [cursor.com](https://cursor.com)

**2.** Clone the repo and open in Cursor:
```bash
git clone https://github.com/burakcanpolat/med-rehber.git
```

**3.** Ready! `.cursor/rules/medgemma.mdc` is loaded automatically (`alwaysApply: true`).

**Note:** OpenRouter models in Cursor only work in Chat mode. Agent mode requires Cursor Pro subscription.

---

### Claude Code

```bash
npm install -g @anthropic-ai/claude-code
git clone https://github.com/burakcanpolat/med-rehber.git
cd med-rehber
claude
```

Ready! `CLAUDE.md` is read automatically.

---

## Usage

### With AI Assistant (Recommended)

Ask the AI assistant in your editor:

> "Analyze the X-rays in the test folder"

> "WBC: 12,500, Hb: 9.2, Ferritin: 8 — interpret"

> "Can Aspirin and Warfarin be taken together?"

### From Terminal

```bash
python3 scripts/medgemma_api.py images/xray.jpeg              # single image
python3 scripts/medgemma_api.py scan.dcm                      # single DICOM
python3 scripts/medgemma_api.py images/d0.jpg images/d1.jpg   # multiple images
python3 scripts/medgemma_api.py archive.zip                   # ZIP archive (JPEG, DICOM, or mixed)
```

> DICOM files (.dcm) are automatically converted to JPEG with appropriate windowing before analysis. All images are sent as base64-encoded data inline in the request. Cold starts are handled automatically with progress feedback (typically 1-3 minutes).

### Pipeline

```
Patient info → Image/DICOM → scripts/medgemma_api.py → Modal (MedGemma)
  ├── DICOM? → auto-convert to JPEG + extract metadata
  ├── Cold start? → single request + progress feedback
  ├── Series ≤85 → single request
  └── Series >85 → smart slice selection
        ↓
AI Assistant → Report in your language → reports/
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MEDGEMMA_ENDPOINT` | Your MedGemma API URL (created during setup) | — (required) |
| `MEDGEMMA_MODEL` | Model name | `google/medgemma-1.5-4b-it` |
| `OPENROUTER_API_KEY` | OpenRouter API key (for Zed / Cursor) | — |
| `MEDGEMMA_VERIFY_SSL` | Set to `false` for corporate proxies | `true` |

These are set up automatically by the setup wizard. See `.env.example` for format.

## Editor Compatibility Matrix

| File | Claude Code | Zed | Cursor | GitHub Copilot |
|------|:-----------:|:---:|:------:|:--------------:|
| `CLAUDE.md` | ✅ auto | ✅ auto | — | — |
| `AGENTS.md` | — | ✅ auto | ✅ auto | ✅ |
| `.cursor/rules/*.mdc` | — | — | ✅ auto | — |
| `.agents/skills/` | ✅ | ✅ | ✅ | — |

## Skills

| Skill | What It Does |
|-------|-------------|
| `medgemma-radiology` | X-ray, CT, MRI image analysis, confidence levels |
| `medgemma-assistant` | Lab results, drug interactions, symptom evaluation |
| `medgemma-setup` | Setup wizard for first-time users |

## Language Support

Med-Rehber supports **English** and **Turkish**. On first use, the AI will ask you to choose your language. All reports and communication will be in your chosen language. You can change your language preference by editing `reports/user_config.md`.

## Requirements

- Python 3.10+
- Internet connection
- Modal account (free — $30/month credit, created during setup)
- HuggingFace account (free — needed to access MedGemma model)
- Modal CLI (installed during setup: `uv tool install modal`)
- pydicom, numpy, Pillow (installed during setup — needed for DICOM support)

## License

MIT — [LICENSE](LICENSE)

---

<a name="turkce-kurulum"></a>

## Türkçe Kurulum

**Med-Rehber** tıbbi görüntü analizi ve klinik yardım için açık kaynak AI skill paketidir. DICOM, JPEG ve PNG formatlarını destekler. **Zed**, **Cursor** ve **Claude Code** ile çalışır.

### Hızlı Başlangıç (Zed + OpenRouter)

1. [Zed](https://zed.dev/download) kurun
2. [OpenRouter](https://openrouter.ai/keys) adresinden API key alın
3. Zed'de: Command Palette → `agent: open settings` → OpenRouter bölümüne API key yapıştırın
4. Klonlayın ve açın:
   ```bash
   git clone https://github.com/burakcanpolat/med-rehber.git
   ```
5. Agent Panel'i açın ve sorun: *"Test klasöründeki X-ray'leri analiz et"*

### Hızlı Başlangıç (Claude Code)

```bash
git clone https://github.com/burakcanpolat/med-rehber.git
cd med-rehber && claude
```

### Dil Desteği

Med-Rehber **İngilizce** ve **Türkçe** destekler. İlk kullanımda AI size dil tercihinizi soracak. Tüm raporlar ve iletişim seçtiğiniz dilde olacak. Dil tercihinizi değiştirmek için `reports/user_config.md` dosyasını düzenleyin.

---

⚠️ **Disclaimer / Sorumluluk Reddi:** These tools are for educational and informational purposes only. Always consult a healthcare professional for diagnosis and treatment. / Bu araçlar eğitim ve bilgilendirme amaçlıdır. Kesin tanı ve tedavi için doktora başvurun.
