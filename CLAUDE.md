# MedGemma Skills

Tıbbi görüntü analizi ve genel tıbbi asistanlık projesi.

## Hasta Bilgisi Toplama (Intake)

Analiz yapmadan ÖNCE, kullanıcıdan şu bilgileri al (tek tek sor):

1. **Bu rapor kimin için?** (kendisi / yakını / genel bilgi)
2. **Yaş ve cinsiyet**
3. **Şikayet/neden** — "Neden bu tetkik yapıldı?"
4. **Bilinen hastalıklar** (varsa)
5. **Kullanılan ilaçlar** (varsa)

Bu bilgileri `reports/hasta_bilgisi.md` dosyasına kaydet. Sonraki analizlerde bu dosyayı oku — tekrar sorma.

Acil durum belirtisi varsa → intake'i kes, 112'yi öner.

## Skill Yönlendirme

- **Tıbbi görüntü** → `skills/radiology-skill.md`
- **Lab, ilaç, semptom** → `skills/medical-assistant-skill.md`

## MedGemma Pipeline

Görüntü analizi için `scripts/medgemma_api.py` kullan:

```
python scripts/medgemma_api.py images/xray.jpeg
python scripts/medgemma_api.py images/d0.jpg images/d1.jpg
python scripts/medgemma_api.py gorseller.zip
```

Her seri bağımsız: ≤85 → tek istek, >85 → 85'lik batch. MedGemma İngilizce çıktı verir → sen Türkçe sade rapora dönüştür.

## Rapor Kaydetme

`reports/YYYY-MM-DD_kisa-aciklama_rapor.md` formatında kaydet.

## Dil

Türkçe, sade, herkesin anlayacağı. Tıbbi terim gerekirse parantez içinde açıkla.
