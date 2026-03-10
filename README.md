# MedGemma Skills

Google'ın açık kaynak tıbbi AI modeli [MedGemma](https://huggingface.co/google/medgemma-1.5-4b-it) için hazır skill dosyaları. Claude Desktop, ChatGPT veya herhangi bir LLM ile kullanılabilir.

## Ne İşe Yarar?

Bir LLM'e "skill" (özel talimat) ekleyerek onu **tıbbi görüntü analizi** ve **genel tıbbi asistanlık** konusunda uzmanlaştırabilirsiniz. Teknik bilgi gerekmez.

## Yapı

```
medgemma-skills/
├── skills/
│   ├── radiology-skill.md         ← Tıbbi görüntü analizi (X-ray, CT, MRI)
│   └── medical-assistant-skill.md ← Lab sonuçları, ilaç, semptom
├── images/                        ← Kendi görsellerinizi buraya atın
└── sample-xrays/                  ← Test için örnek görseller
    ├── normal/                    ← 3 normal göğüs X-ray
    ├── pneumonia/                 ← 2 pnömoni X-ray
    └── temporal/                  ← 3 günlük progresyon serisi
```

## Hızlı Başlangıç

### Claude Desktop / Cowork

1. Bu repo'yu klonlayın veya ZIP olarak indirin
2. Claude Desktop'ta **Projects** > yeni proje oluşturun
3. `skills/` klasöründeki `.md` dosyalarını projeye **Custom Instructions** olarak ekleyin
4. Görsellerinizi `images/` klasörüne koyun
5. Claude'a sorun: *"images klasöründeki görselleri analiz et"*

### ChatGPT

1. `skills/medical-assistant-skill.md` dosyasını açın
2. İçeriği kopyalayın
3. ChatGPT > **Customize ChatGPT** > **Custom Instructions** alanına yapıştırın

### Diğer LLM'ler (Gemini, Copilot, Mistral...)

1. `skills/` klasöründeki istediğiniz skill dosyasını açın
2. İçeriği kopyalayın
3. İlgili platformun system prompt / custom instruction alanına yapıştırın

## Örnek Kullanım

### Radyoloji
> "images klasöründeki X-ray'i analiz et"

> "sample-xrays/temporal klasöründeki 3 görseli karşılaştır, hastalık progresyonunu değerlendir"

> "Bu ZIP dosyasını aç ve içindeki görselleri incele"

### Tıbbi Asistan
> "WBC: 12.500, Hb: 9.2, MCV: 68, Ferritin: 8 — bu değerleri yorumla"

> "Metformin 1000mg, Ramipril 5mg, Aspirin 100mg kullanıyorum. Etkileşim var mı?"

## Örnek Görseller

`sample-xrays/` klasöründe test için hazır görseller bulunur:

| Klasör | İçerik | Kaynak |
|--------|--------|--------|
| `normal/` | 3 normal göğüs X-ray | Kaggle COVID-19 X-ray Dataset |
| `pneumonia/` | 2 pnömoni X-ray | Kaggle COVID-19 X-ray Dataset |
| `temporal/` | 3 günlük progresyon serisi | Kaggle COVID-19 X-ray Dataset |

## Sorumluluk Reddi

⚠️ Bu araçlar **eğitim ve bilgilendirme amaçlıdır**. Kesin tanı ve tedavi kararları için mutlaka uzman hekime başvurun. FDA onaylı bir tıbbi cihaz değildir.

## Lisans

MIT
