import argparse
import json
import sys
from pathlib import Path


def detect_shape_type(polygon_flat, tolerance=0.5):
    n = len(polygon_flat) // 2

    if n != 4:
        return 'polygon'

    xs = [float(polygon_flat[2*i]) for i in range(4)]
    ys = [float(polygon_flat[2*i+1]) for i in range(4)]

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
    else:
        return 'polygon'


def detect_annotation_shape(segmentation, tolerance=0.5):
    if not segmentation:
        return 'polygon'
    return detect_shape_type(segmentation[0], tolerance=tolerance)


def polygon_to_rectangle(segmentation):
    all_xs = []
    all_ys = []
    for polygon in segmentation:
        n = len(polygon) // 2
        for i in range(n):
            all_xs.append(float(polygon[2*i]))
            all_ys.append(float(polygon[2*i+1]))

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


def convert_file(input_path, output_path, tolerance=0.5):
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        print(f"HATA: Dosya bulunamadı → {input_path}")
        return None

    print("=" * 70)
    print(f"Girdi  : {input_path.name}")
    print(f"Çıktı  : {output_path.name}")
    print("=" * 70)

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'annotations' not in data:
        print("HATA: JSON dosyasında 'annotations' alanı yok.")
        return None

    total = len(data['annotations'])
    already_rectangle = 0
    converted = 0
    skipped = 0

    for ann in data['annotations']:
        if 'segmentation' not in ann:
            skipped += 1
            continue

        segmentation = ann['segmentation']

        if isinstance(segmentation, dict):
            skipped += 1
            continue

        if not isinstance(segmentation, list) or len(segmentation) == 0:
            skipped += 1
            continue

        shape = detect_annotation_shape(segmentation, tolerance=tolerance)

        if shape == 'rectangle':
            already_rectangle += 1
            continue

        result = polygon_to_rectangle(segmentation)
        if result is None:
            skipped += 1
            continue

        new_segmentation, new_bbox, new_area = result
        ann['segmentation'] = new_segmentation
        ann['bbox'] = new_bbox
        ann['area'] = new_area
        converted += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nToplam annotation         : {total}")
    print(f"Zaten dikdörtgen          : {already_rectangle}")
    print(f"Polygondan dönüştürülen   : {converted}")
    print(f"Atlanan (geçersiz/RLE)    : {skipped}")
    print(f"\nDönüştürülmüş dosya kaydedildi: {output_path}")
    print("=" * 70)

    return {
        'input_file': input_path.name,
        'output_file': output_path.name,
        'total': total,
        'already_rectangle': already_rectangle,
        'converted': converted,
        'skipped': skipped,
    }


def convert_path(path_str, output_dir=None, suffix='_rectangles', tolerance=0.5):
    path = Path(path_str)

    if not path.exists():
        print(f"HATA: Yol bulunamadı → {path}")
        sys.exit(1)

    if path.is_file():
        if output_dir is None:
            out_path = path.parent / f"{path.stem}{suffix}.json"
        else:
            out_dir = Path(output_dir)
            out_path = out_dir / f"{path.stem}{suffix}.json"
        convert_file(path, out_path, tolerance=tolerance)
        return

    if path.is_dir():
        json_files = sorted(path.glob('*.json'))

        if not json_files:
            print(f"HATA: '{path}' klasöründe hiç .json dosyası yok.")
            sys.exit(1)

        if output_dir is None:
            out_dir = path.parent / f"{path.name}{suffix}"
        else:
            out_dir = Path(output_dir)

        print("=" * 70)
        print(f"KLASÖR DÖNÜŞTÜRME: {path.name}")
        print(f"Hedef klasör     : {out_dir}")
        print(f"Toplam {len(json_files)} adet JSON dosyası bulundu.")
        print("=" * 70)

        all_summaries = []
        for idx, jf in enumerate(json_files, 1):
            print(f"\n\n[{idx}/{len(json_files)}] İşleniyor: {jf.name}")
            out_path = out_dir / jf.name
            summary = convert_file(jf, out_path, tolerance=tolerance)
            if summary is not None:
                all_summaries.append(summary)

        if all_summaries:
            print("\n\n" + "=" * 70)
            print(f"KLASÖR DÖNÜŞTÜRME ÖZETİ")
            print("=" * 70)
            print(f"{'Dosya':<35} {'Toplam':>8} {'Zaten R.':>9} {'Dönüşen':>9} {'Atlanan':>8}")
            print("-" * 70)

            t_total = 0
            t_already = 0
            t_converted = 0
            t_skipped = 0

            for s in all_summaries:
                ad = s['input_file']
                if len(ad) > 34:
                    ad = ad[:31] + "..."

                print(f"{ad:<35} "
                    f"{s['total']:>8} "
                    f"{s['already_rectangle']:>9} "
                    f"{s['converted']:>9} "
                    f"{s['skipped']:>8}")

                t_total += s['total']
                t_already += s['already_rectangle']
                t_converted += s['converted']
                t_skipped += s['skipped']

            print("-" * 70)
            print(f"{'TOPLAM':<35} "
                f"{t_total:>8} "
                f"{t_already:>9} "
                f"{t_converted:>9} "
                f"{t_skipped:>8}")
            print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="COCO formatındaki polygon annotation'ları kare/dikdörtgen forma dönüştürür. "
                    "x ve y'nin min ve max değerlerine bakarak dikdörtgen oluşturulur. "
                    "Tek dosya veya klasör verilebilir."
    )
    parser.add_argument('path',
                        help="COCO format JSON dosyasının yolu VEYA içinde JSON dosyaları olan bir klasör")
    parser.add_argument('--output', default=None,
                        help="Çıktının kaydedileceği klasör (varsayılan: girdi yanına yeni klasör/dosya)")
    parser.add_argument('--suffix', default='_rectangles',
                        help="Çıktı dosya/klasör adına eklenecek son ek (varsayılan: _rectangles)")
    parser.add_argument('--tolerance', type=float, default=0.5,
                        help="Şekil tespiti için piksel tolerans değeri (varsayılan: 0.5)")
    args = parser.parse_args()

    convert_path(args.path,
                output_dir=args.output,
                suffix=args.suffix,
                tolerance=args.tolerance)


if __name__ == '__main__':
    main()