# MedGemma Skills

Google'ın açık kaynak tıbbi AI modeli [MedGemma](https://huggingface.co/google/medgemma-1.5-4b-it) için hazır skill paketi.

## Ne Yapıyor?

Bu repo'yu bir AI IDE'de (Cursor, Claude Code, Antigravity) açtığınızda, AI asistanınız:
1. Sizden **hasta bilgisi** alır (yaş, cinsiyet, şikayet)
2. Görüntüleri **MedGemma** ile analiz eder
3. Sonuçları **herkesin anlayacağı sade Türkçe** ile raporlar
4. Raporları `reports/` klasörüne kaydeder

## Yapı

```
medgemma-skills/
├── CLAUDE.md                      ← Claude Code talimatları
├── .cursor/rules/medgemma.mdc    ← Cursor talimatları
├── scripts/
│   └── medgemma_api.py            ← MedGemma API client (max 85 görüntü/istek)
├── skills/
│   ├── radiology-skill.md         ← Görüntü analizi
│   └── medical-assistant-skill.md ← Lab, ilaç, semptom
├── images/                        ← Görsellerinizi buraya atın
├── reports/                       ← Raporlar buraya kaydedilir
└── sample-xrays/                  ← Test görselleri
    ├── normal/
    ├── pneumonia/
    └── temporal/
```

## Hızlı Başlangıç

```bash
git clone https://github.com/burakcanpolat/medgemma-skills.git
```

IDE'de açın, AI asistana sorun:

> "sample-xrays klasöründeki X-ray'leri analiz et"

> "WBC: 12.500, Hb: 9.2, Ferritin: 8 — yorumla"

## Terminal

```bash
python scripts/medgemma_api.py images/xray.jpeg
python scripts/medgemma_api.py images/a.jpg images/b.jpg images/c.jpg
python scripts/medgemma_api.py gorseller.zip
```

## Pipeline

```
Hasta bilgisi → Görüntü → scripts/medgemma_api.py → Modal (MedGemma)
  ├── Seri ≤85 → tek istek
  └── Seri >85 → 85'lik batch
        ↓
AI Asistan → Türkçe rapor → reports/
```

## Gereksinimler

- Python 3.8+ (sadece stdlib)
- İnternet bağlantısı

## Lisans

MIT

---

⚠️ Bu araçlar eğitim ve bilgilendirme amaçlıdır. Kesin tanı ve tedavi için doktora başvurun.
