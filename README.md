# COCO Annotation Tool

COCO formatındaki etiketli veri kümeleri için doğrulama, analiz ve dikdörtgene dönüştürme aracı. Python ile yazıldı, sağlık alanı segmentasyon verileri başta olmak üzere COCO formatına uyan her veri kümesinde çalışır.

## Özellikler

- JSON dosyasını streaming olarak okur (büyük dosyalarda RAM şişmez)
- Annotation doğruluk kontrolleri (eksik alan, geçersiz polygon, negatif koordinat)
- Polygon alan hesabı (Shoelace formülü)
- Şekil tespiti: dikdörtgen ve polygon ayrımı
- Tüm annotation'ları x ve y'nin min-max değerlerine göre dikdörtgene düzenleme
- Görüntü boyutuna oranlı dinamik tolerans (sigma parametresi)
- Tek dosya veya klasör bazlı toplu işlem
- Klasör modunda toplam özet (gereksiz detay yok)

## Kurulum

Python 3.7 veya üstü gerekir.

```bash
pip install ijson
```

## Kullanım

Tek komut çalıştırıyorsunuz, hem analiz raporu çıkıyor hem de tüm annotation'lar otomatik olarak min-max değerlerine göre dikdörtgene dönüştürülerek yeni bir dosyaya kaydediliyor. Orijinal dosya bozulmuyor.

**Tek dosya:**
```bash
python coco_tool.py annotations.json
```

**Klasör (içindeki tüm JSON dosyaları sırayla işlenir):**
```bash
python coco_tool.py klasor_adi
```

**Sigma parametresi ile:**
```bash
python coco_tool.py annotations.json --sigma 0.002
```

**Yardım menüsü:**
```bash
python coco_tool.py --help
```

## Çıktı Örneği

**Tek dosya:**
```
Klasör : medical_dataset
Dosya  : annotations.json (2.45 MB)

Görüntü sayısı     : 156
Etiketli görüntü   : 145
Toplam annotation  : 225  (geçerli: 225, hatalı: 0)
Şekil dağılımı     : 30 dikdörtgen (13.3%), 195 polygon (86.7%)

Kategoriler (4):
  tumor                :    106 ( 47.1%)
  cyst                 :     55 ( 24.4%)
  calcification        :     46 ( 20.4%)
  necrotic_core        :     18 (  8.0%)

Alan (piksel kare) : ort 7653, min 218, max 35712

Dönüşüm            : 225 annotation min/max ile dikdörtgene düzenlendi
Çıktı dosyası      : annotations_rectangles.json
```

**Klasör:**
```
Klasör             : medical_dataset
Hedef klasör       : medical_dataset_rectangles
Dosya sayısı       : 4

Toplam görüntü     : 471
Etiketli görüntü   : 438
Toplam annotation  : 685  (geçerli: 684, hatalı: 1)
Şekil dağılımı     : 41 dikdörtgen (6.0%), 643 polygon (94.0%)
Farklı kategori    : 6
  calcification, cyst, healthy_tissue, lesion, necrotic_core, tumor
Alan (piksel kare) : ort 8923, min 218, max 490000
Dönüşüm            : 684 annotation min/max ile dikdörtgene düzenlendi
```

## Dönüştürme Mantığı

Her annotation için:
1. Polygon'un tüm noktalarının x ve y koordinatları toplanır
2. x_min, x_max, y_min, y_max hesaplanır
3. Bu 4 değerden 4 köşeli eksen-hizalı dikdörtgen oluşturulur
4. `segmentation`, `bbox` ve `area` alanları güncellenir

Algoritma her tür nokta sayısı için çalışır — 3, 5, 100 nokta fark etmez. Polygon'un boyutlarına göre otomatik olarak ya kare ya dikdörtgen üretir (matematiksel olarak kare de bir dikdörtgendir).

## Sigma Parametresi

Şekil tespiti için kullanılan tolerans, görüntü boyutuna oranlı olarak hesaplanır:

```
tolerance = max(image_width, image_height) * sigma
```

Varsayılan `sigma = 0.001` — yani görüntünün büyük kenarının binde biri kadar tolerans:

| Görüntü boyutu | Tolerans |
|---|---|
| 240×240 | 0.5 piksel (minimum garanti) |
| 1000×1000 | 1.0 piksel |
| 4096×4096 | 4.1 piksel |

Çok küçük görüntülerde sıfıra inmesin diye minimum 0.5 piksel garantisi koyulmuştur. `--sigma` parametresi ile değiştirilebilir.

## Doğruluk Kontrolleri

Her annotation için yapılan kontroller:

- Zorunlu alanlar (`id`, `image_id`, `category_id`, `segmentation`)
- Polygon formatı geçerli mi
- En az 3 nokta var mı
- Segmentation tipi polygon mı (RLE atlanır)

## Bağımlılıklar

- `ijson` — Streaming JSON okuma

## Lisans

MIT License
