# COCO Annotation Tool

Staj çalışmamda COCO JSON dosyalarını kontrol etmek ve polygon anotasyonlarını dikdörtgene dönüştürmek için hazırladığım Python aracı.

## Özellikler

- Büyük JSON listelerini `ijson` ile kayıt kayıt okur ve çıktıyı aynı şekilde yazar. Görüntü kimlikleri ve boyutları ile kategori bilgileri bellekte tutulur.
- Eksik zorunlu alan, polygon formatı ve nokta sayısı kontrolleri
- Polygon alan hesabı (Shoelace formülü)
- Şekil tespiti: dikdörtgen ve polygon ayrımı
- Geçerli polygon anotasyonlarını x ve y'nin min-max değerlerine göre dikdörtgene düzenleme
- Görüntü boyutuna oranlı dinamik tolerans (sigma parametresi)
- Tek dosya veya klasör bazlı toplu işlem
- Klasör modunda toplam özet (gereksiz detay yok)

## Kurulum

Python 3.7 veya üstü gerekir.

```bash
pip install ijson
```

## Kullanım

Tek komutla analiz özeti ve dönüştürülmüş JSON dosyası oluşturulur. Girdi dosyası değiştirilmez; girdi ile aynı dosyaya çıktı yazılması engellenir. RLE ve yapısal kontrolden geçmeyen anotasyonlar dönüştürülmeden korunur ve atlanan sayısına eklenir.

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

**Çıktı klasörü belirterek:**
```bash
python coco_tool.py annotations.json --output sonuclar
```

**Yardım menüsü:**
```bash
python coco_tool.py --help
```

## Çıktı Örneği

Aşağıdaki sayılar çıktı biçimini göstermek için örnektir.

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
Atlanan            : 0 annotation dönüştürülmeden korundu
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
Atlanan            : 1 annotation dönüştürülmeden korundu
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
tolerance = max(0.5, max(image_width, image_height) * sigma)
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

Bu kontroller tam bir COCO şema doğrulaması değildir. Negatif koordinat, görüntü sınırı, kimliklerin tekilliği ve `image_id` / `category_id` ilişkileri ayrıca denetlenmez. Çıktıya standart `info`, `licenses`, `images`, `categories` ve `annotations` alanları aktarılır; özel üst seviye alanlar aktarılmaz.

## Bağımlılıklar

- `ijson` — Streaming JSON okuma

## Lisans

MIT License
