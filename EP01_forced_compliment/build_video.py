#!/usr/bin/env python3
"""
FEP EP.01 "강요된 칭찬의 심리학" — 영상 빌드 스크립트
CineLink(P16) FFmpeg 패턴 참조, FEP 전용 직접 구현

사용법:
  python build_video.py clips                # 씬별 클립 생성 (이미지+오디오→mp4)
  python build_video.py longform             # 롱폼 최종 영상 조립
  python build_video.py shorts               # 쇼츠 7편 생성
  python build_video.py overlay [--lang XX]  # 텍스트 오버레이 (ko|ja|en, 기본 ko)
  python build_video.py all                  # 전체 실행
"""

import subprocess
import json
import os
import sys
from pathlib import Path

# === 설정 ===
BASE_DIR = Path(__file__).parent
SCENES_DIR = BASE_DIR / "scenes"
AUDIO_LONGFORM = BASE_DIR / "audio" / "longform"
AUDIO_SHORTS = BASE_DIR / "audio" / "shorts"
CLIPS_DIR = BASE_DIR / "clips"
OUTPUT_DIR = BASE_DIR / "output"
OVERLAY_DIR = BASE_DIR / "overlaid"
LIVEPORTRAIT_DIR = BASE_DIR / "liveportrait_out"
MANIFEST_PATH = BASE_DIR / "text_overlay_manifest.json"

# 영상 설정
FPS = 30
RESOLUTION = "1920x1080"
SHORTS_RESOLUTION = "1080x1920"
FADE_DURATION = 0.5  # 씬 전환 페이드 (초)

# 숨쉬기(Breathing) 강도 설정 — 인터렉티브 조절용
# intensity 1.0 = 현재 기본값. 0 = 정지, 2.0 = 2배 역동적
# CLI: python build_video.py clips --breathing 1.5
BREATHING_INTENSITY = 1.0  # 0.0 ~ 3.0 권장

# LivePortrait 애니메이션 모드
# --liveportrait CLI 플래그로 활성화. 활성화 시 liveportrait_out/ 영상을 소스로 사용
USE_LIVEPORTRAIT = False

# 폰트: 언어별 매핑
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
FONTS = {
    "ko": "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "ja": "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "en": "/System/Library/Fonts/Helvetica.ttc",
}

# 오버레이 타입별 위치/스타일 설정 (1920x1080 기준)
# x, y: 텍스트 기준점 좌표  fontsize: 크기  fontcolor: 색
# box: 반투명 배경 사용 여부  align: 정렬 (center=중앙)
OVERLAY_STYLES = {
    "speech_bubble": {
        "x": "(w-text_w)/2",
        "y": "h*0.12",
        "fontsize": 52,
        "fontcolor": "white",
        "borderw": 3,
        "bordercolor": "black",
        "box": True,
        "boxcolor": "black@0.45",
        "boxborderw": 16,
    },
    "thought_bubble": {
        "x": "(w-text_w)/2",
        "y": "h*0.15",
        "fontsize": 46,
        "fontcolor": "#E0E0E0",
        "borderw": 2,
        "bordercolor": "black",
        "box": True,
        "boxcolor": "black@0.55",
        "boxborderw": 18,
    },
    "bubbles_fill": {
        "x": "(w-text_w)/2",
        "y": "h*0.45",
        "fontsize": 60,
        "fontcolor": "white",
        "borderw": 3,
        "bordercolor": "black",
        "box": False,
    },
    "button_label": {
        "x": "(w-text_w)/2",
        "y": "h*0.52",
        "fontsize": 48,
        "fontcolor": "white",
        "borderw": 2,
        "bordercolor": "black",
        "box": True,
        "boxcolor": "#333333@0.7",
        "boxborderw": 14,
    },
    "angel_bubble": {
        "x": "w*0.15",
        "y": "h*0.10",
        "fontsize": 42,
        "fontcolor": "#FFFDE7",
        "borderw": 2,
        "bordercolor": "black",
        "box": True,
        "boxcolor": "#1565C0@0.5",
        "boxborderw": 14,
    },
    "devil_bubble": {
        "x": "w*0.55",
        "y": "h*0.10",
        "fontsize": 42,
        "fontcolor": "#FFCDD2",
        "borderw": 2,
        "bordercolor": "black",
        "box": True,
        "boxcolor": "#B71C1C@0.5",
        "boxborderw": 14,
    },
    "scale_label": {
        # 저울 왼쪽/오른쪽 라벨 — 배열의 [0]=왼쪽, [1]=오른쪽
        "positions": [
            {"x": "w*0.15", "y": "h*0.78"},
            {"x": "w*0.65", "y": "h*0.78"},
        ],
        "fontsize": 44,
        "fontcolor": "white",
        "borderw": 2,
        "bordercolor": "black",
        "box": True,
        "boxcolor": "black@0.5",
        "boxborderw": 12,
    },
    "split_labels": {
        # 분할 화면 왼쪽/오른쪽
        "positions": [
            {"x": "w*0.05", "y": "h*0.80"},
            {"x": "w*0.52", "y": "h*0.80"},
        ],
        "fontsize": 40,
        "fontcolor": "white",
        "borderw": 2,
        "bordercolor": "black",
        "box": True,
        "boxcolor": "black@0.55",
        "boxborderw": 12,
    },
    "character_labels": {
        # 세 캐릭터 라벨: 좌/중/우
        "positions": [
            {"x": "w*0.05", "y": "h*0.85"},
            {"x": "(w-text_w)/2", "y": "h*0.85"},
            {"x": "w*0.72", "y": "h*0.85"},
        ],
        "fontsize": 38,
        "fontcolor": "white",
        "borderw": 2,
        "bordercolor": "black",
        "box": True,
        "boxcolor": "black@0.55",
        "boxborderw": 10,
    },
    "cta": {
        "x": "(w-text_w)/2",
        "y": "h*0.82",
        "fontsize": 56,
        "fontcolor": "#FFD600",
        "borderw": 3,
        "bordercolor": "black",
        "box": True,
        "boxcolor": "black@0.5",
        "boxborderw": 20,
    },
}

