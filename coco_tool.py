import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

try:
    import ijson
except ImportError:
    print("HATA: ijson kütüphanesi gerekli. Kurulum: pip install ijson")
    sys.exit(1)


DEFAULT_SIGMA = 0.001
MIN_TOLERANCE = 0.5


def compute_tolerance(image_width, image_height, sigma=DEFAULT_SIGMA):
    if image_width <= 0 or image_height <= 0:
        return MIN_TOLERANCE
    tol = max(image_width, image_height) * sigma
    return max(MIN_TOLERANCE, tol)


def shoelace_area(polygon_flat):
    n = len(polygon_flat) // 2
    if n < 3:
        return 0.0
    points = [(float(polygon_flat[2 * i]), float(polygon_flat[2 * i + 1])) for i in range(n)]
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def detect_shape_type(polygon_flat, tolerance):
    n = len(polygon_flat) // 2
    if n != 4:
        return 'polygon'

    xs = [float(polygon_flat[2 * i]) for i in range(4)]
    ys = [float(polygon_flat[2 * i + 1]) for i in range(4)]

    unique_xs = []
    for x in xs:
        if not any(abs(x - ux) <= tolerance for ux in unique_xs):
            unique_xs.append(x)

    unique_ys = []
    for y in ys:
        if not any(abs(y - uy) <= tolerance for uy in unique_ys):
            unique_ys.append(y)

    if len(unique_xs) == 2 and len(unique_ys) == 2:
        return 'rectangle'
    return 'polygon'


def detect_annotation_shape(segmentation, tolerance):
    if not segmentation:
        return 'polygon'
    return detect_shape_type(segmentation[0], tolerance)


def polygon_to_rectangle(segmentation):
    all_xs = []
    all_ys = []
    for polygon in segmentation:
        n = len(polygon) // 2
        for i in range(n):
            all_xs.append(float(polygon[2 * i]))
            all_ys.append(float(polygon[2 * i + 1]))

    if not all_xs or not all_ys:
        return None

    x_min = min(all_xs)
    x_max = max(all_xs)
    y_min = min(all_ys)
    y_max = max(all_ys)

    rectangle_segmentation = [[
        x_min, y_min,
        x_max, y_min,
        x_max, y_max,
        x_min, y_max,
    ]]
    bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
    area = (x_max - x_min) * (y_max - y_min)

    return rectangle_segmentation, bbox, area


def validate_annotation(ann):
    required_fields = ['id', 'image_id', 'category_id', 'segmentation']
    for field in required_fields:
        if field not in ann:
            return [f"Eksik zorunlu alan: '{field}'"]

    segmentation = ann['segmentation']
    if isinstance(segmentation, dict):
        return ["RLE formatı — bu script polygon bekliyor"]
    if not isinstance(segmentation, list) or len(segmentation) == 0:
        return ["Geçersiz segmentation formatı"]

    for poly_idx, polygon in enumerate(segmentation):
        if not isinstance(polygon, list) or len(polygon) % 2 != 0:
            return [f"Polygon[{poly_idx}] geçersiz format"]
        if len(polygon) // 2 < 3:
            return [f"Polygon[{poly_idx}] en az 3 nokta gerekir"]

    return []


