import argparse
import sys
from collections import defaultdict
from pathlib import Path

try:
    import ijson 
except ImportError:
    print("HATA: ijson kütüphanesi gerekli. Kurulum: pip install ijson")
    sys.exit(1)

# Shapely opsiyonel — yoksa self-intersecting kontrolü atlanır
try:
    from shapely.geometry import Polygon as ShapelyPolygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


def shoelace_area(polygon_flat):

    n = len(polygon_flat) // 2
    if n < 3:
        return 0.0
    # ijson Decimal döndürüyor, float'a çeviriyoruz.
    points = [(float(polygon_flat[2 * i]), float(polygon_flat[2 * i + 1])) for i in range(n)]

    # Shoelace formülü
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]  # Son noktadan ilk noktaya bağla
        area += x1 * y2 - x2 * y1

    return abs(area) / 2.0


def is_self_intersecting(polygon_flat):

    if not SHAPELY_AVAILABLE:
        return False  # shapely yoksa kontrol atlanır

    n = len(polygon_flat) // 2
    if n < 3:
        return False

    points = [(float(polygon_flat[2*i]), float(polygon_flat[2*i+1])) for i in range(n)]
    try:
        poly = ShapelyPolygon(points)
        return not poly.is_valid
    except Exception:
        return False


def polygon_bbox(polygon_flat):
    n = len(polygon_flat) // 2
    if n < 1:
        return (0, 0, 0, 0)

    xs = [float(polygon_flat[2 * i]) for i in range(n)]
    ys = [float(polygon_flat[2 * i + 1]) for i in range(n)]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    return (x_min, y_min, x_max - x_min, y_max - y_min)

def validate_annotation(ann, image_info=None):
    errors = []

    # Zorunlu alanlar
    required_fields = ['id', 'image_id', 'category_id', 'segmentation']
    for field in required_fields:
        if field not in ann:
            errors.append(f"Eksik zorunlu alan: '{field}'")
    if errors:
        return errors

    #Segmentation formatı
    segmentation = ann['segmentation']
    if isinstance(segmentation, dict):
        errors.append("RLE formatı — bu script polygon bekliyor")
        return errors
    if not isinstance(segmentation, list) or len(segmentation) == 0:
        errors.append("Geçersiz segmentation formatı")
        return errors

    # Her polygon için kontroller
    for poly_idx, polygon in enumerate(segmentation):
        if not isinstance(polygon, list) or len(polygon) % 2 != 0:
            errors.append(f"Polygon[{poly_idx}] geçersiz format")
            continue

        n_points = len(polygon) // 2
        if n_points < 3:
            errors.append(f"Polygon[{poly_idx}] sadece {n_points} nokta — en az 3 gerekir")
            continue

        # Negatif koordinat kontrolü
        for i in range(n_points):
            x = float(polygon[2 * i])
            y = float(polygon[2 * i + 1])
            if x < 0 or y < 0:
                errors.append(f"Polygon[{poly_idx}], nokta {i}: negatif koordinat ({x}, {y})")
                break

        # Görüntü sınırları dışı kontrolü
        if image_info is not None:
            img_w = image_info.get('width', 0)
            img_h = image_info.get('height', 0)
            if img_w > 0 and img_h > 0:
                xs = [float(polygon[2 * i]) for i in range(n_points)]
                ys = [float(polygon[2 * i + 1]) for i in range(n_points)]
                if max(xs) > img_w or max(ys) > img_h:
                    errors.append(
                        f"Polygon[{poly_idx}] görüntü sınırları dışında "
                        f"(görüntü: {img_w}x{img_h})"
                    )

        # Self-intersecting kontrolü 
        if is_self_intersecting(polygon):
            errors.append(f"Polygon[{poly_idx}] self-intersecting (kendini kesen şekil)")

    return errors