# Ken Burns 효과 매핑 (씬별)
# CineLink 가이드 참조: zoom_in, pan_left, pan_right, zoom_out, static
SCENE_EFFECTS = {
    "scene_01": "zoom_in",      # 인트로: 시선 집중
    "scene_02": "zoom_in",      # 확인추구: 다가가는 느낌
    "scene_03": "static",       # 강요된동의: 긴장감 유지
    "scene_04": "zoom_out",     # 나르시시즘: 말풍선 전체 보기
    "scene_05": "zoom_in",      # 아기: 가까이 들여다보기
    "scene_06": "static",       # 자율성: 생각 버블 정적
    "scene_07": "zoom_out",     # 자판기: 유머러스 전체샷
    "scene_08": "static",       # 인지부조화: 천사/악마 양쪽
    "scene_09": "zoom_in",      # 경계: 방어막 집중
    "scene_10": "pan_left",     # 관계유지: 저울 좌우 보기
    "scene_11": "zoom_in",      # 합리화: 생각 버블 집중
    "scene_12": "zoom_out",     # 무력감: 잔상 펼쳐지기
    "scene_13": "static",       # 가스라이팅: 분할 화면
    "scene_14": "zoom_out",     # 정리: 세 캐릭터 전체
    "scene_15": "static",       # 아웃트로: CTA
}

# B컷 설정 — 긴 씬(17초+)에 서브 일러스트를 삽입하여 정지 화면 어색함 해소
# 구조: scene_name → [{cut_at: 비율(0~1), image: 파일명, effect: 효과}, ...]
# cut_at: 전체 씬 길이 대비 전환 시점 (0.5 = 절반 지점)
# image: scenes/ 내 B컷 이미지 파일명 (확장자 제외)
# effect: B컷 구간의 Ken Burns 효과 (생략 시 메인과 반대 효과 자동 적용)
# 에피소드별로 이 딕셔너리만 수정하면 됨
SCENE_BCUTS = {
    "scene_03": [{"cut_at": 0.5, "image": "scene_03b_minjun_awkward", "effect": "zoom_in"}],
    "scene_05": [{"cut_at": 0.55, "image": "scene_05b_baby_closeup", "effect": "zoom_out"}],
    "scene_06": [{"cut_at": 0.5, "image": "scene_06b_thought_tangle", "effect": "zoom_in"}],
    "scene_10": [{"cut_at": 0.45, "image": "scene_10b_scale_tilt", "effect": "zoom_in"}],
    "scene_12": [{"cut_at": 0.5, "image": "scene_12b_ghost_repeat", "effect": "zoom_in"}],
    "scene_14": [
        {"cut_at": 0.33, "image": "scene_14b_subin_solo", "effect": "zoom_in"},
        {"cut_at": 0.66, "image": "scene_14c_minjun_solo", "effect": "zoom_in"},
    ],
}

# 씬-오디오 매핑
SCENE_AUDIO = {
    "scene_01": "scene_01_intro.mp3",
    "scene_02": "scene_02_validation.mp3",
    "scene_03": "scene_03_coerced.mp3",
    "scene_04": "scene_04_narcissistic.mp3",
    "scene_05": "scene_05_baby.mp3",
    "scene_06": "scene_06_autonomy.mp3",
    "scene_07": "scene_07_vending.mp3",
    "scene_08": "scene_08_dissonance.mp3",
    "scene_09": "scene_09_boundary.mp3",
    "scene_10": "scene_10_relational.mp3",
    "scene_11": "scene_11_rationalize.mp3",
    "scene_12": "scene_12_helplessness.mp3",
    "scene_13": "scene_13_gaslighting.mp3",
    "scene_14": "scene_14_summary.mp3",
    "scene_15": "scene_15_outro.mp3",
}

# 쇼츠 구성
# 각 쇼츠는 segments 리스트로 구성: 나레이션 흐름에 맞춰 여러 씬 이미지를 시간 분할
# segment: {"scene": 이미지명, "ratio": 시간비율, "crop": 크롭모드}
#   crop 모드: center / left / right / split_lr / split_rl
#   ratio: 해당 이미지가 차지하는 시간 비율 (합계 = 1.0)
#   crop 생략 시 "center" 기본
# 에피소드별로 이 딕셔너리만 교체하면 됨
SHORTS_CONFIG = [
    {
        "name": "EP01_teaser_01", "audio": "teaser_01.mp3",
        # 나레이션: "나 예쁘지?" → 불편함 → "심리학에 답이 있습니다"
        "segments": [
            {"scene": "scene_01", "ratio": 0.35, "crop": "center"},   # 수빈 거울
            {"scene": "scene_03", "ratio": 0.35, "crop": "right"},    # 수빈 표정 (마주보는 구도→right)
            {"scene": "scene_05", "ratio": 0.30, "crop": "center"},   # 수빈+아기
        ],
    },
    {
        "name": "EP01_teaser_02", "audio": "teaser_02.mp3",
        # 나레이션: "가스라이팅이라고 부르는데" → "강요된 동의"
        "segments": [
            {"scene": "scene_13", "ratio": 0.5, "crop": "left"},      # 가스라이팅 비교
            {"scene": "scene_03", "ratio": 0.5, "crop": "right"},     # 수빈 표정 (마주보는 구도→right)
        ],
    },
    {
        "name": "EP01_deep_01", "audio": "deep_01.mp3",
        # 나레이션: "수빈이 콩이한테도" → "확인 추구 행동" → "대답을 받아내는 행위"
        "segments": [
            {"scene": "scene_05", "ratio": 0.5, "crop": "center"},    # 수빈+아기
            {"scene": "scene_05b_baby_closeup", "ratio": 0.5, "crop": "center"},  # 아기 클로즈업
        ],
    },
    {
        "name": "EP01_deep_02", "audio": "deep_02.mp3",
        # 나레이션: "칭찬 자판기" → "도구적 관계"
        "segments": [
            {"scene": "scene_07", "ratio": 0.5, "crop": "left"},      # 자판기 민준
            {"scene": "scene_07", "ratio": 0.5, "crop": "right"},     # 자판기 수빈
        ],
    },
    {
        "name": "EP01_deep_03", "audio": "deep_03.mp3",
        # 나레이션: "솔직한 답 vs 원하는 답" → "인지부조화" → "자기 설득"
        "segments": [
            {"scene": "scene_08", "ratio": 0.5, "crop": "center"},    # 천사/악마
            {"scene": "scene_11", "ratio": 0.5, "crop": "center"},    # 합리화
        ],
    },
    {
        "name": "EP01_deep_04", "audio": "deep_04.mp3",
        # 나레이션: "어차피 또 물어볼 거잖아" → "진정성 지불" → "피로감"
        "segments": [
            {"scene": "scene_12", "ratio": 0.5, "crop": "center"},    # 무력감
            {"scene": "scene_12b_ghost_repeat", "ratio": 0.5, "crop": "center"},  # 잔상
        ],
    },
    {
        "name": "EP01_deep_05", "audio": "deep_05.mp3",
        # 나레이션: "소비자, 거부자, 공급자" 3인
        "segments": [
            {"scene": "scene_14", "ratio": 0.35, "crop": "center"},    # 3인 전체
            {"scene": "scene_14b_subin_solo", "ratio": 0.30, "crop": "center"},  # 수빈
            {"scene": "scene_14c_minjun_solo", "ratio": 0.35, "crop": "center"}, # 민준
        ],
    },
]


