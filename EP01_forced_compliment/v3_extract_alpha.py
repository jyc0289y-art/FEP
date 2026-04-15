#!/usr/bin/env python3
"""
v3 Phase 2.5: 듀얼 스타일 알파 추출
- 스타일 A (char_A_*): 흰 배경 제거 (threshold 기반)
- 스타일 B (char_B_*): 크로마키 녹색 배경 제거
파일명 접두사로 자동 분류, alphas/ 에 RGBA PNG 저장
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


def detect_style(filename):
    """파일명에서 스타일 A/B 자동 판별"""
    name = filename.lower()
    if "_char_a_" in name or "_a_" in name.split("char_")[-1][:3]:
        return "A"
    elif "_char_b_" in name or "_b_" in name.split("char_")[-1][:3]:
        return "B"
    # 파일 내용으로 판별: 초록 비율 높으면 B, 흰색 비율 높으면 A
    return None  # 파일 분석 필요


def detect_style_by_content(img_path):
    """이미지 픽셀로 스타일 자동 판별 (파일명 불확실 시)"""
    img = Image.open(img_path).convert("RGB")
    arr = np.array(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # 초록 배경 비율
    green_ratio = np.mean((g > 100) & (g - r > 40) & (g - b > 40))
    # 흰색 배경 비율
    white_ratio = np.mean((r > 230) & (g > 230) & (b > 230))

    if green_ratio > 0.15:
        return "B"
    elif white_ratio > 0.15:
        return "A"
    return "A"  # 기본값


def whitebg_extract(img_path, output_path, threshold=240, edge_blur=1.5):
    """
    흰 배경을 알파로 변환 (스타일 A용) — v2 Flood Fill 방식
    이미지 가장자리에서 시작하여 흰색으로 연결된 영역만 배경으로 판정.
    흰 옷, 흰 소품 등 캐릭터 내부의 흰색은 보존됨.
    """
    from scipy.ndimage import label, binary_dilation, gaussian_filter

    img = Image.open(img_path).convert("RGBA")
    arr = np.array(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    h, w = r.shape

    # 1단계: 흰색 후보 마스크 (전역)
    white_mask = (r > threshold) & (g > threshold) & (b > threshold)
    # 밝은 무채색도 포함
    near_white = (r > threshold - 15) & (g > threshold - 15) & (b > threshold - 15)
    max_rgb = np.maximum(np.maximum(r, g), b)
    min_rgb = np.minimum(np.minimum(r, g), b)
    low_saturation = (max_rgb - min_rgb) < 20
    candidate_mask = white_mask | (near_white & low_saturation)

    # 2단계: 가장자리 접촉 마스크 (이미지 테두리 2px)
    edge_touch = np.zeros_like(candidate_mask)
    edge_touch[:2, :] = True    # 상단
    edge_touch[-2:, :] = True   # 하단
    edge_touch[:, :2] = True    # 좌측
    edge_touch[:, -2:] = True   # 우측

    # 3단계: 흰색 후보 중 가장자리에 연결된 것만 배경으로 판정 (Flood Fill)
    # connected components에서 가장자리에 닿는 컴포넌트만 선택
    labeled, n_labels = label(candidate_mask)
    bg_mask = np.zeros_like(candidate_mask)
    edge_labels = set(np.unique(labeled[edge_touch & candidate_mask]))
    edge_labels.discard(0)  # 0은 배경 라벨

    for lbl in edge_labels:
        bg_mask |= (labeled == lbl)

    # 4단계: 배경 마스크 약간 확장 (1px) — 흰색 프린지 제거
    bg_mask = binary_dilation(bg_mask, iterations=1)

    # 알파 마스크 (배경=0, 전경=255)
    alpha = np.where(bg_mask, 0, 255).astype(np.uint8)

    # 경계 부드럽게
    if edge_blur > 0:
        alpha_float = alpha.astype(np.float32)
        blurred = gaussian_filter(alpha_float, sigma=edge_blur)
        edge_zone = (blurred > 10) & (blurred < 245)
        alpha = np.where(edge_zone, np.clip(blurred, 0, 255).astype(np.uint8), alpha)

    # 알파 적용
    arr[:, :, 3] = alpha
    result = Image.fromarray(arr.astype(np.uint8), "RGBA")
    result.save(output_path)
    return True


def chromakey_extract(img_path, output_path, tolerance=60, edge_blur=2):
    """
    초록 배경(#00FF00)을 알파로 변환 (스타일 B용)
    tolerance: 초록색 판정 허용 범위 (0-255)
    edge_blur: 경계 부드러움 (픽셀)
    """
    img = Image.open(img_path).convert("RGBA")
    arr = np.array(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # 초록 배경 마스크
    green_mask = (
        (g > 100) &
        (g - r > tolerance) &
        (g - b > tolerance)
    )

    alpha = np.where(green_mask, 0, 255).astype(np.uint8)

    # 경계 부드럽게
    if edge_blur > 0:
        try:
            from scipy.ndimage import gaussian_filter
            alpha_float = alpha.astype(np.float32)
            blurred = gaussian_filter(alpha_float, sigma=edge_blur)
            alpha = np.where(alpha == 255, 255,
                    np.where(alpha == 0, 0,
                    np.clip(blurred, 0, 255))).astype(np.uint8)
        except ImportError:
            pass

    # 초록 스필 제거
    fg_mask = alpha > 128
    if np.any(fg_mask):
        avg_rb = (r + b) / 2
        g_corrected = np.where(
            fg_mask & (g > avg_rb + 20),
            avg_rb + 20,
            g
        )
        arr[:, :, 1] = g_corrected

    arr[:, :, 3] = alpha
    result = Image.fromarray(arr.astype(np.uint8), "RGBA")
    result.save(output_path)
    return True


def extract_one(f, verbose=True):
    """단일 파일 알파 추출 (스타일 자동 감지)"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f.stem
    if "_char_" in stem:
        char_part = stem.split("_char_", 1)[1]
    else:
        char_part = stem

    # 스타일 감지
    style = detect_style(f.name)
    if style is None:
        style = detect_style_by_content(str(f))

    out_name = f"{ts}_alpha_{char_part}.png"
    out_path = ALPHA_DIR / out_name

    try:
        if style == "A":
            whitebg_extract(str(f), str(out_path))
            method = "흰배경"
        else:
            chromakey_extract(str(f), str(out_path))
            method = "크로마키"

        if verbose:
            print(f"  ✅ [{style}/{method}] {f.name} → {out_name}")
        return True
    except Exception as e:
        if verbose:
            print(f"  ❌ {f.name}: {e}")
        return False


def process_all():
    ALPHA_DIR.mkdir(parents=True, exist_ok=True)

    if not CHAR_DIR.exists():
        print(f"❌ 캐릭터 폴더 없음: {CHAR_DIR}")
        return

    char_files = sorted(CHAR_DIR.glob("*.png"))
    if not char_files:
        print("캐릭터 파일 없음")
        return

    # 스타일별 분류 카운트
    style_a = [f for f in char_files if (detect_style(f.name) or detect_style_by_content(str(f))) == "A"]
    style_b = [f for f in char_files if f not in style_a]

    print(f"=== 듀얼 스타일 알파 추출 ===")
    print(f"  스타일 A (흰배경): {len(style_a)}장")
    print(f"  스타일 B (크로마키): {len(style_b)}장")
    print(f"  합계: {len(char_files)}장")
    print()

    ok, fail = 0, 0
    for f in char_files:
        if extract_one(f):
            ok += 1
        else:
            fail += 1

    print(f"\n=== 완료: ✅ {ok}장 / ❌ {fail}장 ===")


def process_single(filename):
    ALPHA_DIR.mkdir(parents=True, exist_ok=True)
    src = CHAR_DIR / filename
    if not src.exists():
        print(f"❌ 파일 없음: {src}")
        return
    extract_one(src)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            # 현재 캐릭터 목록 + 스타일 분류 표시
            char_files = sorted(CHAR_DIR.glob("*.png"))
            for f in char_files:
                style = detect_style(f.name) or "?"
                print(f"  [{style}] {f.name}")
        else:
            process_single(sys.argv[1])
    else:
        process_all()
