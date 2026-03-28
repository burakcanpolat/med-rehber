<div align="center">

<img src="assets/chiron-cover.gif" alt="Med-Guide — Chiron, the Wounded Healer" width="800">

# Med-Guide

**Your AI guide for understanding medical results in plain language.**

Powered by [MedGemma](https://huggingface.co/google/medgemma-1.5-4b-it) | Works with **Zed**, **Cursor**, and **Claude Code**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://python.org)
[![uv](https://img.shields.io/badge/uv-package%20manager-blueviolet.svg)](https://docs.astral.sh/uv/)

---

**[🇬🇧 English](#-what-does-it-do)** | **[🇹🇷 Türkçe](#-turkce)**

</div>

> [!CAUTION]
> **This software is NOT a medical device and is NOT intended to diagnose, treat, cure, or prevent any disease or medical condition.** All outputs are AI-generated, may contain errors, and are provided strictly for educational and informational purposes. **Never use this tool as a substitute for professional medical advice, diagnosis, or treatment.** Always consult a qualified healthcare provider for any medical concerns. Misuse of AI-generated medical information can be dangerous. The authors assume no liability for any decisions made based on this tool's output.
>
> **Bu yazılım tıbbi bir cihaz DEĞİLDİR ve herhangi bir hastalığı teşhis, tedavi veya önleme amacı taşımaz.** Tüm çıktılar yapay zeka tarafından üretilir, hata içerebilir ve yalnızca eğitim ve bilgilendirme amaçlıdır. **Bu aracı profesyonel tıbbi tavsiye, teşhis veya tedavinin yerine asla kullanmayın.** Herhangi bir sağlık sorununuz için mutlaka nitelikli bir sağlık uzmanına başvurun. Yapay zeka tarafından üretilen tıbbi bilgilerin yanlış kullanımı tehlikeli olabilir. Yazarlar, bu aracın çıktılarına dayanarak alınan kararlardan hiçbir sorumluluk kabul etmez.

---

## What Does It Do?

Open this repo in an AI editor, and the assistant will:

1. Ask you to choose your **language** (English or Turkish)
2. Collect basic **patient information** (age, gender, complaint)
3. Analyze images with **MedGemma** (X-ray, CT, MRI, DICOM)
4. Report results in **plain, simple language**
5. Save reports to `reports/`

### Capabilities

| Feature | Description |
|---------|-------------|
| **Radiology Analysis** | X-ray, CT, MRI, and DICOM image interpretation with confidence levels |
| **Lab Results** | Blood work interpretation with normal ranges and pattern detection |
| **Drug Interactions** | Safety checks for drug-drug and drug-food interactions |
| **Symptom Evaluation** | Possible causes, urgency assessment, questions for your doctor |
| **DICOM Support** | Auto-conversion with CT multi-window, MRI normalization, metadata extraction |
| **Series Analysis** | Multi-image comparison, temporal progression, smart slice selection |

---

## Quick Setup

No coding knowledge required. The AI assistant guides you through everything.

### Step 1: Get the project

**Option A — Download ZIP (easiest):**

Go to the repo page → click the green **"Code"** button → **"Download ZIP"** → extract the folder.

**Option B — Git clone:**
```bash
git clone https://github.com/burakcanpolat/med-guide.git
cd med-guide
uv sync
```

### Step 2: Open in an AI editor

| Editor | Download | Best for |
|--------|----------|----------|
| **Zed** (recommended) | [zed.dev/download](https://zed.dev/download) | Free, fast, works with any AI model via OpenRouter |
| **Cursor** | [cursor.com](https://cursor.com) | Built-in AI, familiar VS Code interface |
| **Claude Code** | `npm install -g @anthropic-ai/claude-code` | Terminal-based, most powerful (requires [Node.js](https://nodejs.org)) |

> **Which editor should I choose?** If you've never programmed before, choose **Zed** — it's free and easy to set up. If you already use VS Code, choose **Cursor**. If you're comfortable with the command line, choose **Claude Code**.

> **Important (Zed users):** You need an OpenRouter API key. Get one free at [openrouter.ai/keys](https://openrouter.ai/keys), then add it in Zed: Command Palette → `agent: open settings` → paste your key in the OpenRouter section.

### Step 3: Say "start setup"

Open the AI chat panel in your editor and type:

> **"start setup"**

The AI will guide you through everything step by step:
- uv + Python setup
- Modal account (free, $30/month credit)
- HuggingFace token (free, for AI model access)
- MedGemma deployment
- Your first medical image analysis

### Alternative: Quick prerequisites check

```bash
# macOS / Linux
./setup.sh

# Windows
setup.bat
```

---

## Detailed Setup

<details>
<summary><strong>Zed (Recommended)</strong></summary>

With Zed + OpenRouter you can use **any model** (Claude, Gemini, GPT, Llama...).

1. Install Zed from [zed.dev/download](https://zed.dev/download)
2. Get an OpenRouter API key from [openrouter.ai/keys](https://openrouter.ai/keys)
3. Open Zed → Command Palette → `agent: open settings` → paste your API key
4. Clone and open the repo:
   ```bash
   git clone https://github.com/burakcanpolat/med-guide.git
   cd med-guide
   ```
5. (Optional) Copy the model config:
   ```bash
   cp .zed/settings.json.example .zed/settings.json
   ```
6. Open the Agent Panel and ask: *"Analyze the X-rays in the test folder"*

`CLAUDE.md` is automatically loaded as AI instructions.

</details>

<details>
<summary><strong>Cursor</strong></summary>

1. Install from [cursor.com](https://cursor.com)
2. Clone and open:
   ```bash
   git clone https://github.com/burakcanpolat/med-guide.git
   ```
3. Ready! `.cursor/rules/medgemma.mdc` is loaded automatically.

**Note:** OpenRouter models in Cursor only work in Chat mode. Agent mode requires Cursor Pro.

</details>

<details>
<summary><strong>Claude Code</strong></summary>

```bash
npm install -g @anthropic-ai/claude-code
git clone https://github.com/burakcanpolat/med-guide.git
cd med-guide
uv sync
claude
```

`CLAUDE.md` is read automatically.

</details>

---

## Usage

### With AI Assistant (Recommended)

Ask the AI assistant in your editor:

> "Analyze the X-rays in the test folder"

> "WBC: 12,500, Hb: 9.2, Ferritin: 8 — interpret"

> "Can Aspirin and Warfarin be taken together?"

### From Terminal

```bash
uv run python scripts/medgemma_api.py images/xray.jpeg              # single image
uv run python scripts/medgemma_api.py scan.dcm                      # single DICOM
uv run python scripts/medgemma_api.py images/d0.jpg images/d1.jpg   # multiple images
uv run python scripts/medgemma_api.py archive.zip                   # ZIP archive
```

### Pipeline

```
Patient info → Image/DICOM → scripts/medgemma_api.py → Modal (MedGemma)
  ├── DICOM? → auto-convert to JPEG + extract metadata
  ├── Cold start? → single request + progress feedback (1-3 min)
  ├── Series ≤85 → single request
  └── Series >85 → smart slice selection
        ↓
AI Assistant → Report in your language → reports/
```

---

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MEDGEMMA_ENDPOINT` | Your MedGemma API URL (created during setup) | — (required) |
| `MEDGEMMA_MODEL` | Model name | `google/medgemma-1.5-4b-it` |
| `OPENROUTER_API_KEY` | OpenRouter API key (for Zed / Cursor) | — |
| `MEDGEMMA_VERIFY_SSL` | Set to `false` for corporate proxies | `true` |

Set up automatically by the setup wizard. See `.env.example` for format.

## Editor Compatibility

| File | Claude Code | Zed | Cursor | GitHub Copilot |
|------|:-----------:|:---:|:------:|:--------------:|
| `CLAUDE.md` | ✅ auto | ✅ auto | — | — |
| `AGENTS.md` | — | ✅ auto | ✅ auto | ✅ |
| `.cursor/rules/*.mdc` | — | — | ✅ auto | — |
| `.agents/skills/` | ✅ | ✅ | ✅ | — |

## Skills

| Skill | What It Does |
|-------|-------------|
| `medgemma-radiology` | X-ray, CT, MRI, DICOM image analysis with confidence levels |
| `medgemma-assistant` | Lab results, drug interactions, symptom evaluation |
| `medgemma-setup` | Interactive setup wizard for first-time users |

## Language Support

Med-Guide supports **English** and **Turkish**. On first use, the AI will ask you to choose your language. All reports and communication will be in your chosen language.

Change language anytime by editing `reports/user_config.md`:
```yaml
language: en  # or tr
```

## Project Structure

```
med-guide/
├── CLAUDE.md                         ← Claude Code + Zed instructions
├── AGENTS.md                         ← Universal instructions (Cursor, Zed, Copilot)
├── .cursor/rules/medgemma.mdc        ← Cursor instructions
├── pyproject.toml                    ← Project dependencies (uv)
├── .agents/skills/                   ← Universal Skills (all editors)
│   ├── medgemma-setup/SKILL.md       ← Setup wizard
│   ├── medgemma-radiology/SKILL.md   ← Image analysis
│   └── medgemma-assistant/SKILL.md   ← Lab/drug/symptom
├── skills/                           ← Readable skill files
│   ├── setup-skill.md
│   ├── radiology-skill.md
│   └── medical-assistant-skill.md
├── scripts/
│   ├── medgemma_api.py               ← MedGemma API client
│   ├── dicom_utils.py                ← DICOM processing utilities
│   └── modal_medgemma.py             ← Modal deployment script
├── setup.sh / setup.bat              ← Quick setup scripts
├── .env.example                      ← Environment variable template
├── .zed/settings.json.example        ← Zed config example
├── images/                           ← Place your images here
├── reports/                          ← Reports are saved here
└── test/                             ← Sample test images
```

## Requirements

- [uv](https://docs.astral.sh/uv/) — Python package manager (installed during setup)
- Python 3.10+ (managed by uv)
- Internet connection
- [Modal](https://modal.com/) account (free — $30/month credit)
- [HuggingFace](https://huggingface.co/) account (free — for MedGemma access)

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — [LICENSE](LICENSE)

---

<a name="-turkce"></a>

<div align="center">

## 🇹🇷 Türkçe

**Tıbbi sonuçlarınızı herkesin anlayacağı dile çeviren AI rehberiniz.**

</div>

### Med-Guide Nedir?

Med-Guide, tıbbi görüntü analizi ve klinik yardım için açık kaynak AI skill paketidir. DICOM, JPEG ve PNG formatlarını destekler. **Zed**, **Cursor** ve **Claude Code** ile çalışır.

| Özellik | Açıklama |
|---------|----------|
| **Radyoloji Analizi** | X-ray, BT, MR ve DICOM görüntü yorumlama, güven seviyeleri |
| **Lab Sonuçları** | Kan tahlili yorumlama, normal aralıklar, patern tespiti |
| **İlaç Etkileşimi** | İlaç-ilaç ve ilaç-besin güvenlik kontrolleri |
| **Semptom Değerlendirme** | Olası nedenler, aciliyet değerlendirmesi, doktora sorulacaklar |
| **DICOM Desteği** | BT çoklu pencere, MR normalizasyon, metadata çıkarma ile otomatik dönüşüm |

### Hızlı Başlangıç

#### Zed + OpenRouter (Önerilen)

1. [Zed](https://zed.dev/download) kurun
2. [OpenRouter](https://openrouter.ai/keys) adresinden API key alın (ücretsiz)
3. Zed'de: Command Palette → `agent: open settings` → OpenRouter bölümüne API key yapıştırın
4. Klonlayın ve açın:
   ```bash
   git clone https://github.com/burakcanpolat/med-guide.git
   cd med-guide
   ```
5. Agent Panel'i açın ve yazın: *"kurulum başlat"*

#### Claude Code

```bash
npm install -g @anthropic-ai/claude-code
git clone https://github.com/burakcanpolat/med-guide.git
cd med-guide && uv sync && claude
```

#### Cursor

1. [cursor.com](https://cursor.com) adresinden kurun
2. Repoyu klonlayın ve Cursor'da açın
3. Hazır! `.cursor/rules/medgemma.mdc` otomatik yüklenir.

### Kullanım

AI asistanına sorun:

> *"Test klasöründeki X-ray'leri analiz et"*

> *"WBC: 12.500, Hb: 9.2, Ferritin: 8 — yorumla"*

> *"Aspirin ve Warfarin birlikte alınabilir mi?"*

### Dil Desteği

Med-Guide **İngilizce** ve **Türkçe** destekler. İlk kullanımda AI size dil tercihinizi soracak. Tüm raporlar ve iletişim seçtiğiniz dilde olacak.

Dil tercihinizi değiştirmek için `reports/user_config.md` dosyasını düzenleyin:
```yaml
language: tr  # veya en
```

### Katkıda Bulunma

Katkılarınızı bekliyoruz! Rehber için [CONTRIBUTING.md](CONTRIBUTING.md) dosyasına bakın.

---

<div align="center">

**⚠️ Disclaimer / Sorumluluk Reddi**

These tools are for educational and informational purposes only. Always consult a healthcare professional for diagnosis and treatment.

Bu araçlar yalnızca eğitim ve bilgilendirme amaçlıdır. Kesin tanı ve tedavi için mutlaka bir sağlık uzmanına başvurun.

</div>