def run_ffmpeg(args, desc=""):
    """FFmpeg 명령 실행"""
    cmd = ["ffmpeg", "-y"] + args
    print(f"  → {desc}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ 실패: {result.stderr[-200:]}")
        return False
    return True


def get_duration(filepath):
    """ffprobe로 미디어 길이(초) 반환"""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(filepath)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def _scene_rng(seed_str):
    """씬 이름 기반 결정론적 의사난수 생성기 (재현 가능한 '무작위')

    몬테카를로식 접근: 같은 씬은 항상 같은 결과, 다른 씬은 완전히 다른 패턴.
    random 모듈 사용 시 전역 상태 오염 방지를 위해 별도 인스턴스.
    """
    import hashlib
    h = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    # 6개 파라미터용 [0,1) 난수 생성
    vals = []
    for _ in range(12):
        h, r = divmod(h, 1000003)
        vals.append(r / 1000003)
        h = h ^ (r * 31)
    return vals


def ken_burns_filter(effect, duration, resolution=RESOLUTION, breathing=True, scene_seed=""):
    """Ken Burns 효과 + 숨쉬기(Breathing) 필터 생성

    v6: 씬별 랜덤 위상 + 진폭 변동으로 비규칙적 유기적 모션.
    - 위상(phase): 씬 해시 기반 — 모든 씬이 다른 시점에서 시작
    - 진폭(amplitude): ±30% 변동 — 씬마다 미묘하게 다른 역동성
    - 클램핑: 드리프트가 중앙에서 과도하게 벗어나지 않도록 제한
    양자화 방지: 내부 2x 해상도 + Lanczos 다운스케일.
    에피소드 공용: 모든 씬에 자동 적용.
    """
    w, h = map(int, resolution.split("x"))
    frames = int(float(duration) * FPS)

    # 내부 처리 해상도 (2x → 다운스케일로 서브픽셀 부드러움)
    iw, ih = w * 2, h * 2
    ires = f"{iw}x{ih}"
    upscale = f"scale={iw}:{ih}:flags=lanczos,"
    downscale = f",scale={w}:{h}:flags=lanczos"

    if breathing:
        bi = BREATHING_INTENSITY

        # 씬별 랜덤 파라미터 (결정론적 — 같은 씬은 같은 결과)
        rng = _scene_rng(scene_seed or "default")

        # 위상 오프셋: 0 ~ 2π (각 사인파 독립)
        pz1, pz2 = rng[0] * 6.283, rng[1] * 6.283  # 줌 위상
        px1, px2 = rng[2] * 6.283, rng[3] * 6.283  # 수평 위상
        py1, py2 = rng[4] * 6.283, rng[5] * 6.283  # 수직 위상

        # 진폭 변동: 기본값 × (0.7 ~ 1.3)
        az1 = 0.025 * bi * (0.7 + rng[6] * 0.6)
        az2 = 0.015 * bi * (0.7 + rng[7] * 0.6)
        ax1 = 12.0 * bi * (0.7 + rng[8] * 0.6)
        ax2 = 8.0 * bi * (0.7 + rng[9] * 0.6)
        ay1 = 8.0 * bi * (0.7 + rng[10] * 0.6)
        ay2 = 6.0 * bi * (0.7 + rng[11] * 0.6)

        # 줌 브리딩 (2개 주기 합성 + 랜덤 위상)
        bz = f"+{az1:.4f}*sin(on*0.05+{pz1:.3f})+{az2:.4f}*sin(on*0.03+{pz2:.3f})"

        # 수평 드리프트 + 클램핑 (중앙 ±15px@1x 이내)
        raw_dx = f"{ax1:.1f}*sin(on*0.026+{px1:.3f})+{ax2:.1f}*sin(on*0.016+{px2:.3f})"
        dx = f"+max(-30,min(30,{raw_dx}))"

        # 수직 드리프트 + 클램핑 (중앙 ±12px@1x 이내)
        raw_dy = f"{ay1:.1f}*sin(on*0.035+{py1:.3f})+{ay2:.1f}*sin(on*0.019+{py2:.3f})"
        dy = f"+max(-24,min(24,{raw_dy}))"
    else:
        bz, dx, dy = "", "", ""
        upscale, downscale = "", ""
        ires = resolution

    cx = f"iw/2-(iw/zoom/2){dx}"
    cy = f"ih/2-(ih/zoom/2){dy}"

    if effect == "zoom_in":
        zp = (f"zoompan=z='min(zoom+0.0008,1.2){bz}':"
              f"x='{cx}':y='{cy}':"
              f"d={frames}:s={ires}:fps={FPS}")
    elif effect == "zoom_out":
        zp = (f"zoompan=z='if(eq(on,1),1.2,max(zoom-0.0008,1.0)){bz}':"
              f"x='{cx}':y='{cy}':"
              f"d={frames}:s={ires}:fps={FPS}")
    elif effect == "pan_left":
        zp = (f"zoompan=z='1.15{bz}':x='if(eq(on,1),iw/4,x+2)':"
              f"y='ih/2-(ih/zoom/2){dy}':d={frames}:s={ires}:fps={FPS}")
    elif effect == "pan_right":
        zp = (f"zoompan=z='1.15{bz}':x='if(eq(on,1),0,x+2)':"
              f"y='ih/2-(ih/zoom/2){dy}':d={frames}:s={ires}:fps={FPS}")
    else:  # static
        zp = (f"zoompan=z='1.0{bz}':"
              f"x='{cx}':y='{cy}':"
              f"d={frames}:s={ires}:fps={FPS}")

    return f"{upscale}{zp}{downscale}"


# 오버레이 사용 플래그 (--overlay 시 True로 설정)
USE_OVERLAY = False
OVERLAY_LANG = "ko"

# 패럴랙스 플래그 (--parallax 시 True로 설정)
USE_PARALLAX = False
PARALLAX_DIR = None  # 전경 분리 캐시 디렉토리 (초기화 시 설정)


def find_scene_image(scene_name):
    """씬 이미지 파일 찾기 (확장자 유연, _alt 제외)

    USE_OVERLAY=True일 때: overlaid/ 폴더에서 오버레이 이미지를 우선 탐색.
    없으면 scenes/ 원본으로 폴백.
    """
    # 오버레이 모드: overlaid/ 우선 탐색
    if USE_OVERLAY:
        for ext in [".png", ".jpg"]:
            for pattern in [f"{scene_name}_*_{OVERLAY_LANG}", f"{scene_name}_{OVERLAY_LANG}"]:
                matches = list(OVERLAY_DIR.glob(f"{pattern}{ext}"))
                if matches:
                    return sorted(matches)[0]

    # 기본: scenes/ 탐색
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        for pattern in [f"{scene_name}_*", f"{scene_name}"]:
            matches = [m for m in SCENES_DIR.glob(f"{pattern}{ext}") if "_alt" not in m.name]
            if matches:
                return sorted(matches)[0]
    return None


