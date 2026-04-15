#!/usr/bin/env python3
"""
v3 포트레이트 모드 합성기
배경(블러) + 캐릭터 상반신 나열 — 포켓몬스터/비주얼노벨 스타일
기존 v3_composite_scenes.py와 병행 사용 가능

사용법:
  python3 v3_composite_portrait.py           # 포트레이트 대상 씬 전체
  python3 v3_composite_portrait.py S-04      # 특정 씬만
"""
import sys, json, os
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageFilter, ImageEnhance
    import numpy as np
except ImportError:
    print("pip install Pillow numpy 필요")
    sys.exit(1)

V3_DIR = Path(__file__).parent / "v3_layers"
LOC_DIR = V3_DIR / "locations"
ALPHA_DIR = V3_DIR / "alphas"
SCENE_DIR = V3_DIR / "scenes"

TARGET_W, TARGET_H = 1344, 768


def find_latest(directory, pattern):
    files = sorted(directory.glob(f"*{pattern}*.png"), reverse=True)
    return files[0] if files else None


# ── 포트레이트 모드 씬 레시피 ──
# 포트레이트 모드 = 배경(블러+약간 어둡게) + 캐릭터 상반신(하단에서 솟아오르는 배치)
#
# 캐릭터 설정:
#   position: 0.0=왼쪽, 0.5=중앙, 1.0=오른쪽 (캐릭터 중심 X 위치)
#   height_ratio: 캔버스 높이 대비 캐릭터 높이 (1.3 = 130% → 상반신만 보임)
#   crop_offset: 하단에서 잘리는 비율 (0.35 = 하단 35% 프레임 밖)
#   flip: 좌우 반전 (대화 씬에서 마주보는 연출)