def process_file(input_path, output_path, sigma=DEFAULT_SIGMA, verbose=True):
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"HATA: Dosya bulunamadı → {input_path}")
        return None

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    images_dict = {}
    if 'images' in data:
        for img in data['images']:
            images_dict[img['id']] = {
                'width': int(img.get('width', 0)),
                'height': int(img.get('height', 0)),
            }

    categories = {}
    if 'categories' in data:
        for cat in data['categories']:
            categories[cat['id']] = cat.get('name', f"id_{cat['id']}")

    total = 0
    valid = 0
    invalid = 0
    category_counts = defaultdict(int)
    shape_counts_before = {'rectangle': 0, 'polygon': 0}
    annotated_image_ids = set()

    total_area = 0.0
    min_area = None
    max_area = 0.0

    converted = 0
    skipped = 0

    if 'annotations' in data:
        for ann in data['annotations']:
            total += 1

            errs = validate_annotation(ann)
            if errs:
                invalid += 1
                skipped += 1
                continue

            valid += 1
            img_id = ann.get('image_id')
            image_info = images_dict.get(img_id)
            if image_info is not None:
                annotated_image_ids.add(img_id)
                tol = compute_tolerance(image_info['width'], image_info['height'], sigma)
            else:
                tol = MIN_TOLERANCE

            category_counts[ann.get('category_id')] += 1

            shape_before = detect_annotation_shape(ann['segmentation'], tol)
            shape_counts_before[shape_before] += 1

            ann_area = sum(shoelace_area(p) for p in ann['segmentation'])
            total_area += ann_area
            if min_area is None or ann_area < min_area:
                min_area = ann_area
            if ann_area > max_area:
                max_area = ann_area

            result = polygon_to_rectangle(ann['segmentation'])
            if result is None:
                skipped += 1
                continue

            new_segmentation, new_bbox, new_area = result
            ann['segmentation'] = new_segmentation
            ann['bbox'] = new_bbox
            ann['area'] = new_area
            converted += 1

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if verbose:
        folder_name = input_path.parent.name if input_path.parent.name else str(input_path.parent)
        file_size_mb = input_path.stat().st_size / (1024 * 1024)

        print(f"Klasör : {folder_name}")
        print(f"Dosya  : {input_path.name} ({file_size_mb:.2f} MB)")
        print()
        print(f"Görüntü sayısı     : {len(images_dict)}")
        print(f"Etiketli görüntü   : {len(annotated_image_ids)}")
        print(f"Toplam annotation  : {total}  (geçerli: {valid}, hatalı: {invalid})")

        n_rect = shape_counts_before['rectangle']
        n_poly = shape_counts_before['polygon']
        n_total = n_rect + n_poly
        if n_total > 0:
            print(f"Şekil dağılımı     : {n_rect} dikdörtgen ({100*n_rect/n_total:.1f}%), "
                  f"{n_poly} polygon ({100*n_poly/n_total:.1f}%)")

        if categories:
            print(f"\nKategoriler ({len(categories)}):")
            for cat_id, count in sorted(category_counts.items(), key=lambda x: -x[1]):
                cat_name = categories.get(cat_id, f"id_{cat_id}")
                pct = 100 * count / valid if valid else 0
                print(f"  {cat_name:20s} : {count:6d} ({pct:5.1f}%)")

        if valid > 0:
            avg_area = total_area / valid
            print(f"\nAlan (piksel kare) : ort {avg_area:.0f}, min {min_area:.0f}, max {max_area:.0f}")

        print(f"\nDönüşüm            : {converted} annotation min/max ile dikdörtgene düzenlendi")
        print(f"Çıktı dosyası      : {output_path}")

    return {
        'file': input_path.name,
        'total_images': len(images_dict),
        'annotated_images': len(annotated_image_ids),
        'total_anns': total,
        'valid_anns': valid,
        'invalid_anns': invalid,
        'category_count': len(categories),
        'category_names': set(categories.values()),
        'rectangle_count': shape_counts_before['rectangle'],
        'polygon_count': shape_counts_before['polygon'],
        'converted': converted,
        'total_area': total_area,
        'min_area': min_area if min_area is not None else 0.0,
        'max_area': max_area,
    }