def find_liveportrait_video(scene_name):
    """LivePortrait 출력 영상 탐색. 있으면 경로 반환, 없으면 None."""
    if not LIVEPORTRAIT_DIR.exists():
        return None
    # scene_01_title--wink.mp4 형태 (concat 제외)
    matches = [m for m in LIVEPORTRAIT_DIR.glob(f"{scene_name}_*--*.mp4")
               if "_concat" not in m.name]
    return sorted(matches)[0] if matches else None


def _build_liveportrait_clip(lp_video, duration, output, desc="", scene_seed=""):
    """LivePortrait 영상을 루핑 → 1920x1080 스케일 → 미세 zoom 브리딩 합성.

    LP 영상(~2.3초)을 duration에 맞게 루핑합니다.
    zoompan은 비디오 입력과 호환 불가 → scale+crop 조합으로 미세 줌 구현.
    """
    w, h = 1920, 1080
    breathing_factor = BREATHING_INTENSITY * 0.4  # LP 위 브리딩은 약하게

    if breathing_factor > 0:
        rng = _scene_rng(scene_seed) if scene_seed else [0]*12
        # 미세 줌: 약간 크게 스케일 후, 사인파로 crop 위치 변동
        zoom_px = int(12 * breathing_factor * (0.7 + 0.6 * rng[0]))  # ±12px 범위
        sw, sh = w + zoom_px * 2, h + zoom_px * 2  # 약간 크게 스케일
        period = 6.0 + 2.0 * rng[2]
        phase = rng[4] * 6.2832
        # crop 중심을 사인파로 미세 이동
        cx = f"{zoom_px}+{zoom_px}*sin(2*PI*t/{period:.1f}+{phase:.3f})"
        cy = f"{zoom_px}+{zoom_px}*sin(2*PI*t/{period:.1f}+{phase+1.57:.3f})"
        vf = (
            f"scale={sw}:{sh}:flags=lanczos,"
            f"crop={w}:{h}:{cx}:{cy},"
            f"format=yuv420p"
        )
    else:
        vf = f"scale={w}:{h}:flags=lanczos,format=yuv420p"

    run_ffmpeg([
        "-stream_loop", "-1",
        "-i", str(lp_video),
        "-vf", vf,
        "-t", str(duration),
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-an",
        str(output)
    ], desc or f"LP clip ({duration:.1f}s)")


def _separate_foreground(image_path):
    """rembg로 전경(캐릭터) 분리 → 캐시. 이미 분리된 파일 있으면 재사용."""
    from rembg import remove
    from PIL import Image as PILImage

    image_path = Path(image_path)
    fg_path = PARALLAX_DIR / f"{image_path.stem}_fg.png"

    if fg_path.exists():
        return fg_path

    print(f"    🔪 전경 분리: {image_path.name}")
    img = PILImage.open(image_path)
    fg = remove(img)
    fg.save(str(fg_path))
    return fg_path


def _build_parallax_clip(image, duration, effect, output, desc="", scene_seed=""):
    """패럴랙스 클립: 전경/배경을 분리해 차등 모션으로 입체감 생성.

    배경: 느린 줌 + 느린 드리프트
    전경: 빠른 줌 + 빠른 드리프트 (다른 위상)
    → overlay 합성으로 레이어드 모션
    """
    w, h = map(int, RESOLUTION.split("x"))
    iw, ih = w * 2, h * 2
    frames = int(float(duration) * FPS)
    bi = BREATHING_INTENSITY

    # 씬별 랜덤 파라미터
    rng = _scene_rng(scene_seed or "default")
    pz1, pz2 = rng[0] * 6.283, rng[1] * 6.283
    px1, px2 = rng[2] * 6.283, rng[3] * 6.283
    py1, py2 = rng[4] * 6.283, rng[5] * 6.283

    # === 배경 레이어: 느린 모션 ===
    bg_bz = f"+{0.012*bi:.4f}*sin(on*0.04+{pz1:.3f})+{0.008*bi:.4f}*sin(on*0.025+{pz2:.3f})"
    bg_dx = f"+max(-15,min(15,{6*bi:.1f}*sin(on*0.02+{px1:.3f})+{4*bi:.1f}*sin(on*0.013+{px2:.3f})))"
    bg_dy = f"+max(-12,min(12,{4*bi:.1f}*sin(on*0.028+{py1:.3f})+{3*bi:.1f}*sin(on*0.015+{py2:.3f})))"
    bg_cx = f"iw/2-(iw/zoom/2){bg_dx}"
    bg_cy = f"ih/2-(ih/zoom/2){bg_dy}"

    if effect == "zoom_in":
        bg_zoom = f"min(zoom+0.0004,1.08){bg_bz}"
    elif effect == "zoom_out":
        bg_zoom = f"if(eq(on,1),1.08,max(zoom-0.0004,1.0)){bg_bz}"
    else:
        bg_zoom = f"1.0{bg_bz}"

    bg_filter = (
        f"scale={iw}:{ih}:flags=lanczos,"
        f"zoompan=z='{bg_zoom}':x='{bg_cx}':y='{bg_cy}':"
        f"d={frames}:s={iw}x{ih}:fps={FPS},"
        f"scale={w}:{h}:flags=lanczos"
    )

    # === 전경 레이어: 빠른 모션 (1.5~1.8배) ===
    fg_bz = f"+{0.020*bi:.4f}*sin(on*0.045+{pz1+1.5:.3f})+{0.014*bi:.4f}*sin(on*0.028+{pz2+2.0:.3f})"
    fg_dx = f"+max(-20,min(20,{10*bi:.1f}*sin(on*0.022+{px1+1.8:.3f})+{7*bi:.1f}*sin(on*0.014+{px2+2.3:.3f})))"
    fg_dy = f"+max(-16,min(16,{7*bi:.1f}*sin(on*0.032+{py1+1.2:.3f})+{5*bi:.1f}*sin(on*0.018+{py2+1.7:.3f})))"
    fg_cx = f"iw/2-(iw/zoom/2){fg_dx}"
    fg_cy = f"ih/2-(ih/zoom/2){fg_dy}"

    if effect == "zoom_in":
        fg_zoom = f"min(zoom+0.0006,1.12){fg_bz}"
    elif effect == "zoom_out":
        fg_zoom = f"if(eq(on,1),1.12,max(zoom-0.0006,1.0)){fg_bz}"
    else:
        fg_zoom = f"1.0{fg_bz}"

    fg_filter = (
        f"scale={iw}:{ih}:flags=lanczos,"
        f"zoompan=z='{fg_zoom}':x='{fg_cx}':y='{fg_cy}':"
        f"d={frames}:s={iw}x{ih}:fps={FPS},"
        f"scale={w}:{h}:flags=lanczos"
    )

    # 전경 분리
    fg_path = _separate_foreground(image)

    # 배경 비디오
    bg_vid = str(output).replace(".mp4", "_bg.mp4")
    run_ffmpeg([
        "-loop", "1", "-i", str(image),
        "-vf", bg_filter, "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
        bg_vid
    ], f"{desc} [BG]")

    # 전경 비디오 (RGBA 보존)
    fg_vid = str(output).replace(".mp4", "_fg.mov")
    run_ffmpeg([
        "-loop", "1", "-i", str(fg_path),
        "-vf", fg_filter, "-t", str(duration),
        "-c:v", "png", "-pix_fmt", "rgba",
        fg_vid
    ], f"{desc} [FG]")

    # 합성
    run_ffmpeg([
        "-i", bg_vid, "-i", fg_vid,
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
        "-map", "[v]", "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an",
        str(output)
    ], f"{desc} [합성]")

    # 임시 파일 정리
    Path(bg_vid).unlink(missing_ok=True)
    Path(fg_vid).unlink(missing_ok=True)