PORTRAIT_SCENES = {
    "S-01": {
        "bg_pattern": "loc_LOC_bathroom_morning",
        "bg_blur": 4, "bg_brightness": 0.75,
        "characters": [
            {"alpha_pattern": "alpha_A_subin_mirror", "position": 0.50, "height_ratio": 1.35, "crop_offset": 0.38},
        ],
        "post": None,
        "note": "거울 앞 수빈 — 포트레이트 모드"
    },
    "S-03": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 4, "bg_brightness": 0.75,
        "characters": [
            {"alpha_pattern": "alpha_A_minjun_sofa", "position": 0.50, "height_ratio": 1.35, "crop_offset": 0.38},
        ],
        "post": None,
        "note": "거실 민준 단독 — 포트레이트 모드"
    },
    "S-04": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 4, "bg_brightness": 0.70,
        "characters": [
            # 수빈: 왼쪽, 크게, "나 예쁘지?" 밝은 에너지
            {"alpha_pattern": "alpha_A_subin_entrance", "position": 0.30, "height_ratio": 1.35, "crop_offset": 0.38},
            # 민준: 오른쪽, 약간 작게, 귀찮은 표정
            {"alpha_pattern": "alpha_A_minjun_sofa", "position": 0.72, "height_ratio": 1.20, "crop_offset": 0.35},
        ],
        "post": None,
        "note": "수빈 등장 — 포트레이트 모드"
    },
    "S-06": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 5, "bg_brightness": 0.65,
        "characters": [
            # 수빈: 왼쪽, 더 크게 (압박감)
            {"alpha_pattern": "alpha_B_subin_lean", "position": 0.32, "height_ratio": 1.40, "crop_offset": 0.40},
            # 민준: 오른쪽, 움츠린 (더 작게)
            {"alpha_pattern": "alpha_B_minjun_shrink", "position": 0.72, "height_ratio": 1.15, "crop_offset": 0.32},
        ],
        "post": None,
        "note": "수빈 압박 — 포트레이트 모드"
    },
    "S-07": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 4, "bg_brightness": 0.75,
        "characters": [
            {"alpha_pattern": "alpha_B_subin_baby_crouch", "position": 0.38, "height_ratio": 1.10, "crop_offset": 0.28},
            {"alpha_pattern": "alpha_C_kongi_v1", "position": 0.65, "height_ratio": 0.55, "crop_offset": 0.0},
        ],
        "post": None,
        "note": "수빈+콩이 — 포트레이트 (auto_crop 전체 적용)"
    },
    "S-09": {
        "bg_pattern": "loc_LOC_livingroom_cold",
        "bg_blur": 6, "bg_brightness": 0.60,
        "characters": [
            {"alpha_pattern": "alpha_A_subin_entrance", "position": 0.65, "height_ratio": 1.15, "crop_offset": 0.30,
             "blur": 5, "opacity": 0.35},
            {"alpha_pattern": "alpha_B_minjun_observe", "position": 0.35, "height_ratio": 1.35, "crop_offset": 0.38},
        ],
        "post": "cold_desaturated",
        "note": "되감기 — 수빈 유령 + 민준 선명, 포트레이트"
    },
    "S-11": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 5, "bg_brightness": 0.65,
        "characters": [
            # 민준: 뒤쪽(작게), 구석에 몰림
            {"alpha_pattern": "alpha_B_minjun_cornered", "position": 0.70, "height_ratio": 1.15, "crop_offset": 0.30, "opacity": 0.85},
            # 수빈: 앞쪽(크게), 압박
            {"alpha_pattern": "alpha_B_subin_lean", "position": 0.30, "height_ratio": 1.40, "crop_offset": 0.40},
        ],
        "post": None,
        "note": "코너에 몰린 민준 — 포트레이트 모드"
    },
    "S-15": {
        "bg_pattern": "loc_LOC_cafe_sunny",
        "bg_blur": 4, "bg_brightness": 0.75,
        "characters": [
            # 수빈: 왼쪽, 밝음
            {"alpha_pattern": "alpha_A_subin_cafe", "position": 0.28, "height_ratio": 1.30, "crop_offset": 0.35},
            # 지우: 오른쪽, 방어적
            {"alpha_pattern": "alpha_B_jiwoo_cafe", "position": 0.72, "height_ratio": 1.25, "crop_offset": 0.33},
        ],
        "post": None,
        "note": "카페 수빈+지우 — 포트레이트 모드"
    },
    "S-19": {
        "bg_pattern": "loc_LOC_cafe_sunny",
        "bg_blur": 5, "bg_brightness": 0.65,
        "characters": [
            {"alpha_pattern": "alpha_A_subin_cafe", "position": 0.22, "height_ratio": 1.20, "crop_offset": 0.30},
            {"alpha_pattern": "alpha_B_jiwoo_smile", "position": 0.50, "height_ratio": 1.25, "crop_offset": 0.33, "opacity": 0.9},
            {"alpha_pattern": "alpha_B_jiwoo_smile", "position": 0.60, "height_ratio": 1.25, "crop_offset": 0.33, "opacity": 0.55},
            {"alpha_pattern": "alpha_B_jiwoo_smile", "position": 0.75, "height_ratio": 1.25, "crop_offset": 0.33, "opacity": 0.25},
        ],
        "post": None,
        "note": "다중노출 지우 — 포트레이트 모드"
    },
    "S-22": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 4, "bg_brightness": 0.70,
        "characters": [
            {"alpha_pattern": "alpha_B_minjun_cornered", "position": 0.70, "height_ratio": 1.25, "crop_offset": 0.33},
            {"alpha_pattern": "alpha_B_subin_lean", "position": 0.30, "height_ratio": 1.30, "crop_offset": 0.35},
        ],
        "post": "split_warm_cool",
        "note": "가스라이팅 ≠ — 포트레이트 + 좌우 톤 분할"
    },
    "S-23": {
        "bg_pattern": None,
        "bg_color": (245, 240, 235, 255),
        "bg_blur": 0, "bg_brightness": 1.0,
        "characters": [
            {"alpha_pattern": "alpha_B_subin_standing", "position": 0.22, "height_ratio": 1.30, "crop_offset": 0.35},
            {"alpha_pattern": "alpha_B_minjun_standing", "position": 0.50, "height_ratio": 1.30, "crop_offset": 0.35},
            {"alpha_pattern": "alpha_B_jiwoo_standing", "position": 0.78, "height_ratio": 1.30, "crop_offset": 0.35},
        ],
        "post": None,
        "note": "세 사람 나란히 — 포트레이트 모드"
    },
}


def apply_color_grade(img, tone):
    if tone == "cold_desaturated":
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.3)
        arr = np.array(img)
        arr[:, :, 0] = np.clip(arr[:, :, 0] * 0.7, 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * 1.15, 0, 255)
        return Image.fromarray(arr.astype(np.uint8))
    elif tone == "split_warm_cool":
        arr = np.array(img)
        mid = arr.shape[1] // 2
        arr[:, :mid, 0] = np.clip(arr[:, :mid, 0] * 0.7, 0, 255)
        arr[:, :mid, 2] = np.clip(arr[:, :mid, 2] * 1.2, 0, 255)
        arr[:, mid:, 0] = np.clip(arr[:, mid:, 0] * 1.1, 0, 255)
        arr[:, mid:, 2] = np.clip(arr[:, mid:, 2] * 0.85, 0, 255)
        return Image.fromarray(arr.astype(np.uint8))
    return img