def run(path_str, output_dir=None, suffix='_rectangles', sigma=DEFAULT_SIGMA):
    path = Path(path_str)
    if not path.exists():
        print(f"HATA: Yol bulunamadı → {path}")
        sys.exit(1)

    if path.is_file():
        if output_dir is None:
            out_path = path.parent / f"{path.stem}{suffix}.json"
        else:
            out_path = Path(output_dir) / f"{path.stem}{suffix}.json"
        process_file(path, out_path, sigma, verbose=True)
        return

    json_files = sorted(path.glob('*.json'))
    if not json_files:
        print(f"HATA: '{path}' klasöründe .json dosyası yok.")
        sys.exit(1)

    if output_dir is None:
        out_dir = path.parent / f"{path.name}{suffix}"
    else:
        out_dir = Path(output_dir)

    summaries = []
    for jf in json_files:
        out_path = out_dir / jf.name
        s = process_file(jf, out_path, sigma, verbose=False)
        if s is not None:
            summaries.append(s)

    if not summaries:
        return

    total_files = len(summaries)
    total_images = sum(s['total_images'] for s in summaries)
    total_annotated = sum(s['annotated_images'] for s in summaries)
    total_anns = sum(s['total_anns'] for s in summaries)
    total_valid = sum(s['valid_anns'] for s in summaries)
    total_invalid = sum(s['invalid_anns'] for s in summaries)
    total_rect = sum(s['rectangle_count'] for s in summaries)
    total_poly = sum(s['polygon_count'] for s in summaries)
    total_converted = sum(s['converted'] for s in summaries)

    all_categories = set()
    for s in summaries:
        all_categories.update(s['category_names'])

    total_area_sum = sum(s['total_area'] for s in summaries)
    min_areas = [s['min_area'] for s in summaries if s['min_area'] > 0]
    max_areas = [s['max_area'] for s in summaries if s['max_area'] > 0]
    overall_min = min(min_areas) if min_areas else 0
    overall_max = max(max_areas) if max_areas else 0
    overall_avg = total_area_sum / total_valid if total_valid > 0 else 0

    print(f"Klasör             : {path.name}")
    print(f"Hedef klasör       : {out_dir}")
    print(f"Dosya sayısı       : {total_files}")
    print()
    print(f"Toplam görüntü     : {total_images}")
    print(f"Etiketli görüntü   : {total_annotated}")
    print(f"Toplam annotation  : {total_anns}  (geçerli: {total_valid}, hatalı: {total_invalid})")

    n_shape_total = total_rect + total_poly
    if n_shape_total > 0:
        print(f"Şekil dağılımı     : {total_rect} dikdörtgen ({100*total_rect/n_shape_total:.1f}%), "
            f"{total_poly} polygon ({100*total_poly/n_shape_total:.1f}%)")

    print(f"Farklı kategori    : {len(all_categories)}")
    if all_categories:
        print(f"  {', '.join(sorted(all_categories))}")

    if total_valid > 0:
        print(f"Alan (piksel kare) : ort {overall_avg:.0f}, min {overall_min:.0f}, max {overall_max:.0f}")

    print(f"Dönüşüm            : {total_converted} annotation min/max ile dikdörtgene düzenlendi")


def main():
    parser = argparse.ArgumentParser(
        description="COCO format annotation aracı: analiz eder ve tüm annotation'ları "
                    "x/y min-max değerlerine göre dikdörtgene düzenler."
    )
    parser.add_argument('path',
                        help="JSON dosyasının yolu VEYA içinde JSON olan bir klasör")
    parser.add_argument('--sigma', type=float, default=DEFAULT_SIGMA,
                        help=f"Şekil tespiti için görüntü boyutuna oranlı tolerans katsayısı "
                            f"(varsayılan: {DEFAULT_SIGMA}). "
                             f"tolerance = max(width,height) * sigma. "
                            f"Minimum {MIN_TOLERANCE} piksel garantilidir.")
    parser.add_argument('--output', default=None,
                        help="Çıktı klasörü (varsayılan: girdi yanına _rectangles ek ile)")
    parser.add_argument('--suffix', default='_rectangles',
                        help="Çıktı adına eklenecek son ek (varsayılan: _rectangles)")

    args = parser.parse_args()
    run(args.path, output_dir=args.output, suffix=args.suffix, sigma=args.sigma)


if __name__ == '__main__':
    main()