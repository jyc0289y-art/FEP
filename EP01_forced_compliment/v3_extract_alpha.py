#!/usr/bin/env python3
"""
v3 Phase 2.5: 크로마키 알파 추출
characters/ 폴더의 초록 배경 캐릭터에서 알파 채널 추출 → alphas/ 에 PNG 저장
OpenCV 크로마키 방식 (rembg보다 정확한 경계선)
"""
import sys, os
from pathlib import Path
from datetime import datetime

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("pip install numpy Pillow 필요")
    sys.exit(1)

V3_DIR = Path(__file__).parent / "v3_layers"
CHAR_DIR = V3_DIR / "characters"
ALPHA_DIR = V3_DIR / "alphas"


def chromakey_extract(img_path, output_path, tolerance=60, edge_blur=2):
    """
    초록 배경(#00FF00)을 알파로 변환
    tolerance: 초록색 판정 허용 범위 (0-255)
    edge_blur: 경계 부드러움 (픽셀)
    """
    img = Image.open(img_path).convert("RGBA")
    arr = np.array(img, dtype=np.float32)

    # 초록 채널이 높고 빨강/파랑 채널이 낮은 픽셀 = 배경
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # 초록 배경 마스크: G가 높고 R,B가 낮은 영역
    green_mask = (
        (g > 100) &  # 초록이 충분히 밝음
        (g - r > tolerance) &  # 초록이 빨강보다 확실히 높음
        (g - b > tolerance)    # 초록이 파랑보다 확실히 높음
    )

    # 알파 마스크 생성 (배경=0, 전경=255)
    alpha = np.where(green_mask, 0, 255).astype(np.uint8)

    # 경계 부드럽게 (optional)
    if edge_blur > 0:
        try:
            from scipy.ndimage import gaussian_filter
            # 알파 경계에만 블러 적용
            alpha_float = alpha.astype(np.float32)
            blurred = gaussian_filter(alpha_float, sigma=edge_blur)
            # 원래 확실한 영역은 유지, 경계만 부드럽게
            alpha = np.where(alpha == 255, 255,
                    np.where(alpha == 0, 0,
                    np.clip(blurred, 0, 255))).astype(np.uint8)
        except ImportError:
            pass  # scipy 없으면 블러 없이 진행

    # 초록 배경의 색상 누출(spill) 제거
    # 전경 픽셀에서 과도한 초록을 줄임
    fg_mask = alpha > 128
    if np.any(fg_mask):
        # 초록 스필 제거: 전경에서 G를 R,B 평균으로 클램프
        avg_rb = (r + b) / 2
        g_corrected = np.where(
            fg_mask & (g > avg_rb + 20),
            avg_rb + 20,
            g
        )
        arr[:, :, 1] = g_corrected

    # 알파 채널 적용
    arr[:, :, 3] = alpha
    result = Image.fromarray(arr.astype(np.uint8), "RGBA")
    result.save(output_path)
    return True


def process_all():
    if not CHAR_DIR.exists():
        print(f"❌ 캐릭터 폴더 없음: {CHAR_DIR}")
        return

    char_files = sorted(CHAR_DIR.glob("*.png"))
    if not char_files:
        print("캐릭터 파일 없음")
        return

    print(f"=== 알파 추출: {len(char_files)}장 ===")

    for f in char_files:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 원본 파일명에서 char_ 이후를 추출
        stem = f.stem
        if "_char_" in stem:
            char_part = stem.split("_char_", 1)[1]
        else:
            char_part = stem

        out_name = f"{ts}_alpha_{char_part}.png"
        out_path = ALPHA_DIR / out_name

        try:
            chromakey_extract(str(f), str(out_path))
            print(f"  ✅ {f.name} → {out_name}")
        except Exception as e:
            print(f"  ❌ {f.name}: {e}")


def process_single(filename):
    src = CHAR_DIR / filename
    if not src.exists():
        print(f"❌ 파일 없음: {src}")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = src.stem
    if "_char_" in stem:
        char_part = stem.split("_char_", 1)[1]
    else:
        char_part = stem

    out_name = f"{ts}_alpha_{char_part}.png"
    out_path = ALPHA_DIR / out_name

    chromakey_extract(str(src), str(out_path))
    print(f"✅ {filename} → {out_name}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        process_single(sys.argv[1])
    else:
        process_all()