def load_bg(recipe):
    if recipe.get("bg_pattern"):
        bg_file = find_latest(LOC_DIR, recipe["bg_pattern"])
        if not bg_file:
            print(f"  ⚠️ 배경 없음: {recipe['bg_pattern']}")
            return None
        img = Image.open(bg_file).convert("RGBA")
        # cover resize
        ratio = max(TARGET_W / img.width, TARGET_H / img.height)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        left = (img.width - TARGET_W) // 2
        top = (img.height - TARGET_H) // 2
        img = img.crop((left, top, left + TARGET_W, top + TARGET_H))
    elif recipe.get("bg_color"):
        img = Image.new("RGBA", (TARGET_W, TARGET_H), recipe["bg_color"])
    else:
        img = Image.new("RGBA", (TARGET_W, TARGET_H), (240, 240, 240, 255))

    # 배경 블러
    blur = recipe.get("bg_blur", 0)
    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur))

    # 배경 밝기 조절
    brightness = recipe.get("bg_brightness", 1.0)
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)

    return img


def composite_portrait(scene_id, recipe):
    canvas = load_bg(recipe)
    if canvas is None:
        return None

    for char in recipe.get("characters", []):
        alpha_file = find_latest(ALPHA_DIR, char["alpha_pattern"])
        if not alpha_file:
            print(f"  ⚠️ 알파 없음: {char['alpha_pattern']}")
            continue

        char_img = Image.open(alpha_file).convert("RGBA")

        # auto_crop: 투명 영역 자동 제거
        # 모든 캐릭터에 기본 적용 (Style B 알파는 1344x768 씬 전체 크기라 투명 공간이 많음)
        # auto_crop: False로 명시하면 비활성화 가능
        if char.get("auto_crop", True):
            arr = np.array(char_img)
            alpha_mask = arr[:, :, 3] > 10
            if alpha_mask.any():
                rows = np.any(alpha_mask, axis=1)
                cols = np.any(alpha_mask, axis=0)
                rmin, rmax = np.where(rows)[0][[0, -1]]
                cmin, cmax = np.where(cols)[0][[0, -1]]
                pad = 10  # 약간의 여백
                rmin = max(0, rmin - pad)
                rmax = min(arr.shape[0] - 1, rmax + pad)
                cmin = max(0, cmin - pad)
                cmax = min(arr.shape[1] - 1, cmax + pad)
                char_img = char_img.crop((cmin, rmin, cmax + 1, rmax + 1))

        # 포트레이트 스케일링: 캔버스 높이 × height_ratio
        target_h = int(TARGET_H * char.get("height_ratio", 1.3))
        ratio = target_h / char_img.height
        target_w = int(char_img.width * ratio)
        char_img = char_img.resize((target_w, target_h), Image.LANCZOS)

        # 블러 (유령 효과 등)
        if char.get("blur"):
            char_img = char_img.filter(ImageFilter.GaussianBlur(radius=char["blur"]))

        # 투명도
        if char.get("opacity") and char["opacity"] < 1.0:
            arr = np.array(char_img)
            arr[:, :, 3] = (arr[:, :, 3] * char["opacity"]).astype(np.uint8)
            char_img = Image.fromarray(arr)

        # 위치: position=X중심비율, crop_offset=하단 잘림 비율
        position = char.get("position", 0.5)
        crop_offset = char.get("crop_offset", 0.35)

        x = int(position * TARGET_W - target_w / 2)
        y = TARGET_H - target_h + int(TARGET_H * crop_offset)

        # 좌우 반전
        if char.get("flip"):
            char_img = char_img.transpose(Image.FLIP_LEFT_RIGHT)

        # 캔버스 밖으로 넘치는 부분을 클리핑 (안전장치)
        cw, ch = char_img.size
        # 왼쪽 오버플로우
        if x < 0:
            char_img = char_img.crop((-x, 0, cw, ch))
            cw, ch = char_img.size
            x = 0
        # 오른쪽 오버플로우
        if x + cw > TARGET_W:
            char_img = char_img.crop((0, 0, TARGET_W - x, ch))
            cw, ch = char_img.size
        # 상단 오버플로우
        if y < 0:
            char_img = char_img.crop((0, -y, cw, ch))
            cw, ch = char_img.size
            y = 0

        canvas.paste(char_img, (x, y), char_img)

    # 후처리
    if recipe.get("post"):
        canvas = apply_color_grade(canvas, recipe["post"])

    # 저장
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"{ts}_portrait_{scene_id}.png"
    out_path = SCENE_DIR / out_name
    canvas.convert("RGB").save(out_path, quality=95)
    print(f"  ✅ {scene_id}: {out_name} ({recipe.get('note', '')})")
    return out_name


def main():
    print(f"=== 포트레이트 모드 합성 ===")
    targets = sys.argv[1:] if len(sys.argv) > 1 else PORTRAIT_SCENES.keys()

    ok, fail = 0, 0
    for sid in targets:
        if sid not in PORTRAIT_SCENES:
            print(f"  ❌ 알 수 없는 씬: {sid}")
            fail += 1
            continue
        result = composite_portrait(sid, PORTRAIT_SCENES[sid])
        if result:
            ok += 1
        else:
            fail += 1

    print(f"\n=== 결과: {ok}성공 / {fail}실패 ===")


if __name__ == "__main__":
    main()
