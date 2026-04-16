#!/usr/bin/env python3
"""
FEP EP.01 v3 빌드 — LP 애니메이션 + 말풍선 통합
v2에서 발전: 정적 이미지 → LP 캐릭터 영상 합성 + 말풍선 오버레이

사용법:
  python build_video_v3.py preview     # LP+말풍선 적용 프리뷰 (특정 씬)
  python build_video_v3.py clips       # 전체 클립 생성
  python build_video_v3.py longform    # 롱폼 조립
  python build_video_v3.py all         # 전체
"""
import subprocess, sys, os, json, time
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
    import numpy as np
except ImportError:
    print("pip install Pillow numpy")
    sys.exit(1)

# === 경로 ===
BASE_DIR = Path(__file__).parent
V3_DIR = BASE_DIR / "v3_layers"
LOC_DIR = V3_DIR / "locations"
ALPHA_DIR = V3_DIR / "alphas"
SCENE_DIR = V3_DIR / "scenes"
LP_DIR = V3_DIR / "lp"
AUDIO_V2_DIR = BASE_DIR / "audio" / "longform_v2"

def ts():
    """현재 시각 타임스탬프 (YYYYMMDD_HHMMSS)"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
CLIPS_DIR = BASE_DIR / "clips_v3"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = Path(__file__).parent.parent / "assets"
BUBBLE_DIR = ASSETS_DIR / "bubbles"
ANGEL_DIR = ASSETS_DIR / "angel"
DEVIL_DIR = ASSETS_DIR / "devil"

# 폰트
FONT_PATHS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/NanumGothicBold.ttf",
]
def get_font(size=28, bold=False):
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                continue
    return ImageFont.load_default()

FPS = 30
TARGET_W, TARGET_H = 1920, 1080
V3_W, V3_H = 1344, 768  # v3 레이어 원본 해상도

# ── 말풍선 타이밍 오프셋 ──
# TTS 오디오에 자연스러운 리드인 여백이 있어 말풍선이 대사보다 먼저 표시되는 문제 보정
# A/B 타입(말풍선/생각풍선)에만 적용, C/D/E는 의도적 타이밍이므로 미적용
BUBBLE_TIMING_DELAY_SEC = 0.4  # 말풍선 표시를 0.4초 늦춤 (대사 시작과 동기화)

# ── 씬 → LP 캐릭터 매핑 ──
# 각 씬에서 사용하는 캐릭터와 LP 영상 매핑
# lp_key: LP 파일의 캐릭터 식별자 (alpha_B_{lp_key}--{motion}.mp4)
# active_motion: 대사 중 talking, 대기 중 idle

SCENE_LP_MAP = {
    "S-01": {"type": "portrait", "characters": [
        {"alpha": "alpha_A_subin_mirror", "lp": None},  # Style A, LP 미지원
    ]},
    "S-03": {"type": "portrait", "characters": [
        {"alpha": "alpha_A_minjun_sofa", "lp": None},  # Style A
    ]},
    "S-04": {"type": "portrait", "characters": [
        {"alpha": "alpha_A_subin_entrance", "lp": None},  # Style A
        {"alpha": "alpha_A_minjun_sofa", "lp": None},
    ]},
    "S-06": {"type": "portrait", "characters": [
        {"alpha": "alpha_B_subin_lean", "lp": "subin_lean", "motion": "talking"},
        {"alpha": "alpha_B_minjun_shrink", "lp": "minjun_shrink", "motion": "idle"},
    ]},
    "S-07": {"type": "portrait", "characters": [
        {"alpha": "alpha_B_subin_baby_crouch", "lp": "subin_baby_crouch", "motion": "talking"},
        {"alpha": "alpha_C_kongi_v1", "lp": None},  # 아기, LP 없음
    ]},
    "S-09": {"type": "portrait", "characters": [
        {"alpha": "alpha_A_subin_entrance", "lp": None, "blur": 5, "opacity": 0.35},
        {"alpha": "alpha_B_minjun_observe", "lp": "minjun_observe", "motion": "idle"},
    ]},
    "S-11": {"type": "portrait", "characters": [
        {"alpha": "alpha_B_minjun_cornered", "lp": "minjun_cornered", "motion": "idle"},
        {"alpha": "alpha_B_subin_lean", "lp": "subin_lean", "motion": "talking"},
    ]},
    "S-15": {"type": "portrait", "characters": [
        {"alpha": "alpha_A_subin_cafe", "lp": None},
        {"alpha": "alpha_B_jiwoo_cafe", "lp": "jiwoo_cafe", "motion": "idle"},
    ]},
    "S-19": {"type": "portrait", "characters": [
        {"alpha": "alpha_A_subin_cafe", "lp": None},
        {"alpha": "alpha_B_jiwoo_smile", "lp": "jiwoo_smile", "motion": "idle"},
    ]},
    "S-22": {"type": "portrait", "characters": [
        {"alpha": "alpha_B_minjun_cornered", "lp": "minjun_cornered", "motion": "idle"},
        {"alpha": "alpha_B_subin_lean", "lp": "subin_lean", "motion": "idle"},
    ]},
    "S-23": {"type": "portrait", "characters": [
        {"alpha": "alpha_B_subin_standing", "lp": "subin_standing", "motion": "idle"},
        {"alpha": "alpha_B_minjun_standing", "lp": "minjun_standing", "motion": "idle"},
        {"alpha": "alpha_B_jiwoo_standing", "lp": "jiwoo_standing", "motion": "idle"},
    ]},
    # S-10: 민준 내면 — 단색 배경 + LP (portrait 전환)
    "S-10": {"type": "portrait", "characters": [
        {"alpha": "alpha_B_minjun_observe", "lp": "minjun_observe", "motion": "talking"},
    ]},
    # S-16: 지우 내면 갈등 — 카페 BG + LP (portrait 전환)
    "S-16": {"type": "portrait", "characters": [
        {"alpha": "alpha_B_jiwoo_scale", "lp": "jiwoo_scale", "motion": "shy"},
    ]},
    # S-17: 지우 억지 미소 — 카페 BG + LP (핵심 비주얼: 눈과 입의 불일치)
    "S-17": {"type": "portrait", "characters": [
        {"alpha": "alpha_A_subin_cafe", "lp": None},
        {"alpha": "alpha_B_jiwoo_smile", "lp": "jiwoo_smile", "motion": "talking"},
    ]},
    # S-21: 수빈의 밤 — 침실 BG + LP (감정 클라이맥스)
    "S-21": {"type": "portrait", "characters": [
        {"alpha": "alpha_B_subin_night", "lp": "subin_night", "motion": "shy"},
    ]},
    # non-portrait scenes — 정적 이미지
    "S-05": {"type": "scene_static"},
    "S-08": {"type": "scene_static"},
    "S-12": {"type": "scene_static"},
    "S-13": {"type": "scene_static"},
    "S-14": {"type": "scene_static"},
    "S-18": {"type": "scene_static"},
    "S-20": {"type": "scene_static"},
    "S-24": {"type": "scene_static"},
}

# ── 포트레이트 레시피 (v3_composite_portrait.py에서 가져옴) ──
PORTRAIT_RECIPES = {
    "S-01": {
        "bg_pattern": "loc_LOC_bathroom_morning",
        "bg_blur": 4, "bg_brightness": 0.75,
        "characters": [
            {"alpha_pattern": "alpha_A_subin_mirror", "position": 0.50, "height_ratio": 1.35, "crop_offset": 0.38},
        ],
    },
    "S-03": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 4, "bg_brightness": 0.75,
        "characters": [
            {"alpha_pattern": "alpha_A_minjun_sofa", "position": 0.50, "height_ratio": 1.35, "crop_offset": 0.38},
        ],
    },
    "S-04": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 4, "bg_brightness": 0.70,
        "characters": [
            {"alpha_pattern": "alpha_A_subin_entrance", "position": 0.30, "height_ratio": 1.35, "crop_offset": 0.38},
            {"alpha_pattern": "alpha_A_minjun_sofa", "position": 0.72, "height_ratio": 1.20, "crop_offset": 0.35},
        ],
    },
    "S-06": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 5, "bg_brightness": 0.65,
        "characters": [
            {"alpha_pattern": "alpha_B_subin_lean", "position": 0.32, "height_ratio": 1.40, "crop_offset": 0.40},
            {"alpha_pattern": "alpha_B_minjun_shrink", "position": 0.72, "height_ratio": 1.15, "crop_offset": 0.32},
        ],
    },
    "S-07": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 4, "bg_brightness": 0.75,
        "characters": [
            {"alpha_pattern": "alpha_B_subin_baby_crouch", "position": 0.38, "height_ratio": 1.10, "crop_offset": 0.28},
            {"alpha_pattern": "alpha_C_kongi_v1", "position": 0.65, "height_ratio": 0.55, "crop_offset": 0.0},
        ],
    },
    "S-09": {
        "bg_pattern": "loc_LOC_livingroom_cold",
        "bg_blur": 6, "bg_brightness": 0.60,
        "characters": [
            {"alpha_pattern": "alpha_A_subin_entrance", "position": 0.65, "height_ratio": 1.15, "crop_offset": 0.30, "blur": 5, "opacity": 0.35},
            {"alpha_pattern": "alpha_B_minjun_observe", "position": 0.35, "height_ratio": 1.35, "crop_offset": 0.38},
        ],
        "post": "cold_desaturated",
    },
    "S-11": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 5, "bg_brightness": 0.65,
        "characters": [
            {"alpha_pattern": "alpha_B_minjun_cornered", "position": 0.70, "height_ratio": 1.15, "crop_offset": 0.30, "opacity": 0.85},
            {"alpha_pattern": "alpha_B_subin_lean", "position": 0.30, "height_ratio": 1.40, "crop_offset": 0.40},
        ],
    },
    "S-15": {
        "bg_pattern": "loc_LOC_cafe_sunny",
        "bg_blur": 4, "bg_brightness": 0.75,
        "characters": [
            {"alpha_pattern": "alpha_A_subin_cafe", "position": 0.28, "height_ratio": 1.30, "crop_offset": 0.35},
            {"alpha_pattern": "alpha_B_jiwoo_cafe", "position": 0.72, "height_ratio": 1.25, "crop_offset": 0.33},
        ],
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
    },
    # S-10: 민준 내면 모놀로그 — 단색 어두운 배경 + 민준 중앙 대형
    "S-10": {
        "bg_pattern": None,
        "bg_color": (75, 80, 100, 255),  # 어두운 블루-그레이 단색 (각본: "배경이 사라지고")
        "bg_blur": 0, "bg_brightness": 1.0,
        "characters": [
            {"alpha_pattern": "alpha_B_minjun_observe", "position": 0.50, "height_ratio": 1.50, "crop_offset": 0.42},
        ],
    },
    # S-16: 지우 내면 갈등 — 카페 배경 + 지우 중앙 (내면 POV이므로 단독 클로즈업)
    "S-16": {
        "bg_pattern": "loc_LOC_cafe_sunny",
        "bg_blur": 8, "bg_brightness": 0.55,
        "characters": [
            {"alpha_pattern": "alpha_B_jiwoo_scale", "position": 0.50, "height_ratio": 1.40, "crop_offset": 0.38},
        ],
        "post": "cold_desaturated",  # 내면 갈등 → 탈채도
    },
    # S-17: 지우 억지 미소 — 카페 배경 + 수빈(좌) + 지우(우, LP 핵심)
    "S-17": {
        "bg_pattern": "loc_LOC_cafe_sunny",
        "bg_blur": 4, "bg_brightness": 0.72,
        "characters": [
            {"alpha_pattern": "alpha_A_subin_cafe", "position": 0.28, "height_ratio": 1.25, "crop_offset": 0.33},
            {"alpha_pattern": "alpha_B_jiwoo_smile", "position": 0.72, "height_ratio": 1.30, "crop_offset": 0.35},
        ],
    },
    # S-21: 수빈의 밤 — 침실 배경 + 수빈 단독 (감정 클라이맥스)
    "S-21": {
        "bg_pattern": "loc_LOC_bedroom_night",
        "bg_blur": 5, "bg_brightness": 0.50,
        "characters": [
            {"alpha_pattern": "alpha_B_subin_night", "position": 0.50, "height_ratio": 1.45, "crop_offset": 0.40},
        ],
    },
    "S-22": {
        "bg_pattern": "loc_LOC_livingroom_afternoon",
        "bg_blur": 4, "bg_brightness": 0.70,
        "characters": [
            {"alpha_pattern": "alpha_B_minjun_cornered", "position": 0.70, "height_ratio": 1.25, "crop_offset": 0.33},
            {"alpha_pattern": "alpha_B_subin_lean", "position": 0.30, "height_ratio": 1.30, "crop_offset": 0.35},
        ],
        "post": "split_warm_cool",
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
    },
}


# ── 오버레이 매니페스트 (전체 타입 A/B/C/D/E) ──
def load_overlay_manifest():
    manifest_path = BASE_DIR / "text_overlay_v2_manifest.json"
    if not manifest_path.exists():
        return {}
    with open(manifest_path) as f:
        data = json.load(f)
    # (clip_id, scene) → items 매핑
    result = {}
    for entry in data.get("overlays", []):
        scene = entry["scene"]
        clip_id = entry["clip_id"]
        for item in entry.get("items", []):
            if item["type"] in ("A", "B", "C", "D", "E"):
                key = (clip_id, scene)
                if key not in result:
                    result[key] = []
                result[key].append(item)
    return result


# ── 유틸리티 ──
def run_cmd(cmd, desc=""):
    if desc:
        print(f"  → {desc}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ {result.stderr[-300:]}")
        return False
    return True

def get_duration(filepath):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(filepath)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def find_latest(directory, pattern, exclude_alpha=True):
    files = sorted(directory.glob(f"*{pattern}*.png"), reverse=True)
    # _alt 제외, _alpha 제외는 씬 이미지 검색 시에만 (알파 디렉토리에서는 비활성)
    files = [f for f in files if "_alt" not in f.stem]
    if exclude_alpha:
        files = [f for f in files if "_alpha" not in f.stem]
    return files[0] if files else None

def find_lp_video(lp_key, motion="talking"):
    """LP 영상 찾기: alpha_B_{lp_key}--{motion}.mp4
    motion: "talking", "idle" (→ wink/shy 폴백), "shy", "wink" (직접 지정)
    """
    if not lp_key:
        return None
    if motion == "idle":
        # idle: wink → shy 폴백
        search_order = ["wink", "shy"]
    elif motion in ("shy", "wink", "talking"):
        # 직접 지정
        search_order = [motion]
    else:
        search_order = ["talking"]
    for m in search_order:
        pattern = f"alpha_B_{lp_key}--{m}.mp4"
        matches = sorted(LP_DIR.glob(f"*{pattern}"), reverse=True)
        if matches:
            return matches[0]
    return None

def find_v3_scene(scene_id):
    """기존 합성 씬 이미지 찾기 (LP 미적용 폴백)"""
    portrait = sorted(SCENE_DIR.glob(f"*portrait_{scene_id}.png"), reverse=True)
    if portrait:
        return portrait[0]
    scene = sorted(SCENE_DIR.glob(f"*scene_{scene_id}.png"), reverse=True)
    if scene:
        return scene[0]
    return None


# ── LP 캐릭터 프레임 추출 + 크로마키 ──
def extract_lp_frame(lp_video, frame_num):
    """LP 영상에서 특정 프레임 추출 → numpy 배열 (RGBA, 크로마키 적용)"""
    # 프레임 추출
    cmd = ["ffmpeg", "-y", "-i", str(lp_video),
           "-vf", f"select=eq(n\\,{frame_num})",
           "-vframes", "1", "-f", "image2pipe", "-pix_fmt", "rgb24",
           "-vcodec", "rawvideo", "-"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        return None

    # 프레임 해상도 가져오기
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(lp_video)],
        capture_output=True, text=True
    )
    w, h = map(int, probe.stdout.strip().split("x"))

    # raw RGB → numpy
    raw = np.frombuffer(result.stdout, dtype=np.uint8).reshape((h, w, 3))

    # 크로마키: 그린 배경 제거
    r, g, b = raw[:,:,0].astype(float), raw[:,:,1].astype(float), raw[:,:,2].astype(float)
    green_score = g - (r + b) / 2
    threshold = 60
    alpha = np.clip((threshold - green_score) / (threshold * 0.3), 0, 1) * 255
    alpha = alpha.astype(np.uint8)

    # RGBA 합성
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:,:,:3] = raw
    rgba[:,:,3] = alpha

    return rgba


# ── FFmpeg 기반 LP+BG 합성 (프레임 단위 Python 합성보다 빠름) ──
def build_lp_portrait_clip(scene_id, duration, audio_path, output_path):
    """
    포트레이트 씬을 LP 영상으로 빌드:
    1. BG 이미지 → 블러+어둡게 → 영상화
    2. LP 캐릭터 영상 → chromakey로 배경 제거
    3. FFmpeg overlay로 합성
    """
    recipe = PORTRAIT_RECIPES.get(scene_id)
    lp_map = SCENE_LP_MAP.get(scene_id, {})

    if not recipe or lp_map.get("type") != "portrait":
        return False

    # 1. BG 준비 (Pillow → 1920x1080 PNG)
    bg = prepare_bg(recipe)
    if bg is None:
        return False

    bg_1080 = bg.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    bg_path = CLIPS_DIR / f"_temp_{scene_id}_bg.png"
    bg_1080.save(bg_path)

    # 2. LP 캐릭터 정보 수집
    lp_chars = lp_map.get("characters", [])
    recipe_chars = recipe.get("characters", [])

    # LP가 있는 캐릭터와 없는 캐릭터 분리
    has_lp = []
    no_lp = []
    for i, (lp_info, recipe_char) in enumerate(zip(lp_chars, recipe_chars)):
        lp_key = lp_info.get("lp")
        motion = lp_info.get("motion", "talking")
        lp_video = find_lp_video(lp_key, motion)
        if lp_video:
            has_lp.append((i, lp_info, recipe_char, lp_video))
        else:
            no_lp.append((i, recipe_char))

    # 3. 정적 캐릭터는 BG 위에 미리 합성 (Pillow)
    static_bg = bg_1080.copy()
    for i, recipe_char in no_lp:
        paste_static_character(static_bg, recipe_char)

    # 포스트 프로세싱 적용 (정적 부분에만)
    post = recipe.get("post")
    if post:
        static_bg = apply_color_grade(static_bg, post)

    static_bg_path = CLIPS_DIR / f"_temp_{scene_id}_static_bg.png"
    static_bg.save(static_bg_path)

    # 4. LP 캐릭터가 없으면 정적 이미지 영상
    if not has_lp:
        cmd = ["ffmpeg", "-y",
               "-loop", "1", "-i", str(static_bg_path),
               "-i", str(audio_path),
               "-t", str(duration),
               "-c:v", "libx264", "-tune", "stillimage",
               "-c:a", "aac", "-b:a", "192k",
               "-pix_fmt", "yuv420p", "-shortest",
               str(output_path)]
        success = run_cmd(cmd, f"{scene_id}: 정적 포트레이트 ({duration:.1f}s)")
        cleanup_temps(scene_id)
        return success

    # 5. LP 캐릭터 영상을 BG 위에 크로마키 오버레이
    # 각 LP 캐릭터의 위치/스케일 계산 (1920x1080 기준)
    filter_parts = []
    input_args = ["-loop", "1", "-i", str(static_bg_path)]

    for idx, (i, lp_info, recipe_char, lp_video) in enumerate(has_lp):
        input_args += ["-stream_loop", "-1", "-i", str(lp_video)]

        # LP 영상의 캐릭터 위치 계산
        pos = recipe_char.get("position", 0.5)
        h_ratio = recipe_char.get("height_ratio", 1.3)
        crop_off = recipe_char.get("crop_offset", 0.35)
        opacity = recipe_char.get("opacity", 1.0)

        # LP 영상 해상도 → 타겟 크기 계산
        # LP 원본: 1280x730 (v3 레이어 원본에서 생성)
        # 타겟: V3_H * h_ratio 높이로 스케일
        target_h = int(TARGET_H * h_ratio)
        scale_ratio = target_h / 730  # LP 원본 높이
        target_w = int(1280 * scale_ratio)

        # 위치: position은 캐릭터 중심 X
        x = int(TARGET_W * pos - target_w / 2)
        y = TARGET_H - int(target_h * (1 - crop_off))

        # FFmpeg 필터: 크로마키 + 스케일 + 오버레이
        inp_idx = idx + 1  # [0]=bg, [1+]=LP
        filter_parts.append(
            f"[{inp_idx}:v]chromakey=0x30C010:0.12:0.02,"
            f"scale={target_w}:{target_h}:flags=lanczos"
            + (f",colorchannelmixer=aa={opacity}" if opacity < 1.0 else "")
            + f"[lp{idx}]"
        )

    # overlay 체인 구성
    current = "[0:v]"
    for idx in range(len(has_lp)):
        i, lp_info, recipe_char, lp_video = has_lp[idx]
        pos = recipe_char.get("position", 0.5)
        h_ratio = recipe_char.get("height_ratio", 1.3)
        crop_off = recipe_char.get("crop_offset", 0.35)
        target_h = int(TARGET_H * h_ratio)
        scale_ratio = target_h / 730
        target_w = int(1280 * scale_ratio)
        x = int(TARGET_W * pos - target_w / 2)
        y = TARGET_H - int(target_h * (1 - crop_off))

        out_label = f"[ov{idx}]" if idx < len(has_lp) - 1 else "[out]"
        # TRAP-032: shortest=1 제거 — stream_loop -1 LP도 조기 EOF 발생, -t duration만 의존
        filter_parts.append(
            f"{current}[lp{idx}]overlay={x}:{y}:eof_action=repeat{out_label}"
        )
        current = f"[ov{idx}]"

    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"] + input_args + [
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", f"{len(has_lp) + 1}:a",
        "-t", str(duration),
        "-r", str(FPS),
        "-c:v", "libx264", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]

    success = run_cmd(cmd, f"{scene_id}: LP 포트레이트 ({len(has_lp)} LP + {len(no_lp)} static, {duration:.1f}s)")
    cleanup_temps(scene_id)
    return success


def prepare_bg(recipe):
    """포트레이트 배경 준비 (Pillow)"""
    if recipe.get("bg_pattern"):
        bg_file = find_latest(LOC_DIR, recipe["bg_pattern"])
        if not bg_file:
            print(f"  ⚠️ 배경 없음: {recipe['bg_pattern']}")
            return None
        img = Image.open(bg_file).convert("RGBA")
        ratio = max(V3_W / img.width, V3_H / img.height)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        left = (img.width - V3_W) // 2
        top = (img.height - V3_H) // 2
        img = img.crop((left, top, left + V3_W, top + V3_H))
    elif recipe.get("bg_color"):
        img = Image.new("RGBA", (V3_W, V3_H), recipe["bg_color"])
    else:
        img = Image.new("RGBA", (V3_W, V3_H), (240, 240, 240, 255))

    blur = recipe.get("bg_blur", 0)
    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur))
    brightness = recipe.get("bg_brightness", 1.0)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    return img


def paste_static_character(canvas, recipe_char):
    """정적 캐릭터를 캔버스에 합성 (v3_composite_portrait.py 로직 이식)"""
    alpha_file = find_latest(ALPHA_DIR, recipe_char["alpha_pattern"], exclude_alpha=False)
    if not alpha_file:
        print(f"  ⚠️ 알파 없음: {recipe_char['alpha_pattern']}")
        return

    char_img = Image.open(alpha_file).convert("RGBA")

    # auto_crop
    arr = np.array(char_img)
    alpha_mask = arr[:, :, 3] > 10
    if alpha_mask.any():
        rows = np.any(alpha_mask, axis=1)
        cols = np.any(alpha_mask, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        pad = 10
        rmin, rmax = max(0, rmin - pad), min(arr.shape[0]-1, rmax + pad)
        cmin, cmax = max(0, cmin - pad), min(arr.shape[1]-1, cmax + pad)
        char_img = char_img.crop((cmin, rmin, cmax+1, rmax+1))

    # 스케일링 (1920x1080 기준)
    target_h = int(TARGET_H * recipe_char.get("height_ratio", 1.3))
    ratio = target_h / char_img.height
    target_w = int(char_img.width * ratio)
    char_img = char_img.resize((target_w, target_h), Image.LANCZOS)

    # 블러
    if recipe_char.get("blur"):
        char_img = char_img.filter(ImageFilter.GaussianBlur(radius=recipe_char["blur"]))

    # 투명도
    opacity = recipe_char.get("opacity", 1.0)
    if opacity < 1.0:
        arr = np.array(char_img)
        arr[:, :, 3] = (arr[:, :, 3] * opacity).astype(np.uint8)
        char_img = Image.fromarray(arr)

    # 위치 계산
    pos_x = recipe_char.get("position", 0.5)
    crop_off = recipe_char.get("crop_offset", 0.35)
    x = int(TARGET_W * pos_x - target_w / 2)
    y = TARGET_H - int(target_h * (1 - crop_off))

    # 캔버스 클리핑
    cw, ch = char_img.size
    paste_x, paste_y = x, y
    crop_l, crop_t, crop_r, crop_b = 0, 0, cw, ch
    if paste_x < 0:
        crop_l = -paste_x; paste_x = 0
    if paste_y < 0:
        crop_t = -paste_y; paste_y = 0
    if paste_x + (crop_r - crop_l) > TARGET_W:
        crop_r = crop_l + (TARGET_W - paste_x)
    if paste_y + (crop_b - crop_t) > TARGET_H:
        crop_b = crop_t + (TARGET_H - paste_y)

    if crop_r > crop_l and crop_b > crop_t:
        cropped = char_img.crop((crop_l, crop_t, crop_r, crop_b))
        canvas.paste(cropped, (paste_x, paste_y), cropped)


def apply_color_grade(img, tone):
    if tone == "cold_desaturated":
        img = ImageEnhance.Color(img).enhance(0.3)
        arr = np.array(img)
        arr[:,:,0] = np.clip(arr[:,:,0] * 0.7, 0, 255)
        arr[:,:,2] = np.clip(arr[:,:,2] * 1.15, 0, 255)
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


def cleanup_temps(scene_id):
    for f in CLIPS_DIR.glob(f"_temp_{scene_id}*"):
        try:
            f.unlink()
        except:
            pass


# ── 말풍선 오버레이 프레임 생성 ──
SPEAKER_NAME_MAP = {
    "수빈": "subin", "민준": "minjun", "지우": "jiwoo",
    "콩이": "kongi", "천사": "angel", "악마": "devil",
    "내레이터": "narrator",
}

def _get_speaker_position(scene_id, speaker):
    """화자의 캐릭터 포지션을 PORTRAIT_RECIPES에서 조회 → X 좌표 비율 반환"""
    recipe = PORTRAIT_RECIPES.get(scene_id)
    if not recipe:
        return None
    # 한국어 화자명 → 영어 alpha_pattern 키 변환
    speaker_en = SPEAKER_NAME_MAP.get(speaker, speaker.lower() if speaker else "")
    for char in recipe.get("characters", []):
        pat = char.get("alpha_pattern", "").lower()
        if speaker_en and speaker_en in pat:
            return char.get("position", 0.5)
    return None


def render_bubble_overlay(item, canvas_size=(TARGET_W, TARGET_H), scene_id=None):
    """말풍선/생각풍선 오버레이 프레임 생성 → RGBA 이미지
    scene_id가 주어지면 PORTRAIT_RECIPES에서 화자 위치를 참조하여 캐릭터 머리 위에 배치
    """
    overlay = Image.new("RGBA", canvas_size, (0, 0, 0, 0))

    item_type = item["type"]
    text = item["text"]
    position = item.get("position", "center")
    speaker = item.get("speaker", "")
    style = item.get("style_override", {})

    # 화자의 캐릭터 위치 조회 (캐릭터 상단에 말풍선 배치용)
    speaker_x_ratio = _get_speaker_position(scene_id, speaker) if scene_id else None

    if item_type in ("A", "B"):
        # ── 꼬리 방향 결정 (speaker_x_ratio 우선, manifest position 폴백) ──
        # 꼬리가 화자 캐릭터를 향해야 한다:
        #   화자가 화면 좌측(x < 0.5) → left 꼬리 (꼬리가 좌하단)
        #   화자가 화면 우측(x >= 0.5) → right 꼬리 (꼬리가 우하단)
        if speaker_x_ratio is not None:
            tail_side = "left" if speaker_x_ratio < 0.5 else "right"
        elif "left" in position:
            tail_side = "left"
        elif "right" in position:
            tail_side = "right"
        else:
            tail_side = "left"

        # 말풍선 에셋 선택
        if item_type == "A":
            bubble_name = f"speech_bubble_{tail_side}"
        else:
            bubble_name = f"thought_bubble_{tail_side}"

        bubble_file = BUBBLE_DIR / f"{bubble_name}_alpha.png"
        if not bubble_file.exists():
            bubble_file = BUBBLE_DIR / f"{bubble_name}.png"
        if not bubble_file.exists():
            return overlay  # 에셋 없으면 빈 오버레이

        bubble = Image.open(bubble_file).convert("RGBA")

        # 말풍선 크기: 폰트 크기 + 패딩 + 최소 크기
        default_font = 44 if item_type == "A" else 40
        font_size = style.get("font_size", default_font)
        lines = text.split("\n")
        font = get_font(font_size)
        max_line_w = max(font.getbbox(l)[2] - font.getbbox(l)[0] for l in lines)
        line_h = int(font_size * 1.35)
        text_h = len(lines) * line_h
        bubble_w = max(max_line_w + 160, 380)
        bubble_h = max(text_h + 120, 250)
        bubble = bubble.resize((bubble_w, bubble_h), Image.LANCZOS)

        # ── 꼬리-캐릭터 정렬 위치 계산 ──
        # 꼬리 위치 (bubble 내부 비율): left 꼬리는 ~30%, right 꼬리는 ~70%
        TAIL_X_LEFT = 0.30   # speech_bubble_left 꼬리 X 위치 (bubble 좌측 30%)
        TAIL_X_RIGHT = 0.70  # speech_bubble_right 꼬리 X 위치 (bubble 좌측 70%)
        tail_x_ratio = TAIL_X_LEFT if tail_side == "left" else TAIL_X_RIGHT

        if speaker_x_ratio is not None:
            # 꼬리가 캐릭터 머리 위를 가리키도록 오프셋
            speaker_x_px = int(canvas_size[0] * speaker_x_ratio)
            bx = int(speaker_x_px - bubble_w * tail_x_ratio)
        elif "left" in position:
            bx = int(canvas_size[0] * 0.05)
        elif "right" in position:
            bx = int(canvas_size[0] * 0.95 - bubble_w)
        else:
            bx = (canvas_size[0] - bubble_w) // 2

        # 화면 밖으로 나가지 않도록 클램프
        bx = max(20, min(bx, canvas_size[0] - bubble_w - 20))
        by = int(canvas_size[1] * 0.04)  # 상단 4%

        overlay.paste(bubble, (bx, by), bubble)

        # 텍스트 렌더링
        draw = ImageDraw.Draw(overlay)
        text_x = bx + bubble_w // 2
        text_y = by + (bubble_h - text_h) // 2  # 수직 중앙 정렬

        if item_type == "A":
            text_color = style.get("color", "#282828")
            if text_color.startswith("#"):
                r, g, b = int(text_color[1:3], 16), int(text_color[3:5], 16), int(text_color[5:7], 16)
                fill = (r, g, b, 255)
            else:
                fill = (40, 40, 40, 255)
        else:
            # 생각풍선은 연한 블루-그레이
            fill = (60, 60, 80, 230)

        for line in lines:
            bbox = font.getbbox(line)
            lw = bbox[2] - bbox[0]
            draw.text((text_x - lw // 2, text_y), line, fill=fill, font=font)
            text_y += line_h

    elif item_type == "C":
        # 심리학 용어 (하단 자막)
        font_term = get_font(36)
        font_annotation = get_font(24)
        lines = text.split("\n")
        annotation = item.get("annotation", "")

        # 반투명 하단 바
        bar_h = 120 if annotation else 90
        bar_y = canvas_size[1] - bar_h - 30
        bar = Image.new("RGBA", (canvas_size[0], bar_h), (0, 0, 0, 160))
        overlay.paste(bar, (0, bar_y), bar)

        draw = ImageDraw.Draw(overlay)
        # 용어 (크게)
        term_text = lines[0] if lines else ""
        eng_text = lines[1] if len(lines) > 1 else ""
        bbox = font_term.getbbox(term_text)
        tw = bbox[2] - bbox[0]
        draw.text(((canvas_size[0] - tw) // 2, bar_y + 12), term_text,
                  fill=(255, 255, 255, 255), font=font_term)
        # 영어
        if eng_text:
            bbox2 = font_annotation.getbbox(eng_text)
            ew = bbox2[2] - bbox2[0]
            draw.text(((canvas_size[0] - ew) // 2, bar_y + 52), eng_text,
                      fill=(200, 200, 200, 200), font=font_annotation)
        # 주석
        if annotation:
            bbox3 = font_annotation.getbbox(annotation)
            aw = bbox3[2] - bbox3[0]
            draw.text(((canvas_size[0] - aw) // 2, bar_y + 82), annotation,
                      fill=(220, 200, 140, 230), font=font_annotation)

    elif item_type == "D":
        # 킬링 라인 / 강조 텍스트 — 화면 중앙 또는 지정 위치에 큰 텍스트
        font_size = style.get("font_size", 52)
        font = get_font(font_size)
        lines = text.split("\n")
        line_h = int(font_size * 1.4)
        text_h = len(lines) * line_h
        max_line_w = max(font.getbbox(l)[2] - font.getbbox(l)[0] for l in lines)

        # 텍스트 색상
        text_color = style.get("color", "#FFFFFF")
        if text_color.startswith("#"):
            r, g, b = int(text_color[1:3], 16), int(text_color[3:5], 16), int(text_color[5:7], 16)
            fill = (r, g, b, 255)
        else:
            fill = (255, 255, 255, 255)

        # 그림자 효과
        has_shadow = style.get("shadow", True)

        # 위치 계산
        if "center_bottom" in position:
            tx = canvas_size[0] // 2
            ty = int(canvas_size[1] * 0.78) - text_h // 2
        elif "center" in position:
            tx = canvas_size[0] // 2
            ty = (canvas_size[1] - text_h) // 2
        elif "left_label" in position:
            tx = int(canvas_size[0] * 0.22)
            ty = int(canvas_size[1] * 0.35)
        elif "center_label" in position:
            tx = canvas_size[0] // 2
            ty = int(canvas_size[1] * 0.35)
        elif "right_label" in position:
            tx = int(canvas_size[0] * 0.78)
            ty = int(canvas_size[1] * 0.35)
        else:
            tx = canvas_size[0] // 2
            ty = (canvas_size[1] - text_h) // 2

        # 반투명 백드롭 (가독성)
        if "label" not in position:
            pad_x, pad_y = 40, 20
            backdrop = Image.new("RGBA",
                                 (max_line_w + pad_x * 2, text_h + pad_y * 2),
                                 (0, 0, 0, 120))
            bx = tx - max_line_w // 2 - pad_x
            by_pos = ty - pad_y
            overlay.paste(backdrop, (max(0, bx), max(0, by_pos)), backdrop)

        draw = ImageDraw.Draw(overlay)
        current_y = ty
        for line in lines:
            bbox = font.getbbox(line)
            lw = bbox[2] - bbox[0]
            lx = tx - lw // 2
            # 그림자
            if has_shadow:
                draw.text((lx + 2, current_y + 2), line, fill=(0, 0, 0, 180), font=font)
            draw.text((lx, current_y), line, fill=fill, font=font)
            current_y += line_h

    elif item_type == "E":
        # 구조 라벨 — 좌상단 작은 라벨 (막 전환)
        font_size = style.get("font_size", 28)
        font = get_font(font_size)
        lines = text.split("\n")
        line_h = int(font_size * 1.3)
        text_h = len(lines) * line_h
        max_line_w = max(font.getbbox(l)[2] - font.getbbox(l)[0] for l in lines)

        # 반투명 배경 패널
        pad = 16
        panel = Image.new("RGBA",
                          (max_line_w + pad * 2, text_h + pad * 2),
                          (0, 0, 0, 140))
        px, py = 40, 30
        overlay.paste(panel, (px, py), panel)

        draw = ImageDraw.Draw(overlay)
        current_y = py + pad
        for line in lines:
            bbox = font.getbbox(line)
            lw = bbox[2] - bbox[0]
            draw.text((px + pad, current_y), line, fill=(255, 255, 255, 220), font=font)
            current_y += line_h

    return overlay


def build_bubble_overlay_video(scene_id, clip_id, duration, overlays, output_path):
    """말풍선 오버레이 시퀀스 → 투명 PNG 시퀀스 → FFmpeg overlay
    overlays: manifest의 items 리스트 (type A/B/C/D/E)
    """
    if not overlays:
        return None

    temp_dir = CLIPS_DIR / f"_overlay_{scene_id}"
    temp_dir.mkdir(exist_ok=True)

    total_frames = int(duration * FPS)

    # 각 오버레이 아이템의 프레임 범위 계산
    active_items = []
    bubble_delay_frames = int(BUBBLE_TIMING_DELAY_SEC * FPS)  # A/B 타입 딜레이
    for item in overlays:
        start_ratio = item.get("start_ratio", 0.0)
        dur_ratio = item.get("duration_ratio", 1.0)
        start_frame = int(total_frames * start_ratio)
        end_frame = int(total_frames * (start_ratio + dur_ratio))
        # A/B 타입(말풍선/생각풍선)은 대사 동기화를 위해 딜레이 적용
        if item.get("type") in ("A", "B"):
            start_frame = min(start_frame + bubble_delay_frames, total_frames - 1)
            end_frame = min(end_frame + bubble_delay_frames, total_frames)
        # 페이드 인/아웃 (5프레임씩)
        active_items.append({
            "item": item,
            "start": start_frame,
            "end": end_frame,
            "fade_in": 5,
            "fade_out": 5,
        })

    # 프레임별 오버레이 렌더링
    # 최적화: 동일 오버레이가 활성인 구간은 같은 PNG 재사용
    prev_active_set = None
    prev_overlay_path = None
    frame_list = []

    for frame in range(total_frames):
        # 이 프레임에서 활성인 오버레이
        current_active = []
        for ai in active_items:
            if ai["start"] <= frame < ai["end"]:
                # 페이드 계산
                if frame < ai["start"] + ai["fade_in"]:
                    alpha = (frame - ai["start"]) / ai["fade_in"]
                elif frame >= ai["end"] - ai["fade_out"]:
                    alpha = (ai["end"] - frame) / ai["fade_out"]
                else:
                    alpha = 1.0
                current_active.append((id(ai), alpha))

        active_key = tuple(current_active)

        if active_key == prev_active_set and prev_overlay_path:
            frame_list.append(prev_overlay_path)
            continue

        # 새 오버레이 프레임 생성
        canvas = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
        for ai in active_items:
            if ai["start"] <= frame < ai["end"]:
                if frame < ai["start"] + ai["fade_in"]:
                    alpha = (frame - ai["start"]) / ai["fade_in"]
                elif frame >= ai["end"] - ai["fade_out"]:
                    alpha = (ai["end"] - frame) / ai["fade_out"]
                else:
                    alpha = 1.0

                # 멀티세그먼트: 오버레이별 scene_id 지원 (_scene_id 필드 우선)
                item_scene = ai["item"].get("_scene_id", scene_id)
                item_overlay = render_bubble_overlay(ai["item"], scene_id=item_scene)
                if alpha < 1.0:
                    arr = np.array(item_overlay)
                    arr[:, :, 3] = (arr[:, :, 3] * alpha).astype(np.uint8)
                    item_overlay = Image.fromarray(arr)
                canvas = Image.alpha_composite(canvas, item_overlay)

        # 키프레임만 저장 (최적화)
        overlay_path = temp_dir / f"overlay_{frame:05d}.png"
        canvas.save(overlay_path)
        frame_list.append(overlay_path)
        prev_active_set = active_key
        prev_overlay_path = overlay_path

    # PNG 시퀀스 → 영상
    # 프레임 리스트 파일 생성 (중복 참조 포함)
    frame_list_path = temp_dir / "frames.txt"
    with open(frame_list_path, "w") as f:
        for fp in frame_list:
            f.write(f"file '{fp}'\nduration {1/FPS:.6f}\n")

    run_cmd([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(frame_list_path),
        "-c:v", "png", "-pix_fmt", "rgba",
        str(output_path)
    ], f"말풍선 오버레이 시퀀스 ({len(overlays)} items)")

    # 정리
    for f in temp_dir.glob("*.png"):
        f.unlink()
    frame_list_path.unlink()
    try:
        temp_dir.rmdir()
    except:
        pass

    return output_path.exists()


# ── v2 시퀀스 (build_video_v2.py에서 가져옴) ──
V2_SEQUENCE = [
    {"id": "00_prologue", "audio": "S00_S01_prologue.mp3", "beat_after": 0.8,
     "segments": [
         # TRAP-034: 텍스트 분석 기반 ratio 재계산 (글자 수 비례)
         {"scene": "S-00", "ratio": 0.08, "effect": "static"},       # "질문 하나 할게요" (짧은 훅)
         {"scene": "S-01", "ratio": 0.45, "effect": "zoom_in"},      # 수빈 질문 + 해설
         {"scene": "S-23", "ratio": 0.34, "effect": "static"},       # "세 사람의 심리"
         {"scene": "S-02", "ratio": 0.13, "effect": "static"},       # 타이틀 카드 (Phase 1: 3초+ 확보)
     ]},
    {"id": "01_siblings", "audio": "S03_S06_siblings.mp3", "beat_after": 0.8,
     "segments": [
         {"scene": "S-03", "ratio": 0.20, "effect": "static"},       # 민준 거실 도입
         {"scene": "S-04", "ratio": 0.08, "effect": "static"},       # "오빠, 나 예쁘지?" (Phase 2: 전환점 확장)
         {"scene": "S-05", "ratio": 0.31, "effect": "zoom_in"},      # 민준 내면 + "왜 대답 안해?"
         {"scene": "S-06", "ratio": 0.41, "effect": "zoom_in"},      # 강요 대화 + 해설
     ]},
    {"id": "02_baby", "audio": "S07_S08_baby.mp3", "beat_after": 0.8,
     "segments": [
         {"scene": "S-07", "ratio": 0.35, "effect": "static"},       # 콩이+수빈 질문
         {"scene": "S-08", "ratio": 0.65, "effect": "static"},       # 민준 관찰 + 해설
     ]},
    {"id": "03_validation", "audio": "S08_validation.mp3", "beat_after": 0.8,
     "segments": [
         {"scene": "S-07", "ratio": 0.08, "effect": "static"},       # 콩이 콜백 (짧게)
         {"scene": "S-08", "ratio": 0.92, "effect": "zoom_in"},      # 확인 추구 행동 전체 해설
     ]},
    {"id": "04_transition", "audio": "S08_transition.mp3", "beat_after": 1.3,
     "segments": [{"scene": "S-05", "ratio": 1.0, "effect": "zoom_in"}]},
    {"id": "05_minjun_pov", "audio": "S09_S10_minjun_pov.mp3", "beat_after": 0.8,
     "segments": [
         {"scene": "S-09", "ratio": 0.33, "effect": "static"},       # 되감기 + 민준 내면 대사
         {"scene": "S-10", "ratio": 0.67, "effect": "zoom_in"},      # 자율성 침해 해설
     ]},
    {"id": "06_coerced", "audio": "S11_coerced.mp3", "beat_after": 0.8,
     "segments": [{"scene": "S-11", "ratio": 1.0, "effect": "zoom_in"}]},
    {"id": "07_vending", "audio": "S12_vending.mp3", "beat_after": 0.8,
     "segments": [{"scene": "S-12", "ratio": 1.0, "effect": "static"}]},
    {"id": "08_dissonance_boundary", "audio": "S13_S14_dissonance_boundary.mp3", "beat_after": 1.3,
     "segments": [
         {"scene": "S-13", "ratio": 0.50, "effect": "static"},
         {"scene": "S-14", "ratio": 0.50, "effect": "zoom_in"},
     ]},
    {"id": "09_jiwoo_intro", "audio": "S15_S17_jiwoo_intro.mp3", "beat_after": 0.8,
     "segments": [
         {"scene": "S-15", "ratio": 0.15, "effect": "static"},       # "지우야, 새 옷 샀거든?" (짧은 만남)
         {"scene": "S-16", "ratio": 0.78, "effect": "zoom_in"},      # 지우 내면 계산 + 관계유지동기 해설
         {"scene": "S-17", "ratio": 0.07, "effect": "static"},       # "어, 예쁘다!" (짧은 답변)
     ]},
    {"id": "10_rationalize", "audio": "S18_rationalize.mp3", "beat_after": 0.8,
     "segments": [{"scene": "S-18", "ratio": 1.0, "effect": "static"}]},
    {"id": "11_helplessness", "audio": "S19_S20_helplessness.mp3", "beat_after": 1.3,
     "segments": [
         {"scene": "S-19", "ratio": 0.50, "effect": "zoom_in"},
         {"scene": "S-20", "ratio": 0.50, "effect": "static"},
     ]},
    {"id": "12_subin_reversal", "audio": "S21_subin_reversal.mp3", "beat_after": 1.8,
     "segments": [{"scene": "S-21", "ratio": 1.0, "effect": "zoom_in"}]},
    {"id": "13_gaslighting", "audio": "S22_gaslighting.mp3", "beat_after": 0.8,
     "segments": [{"scene": "S-22", "ratio": 1.0, "effect": "static"}]},
    {"id": "14_structure", "audio": "S23_structure.mp3", "beat_after": 1.3,
     "segments": [{"scene": "S-23", "ratio": 1.0, "effect": "static"}]},
    {"id": "15_epilogue", "audio": "S24_S25_epilogue.mp3", "beat_after": 2.3,
     "segments": [{"scene": "S-24", "ratio": 1.0, "effect": "zoom_out"}]},
]


def build_segment_clip(seg, duration, clip_id, output_path):
    """단일 세그먼트 클립 생성 — LP 포트레이트 or 정적 이미지"""
    scene_id = seg["scene"]
    lp_map = SCENE_LP_MAP.get(scene_id, {})

    # LP 포트레이트 가능 여부 확인 (portrait 타입 + PORTRAIT_RECIPES 존재 시)
    if lp_map.get("type") == "portrait":
        has_any_lp = False
        for char in lp_map.get("characters", []):
            if char.get("lp") and find_lp_video(char["lp"], char.get("motion", "talking")):
                has_any_lp = True
                break

        if has_any_lp:
            # LP 포트레이트 빌드 — 무음 영상 생성
            silence_path = CLIPS_DIR / f"_silence_{clip_id}.wav"
            run_cmd(["ffmpeg", "-y",
                     "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
                     "-t", str(duration), str(silence_path)], "무음 생성")
            success = build_lp_portrait_clip(scene_id, duration, silence_path, output_path)
            silence_path.unlink(missing_ok=True)
            if success:
                return True

    # 폴백: 정적 이미지
    image = find_v3_scene(scene_id)
    if not image:
        print(f"    ⚠ {scene_id}: 이미지 없음")
        return False

    # 1920x1080으로 스케일
    run_cmd([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image),
        "-vf", f"scale={TARGET_W}:{TARGET_H}:flags=lanczos",
        "-t", str(duration),
        "-r", str(FPS),
        "-c:v", "libx264", "-tune", "stillimage",
        "-pix_fmt", "yuv420p", "-an",
        str(output_path)
    ], f"  정적: {scene_id} ({duration:.1f}s)")

    return output_path.exists()


def build_clips():
    """전체 클립 생성 — LP + 말풍선"""
    print("\n=== v3 클립 생성 (LP + 말풍선) ===")
    CLIPS_DIR.mkdir(exist_ok=True)
    stamp = ts()

    overlay_data = load_overlay_manifest()

    for idx, item in enumerate(V2_SEQUENCE):
        clip_id = item["id"]
        audio_file = AUDIO_V2_DIR / item["audio"]
        output = CLIPS_DIR / f"{stamp}_clip_{idx:02d}_{clip_id}.mp4"

        if not audio_file.exists():
            print(f"  ⚠ {clip_id}: 오디오 없음 ({item['audio']})")
            continue

        duration = get_duration(audio_file)
        segments = item["segments"]
        print(f"\n[{idx+1}/{len(V2_SEQUENCE)}] {clip_id} ({duration:.1f}s, {len(segments)}씬)")

        if len(segments) == 1:
            seg = segments[0]
            seg_output = CLIPS_DIR / f"_seg_{clip_id}.mp4"
            build_segment_clip(seg, duration, clip_id, seg_output)

            # 말풍선 오버레이 체크
            scene_id = seg["scene"]
            overlays = overlay_data.get((clip_id, scene_id), [])

            if overlays and seg_output.exists():
                # 오버레이 영상 생성 + 합성
                overlay_vid = CLIPS_DIR / f"_overlay_{clip_id}.mov"
                if build_bubble_overlay_video(scene_id, clip_id, duration, overlays, overlay_vid):
                    # 오버레이 합성
                    run_cmd([
                        "ffmpeg", "-y",
                        "-i", str(seg_output),
                        "-i", str(overlay_vid),
                        "-i", str(audio_file),
                        "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1[v]",
                        "-map", "[v]", "-map", "2:a",
                        "-t", str(duration),
                        "-c:v", "libx264", "-crf", "20",
                        "-c:a", "aac", "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        str(output)
                    ], f"오버레이 합성")
                    overlay_vid.unlink(missing_ok=True)
                    seg_output.unlink(missing_ok=True)
                else:
                    # 오버레이 실패 → 세그먼트 + 오디오
                    run_cmd([
                        "ffmpeg", "-y",
                        "-i", str(seg_output), "-i", str(audio_file),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-t", str(duration), "-shortest",
                        str(output)
                    ], "오디오 합성 (오버레이 없음)")
                    seg_output.unlink(missing_ok=True)
            elif seg_output.exists():
                # 오버레이 없음 → 세그먼트 + 오디오
                run_cmd([
                    "ffmpeg", "-y",
                    "-i", str(seg_output), "-i", str(audio_file),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", str(duration), "-shortest",
                    str(output)
                ], "오디오 합성")
                seg_output.unlink(missing_ok=True)
        else:
            # 멀티 세그먼트 — 각각 빌드 후 concat
            temp_dir = CLIPS_DIR / f"_temp_{clip_id}"
            temp_dir.mkdir(exist_ok=True)
            seg_files = []

            for si, seg in enumerate(segments):
                seg_dur = duration * seg["ratio"]
                seg_out = temp_dir / f"seg_{si:02d}.mp4"
                build_segment_clip(seg, seg_dur, f"{clip_id}_s{si}", seg_out)
                if seg_out.exists():
                    seg_files.append(seg_out)

            if seg_files:
                concat_list = temp_dir / "concat.txt"
                with open(concat_list, "w") as f:
                    for sf in seg_files:
                        f.write(f"file '{sf}'\n")

                # TRAP-033: 멀티 세그먼트 concat 시 외부 오디오 명시적 map 필수
                # 세그먼트들의 silent 트랙이 자동 선택되어 실제 오디오가 무시됨
                # TRAP-034: 멀티세그먼트 오버레이 — 세그먼트별 ratio를 전체 클립 기준으로 변환
                all_overlays = []
                cumulative_ratio = 0.0
                for si2, seg2 in enumerate(segments):
                    seg2_scene = seg2["scene"]
                    seg2_ratio = seg2["ratio"]
                    seg_overlays = overlay_data.get((clip_id, seg2_scene), [])
                    for ov in seg_overlays:
                        remapped = dict(ov)
                        orig_start = ov.get("start_ratio", 0.0)
                        orig_dur = ov.get("duration_ratio", 1.0)
                        remapped["start_ratio"] = cumulative_ratio + orig_start * seg2_ratio
                        remapped["duration_ratio"] = orig_dur * seg2_ratio
                        remapped["_scene_id"] = seg2_scene
                        all_overlays.append(remapped)
                    cumulative_ratio += seg2_ratio

                has_overlays = bool(all_overlays)

                if has_overlays:
                    # 오버레이가 있으면: 먼저 비디오만 concat → 오버레이 합성 → 오디오 합성
                    concat_video = temp_dir / "concat_video.mp4"
                    run_cmd([
                        "ffmpeg", "-y",
                        "-f", "concat", "-safe", "0", "-i", str(concat_list),
                        "-c:v", "libx264", "-an",
                        "-pix_fmt", "yuv420p",
                        str(concat_video)
                    ], f"멀티 세그먼트 비디오 concat ({len(seg_files)}개)")

                    overlay_vid = CLIPS_DIR / f"_overlay_{clip_id}.mov"
                    if concat_video.exists() and build_bubble_overlay_video(
                            segments[0]["scene"], clip_id, duration, all_overlays, overlay_vid):
                        run_cmd([
                            "ffmpeg", "-y",
                            "-i", str(concat_video),
                            "-i", str(overlay_vid),
                            "-i", str(audio_file),
                            "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1[v]",
                            "-map", "[v]", "-map", "2:a",
                            "-t", str(duration),
                            "-c:v", "libx264", "-crf", "20",
                            "-c:a", "aac", "-b:a", "192k",
                            "-pix_fmt", "yuv420p",
                            str(output)
                        ], "멀티 세그먼트 오버레이 합성")
                        overlay_vid.unlink(missing_ok=True)
                    else:
                        # 오버레이 실패 → concat_video + 오디오
                        run_cmd([
                            "ffmpeg", "-y",
                            "-i", str(concat_video), "-i", str(audio_file),
                            "-map", "0:v:0", "-map", "1:a:0",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                            "-t", str(duration),
                            str(output)
                        ], "멀티 세그먼트 오디오 합성 (오버레이 없음)")
                    concat_video.unlink(missing_ok=True)
                else:
                    # 오버레이 없음 → 기존대로 concat + 오디오 직접 합성
                    run_cmd([
                        "ffmpeg", "-y",
                        "-f", "concat", "-safe", "0", "-i", str(concat_list),
                        "-i", str(audio_file),
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                        "-t", str(duration), "-pix_fmt", "yuv420p",
                        str(output)
                    ], f"멀티 세그먼트 합성 ({len(seg_files)}개)")

                for sf in seg_files:
                    sf.unlink(missing_ok=True)
                concat_list.unlink(missing_ok=True)
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass

        # 비트 클립
        beat = item.get("beat_after", 0)
        if beat > 0:
            beat_out = CLIPS_DIR / f"{stamp}_clip_{idx:02d}_{clip_id}_beat.mp4"
            run_cmd([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s={TARGET_W}x{TARGET_H}:d={beat}:r={FPS}",
                "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
                "-t", str(beat),
                "-c:v", "libx264", "-c:a", "aac", "-ar", "24000", "-ac", "1",
                "-pix_fmt", "yuv420p",
                str(beat_out)
            ], f"beat ({beat:.1f}s)")

    clip_count = len(list(CLIPS_DIR.glob(f"{stamp}_clip_*.mp4")))
    print(f"\n✓ v3 클립 생성 완료: {clip_count}개")


def build_longform():
    """롱폼 영상 조립"""
    print("\n=== v3 롱폼 조립 ===")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 최신 타임스탬프의 클립 세트를 찾기 (타임스탬프_clip_NN_name.mp4)
    all_clips = sorted([
        f for f in CLIPS_DIR.glob("*_clip_*.mp4")
        if "_temp_" not in str(f)
    ])
    # 가장 최근 빌드 타임스탬프만 사용
    if all_clips:
        latest_ts = all_clips[-1].name[:15]  # YYYYMMDD_HHMMSS
        clips = [f for f in all_clips if f.name.startswith(latest_ts)]
    else:
        # 레거시 호환 (타임스탬프 없는 이전 빌드)
        clips = sorted([
            f for f in CLIPS_DIR.glob("clip_*.mp4")
            if "_temp_" not in str(f)
        ])

    if not clips:
        print("  ✗ 클립 없음. 'clips' 먼저 실행")
        return

    concat_file = CLIPS_DIR / "concat_v3.txt"
    with open(concat_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    stamp = ts()
    output = OUTPUT_DIR / f"{stamp}_EP01_v3_lp_bubble.mp4"

    run_cmd([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-crf", "18", "-c:a", "aac",
        str(output)
    ], "롱폼 연결")

    if output.exists():
        dur = get_duration(output)
        size_mb = output.stat().st_size / 1024 / 1024
        print(f"\n✓ v3 프리뷰 완성: {output.name}")
        print(f"  길이: {dur:.0f}초 = {dur/60:.1f}분")
        print(f"  크기: {size_mb:.1f}MB")


def build_preview():
    """LP+말풍선 적용 프리뷰 — S-06 (가장 드라마틱한 대화 씬)"""
    print("\n=== v3 프리뷰: S-06 (수빈 압박) ===")
    CLIPS_DIR.mkdir(exist_ok=True)

    # S-06: 수빈(talking) + 민준(idle), 말풍선 5개
    audio = AUDIO_V2_DIR / "S03_S06_siblings.mp3"
    if not audio.exists():
        print("  ✗ 오디오 없음")
        return

    total_dur = get_duration(audio)
    # S-06은 전체 오디오의 56% (마지막 세그먼트)
    seg_start_ratio = 0.15 + 0.07 + 0.22  # = 0.44
    seg_dur = total_dur * 0.56
    seg_start = total_dur * seg_start_ratio

    # S-06 세그먼트 오디오 추출
    seg_audio = CLIPS_DIR / "_preview_s06_audio.wav"
    run_cmd([
        "ffmpeg", "-y", "-i", str(audio),
        "-ss", str(seg_start), "-t", str(seg_dur),
        "-ar", "24000", "-ac", "1",
        str(seg_audio)
    ], "S-06 오디오 추출")

    # LP 포트레이트 빌드
    stamp = ts()
    output = CLIPS_DIR / f"{stamp}_preview_S-06_lp_bubble.mp4"
    success = build_lp_portrait_clip("S-06", seg_dur, seg_audio, output)

    if success and output.exists():
        # 말풍선 오버레이
        overlay_data = load_overlay_manifest()
        overlays = overlay_data.get(("01_siblings", "S-06"), [])

        if overlays:
            overlay_vid = CLIPS_DIR / "_preview_overlay.mov"
            build_bubble_overlay_video("S-06", "preview", seg_dur, overlays, overlay_vid)

            if overlay_vid.exists():
                final = CLIPS_DIR / f"{stamp}_preview_S-06_FINAL.mp4"
                run_cmd([
                    "ffmpeg", "-y",
                    "-i", str(output), "-i", str(overlay_vid),
                    "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1[v]",
                    "-map", "[v]", "-map", "0:a",
                    "-r", str(FPS),
                    "-c:v", "libx264", "-crf", "20",
                    "-c:a", "aac", "-pix_fmt", "yuv420p",
                    str(final)
                ], "말풍선 합성")
                overlay_vid.unlink(missing_ok=True)
                if final.exists():
                    dur = get_duration(final)
                    print(f"\n✓ 프리뷰 완성: {final.name} ({dur:.1f}s)")
                    return

        dur = get_duration(output)
        print(f"\n✓ LP 프리뷰 완성 (말풍선 없음): {output.name} ({dur:.1f}s)")
    else:
        print("  ✗ LP 빌드 실패")

    seg_audio.unlink(missing_ok=True)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "preview":
        build_preview()
    elif cmd == "clips":
        build_clips()
    elif cmd == "longform":
        build_longform()
    elif cmd == "all":
        build_clips()
        build_longform()
    else:
        print(f"알 수 없는 명령: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