def _build_single_clip(image, duration, effect, output, desc="", scene_seed=""):
    """단일 이미지 → 영상 클립 (무음).
    우선순위: LivePortrait > 패럴랙스 > 정지이미지+브리딩
    """
    # LivePortrait 모드: LP 영상이 있으면 루핑+스케일+미세브리딩
    # B컷 세그먼트("bcut" in seed)는 LP 적용하지 않음 (별도 이미지 사용)
    if USE_LIVEPORTRAIT and "bcut" not in (scene_seed or ""):
        # scene_seed에서 씬 이름 추출 (예: "scene_01_main_0" → "scene_01")
        scene_base = "_".join(scene_seed.split("_")[:2]) if scene_seed else ""
        lp_video = find_liveportrait_video(scene_base) if scene_base else None
        if lp_video:
            _build_liveportrait_clip(lp_video, duration, output, desc, scene_seed)
            return

    if USE_PARALLAX and PARALLAX_DIR:
        _build_parallax_clip(image, duration, effect, output, desc, scene_seed)
    else:
        vf = ken_burns_filter(effect, duration, scene_seed=scene_seed)
        run_ffmpeg([
            "-loop", "1", "-i", str(image),
            "-vf", vf,
            "-t", str(duration),
            "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-an",
            str(output)
        ], desc)


def _build_bcut_clip(scene_name, main_image, audio, duration, main_effect, bcuts, output):
    """B컷이 있는 씬: 메인+B컷 세그먼트를 생성 → 연결 → 오디오 합성

    재사용 설계: SCENE_BCUTS 딕셔너리만 에피소드별로 변경하면 됨.
    B컷 이미지가 없으면 해당 구간은 메인 이미지로 폴백.
    """
    segments = []
    prev_t = 0.0

    # B컷 시점 정렬
    sorted_bcuts = sorted(bcuts, key=lambda b: b["cut_at"])

    for i, bc in enumerate(sorted_bcuts):
        cut_time = duration * bc["cut_at"]

        # 메인 이미지 구간: prev_t → cut_time
        seg_dur = cut_time - prev_t
        if seg_dur > 0.1:
            seg_file = CLIPS_DIR / f"{scene_name}_seg{len(segments)}.mp4"
            seg_effect = main_effect if len(segments) == 0 else "static"
            _build_single_clip(main_image, seg_dur, seg_effect, seg_file,
                             f"{scene_name} main ({seg_dur:.1f}s)",
                             scene_seed=f"{scene_name}_main_{len(segments)}")
            segments.append(seg_file)

        # B컷 구간: cut_time → 다음 cut_time 또는 끝
        next_t = duration * sorted_bcuts[i + 1]["cut_at"] if i + 1 < len(sorted_bcuts) else duration
        bcut_dur = next_t - cut_time
        if bcut_dur > 0.1:
            bcut_image = find_scene_image(bc["image"])
            if not bcut_image:
                # B컷 이미지 없으면 메인으로 폴백
                print(f"    ⚠ B컷 {bc['image']} 없음 → 메인 폴백")
                bcut_image = main_image
            bcut_effect = bc.get("effect", "zoom_in")
            seg_file = CLIPS_DIR / f"{scene_name}_seg{len(segments)}.mp4"
            _build_single_clip(bcut_image, bcut_dur, bcut_effect, seg_file,
                             f"{scene_name} B컷 ({bcut_dur:.1f}s)",
                             scene_seed=f"{scene_name}_bcut_{i}")
            segments.append(seg_file)
        prev_t = next_t

    # 마지막 메인 구간 (B컷 이후 ~ 끝)
    remaining = duration - prev_t
    if remaining > 0.1:
        seg_file = CLIPS_DIR / f"{scene_name}_seg{len(segments)}.mp4"
        _build_single_clip(main_image, remaining, main_effect, seg_file,
                         f"{scene_name} tail ({remaining:.1f}s)",
                         scene_seed=f"{scene_name}_tail")
        segments.append(seg_file)

    # 세그먼트 연결
    concat_list = CLIPS_DIR / f"{scene_name}_bcut_concat.txt"
    with open(concat_list, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")

    # 연결 + 오디오 합성
    run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", str(audio),
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        "-shortest", "-pix_fmt", "yuv420p",
        str(output)
    ], f"{scene_name} B컷 merge ({len(segments)}seg, {duration:.1f}s)")