def analyze_coco(json_path, top_n=5):
    json_path = Path(json_path)
    if not json_path.exists():
        print(f"HATA: Dosya Bulunamadı → {json_path}")
        return None

    file_size_mb = json_path.stat().st_size / (1024 * 1024)

    # Klasör adı ve dosya adı bilgisini en başta göster
    folder_name = json_path.parent.name if json_path.parent.name else str(json_path.parent)
    print("=" * 70)
    print(f"Klasör: {folder_name}")
    print(f"Dosya : {json_path.name} ({file_size_mb:.2f} MB)")
    print("=" * 70)


    images = {}
    with open(json_path, 'rb') as f:
        for img in ijson.items(f, 'images.item'):
            images[img['id']] = {
                'width': img.get('width', 0),
                'height': img.get('height', 0),
                'file_name': img.get('file_name', '?'),
            }
    print(f"   → {len(images)} görüntü bulundu")
    categories = {}
    with open(json_path, 'rb') as f:
        for cat in ijson.items(f, 'categories.item'):
            categories[cat['id']] = cat.get('name', f"id_{cat['id']}")
    print(f"   → {len(categories)} kategori: {list(categories.values())}")

    total = 0
    valid = 0
    invalid = 0
    errors_log = []
    seen_ids = set()
    duplicate_ids = []
    orphan_count = 0
    category_counts = defaultdict(int)
    all_areas = []

    #kaç görselde etiket var, kaçı hatalı
    annotated_image_ids = set()
    image_ids_with_errors = set()

    area_mismatches = []  # JSON'daki area ile hesaplanan farklı (>%10)
    too_large_anns = []   # Görüntünün %90+'ını kaplayan
    too_small_anns = []   # 10 px²'den küçük

    with open(json_path, 'rb') as f:
        for ann in ijson.items(f, 'annotations.item'):
            total += 1

            # Duplicate id kontrolü
            ann_id = ann.get('id')
            if ann_id is not None:
                if ann_id in seen_ids:
                    duplicate_ids.append(ann_id)
                seen_ids.add(ann_id)

            img_id = ann.get('image_id')
            image_info = images.get(img_id)
            if image_info is None:
                orphan_count += 1
            else:
                annotated_image_ids.add(img_id)

            # Doğrulama
            errs = validate_annotation(ann, image_info)
            if errs:
                invalid += 1
                errors_log.append({
                    'ann_id': ann_id,
                    'image_id': img_id,
                    'errors': errs,
                })
                if image_info is not None:
                    image_ids_with_errors.add(img_id)
                continue

            valid += 1
            category_counts[ann.get('category_id')] += 1

            # Alan hesabı
            total_area = sum(shoelace_area(p) for p in ann['segmentation'])

            # Bounding box
            all_xs, all_ys = [], []
            for polygon in ann['segmentation']:
                n = len(polygon) // 2
                all_xs.extend(float(polygon[2*i]) for i in range(n))
                all_ys.extend(float(polygon[2*i+1]) for i in range(n))
            bbox_w = max(all_xs) - min(all_xs) if all_xs else 0
            bbox_h = max(all_ys) - min(all_ys) if all_ys else 0

            all_areas.append({
                'ann_id': ann_id,
                'image_id': img_id,
                'image_file': image_info['file_name'] if image_info else '?',
                'category': categories.get(ann.get('category_id'), '?'),
                'area_calculated': total_area,
                'area_in_json': float(ann['area']) if 'area' in ann else None,
                'bbox_width': bbox_w,
                'bbox_height': bbox_h,
                'image_width': image_info['width'] if image_info else 0,
                'image_height': image_info['height'] if image_info else 0,
            })

            # Area mismatch: JSON'daki area ile hesaplanan farklı mı (>%10)
            if 'area' in ann:
                json_area = float(ann['area'])
                if json_area > 0:
                    diff_pct = abs(total_area - json_area) / json_area * 100
                    if diff_pct > 10:
                        area_mismatches.append({
                            'ann_id': ann_id,
                            'json_area': json_area,
                            'calc_area': total_area,
                            'diff_pct': diff_pct,
                        })

            # Outlier: çok büyük annotation (>%90 görüntü kaplama)
            if image_info is not None:
                img_w = image_info.get('width', 0)
                img_h = image_info.get('height', 0)
                if img_w > 0 and img_h > 0:
                    coverage = total_area / (img_w * img_h)
                    if coverage > 0.9:
                        too_large_anns.append({
                            'ann_id': ann_id,
                            'coverage_pct': coverage * 100,
                        })

            # Outlier: çok küçük annotation (<10 px²)
            if total_area < 10:
                too_small_anns.append({
                    'ann_id': ann_id,
                    'area': total_area,
                })

            if total % 1000 == 0:
                print(f"{total} annotation işlendi", end='\r')

    print(f"{total} annotation işlendi              ")

    print("\n" + "=" * 70)

    print("=" * 70)

    total_images = len(images)
    n_annotated = len(annotated_image_ids)
    n_with_errors = len(image_ids_with_errors)

    print(f"\nGörüntüler:")
    print(f"  Toplam görüntü     : {total_images}")
    print(f"  Etiketli görüntü   : {n_annotated}")
    print(f"  Hatalı görüntü     : {n_with_errors}")

    print(f"\nAnnotation:")
    print(f"  Toplam             : {total}")
    print(f"Geçerli         : {valid}")
    print(f"Hatalı          : {invalid}")
    print(f"Orphan          : {orphan_count}")
    print(f"Duplicate id    : {len(duplicate_ids)}")

    if duplicate_ids:
        print(f"Örnek: {duplicate_ids[:5]}")

    print(f"\nKategori")
    for cat_id, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        cat_name = categories.get(cat_id, f"id_{cat_id}")
        pct = 100 * count / valid if valid else 0
        print(f"  {cat_name:20s} : {count:6d}  ({pct:5.1f}%)")
    if errors_log:
        print(f"\nHata örnekleri (ilk 5):")
        for entry in errors_log[:5]:
            print(f"  Annotation id={entry['ann_id']}, image_id={entry['image_id']}")
            for err in entry['errors']:
                print(f"     - {err}")

    has_warnings = area_mismatches or too_large_anns or too_small_anns
    if has_warnings:
        print(f"\n uyarılar:")
        if area_mismatches:
            print(f"Area uyumsuzluğu (>%10 fark) : {len(area_mismatches)} adet")
            for item in area_mismatches[:3]:
                print(f"     - id={item['ann_id']}: JSON={item['json_area']:.0f}, "
                    f"hesaplanan={item['calc_area']:.0f} (%{item['diff_pct']:.1f} fark)")
        if too_large_anns:
            print(f"Çok büyük annotation (>%90 kaplama): {len(too_large_anns)} adet")
        if too_small_anns:
            print(f"Çok küçük annotation (<10 px²)   : {len(too_small_anns)} adet")

    if all_areas:
        all_areas.sort(key=lambda x: x['area_calculated'], reverse=True)
        print(f"\nEN BÜYÜK {min(top_n, len(all_areas))} ALANLI ETİKET:")
        print("-" * 70)
        for i, item in enumerate(all_areas[:top_n], 1):
            print(f"\n#{i}")
            print(f"  Annotation ID  : {item['ann_id']}")
            print(f"  Görüntü        : {item['image_file']}")
            print(f"  Görüntü boyutu : {item['image_width']} x {item['image_height']} px")
            print(f"  Kategori       : {item['category']}")
            print(f"  Hesaplanan alan: {item['area_calculated']:.2f} px²")
            if item['area_in_json'] is not None:
                diff = abs(item['area_calculated'] - item['area_in_json'])
                print(f"  JSON'daki alan : {item['area_in_json']:.2f} px²  (fark: {diff:.2f})")
            print(f"  Bounding box   : {item['bbox_width']:.1f} x {item['bbox_height']:.1f} px")
            if item['image_width'] > 0:
                coverage = (item['area_calculated'] /
                            (item['image_width'] * item['image_height'])) * 100
                print(f"  Görüntü kaplama: %{coverage:.2f}")

        areas_only = [a['area_calculated'] for a in all_areas]
        print(f"\n Alan istatistikleri:")
        print(f"  Min      : {min(areas_only):.2f} px²")
        print(f"  Max      : {max(areas_only):.2f} px²")
        print(f"  Ortalama : {sum(areas_only)/len(areas_only):.2f} px²")
        print(f"  Medyan   : {sorted(areas_only)[len(areas_only)//2]:.2f} px²")

    print("\n" + "=" * 70)
    print("=" * 70)
    print(f"  Klasör            : {folder_name}")
    print(f"  Dosya             : {json_path.name} ({file_size_mb:.2f} MB)")
    print(f"  Toplam görüntü    : {total_images}")
    print(f"  Etiketli görüntü  : {n_annotated}")
    print(f"  Hatalı görüntü    : {n_with_errors}")
    print(f"  Toplam annotation : {total}")
    print(f"  Geçerli           : {valid}")
    print(f"  Hatalı            : {invalid}")
    print(f"  Kategori sayısı   : {len(categories)}")

    # Klasör modunda toplam tablosu için bu özeti döndürüyoruz
    return {
        'folder': folder_name,
        'file': json_path.name,
        'total_images': total_images,
        'annotated_images': n_annotated,
        'error_images': n_with_errors,
        'total_anns': total,
        'valid_anns': valid,
        'invalid_anns': invalid,
        'category_count': len(categories),
    }


