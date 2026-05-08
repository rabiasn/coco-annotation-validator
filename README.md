COCO Annotation Tool
COCO formatındaki etiketli veri kümeleri için doğrulama, analiz ve dikdörtgene dönüştürme aracı. Python ile yazıldı; sağlık alanı segmentasyon verileri başta olmak üzere COCO formatına uyan her veri kümesinde çalışır.
Ne yapıyor?
Tek komut çalıştırıyorsun, hem analiz raporu çıkıyor hem de tüm annotation'lar otomatik olarak min/max değerlerine göre dikdörtgene dönüştürülüp yeni bir dosyaya kaydediliyor. Orijinal dosya bozulmuyor.
Özellikler

JSON dosyalarını streaming olarak okur, büyük dosyalarda RAM şişmiyor
Annotation doğruluk kontrolleri (eksik alan, geçersiz polygon, negatif koordinat)
Polygon alan hesabı (Shoelace formülü)
Şekil tespiti yapıyor: dikdörtgen mi yoksa polygon mu
Tüm annotation'ları min/max değerlerine göre dikdörtgene düzenliyor
Görüntü boyutuna oranlı dinamik tolerans (sigma parametresi)
Tek dosya da çalışıyor, klasör de — klasör verince içindeki tüm JSON'ları sırayla işliyor

Kurulum
Python 3.7 ve üstü gerekiyor.
bashpip install ijson
Kullanım
Tek dosya için:
bashpython coco_tool.py annotations.json
Klasör için (içindeki tüm JSON dosyaları sırayla işlenir):
bashpython coco_tool.py klasor_adi
Sigma parametresini değiştirmek istersen:
bashpython coco_tool.py annotations.json --sigma 0.002
Çıktı nasıl görünüyor?
Tek dosya verince:
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
Klasör verdiğinde her dosya için ayrı ayrı uzun rapor değil, sadece toplam özet veriyor:
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
Dönüştürme nasıl çalışıyor?
Her annotation için:

Polygon'un tüm noktalarının x ve y koordinatlarını topluyorum
x_min, x_max, y_min, y_max hesaplıyorum
Bu 4 değerden 4 köşeli eksen-hizalı dikdörtgen oluşturuyorum
segmentation, bbox ve area alanlarını güncelliyorum

Algoritma her tür nokta sayısı için çalışıyor — 3, 5, 100 nokta fark etmez. Polygon'un boyutlarına göre otomatik olarak ya kare ya dikdörtgen üretiyor (matematiksel olarak kare de bir dikdörtgendir).
Sigma parametresi nedir?
Şekil tespiti yaparken kullanılan tolerance değeri, görüntü boyutuna oranlı olarak hesaplanıyor:
tolerance = max(image_width, image_height) * sigma
Varsayılan sigma = 0.001, yani görüntünün büyük kenarının binde biri kadar tolerans:
Görüntü boyutuTolerans240×2400.5 piksel (minimum garanti)1000×10001.0 piksel4096×40964.1 piksel
Çok küçük görüntülerde sıfıra inmesin diye minimum 0.5 piksel garantisi koydum. --sigma parametresi ile istediğin değeri verebilirsin.
Doğruluk kontrolleri
Her annotation için şunları kontrol ediyorum:

Zorunlu alanlar var mı (id, image_id, category_id, segmentation)
Polygon formatı geçerli mi
En az 3 nokta var mı
Segmentation tipi polygon mu (RLE formatı atlanıyor)

Bağımlılıklar

ijson — streaming JSON okuma için

Lisans
MIT License