def build_clips():
    """Phase 4A: 씬별 클립 생성 (이미지 + Ken Burns + 오디오)
    B컷이 설정된 씬은 자동으로 멀티세그먼트 클립 생성.
    """
    print("\n=== 씬별 클립 생성 ===")
    CLIPS_DIR.mkdir(exist_ok=True)

    for scene_name, audio_file in SCENE_AUDIO.items():
        image = find_scene_image(scene_name)
        audio = AUDIO_LONGFORM / audio_file
        output = CLIPS_DIR / f"{scene_name}.mp4"

        if not image:
            print(f"  ⚠ {scene_name}: 이미지 없음, 건너뜀")
            continue
        if not audio.exists():
            print(f"  ⚠ {scene_name}: 오디오 없음, 건너뜀")
            continue

        duration = get_duration(audio)
        effect = SCENE_EFFECTS.get(scene_name, "static")

        # B컷이 있는 씬은 멀티세그먼트 빌드
        if scene_name in SCENE_BCUTS:
            bcuts = SCENE_BCUTS[scene_name]
            _build_bcut_clip(scene_name, image, audio, duration, effect, bcuts, output)
        else:
            # 기존 단일 이미지 빌드
            vf = ken_burns_filter(effect, duration, scene_seed=scene_name)
            run_ffmpeg([
                "-loop", "1", "-i", str(image),
                "-i", str(audio),
                "-vf", vf,
                "-t", str(duration),
                "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-pix_fmt", "yuv420p",
                str(output)
            ], f"{scene_name} ({duration:.1f}s, {effect})")

    print(f"\n✓ 클립 생성 완료: {len(list(CLIPS_DIR.glob('*.mp4')))}개")


def build_longform():
    """Phase 4B+C: 롱폼 영상 조립 (연결 + BGM + 자막)"""
    print("\n=== 롱폼 영상 조립 ===")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 클립 목록 생성 (_seg, _cut, _bcut, _concat 등 임시 파일 제외)
    clips = sorted([
        f for f in CLIPS_DIR.glob("scene_*.mp4")
        if "_seg" not in f.name and "_cut" not in f.name
        and "_bcut" not in f.name and "_concat" not in f.name
    ])
    if not clips:
        print("  ✗ 클립이 없습니다. 먼저 'clips' 명령을 실행하세요.")
        return

    # 방법 1: 단순 연결 (트랜지션 없이)
    concat_file = BASE_DIR / "clips" / "concat_list.txt"
    with open(concat_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    # 오버레이 모드: 별도 파일명으로 저장 (원본 덮어쓰기 방지)
    suffix = f"_{OVERLAY_LANG}" if USE_OVERLAY else ""
    raw_output = OUTPUT_DIR / f"EP01_longform_raw{suffix}.mp4"
    run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-crf", "18", "-c:a", "aac",
        str(raw_output)
    ], "클립 연결")

    # BGM이 있으면 믹싱
    bgm_path = BASE_DIR / "audio" / "bgm.mp3"
    final_output = OUTPUT_DIR / f"EP01_longform_final{suffix}.mp4"

    if bgm_path.exists():
        total_duration = get_duration(raw_output)
        # CineLink 패턴: 나레이션 0dB, BGM -18dB, 페이드인/아웃 3초
        run_ffmpeg([
            "-i", str(raw_output),
            "-i", str(bgm_path),
            "-filter_complex",
            (f"[1:a]volume=0.12,afade=t=in:st=0:d=3,"
             f"afade=t=out:st={total_duration-3}:d=3[bgm];"
             f"[0:a][bgm]amix=inputs=2:duration=first[aout]"),
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac",
            str(final_output)
        ], "BGM 믹싱")
    else:
        # BGM 없으면 raw를 final로
        raw_output.rename(final_output)
        print("  ℹ BGM 없음 — raw를 final로 사용")

    if final_output.exists():
        dur = get_duration(final_output)
        print(f"\n✓ 롱폼 완성: {final_output.name} ({dur:.0f}초 = {dur/60:.1f}분)")


def _shorts_crop_filter(crop_mode, duration, position="left", left_offset=None):
    """9:16 쇼츠 필터 — 블러 배경 + 원본 비율 유지 (letterbox 스타일)

    원본 16:9 이미지를 9:16 프레임에 자연스럽게 배치:
    1. 배경: 원본을 크게 확대+블러하여 9:16 전체 채움
    2. 전경: 원본을 너비 맞춤 스케일로 중앙 배치
    crop_mode: left/right/center → 배경 블러의 초점 영역 결정
    """
    # 출력 크기
    ow, oh = 1080, 1920

    # crop_mode에 따라 배경 블러 초점 위치
    if crop_mode == "left" or (crop_mode in ("split_lr", "split_rl") and position == "left"):
        bg_crop_x = "0"
    elif crop_mode == "right" or (crop_mode in ("split_lr", "split_rl") and position == "right"):
        bg_crop_x = f"iw-ih*{ow}/{oh}"
    else:  # center
        bg_crop_x = f"(iw-ih*{ow}/{oh})/2"

    # 복합 필터:
    # [0] 배경 레이어: crop→scale(1080x1920)→blur→darken
    # [1] 전경 레이어: scale(width=1080, keep ratio)→pad to 1080x1920
    vf = (
        f"split[bg][fg];"
        f"[bg]crop=ih*{ow}/{oh}:ih:{bg_crop_x}:0,"
        f"scale={ow}:{oh},gblur=sigma=25,eq=brightness=-0.15[blurred];"
        f"[fg]scale={ow}:-2[scaled];"
        f"[blurred][scaled]overlay=(W-w)/2:(H-h)/2"
    )
    return vf


def build_shorts():
    """Phase 5: 쇼츠 7편 생성 (9:16 크롭 + 오디오, 멀티 세그먼트 지원)

    각 쇼츠는 segments 리스트로 구성:
    - 나레이션 흐름에 맞춰 여러 씬 이미지를 시간 분할
    - 각 세그먼트별 독립적 크롭 모드 지원
    - 에피소드별로 SHORTS_CONFIG만 교체하면 됨
    """
    print("\n=== 쇼츠 7편 생성 ===")
    OUTPUT_DIR.mkdir(exist_ok=True)
    CLIPS_DIR.mkdir(exist_ok=True)

    for config in SHORTS_CONFIG:
        output_name = config["name"]
        audio = AUDIO_SHORTS / config["audio"]
        suffix = f"_{OVERLAY_LANG}" if USE_OVERLAY else ""
        output = OUTPUT_DIR / f"{output_name}{suffix}.mp4"
        segments = config["segments"]

        if not audio.exists():
            print(f"  ⚠ {output_name}: 오디오 없음, 건너뜀")
            continue

        duration = get_duration(audio)

        if len(segments) == 1:
            # 단일 세그먼트: 직접 빌드
            seg = segments[0]
            image = find_scene_image(seg["scene"])
            if not image:
                print(f"  ⚠ {output_name}: 이미지 없음, 건너뜀")
                continue
            crop = seg.get("crop", "center")
            run_ffmpeg([
                "-loop", "1", "-i", str(image),
                "-i", str(audio),
                "-filter_complex", _shorts_crop_filter(crop, duration),
                "-t", str(duration),
                "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                str(output)
            ], f"{output_name} ({duration:.1f}s, {crop})")

        else:
            # 멀티 세그먼트: 각각 빌드 → concat → 오디오
            seg_files = []
            for i, seg in enumerate(segments):
                image = find_scene_image(seg["scene"])
                if not image:
                    print(f"    ⚠ {output_name} seg{i}: {seg['scene']} 없음, 건너뜀")
                    continue
                seg_dur = duration * seg["ratio"]
                crop = seg.get("crop", "center")
                seg_file = CLIPS_DIR / f"{output_name}_seg{i}.mp4"
                run_ffmpeg([
                    "-loop", "1", "-i", str(image),
                    "-filter_complex", _shorts_crop_filter(crop, seg_dur),
                    "-t", str(seg_dur),
                    "-c:v", "libx264", "-tune", "stillimage",
                    "-pix_fmt", "yuv420p", "-an",
                    str(seg_file)
                ], f"{output_name} seg{i}/{seg['scene']} ({seg_dur:.1f}s, {crop})")
                seg_files.append(seg_file)

            if not seg_files:
                continue

            # concat + 오디오
            concat_list = CLIPS_DIR / f"{output_name}_concat.txt"
            with open(concat_list, "w") as f:
                for sf in seg_files:
                    f.write(f"file '{sf}'\n")

            run_ffmpeg([
                "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-i", str(audio),
                "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                str(output)
            ], f"{output_name} merge ({len(seg_files)}seg, {duration:.1f}s)")

    shorts = list(OUTPUT_DIR.glob("EP01_teaser_*.mp4")) + \
             list(OUTPUT_DIR.glob("EP01_deep_*.mp4"))
    print(f"\n✓ 쇼츠 생성 완료: {len(shorts)}편")


