#!/usr/bin/env python3
"""
v3 Phase 3: 씬 합성
로케이션 배경 + 알파 캐릭터를 Pillow로 합성하여 최종 씬 이미지 생성
타임스탬프 파일명, v3_layers/scenes/ 에 저장
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
META_DIR = V3_DIR / "_meta"

# 출력 해상도
TARGET_W, TARGET_H = 1344, 768


def find_latest(directory, pattern):
    """디렉토리에서 패턴에 맞는 가장 최근 파일 찾기"""
    files = sorted(directory.glob(f"*{pattern}*.png"), reverse=True)
    return files[0] if files else None


def load_and_resize(img_path, target_w, target_h, mode="cover"):
    """이미지 로드 + 리사이즈. mode: cover(크롭), contain(패딩), stretch"""
    img = Image.open(img_path).convert("RGBA")
    if mode == "stretch":
        return img.resize((target_w, target_h), Image.LANCZOS)
    elif mode == "cover":
        # 비율 유지하면서 꽉 차게, 넘치는 부분 크롭
        ratio = max(target_w / img.width, target_h / img.height)
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        return img.crop((left, top, left + target_w, top + target_h))
    else:  # contain
        ratio = min(target_w / img.width, target_h / img.height)
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        x = (target_w - new_w) // 2
        y = (target_h - new_h) // 2
        canvas.paste(img, (x, y))
        return canvas


def apply_color_grade(img, tone="warm"):
    """색보정 적용"""
    if tone == "cold_desaturated":
        # 차가운 블루-그레이 톤
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.3)  # 채도 70% 감소
        # 블루 틴트 추가
        arr = np.array(img)
        arr[:, :, 0] = np.clip(arr[:, :, 0] * 0.7, 0, 255)  # R 감소
        arr[:, :, 2] = np.clip(arr[:, :, 2] * 1.15, 0, 255)  # B 증가
        return Image.fromarray(arr.astype(np.uint8))
    elif tone == "dim_evening":
        # 어두운 저녁
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.5)
        enhancer = ImageEnhance.Color(img)
        return enhancer.enhance(0.6)
    elif tone == "night_phone":
        # 밤 폰빛
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.25)
        arr = np.array(img)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * 1.3, 0, 255)  # 블루 틴트
        return Image.fromarray(arr.astype(np.uint8))
    elif tone == "split_warm_cool":
        # 좌우 분할 (왼쪽 차가운, 오른쪽 따뜻한)
        arr = np.array(img)
        mid = arr.shape[1] // 2
        # 왼쪽: 차가운 블루
        arr[:, :mid, 0] = np.clip(arr[:, :mid, 0] * 0.7, 0, 255)
        arr[:, :mid, 2] = np.clip(arr[:, :mid, 2] * 1.2, 0, 255)
        # 오른쪽: 따뜻한
        arr[:, mid:, 0] = np.clip(arr[:, mid:, 0] * 1.1, 0, 255)
        arr[:, mid:, 2] = np.clip(arr[:, mid:, 2] * 0.85, 0, 255)
        return Image.fromarray(arr.astype(np.uint8))
    return img


def make_blurry(img, radius=5):
    """흐릿하게 만들기 (되감기 씬의 수빈 등)"""
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def adjust_opacity(img, opacity):
    """투명도 조절 (0.0~1.0)"""
    arr = np.array(img)
    arr[:, :, 3] = (arr[:, :, 3] * opacity).astype(np.uint8)
    return Image.fromarray(arr)


# === 씬별 합성 레시피 ===
# 각 씬은 배경 + 캐릭터 배치 + 후처리를 정의
SCENE_RECIPES = {
    "S-01": {
        "bg_pattern": "loc_LOC_bathroom",
        "layers": [
            {"alpha_pattern": "alpha_subin_mirror", "x": 0.35, "y": 0.1, "scale": 0.85}
        ],
        "post": None,
        "note": "거울 앞 수빈"
    },
    "S-03": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            {"alpha_pattern": "alpha_minjun_sofa_lazy", "x": 0.15, "y": 0.2, "scale": 0.9}
        ],
        "post": None,
        "note": "거실 소파 민준"
    },
    "S-04": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            {"alpha_pattern": "alpha_minjun_sofa_lazy", "x": 0.6, "y": 0.25, "scale": 0.55, "opacity": 0.85},
            {"alpha_pattern": "alpha_subin_entrance", "x": 0.2, "y": 0.05, "scale": 0.85}
        ],
        "post": None,
        "note": "수빈 등장 (수빈 중앙, 민준 구석)"
    },
    "S-05": {
        "bg_pattern": None,
        "bg_color": (245, 230, 215, 255),
        "layers": [
            {"alpha_pattern": "alpha_minjun_reaction", "x": 0.15, "y": 0.05, "scale": 1.0}
        ],
        "post": None,
        "note": "민준 리액션 클로즈업 (추상 배경)"
    },
    "S-06": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            {"alpha_pattern": "alpha_minjun_sofa_shrink", "x": 0.55, "y": 0.2, "scale": 0.65},
            {"alpha_pattern": "alpha_subin_lean", "x": 0.15, "y": 0.0, "scale": 0.9}
        ],
        "post": None,
        "note": "수빈 압박 (내려다보는 구도)"
    },
    "S-07": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            {"alpha_pattern": "alpha_kongi_sitting", "x": 0.45, "y": 0.45, "scale": 0.4},
            {"alpha_pattern": "alpha_subin_baby", "x": 0.2, "y": 0.15, "scale": 0.75}
        ],
        "post": None,
        "note": "수빈+콩이"
    },
    "S-08": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            {"alpha_pattern": "alpha_minjun_observing", "x": 0.3, "y": 0.15, "scale": 0.75}
        ],
        "post": None,
        "note": "민준 관찰"
    },
    "S-09": {
        "bg_pattern": "loc_LOC_livingroom_cold",
        "layers": [
            {"alpha_pattern": "alpha_subin_entrance", "x": 0.55, "y": 0.1, "scale": 0.7, "blur": 5, "opacity": 0.4},
            {"alpha_pattern": "alpha_minjun_observing", "x": 0.2, "y": 0.15, "scale": 0.8}
        ],
        "post": "cold_desaturated",
        "note": "되감기 (수빈 흐릿, 민준 선명, 차가운 톤)"
    },
    "S-10": {
        "bg_pattern": None,
        "bg_color": (200, 210, 220, 255),
        "layers": [
            {"alpha_pattern": "alpha_minjun_closeup_fatigue", "x": 0.15, "y": 0.05, "scale": 1.0}
        ],
        "post": None,
        "note": "민준 내면 클로즈업 (추상 배경)"
    },
    "S-11": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            {"alpha_pattern": "alpha_minjun_cornered", "x": 0.6, "y": 0.1, "scale": 0.7},
            {"alpha_pattern": "alpha_subin_entrance", "x": 0.15, "y": 0.05, "scale": 0.8}
        ],
        "post": None,
        "note": "코너에 몰린 민준 (드라마틱 조명은 후처리)"
    },
    "S-12": {
        "bg_pattern": None,
        "bg_color": (255, 245, 230, 255),
        "layers": [
            {"alpha_pattern": "alpha_minjun_vending", "x": 0.2, "y": 0.05, "scale": 0.9}
        ],
        "post": None,
        "note": "자판기 메타포"
    },
    "S-13": {
        "bg_pattern": None,
        "bg_color": (240, 235, 225, 255),
        "layers": [
            {"alpha_pattern": "alpha_minjun_angel_devil", "x": 0.2, "y": 0.05, "scale": 0.9}
        ],
        "post": None,
        "note": "천사/악마"
    },
    "S-14": {
        "bg_pattern": None,
        "bg_color": (235, 240, 235, 255),
        "layers": [
            {"alpha_pattern": "alpha_minjun_boundary", "x": 0.2, "y": 0.05, "scale": 0.9}
        ],
        "post": None,
        "note": "방어막/경계선"
    },
    "S-15": {
        "bg_pattern": "loc_LOC_cafe_sunny",
        "layers": [
            {"alpha_pattern": "alpha_jiwoo_cafe_defensive", "x": 0.55, "y": 0.1, "scale": 0.7},
            {"alpha_pattern": "alpha_subin_cafe_bright", "x": 0.1, "y": 0.08, "scale": 0.7}
        ],
        "post": None,
        "note": "카페 수빈+지우"
    },
    "S-16": {
        "bg_pattern": None,
        "bg_color": (240, 235, 225, 255),
        "layers": [
            {"alpha_pattern": "alpha_jiwoo_scale", "x": 0.2, "y": 0.05, "scale": 0.9}
        ],
        "post": None,
        "note": "지우 저울 메타포"
    },
    "S-17": {
        "bg_pattern": "loc_LOC_cafe_sunny",
        "layers": [
            {"alpha_pattern": "alpha_jiwoo_forced_smile", "x": 0.15, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "지우 강제 미소 클로즈업"
    },
    "S-18": {
        "bg_pattern": "loc_LOC_cafe_rainy",
        "layers": [
            {"alpha_pattern": "alpha_jiwoo_window_rain", "x": 0.3, "y": 0.1, "scale": 0.8}
        ],
        "post": None,
        "note": "지우 창밖 비"
    },
    "S-19": {
        "bg_pattern": "loc_LOC_cafe_sunny",
        "layers": [
            {"alpha_pattern": "alpha_subin_cafe_bright", "x": 0.05, "y": 0.08, "scale": 0.65},
            {"alpha_pattern": "alpha_jiwoo_forced_smile", "x": 0.35, "y": 0.08, "scale": 0.6, "opacity": 0.9},
            {"alpha_pattern": "alpha_jiwoo_forced_smile", "x": 0.45, "y": 0.08, "scale": 0.6, "opacity": 0.6},
            {"alpha_pattern": "alpha_jiwoo_forced_smile", "x": 0.55, "y": 0.08, "scale": 0.6, "opacity": 0.35},
            {"alpha_pattern": "alpha_jiwoo_forced_smile", "x": 0.65, "y": 0.08, "scale": 0.6, "opacity": 0.15}
        ],
        "post": None,
        "note": "다중노출 반복 (지우 4겹 점점 흐려짐)"
    },
    "S-20": {
        "bg_pattern": "loc_LOC_hallway_dim",
        "layers": [
            {"alpha_pattern": "alpha_jiwoo_door_lean", "x": 0.3, "y": 0.0, "scale": 0.9}
        ],
        "post": "dim_evening",
        "note": "지우 현관문 기대기"
    },
    "S-21": {
        "bg_pattern": "loc_LOC_bedroom_night",
        "layers": [
            {"alpha_pattern": "alpha_subin_night_bed", "x": 0.15, "y": 0.2, "scale": 0.85}
        ],
        "post": "night_phone",
        "note": "수빈 밤 침대"
    },
    "S-22": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            {"alpha_pattern": "alpha_minjun_cornered", "x": 0.6, "y": 0.1, "scale": 0.65},
            {"alpha_pattern": "alpha_subin_entrance", "x": 0.15, "y": 0.05, "scale": 0.7}
        ],
        "post": "split_warm_cool",
        "note": "가스라이팅 vs 강요된 동의 비교 (분할)"
    },
    "S-23": {
        "bg_pattern": None,
        "bg_color": (245, 240, 235, 255),
        "layers": [
            {"alpha_pattern": "alpha_subin_standing_lineup", "x": 0.1, "y": 0.05, "scale": 0.75},
            {"alpha_pattern": "alpha_minjun_standing_lineup", "x": 0.35, "y": 0.05, "scale": 0.75},
            {"alpha_pattern": "alpha_jiwoo_standing_lineup", "x": 0.6, "y": 0.05, "scale": 0.75}
        ],
        "post": None,
        "note": "세 사람 나란히"
    },
    "S-24": {
        "bg_pattern": "loc_LOC_minimal_chairs",
        "layers": [],
        "post": None,
        "note": "빈 의자 (인물 없음, 배경이 완성본)"
    }
}


def composite_scene(scene_id, recipe):
    """단일 씬 합성"""
    # 1. 배경 준비
    if recipe.get("bg_pattern"):
        bg_file = find_latest(LOC_DIR, recipe["bg_pattern"])
        if not bg_file:
            print(f"  ⚠️ 배경 없음: {recipe['bg_pattern']}")
            return None
        canvas = load_and_resize(bg_file, TARGET_W, TARGET_H, mode="cover")
    elif recipe.get("bg_color"):
        canvas = Image.new("RGBA", (TARGET_W, TARGET_H), recipe["bg_color"])
    else:
        canvas = Image.new("RGBA", (TARGET_W, TARGET_H), (240, 240, 240, 255))

    # 2. 캐릭터 레이어 합성
    for layer in recipe.get("layers", []):
        alpha_file = find_latest(ALPHA_DIR, layer["alpha_pattern"])
        if not alpha_file:
            print(f"  ⚠️ 알파 없음: {layer['alpha_pattern']}")
            continue

        char_img = Image.open(alpha_file).convert("RGBA")

        # 스케일
        scale = layer.get("scale", 1.0)
        new_h = int(TARGET_H * scale)
        ratio = new_h / char_img.height
        new_w = int(char_img.width * ratio)
        char_img = char_img.resize((new_w, new_h), Image.LANCZOS)

        # 블러 (되감기 씬 등)
        if layer.get("blur"):
            char_img = make_blurry(char_img, layer["blur"])

        # 투명도
        if layer.get("opacity") and layer["opacity"] < 1.0:
            char_img = adjust_opacity(char_img, layer["opacity"])

        # 위치 (비율 기반)
        x = int(layer.get("x", 0) * TARGET_W)
        y = int(layer.get("y", 0) * TARGET_H)

        # 합성
        canvas.paste(char_img, (x, y), char_img)

    # 3. 후처리
    if recipe.get("post"):
        canvas = apply_color_grade(canvas, recipe["post"])

    # 4. 저장
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"{ts}_scene_{scene_id}.png"
    out_path = SCENE_DIR / out_name
    canvas.convert("RGB").save(out_path, quality=95)
    print(f"  ✅ {scene_id}: {out_name} ({recipe.get('note', '')})")
    return out_name


def main():
    print(f"=== v3 Phase 3: 씬 합성 ===")

    # 사용 가능한 리소스 확인
    loc_files = list(LOC_DIR.glob("*.png"))
    alpha_files = list(ALPHA_DIR.glob("*.png"))
    print(f"로케이션: {len(loc_files)}장, 알파: {len(alpha_files)}장")

    if not loc_files and not alpha_files:
        print("❌ 리소스 없음. Phase 1,2를 먼저 실행하세요.")
        return

    # 특정 씬만 합성
    targets = sys.argv[1:] if len(sys.argv) > 1 else SCENE_RECIPES.keys()

    results = {"success": [], "failed": []}
    for scene_id in targets:
        if scene_id not in SCENE_RECIPES:
            print(f"  ❌ 알 수 없는 씬: {scene_id}")
            results["failed"].append(scene_id)
            continue

        recipe = SCENE_RECIPES[scene_id]
        out = composite_scene(scene_id, recipe)
        if out:
            results["success"].append(scene_id)
        else:
            results["failed"].append(scene_id)

    print(f"\n=== 결과: {len(results['success'])}성공 / {len(results['failed'])}실패 ===")
    if results["failed"]:
        print(f"실패: {', '.join(results['failed'])}")


if __name__ == "__main__":
    main()
