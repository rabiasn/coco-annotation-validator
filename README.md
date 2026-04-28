[README (2).md](https://github.com/user-attachments/files/27177682/README.2.md)
# coco-annotation-validator
COCO formatındaki etiketli veri için doğrulama ve alan analiz scripti (Python)
# COCO Annotation Validator

COCO formatındaki etiketli veri kümeleri için doğrulama ve alan analiz aracı. Python ile yazıldı, sağlık alanı segmentasyon verileri başta olmak üzere COCO formatına uyan her veri kümesinde çalışır.

## Özellikler

- JSON dosyasını streaming olarak okur (büyük dosyalarda RAM şişmez)
- Annotation doğruluk kontrolleri (eksik alan, geçersiz polygon, negatif koordinat, sınır dışı, self-intersecting)
- Polygon alan hesabı (Shoelace formülü)
- Bounding box boyut bilgisi
- En büyük alanlı annotation'ları sıralı listeleme
- Veri kalitesi uyarıları (area mismatch, outlier tespiti)
- Tek dosya veya klasör bazlı toplu analiz desteği
- Klasör modunda dosyalar arası karşılaştırma tablosu

## Kurulum

Python 3.7 veya üstü gerekir.

```bash
pip install ijson
pip install shapely
```

`shapely` opsiyoneldir — kurulu değilse self-intersecting polygon kontrolü atlanır, scriptin geri kalanı çalışmaya devam eder.

## Kullanım

**Tek dosya analizi:**
```bash
python coco_validator.py annotations.json
```

**Klasör analizi (içindeki tüm JSON dosyaları sırayla işlenir):**
```bash
python coco_validator.py klasor_adi
```

**En büyük 10 annotation'ı göstermek:**
```bash
python coco_validator.py annotations.json --top 10
```

**Yardım menüsü:**
```bash
python coco_validator.py --help
```

## Çıktı Örneği

```
======================================================================
Klasör: medical_dataset
Dosya : train_annotations.json (2.45 MB)
======================================================================
   → 156 görüntü bulundu
   → 4 kategori: ['tumor', 'cyst', 'calcification', 'necrotic_core']

Görüntüler:
  Toplam görüntü     : 156
  Etiketli görüntü   : 145
  Hatalı görüntü     : 5

Annotation:
  Toplam             : 225
  Geçerli            : 220
  Hatalı             : 5

EN BÜYÜK 5 ALANLI ETİKET:
...
```

## Doğruluk Kontrolleri

Her annotation için yapılan kontroller:

- Zorunlu alanlar (`id`, `image_id`, `category_id`, `segmentation`)
- Polygon formatı geçerli mi
- En az 3 nokta var mı
- Koordinatlar negatif değil mi
- Görüntü sınırları içinde mi
- Self-intersecting (kendini kesen) polygon var mı

Veri seti seviyesinde:

- Duplicate annotation id tespiti
- Orphan annotation (var olmayan görüntüye referans) tespiti
- Kategori dağılımı analizi

## Veri Kalitesi Uyarıları

- **Area mismatch:** JSON'daki `area` ile Shoelace ile hesaplanan alan arasında %10'dan fazla fark
- **Çok büyük annotation:** Görüntünün %90'ından fazlasını kaplayan etiketler
- **Çok küçük annotation:** 10 piksel kareden küçük etiketler

## Bağımlılıklar

- `ijson` — Streaming JSON okuma
- `shapely` (opsiyonel) — Self-intersecting polygon kontrolü

## Lisans

MIT License