def analyze_path(path_str, top_n=5):
    path = Path(path_str)

    if not path.exists():
        print(f"HATA: Yol bulunamadı → {path}")
        sys.exit(1)

    # Tek dosya verildiyse direkt analiz et
    if path.is_file():
        analyze_coco(path, top_n=top_n)
        return

    # Klasör verildiyse içindeki tüm .json dosyalarını topla
    if path.is_dir():
        # sorted ile alfabetik sırada işle, böylece çıktı tutarlı olur
        json_files = sorted(path.glob('*.json'))

        if not json_files:
            print(f"HATA: '{path}' klasöründe hiç .json dosyası yok.")
            sys.exit(1)

        print("=" * 70)
        print(f"KLASÖR ANALİZİ: {path.name}")
        print(f"Toplam {len(json_files)} adet JSON dosyası bulundu.")
        print("=" * 70)

        all_summaries = []
        for idx, jf in enumerate(json_files, 1):
            print(f"\n\n[{idx}/{len(json_files)}] İşleniyor: {jf.name}")
            summary = analyze_coco(jf, top_n=top_n)
            if summary is not None:
                all_summaries.append(summary)

        # karşılaştırma tablosu
        if all_summaries:
            print("\n\n" + "=" * 70)
            print(f"KLASÖR GENEL ÖZETİ: {path.name}")
            print("=" * 70)
            print(f"{'Dosya':<35} {'Görüntü':>8} {'Annot.':>8} {'Geçerli':>8} {'Hatalı':>8}")
            print("-" * 70)

            toplam_gorseller = 0
            toplam_annot = 0
            toplam_gecerli = 0
            toplam_hatali = 0

            for s in all_summaries:
                gosterilecek_ad = s['file']
                if len(gosterilecek_ad) > 34:
                    gosterilecek_ad = gosterilecek_ad[:31] + "..."

                print(f"{gosterilecek_ad:<35} "
                      f"{s['total_images']:>8} "
                      f"{s['total_anns']:>8} "
                      f"{s['valid_anns']:>8} "
                      f"{s['invalid_anns']:>8}")

                toplam_gorseller += s['total_images']
                toplam_annot += s['total_anns']
                toplam_gecerli += s['valid_anns']
                toplam_hatali += s['invalid_anns']

            print("-" * 70)
            print(f"{'TOPLAM':<35} "
                  f"{toplam_gorseller:>8} "
                  f"{toplam_annot:>8} "
                  f"{toplam_gecerli:>8} "
                  f"{toplam_hatali:>8}")
            print("=" * 70)



def main():
    parser = argparse.ArgumentParser(
        description="COCO formatındaki etiketli veriyi doğrular ve alanları analiz eder. "
                    "Tek dosya ya da klasör verilebilir; klasör verildiğinde içindeki "
                    "tüm .json dosyaları sırayla işlenir."
    )
    parser.add_argument('path',
                        help="COCO format JSON dosyasının yolu VEYA içinde JSON dosyaları olan bir klasör")
    parser.add_argument('--top', type=int, default=5,
                        help="En büyük kaç annotation gösterilsin (varsayılan: 5)")
    args = parser.parse_args()

    analyze_path(args.path, top_n=args.top)


if __name__ == '__main__':
    main()