def _resolve_coord(expr, w, h, text_w=0, text_h=0):
    """FFmpeg 스타일 좌표 표현식을 실수 좌표로 변환"""
    expr = str(expr)
    expr = expr.replace("text_w", str(text_w)).replace("text_h", str(text_h))
    expr = expr.replace("w", str(w)).replace("h", str(h))
    try:
        return int(eval(expr))
    except:
        return 0


def _parse_color(color_str):
    """색상 문자열 → (R, G, B, A) 튜플"""
    if "@" in color_str:
        color_part, alpha_str = color_str.rsplit("@", 1)
        alpha = int(float(alpha_str) * 255)
    else:
        color_part = color_str
        alpha = 255

    color_map = {
        "white": (255, 255, 255), "black": (0, 0, 0),
        "red": (255, 0, 0), "blue": (0, 0, 255),
    }
    if color_part in color_map:
        return (*color_map[color_part], alpha)
    if color_part.startswith("#"):
        h = color_part.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)
    return (255, 255, 255, alpha)



def apply_text_overlays(scene_image, scene_id, lang="ko"):
    """
    Pillow 기반 텍스트 오버레이 합성 (FFmpeg drawtext 대체)

    Args:
        scene_image: 원본 이미지 경로 (str 또는 Path)
        scene_id: manifest 키 (예: "scene_01_title")
        lang: 언어 코드 ("ko", "ja", "en")

    Returns:
        Path: 오버레이된 이미지 경로, 실패 시 None
    """
    from PIL import Image as PILImage, ImageDraw, ImageFont

    scene_image = Path(scene_image)
    if not scene_image.exists():
        print(f"  ✗ 이미지 없음: {scene_image}")
        return None

    if not MANIFEST_PATH.exists():
        print(f"  ✗ manifest 없음: {MANIFEST_PATH}")
        return None

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if scene_id not in manifest:
        print(f"  ℹ {scene_id}: manifest에 오버레이 없음, 원본 사용")
        return scene_image

    overlays = manifest[scene_id]
    text_key = f"text_{lang}"
    font_path = FONTS.get(lang, FONTS["ko"])

    # 이미지 열기
    img = PILImage.open(scene_image).convert("RGBA")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    overlay_count = 0

    for overlay in overlays:
        overlay_type = overlay["type"]
        raw_text = overlay.get(text_key)
        if raw_text is None:
            print(f"  ⚠ {scene_id}/{overlay_type}: {text_key} 없음, 건너뜀")
            continue

        style = OVERLAY_STYLES.get(overlay_type)
        if style is None:
            print(f"  ⚠ 알 수 없는 오버레이 타입: {overlay_type}")
            continue

        fontsize = style["fontsize"]
        try:
            font = ImageFont.truetype(font_path, fontsize)
        except:
            font = ImageFont.load_default()

        if isinstance(raw_text, list):
            positions = style.get("positions", [])
            for i, item_text in enumerate(raw_text):
                if i < len(positions):
                    pos = positions[i]
                else:
                    last = positions[-1] if positions else {"x": "(w-text_w)/2", "y": "h*0.85"}
                    pos = {"x": last["x"], "y": f"{last['y']}+{50*(i-len(positions)+1)}"}
                # 박스 배경을 별도 레이어에 그림
                if style.get("box"):
                    bbox = font.getbbox(item_text)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    px = _resolve_coord(pos["x"], w, h, tw, th)
                    py = _resolve_coord(pos["y"], w, h, tw, th)
                    pad = style.get("boxborderw", 10)
                    box_layer = PILImage.new("RGBA", (w, h), (0, 0, 0, 0))
                    box_draw = ImageDraw.Draw(box_layer)
                    box_color = _parse_color(style["boxcolor"])
                    box_draw.rectangle([px-pad, py-pad, px+tw+pad, py+th+pad], fill=box_color)
                    img = PILImage.alpha_composite(img, box_layer)
                    draw = ImageDraw.Draw(img)
                _pillow_draw_text_simple(draw, item_text, pos["x"], pos["y"], font, style, (w, h))
                overlay_count += 1
        else:
            lines = raw_text.split("\\n") if "\\n" in raw_text else raw_text.split("\n")
            line_height = fontsize + 12
            base_y = style.get("y", "h*0.12")
            base_x = style.get("x", "(w-text_w)/2")

            for li, line in enumerate(lines):
                y_expr = base_y if li == 0 else f"{base_y}+{line_height * li}"
                if style.get("box"):
                    bbox = font.getbbox(line)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    px = _resolve_coord(base_x, w, h, tw, th)
                    py = _resolve_coord(y_expr, w, h, tw, th)
                    pad = style.get("boxborderw", 10)
                    box_layer = PILImage.new("RGBA", (w, h), (0, 0, 0, 0))
                    box_draw = ImageDraw.Draw(box_layer)
                    box_color = _parse_color(style["boxcolor"])
                    box_draw.rectangle([px-pad, py-pad, px+tw+pad, py+th+pad], fill=box_color)
                    img = PILImage.alpha_composite(img, box_layer)
                    draw = ImageDraw.Draw(img)
                _pillow_draw_text_simple(draw, line, base_x, y_expr, font, style, (w, h))
                overlay_count += 1

    if overlay_count == 0:
        print(f"  ℹ {scene_id}: 유효한 오버레이 없음, 원본 사용")
        return scene_image

    OVERLAY_DIR.mkdir(exist_ok=True)
    output_path = OVERLAY_DIR / f"{scene_id}_{lang}.png"
    img.save(str(output_path), "PNG")
    print(f"  → {scene_id} [{lang}] Pillow 오버레이 ({overlay_count}개)")
    return output_path


