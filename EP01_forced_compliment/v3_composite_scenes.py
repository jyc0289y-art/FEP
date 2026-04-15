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
        # 밤 폰빛 — v2: 밝기 상향 + 중앙 림라이트
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.55)  # 0.25→0.55 (캐릭터 가시성 확보)
        arr = np.array(img, dtype=np.float64)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * 1.2, 0, 255)  # 블루 틴트 (약화)
        # 중앙 비네팅 역전: 중앙이 밝고 가장자리가 어둡게 (폰 빛 시뮬레이션)
        h, w = arr.shape[:2]
        Y, X = np.ogrid[:h, :w]
        cx, cy = w * 0.45, h * 0.45  # 약간 좌상단 (캐릭터 얼굴 위치)
        dist = np.sqrt(((X - cx) / (w * 0.5)) ** 2 + ((Y - cy) / (h * 0.5)) ** 2)
        vignette = np.clip(1.0 - dist * 0.4, 0.5, 1.0)  # 0.5~1.0 범위
        for c in range(3):
            arr[:, :, c] = np.clip(arr[:, :, c] * vignette, 0, 255)
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
# 좌표 설계 원칙:
#   - Style A (800x1328 세로): 캔버스 높이 대비 scale로 크기 결정, x/y로 위치 배치
#   - Style B (1344x768 가로): 캔버스와 동일 해상도. scale=1.0이면 1:1 오버레이.
#     캐릭터가 이미지 내 자연스러운 위치에 있으므로 x=0,y=0이 기본.
#     미세 조정만 필요. shift_x, shift_y 개념으로 사용.
# alpha_pattern: 캐릭터 키에 맞춤 (A_xxx = Style A 흰배경, B_xxx = Style B 크로마키)
SCENE_RECIPES = {
    # ── 프롤로그 ──
    "S-01": {
        "bg_pattern": "loc_LOC_bathroom",
        "layers": [
            # 수빈 혼자 거울 보는 장면. 중앙 배치, 전신 보이게.
            {"alpha_pattern": "alpha_A_subin_mirror", "x": 0.28, "y": 0.03, "scale": 0.92}
        ],
        "post": None,
        "note": "거울 앞 수빈 혼자 — 자기만족의 세계 (스타일A)"
    },

    # ── 1막: 그 질문 ──
    "S-03": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            # 민준이 소파에 누워 폰 보는 장면. 소파 중앙 위치.
            {"alpha_pattern": "alpha_A_minjun_sofa", "x": 0.27, "y": 0.05, "scale": 0.88}
        ],
        "post": None,
        "note": "거실 소파 민준 — 폭풍 전 고요 (스타일A)"
    },
    "S-04": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            # 각본: "수빈은 화면 중앙에서 빛을 받고, 민준은 구석에서 그늘에 있다"
            # 민준 먼저(뒤에), 수빈 나중에(앞에) — 레이어 순서 = 그리기 순서
            {"alpha_pattern": "alpha_A_minjun_sofa", "x": 0.62, "y": 0.15, "scale": 0.55, "opacity": 0.8},
            {"alpha_pattern": "alpha_A_subin_entrance", "x": 0.25, "y": 0.02, "scale": 0.92}
        ],
        "post": None,
        "note": "수빈 등장 — 수빈 중앙+빛, 민준 우측 구석+그늘 (스타일A)"
    },
    "S-05": {
        # 각본: "민준의 얼굴 클로즈업. 배경 없이."
        "bg_pattern": None,
        "bg_color": (245, 230, 215, 255),
        "layers": [
            # Style B 클로즈업 — 이미 프레임 채움. 1:1 오버레이.
            {"alpha_pattern": "alpha_B_minjun_reaction", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "민준 리액션 클로즈업 — 추상 배경 (스타일B)"
    },
    "S-06": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            # 각본: "수빈이 민준을 내려다보는 위치. 수빈 크게, 민준 움츠림."
            # 민준(뒤, 우측) → 수빈(앞, 좌측+크게) — 두 캐릭터 모두 보이게 배치
            {"alpha_pattern": "alpha_B_minjun_shrink", "x": 0.25, "y": 0.05, "scale": 0.80},
            {"alpha_pattern": "alpha_B_subin_lean", "x": -0.20, "y": -0.02, "scale": 1.0}
        ],
        "post": None,
        "note": "수빈 압박 — 수빈 크게(지배), 민준 작게(움츠림) (스타일B)"
    },
    "S-07": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            # 각본: "수빈이 콩이 앞에 쪼그려 앉아있다. 콩이는 바닥에."
            # 콩이(작게) 뒤, 수빈(쪼그린 채) 앞
            {"alpha_pattern": "alpha_A_kongi_sitting", "x": 0.55, "y": 0.35, "scale": 0.55},
            {"alpha_pattern": "alpha_B_subin_baby_crouch", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "수빈+콩이 — 수빈 쪼그려 앉고 콩이 바닥 (스타일 혼합)"
    },
    "S-08": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            # 각본: "민준이 소파에서 멀리서 바라본다. 폰 내려놓음. 무언가를 읽는 눈."
            {"alpha_pattern": "alpha_B_minjun_observe", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "민준 관찰 — 소파에서 지켜보는 시선 (스타일B)"
    },

    # ── 2막A: 민준의 진실 ──
    "S-09": {
        # 각본: "같은 거실, 색감 차가움. 수빈 흐릿+멈춤, 민준만 선명."
        "bg_pattern": "loc_LOC_livingroom_cold",
        "layers": [
            {"alpha_pattern": "alpha_A_subin_entrance", "x": 0.52, "y": 0.05, "scale": 0.65, "blur": 5, "opacity": 0.35},
            {"alpha_pattern": "alpha_B_minjun_observe", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": "cold_desaturated",
        "note": "되감기 — 수빈 흐릿(유령), 민준 선명, 차가운 톤"
    },
    "S-10": {
        # 각본: "민준 클로즈업. 배경 완전히 사라짐. 단색."
        "bg_pattern": None,
        "bg_color": (200, 210, 220, 255),
        "layers": [
            {"alpha_pattern": "alpha_B_minjun_fatigue", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "민준 내면 독백 — 피로+짜증 클로즈업 (스타일B)"
    },
    "S-11": {
        # 각본: "민준 보이지 않는 벽에 등. 수빈 환한 미소로 앞에. 수빈만 밝고 민준 어둡다."
        # 민준 우측(뒤), 수빈 좌측(앞) — 좌우 분리 배치
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            {"alpha_pattern": "alpha_B_minjun_cornered", "x": 0.20, "y": 0.0, "scale": 0.90, "opacity": 0.85},
            {"alpha_pattern": "alpha_B_subin_lean", "x": -0.22, "y": -0.02, "scale": 1.0}
        ],
        "post": None,
        "note": "코너에 몰린 민준 — 수빈의 밝은 에너지가 압박 (스타일B)"
    },
    "S-12": {
        # 각본: "민준이 자판기 형태, 수빈이 버튼 누름. 코믹."
        "bg_pattern": None,
        "bg_color": (255, 245, 230, 255),
        "layers": [
            {"alpha_pattern": "alpha_A_minjun_vending", "x": 0.10, "y": -0.08, "scale": 1.30}
        ],
        "post": None,
        "note": "자판기 메타포 — 코믹 환기 (스타일A)"
    },
    "S-13": {
        # 각본: "민준 양쪽 어깨 위 천사/악마. 지친 중립 표정."
        "bg_pattern": None,
        "bg_color": (240, 235, 225, 255),
        "layers": [
            {"alpha_pattern": "alpha_B_minjun_angel", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "천사/악마 인지부조화 (스타일B)"
    },
    "S-14": {
        # 각본: "민준 앞에 투명 방어막. 안쪽 따뜻한 빛. 조용한 단단함."
        "bg_pattern": None,
        "bg_color": (235, 240, 235, 255),
        "layers": [
            {"alpha_pattern": "alpha_B_minjun_boundary", "x": -0.10, "y": -0.15, "scale": 1.35}
        ],
        "post": None,
        "note": "심리적 경계선 — 차분한 단단함 (스타일B)"
    },

    # ── 2막B: 지우의 진실 ──
    "S-15": {
        # 각본: "카페 창가. 수빈 밝은 표정+쇼핑백, 지우 커피 감싸기."
        # 지우(B, 뒤쪽 우측) + 수빈(A, 앞쪽 좌측) — 수빈 스케일 키워서 자연스럽게
        "bg_pattern": "loc_LOC_cafe_sunny",
        "layers": [
            {"alpha_pattern": "alpha_B_jiwoo_cafe", "x": 0.10, "y": 0.0, "scale": 0.90},
            {"alpha_pattern": "alpha_A_subin_cafe", "x": -0.02, "y": -0.02, "scale": 1.0}
        ],
        "post": None,
        "note": "카페 — 수빈(A 밝음) + 지우(B 방어적) 대비"
    },
    "S-16": {
        # 각본: "지우 양 손 저울. 솔직함 vs 관계의 평화. 추상 배경."
        "bg_pattern": None,
        "bg_color": (240, 235, 225, 255),
        "layers": [
            {"alpha_pattern": "alpha_B_jiwoo_scale", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "지우 저울 메타포 — 내면의 계산 (스타일B)"
    },
    "S-17": {
        # 각본: "지우 클로즈업. 입은 웃지만 눈은 죽어있다."
        "bg_pattern": "loc_LOC_cafe_sunny",
        "layers": [
            {"alpha_pattern": "alpha_B_jiwoo_smile", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "지우 강제 미소 — 눈과 입의 불일치 (스타일B)"
    },
    "S-18": {
        # 각본: "지우 커피 마시며 창밖 봄. 밖에 비. 유리창 빗방울."
        "bg_pattern": "loc_LOC_cafe_rainy",
        "layers": [
            {"alpha_pattern": "alpha_B_jiwoo_window", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "지우 창밖 비 — 감정의 외적 투사 (스타일B)"
    },
    "S-19": {
        # 각본: "같은 구도 여러 겹. 지우 표정이 겹칠수록 무뎌진다."
        # 수빈(앞), 지우 4겹(뒤→앞으로 점점 투명)
        "bg_pattern": "loc_LOC_cafe_sunny",
        "layers": [
            {"alpha_pattern": "alpha_A_subin_cafe", "x": 0.0, "y": 0.05, "scale": 0.70},
            {"alpha_pattern": "alpha_B_jiwoo_smile", "x": 0.15, "y": 0.0, "scale": 0.85, "opacity": 0.9},
            {"alpha_pattern": "alpha_B_jiwoo_smile", "x": 0.25, "y": 0.0, "scale": 0.85, "opacity": 0.6},
            {"alpha_pattern": "alpha_B_jiwoo_smile", "x": 0.35, "y": 0.0, "scale": 0.85, "opacity": 0.35},
            {"alpha_pattern": "alpha_B_jiwoo_smile", "x": 0.45, "y": 0.0, "scale": 0.85, "opacity": 0.15}
        ],
        "post": None,
        "note": "다중노출 — 지우 4겹 점점 흐려짐 (학습된 무력감)"
    },
    "S-20": {
        # 각본: "어두운 현관. 신발 안 벗고 문에 등 기대기. 블루-그레이."
        "bg_pattern": "loc_LOC_hallway_dim",
        "layers": [
            {"alpha_pattern": "alpha_B_jiwoo_door", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": "dim_evening",
        "note": "지우 현관문 — 가장 조용하고 슬픈 장면 (스타일B)"
    },

    # ── 2막C: 수빈의 진실 ──
    "S-21": {
        # 각본: "밤. 침대. 폰 파란 빛만. 화장 지운 맨얼굴. 눈이 천장."
        # 배경이 이미 충분히 어두움 — 후처리 없이 BG 자체 분위기 활용
        "bg_pattern": "loc_LOC_bedroom_night",
        "layers": [
            {"alpha_pattern": "alpha_B_subin_night", "x": 0.0, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "수빈 밤 침대 — 감정적 정점, 반전 (스타일B)"
    },

    # ── 3막: 정리 ──
    "S-22": {
        # 각본: "화면 분할. 왼쪽 어두운 가스라이팅, 오른쪽 밝은 강요된 동의."
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "layers": [
            {"alpha_pattern": "alpha_B_minjun_cornered", "x": 0.0, "y": 0.0, "scale": 1.0},
            {"alpha_pattern": "alpha_B_subin_lean", "x": -0.1, "y": 0.0, "scale": 1.0}
        ],
        "post": "split_warm_cool",
        "note": "가스라이팅 ≠ 이 상황 — 좌우 톤 분할 (스타일B)"
    },
    "S-23": {
        # 각본: "수빈, 민준, 지우 나란히. 보이지 않는 실선 연결."
        # 세 명 모두 Style B standing — 각각 1/3 위치에 배치
        "bg_pattern": None,
        "bg_color": (245, 240, 235, 255),
        "layers": [
            {"alpha_pattern": "alpha_B_subin_standing", "x": -0.22, "y": 0.0, "scale": 1.0},
            {"alpha_pattern": "alpha_B_minjun_standing", "x": 0.0, "y": 0.0, "scale": 1.0},
            {"alpha_pattern": "alpha_B_jiwoo_standing", "x": 0.22, "y": 0.0, "scale": 1.0}
        ],
        "post": None,
        "note": "세 사람 나란히 — 각자의 진실 (스타일B)"
    },

    # ── 에필로그 ──
    "S-24": {
        "bg_pattern": "loc_LOC_minimal_chairs",
        "layers": [],
        "post": None,
        "note": "빈 의자 — 네 번째 의자는 시청자 것 (스타일A)"
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