def _pillow_draw_text_simple(draw, text, x_expr, y_expr, font, style, img_size):
    """Pillow로 텍스트 렌더링 (테두리 포함)"""
    w, h = img_size
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    px = _resolve_coord(x_expr, w, h, tw, th)
    py = _resolve_coord(y_expr, w, h, tw, th)

    borderw = style.get("borderw", 2)
    border_color = _parse_color(style.get("bordercolor", "black"))[:3]
    text_color = _parse_color(style["fontcolor"])[:3]

    # 테두리
    for dx in range(-borderw, borderw + 1):
        for dy in range(-borderw, borderw + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((px + dx, py + dy), text, font=font, fill=border_color)
    # 본체
    draw.text((px, py), text, font=font, fill=text_color)


def build_overlaid_scenes(lang="ko"):
    """매니페스트의 모든 씬에 텍스트 오버레이 적용"""
    print(f"\n=== 텍스트 오버레이 적용 (lang={lang}) ===")
    OVERLAY_DIR.mkdir(exist_ok=True)

    if not MANIFEST_PATH.exists():
        print(f"  ✗ manifest 없음: {MANIFEST_PATH}")
        return

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    success_count = 0
    skip_count = 0

    for scene_id in manifest:
        # scene_id에서 씬 이미지 이름 추출 (예: scene_01_title → scene_01)
        parts = scene_id.split("_")
        if len(parts) >= 2:
            scene_base = f"{parts[0]}_{parts[1]}"  # "scene_01"
        else:
            scene_base = scene_id

        image = find_scene_image(scene_base)
        if not image:
            print(f"  ⚠ {scene_id}: 씬 이미지 없음 ({scene_base}), 건너뜀")
            skip_count += 1
            continue

        result = apply_text_overlays(image, scene_id, lang=lang)
        if result and result != image:
            success_count += 1
        else:
            skip_count += 1

    total = len(manifest)
    print(f"\n✓ 오버레이 완료: {success_count}/{total} 성공, {skip_count} 건너뜀")
    print(f"  출력 폴더: {OVERLAY_DIR}/")


def status():
    """현재 상태 출력"""
    print("\n=== FEP EP.01 빌드 상태 ===")
    scenes = list(SCENES_DIR.glob("scene_*.*"))
    audio_lf = list(AUDIO_LONGFORM.glob("*.mp3"))
    audio_sh = list(AUDIO_SHORTS.glob("*.mp3"))
    clips = list(CLIPS_DIR.glob("*.mp4"))
    outputs = list(OUTPUT_DIR.glob("*.mp4"))

    overlaid = list(OVERLAY_DIR.glob("*_ko.png")) if OVERLAY_DIR.exists() else []

    print(f"  씬 일러스트:  {len(scenes):2d}/15")
    print(f"  롱폼 오디오:  {len(audio_lf):2d}/15")
    print(f"  쇼츠 오디오:  {len(audio_sh):2d}/7")
    print(f"  오버레이(ko): {len(overlaid):2d}")
    print(f"  클립:        {len(clips):2d}/15")
    print(f"  최종 산출물:  {len(outputs):2d}/8")

    if len(scenes) == 0:
        print("\n  �� 씬 일러스트가 없습니다. ComfyUI에서 생성 후 scenes/ 폴더에 저장하세요.")
    if len(audio_lf) == 15 and len(scenes) >= 15:
        print("\n  → 'python build_video.py all' 로 전체 빌드 가능")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="FEP EP.01 영상 빌드 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  clips      씬별 클립 생성
  longform   롱폼 영상 조립
  shorts     쇼츠 7편 조립
  overlay    텍스트 오버레이 생성
  all        clips → longform → shorts 전체 빌드
  status     현재 상태 확인 (기본값)
        """,
    )
    parser.add_argument("command", nargs="?", default="status",
                        choices=["clips", "longform", "shorts", "overlay", "all", "status"])
    parser.add_argument("--breathing", type=float, default=None,
                        help="브리딩 효과 강도 (0.0=끔 ~ 3.0=강함, 기본=1.0)")
    parser.add_argument("--lang", default="ko", choices=["ko", "ja", "en"],
                        help="오버레이 언어 (기본: ko)")
    parser.add_argument("--overlay", action="store_true",
                        help="텍스트 오버레이 이미지 사용 (overlaid/ 우선, 없으면 scenes/ 폴백)")
    parser.add_argument("--parallax", action="store_true",
                        help="패럴랙스 효과: 전경/배경 분리 차등 모션 (rembg 필요)")
    parser.add_argument("--liveportrait", action="store_true",
                        help="LivePortrait 애니메이션 클립 사용 (liveportrait_out/ 영상 루핑)")

    args = parser.parse_args()

    # --breathing 글로벌 적용
    if args.breathing is not None:
        BREATHING_INTENSITY = args.breathing
        print(f"  🎛️  브리딩 강도: {BREATHING_INTENSITY:.1f}")

    # --overlay 글로벌 적용
    if args.overlay:
        USE_OVERLAY = True
        OVERLAY_LANG = args.lang
        print(f"  📝 오버레이 모드: {OVERLAY_LANG}")

    # --parallax 글로벌 적용
    if args.parallax:
        USE_PARALLAX = True
        PARALLAX_DIR = BASE_DIR / "parallax_cache"
        PARALLAX_DIR.mkdir(exist_ok=True)
        print(f"  🎭 패럴랙스 모드: 전경/배경 분리 차등 모션")

    # --liveportrait 글로벌 적용
    if args.liveportrait:
        USE_LIVEPORTRAIT = True
        print(f"  🎬 LivePortrait 모드: liveportrait_out/ 영상 우선 사용")

    if args.command == "clips":
        build_clips()
    elif args.command == "longform":
        build_longform()
    elif args.command == "shorts":
        build_shorts()
    elif args.command == "overlay":
        if args.lang not in ("ko", "ja", "en"):
            print(f"  ✗ 지원하지 않는 언어: {args.lang} (ko|ja|en)")
            sys.exit(1)
        build_overlaid_scenes(lang=args.lang)
    elif args.command == "all":
        build_clips()
        build_longform()
        build_shorts()
    elif args.command == "status":
        status()
