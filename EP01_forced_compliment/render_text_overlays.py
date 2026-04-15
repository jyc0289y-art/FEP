#!/usr/bin/env python3
"""
FEP EP.01 텍스트 오버레이 렌더러
말풍선 / 내면 독백 / 심리학 용어 / 킬링 라인 / 구조 라벨

Pillow 기반 — FFmpeg drawtext 사용 불가 (CLAUDE.md 확정사항)

사용법:
  python render_text_overlays.py              # 전체 오버레이 이미지 생성
  python render_text_overlays.py S-04         # 특정 씬만
  python render_text_overlays.py --preview    # 합성 미리보기 (씬 이미지 위에 오버레이)
"""

import json
import sys
import math
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import numpy as np
except ImportError:
    print("pip install Pillow numpy 필요")
    sys.exit(1)

BASE_DIR = Path(__file__).parent
MANIFEST = BASE_DIR / "text_overlay_v2_manifest.json"
OVERLAY_DIR = BASE_DIR / "v3_layers" / "overlays"
SCENES_DIR = BASE_DIR / "v3_layers" / "scenes"

TARGET_W, TARGET_H = 1920, 1080

# ── 폰트 설정 ──
FONT_PATHS = {
    "main": "/Library/Fonts/NanumGothicBold.otf",
    "sub": "/Library/Fonts/NanumGothic.otf",
    "emphasis": "/Library/Fonts/NanumGothicExtraBold.otf",
    "label": "/Library/Fonts/NanumGothic.otf",
}

# 폰트 폴백
def _find_font(key, size):
    paths = [
        FONT_PATHS.get(key, ""),
        "/Library/Fonts/NanumGothicBold.otf",
        "/Library/Fonts/NanumGothic.otf",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ── 스타일 정의 ──
STYLES = {
    "speech_bubble": {
        "bg_color": (255, 255, 255, 230),
        "text_color": (30, 30, 30),
        "border_color": (80, 80, 80, 200),
        "border_width": 3,
        "corner_radius": 20,
        "padding": (20, 16, 20, 16),  # left, top, right, bottom
        "font_key": "main",
        "font_size": 32,
        "tail": True,
        "shadow": False,
    },
    "thought_bubble": {
        "bg_color": (240, 240, 255, 180),
        "text_color": (60, 60, 80),
        "border_color": (120, 120, 160, 150),
        "border_width": 2,
        "corner_radius": 30,
        "padding": (22, 18, 22, 18),
        "font_key": "main",
        "font_size": 30,
        "tail": False,  # 점 꼬리는 별도 처리
        "thought_dots": True,
        "shadow": False,
    },
    "lower_third": {
        "bg_color": (0, 0, 0, 180),
        "text_color": (255, 255, 255),
        "border_color": None,
        "border_width": 0,
        "corner_radius": 8,
        "padding": (30, 12, 30, 12),
        "font_key": "main",
        "font_size": 36,
        "font_size_sub": 22,
        "tail": False,
        "shadow": False,
    },
    "emphasis": {
        "bg_color": None,
        "text_color": (255, 255, 255),
        "border_color": None,
        "border_width": 0,
        "corner_radius": 0,
        "padding": (0, 0, 0, 0),
        "font_key": "emphasis",
        "font_size": 52,
        "tail": False,
        "shadow": True,
    },
    "structure_label": {
        "bg_color": (0, 0, 0, 120),
        "text_color": (255, 255, 255, 220),
        "border_color": None,
        "border_width": 0,
        "corner_radius": 6,
        "padding": (16, 8, 16, 8),
        "font_key": "label",
        "font_size": 24,
        "tail": False,
        "shadow": False,
    },
}

# 캐릭터별 말풍선 색상
SPEAKER_COLORS = {
    "수빈": {"bg": (255, 230, 235, 230), "border": (220, 120, 150, 200)},
    "민준": {"bg": (230, 240, 255, 230), "border": (100, 140, 200, 200)},
    "지우": {"bg": (235, 255, 235, 230), "border": (120, 180, 120, 200)},
}


def _round_rect(draw, xy, radius, fill=None, outline=None, width=1):
    """둥근 사각형"""
    x0, y0, x1, y1 = xy
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    # 코너
    draw.pieslice([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=fill, outline=outline, width=width)
    draw.pieslice([x1 - 2 * r, y0, x1, y0 + 2 * r], 270, 360, fill=fill, outline=outline, width=width)
    draw.pieslice([x0, y1 - 2 * r, x0 + 2 * r, y1], 90, 180, fill=fill, outline=outline, width=width)
    draw.pieslice([x1 - 2 * r, y1 - 2 * r, x1, y1], 0, 90, fill=fill, outline=outline, width=width)
    # 사각형 영역
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x0 + r, y1 - r], fill=fill)
    draw.rectangle([x1 - r, y0 + r, x1, y1 - r], fill=fill)
    # 외곽선
    if outline and width > 0:
        draw.arc([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=outline, width=width)
        draw.arc([x1 - 2 * r, y0, x1, y0 + 2 * r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1 - 2 * r, x0 + 2 * r, y1], 90, 180, fill=outline, width=width)
        draw.arc([x1 - 2 * r, y1 - 2 * r, x1, y1], 0, 90, fill=outline, width=width)
        draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
        draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
        draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
        draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)


def render_speech_bubble(item, style_base):
    """말풍선 타입 (A) 렌더"""
    style = {**style_base}
    override = item.get("style_override", {})

    # 캐릭터별 색상
    speaker = item.get("speaker", "")
    if speaker in SPEAKER_COLORS:
        style["bg_color"] = SPEAKER_COLORS[speaker]["bg"]
        style["border_color"] = SPEAKER_COLORS[speaker]["border"]

    font_size = override.get("font_size", style["font_size"])
    font = _find_font(style["font_key"], font_size)

    text = item["text"]
    lines = text.split("\n")

    # 텍스트 크기 계산
    dummy = Image.new("RGBA", (1, 1))
    dd = ImageDraw.Draw(dummy)
    line_bboxes = [dd.textbbox((0, 0), line, font=font) for line in lines]
    max_w = max(bbox[2] - bbox[0] for bbox in line_bboxes)
    line_h = max(bbox[3] - bbox[1] for bbox in line_bboxes) + 6
    total_h = line_h * len(lines)

    pl, pt, pr, pb = style["padding"]
    bubble_w = max_w + pl + pr
    bubble_h = total_h + pt + pb
    tail_h = 20 if style.get("tail") else 0

    # 오버레이 이미지 (bubble + tail 공간)
    canvas = Image.new("RGBA", (bubble_w + 10, bubble_h + tail_h + 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # 둥근 사각형 배경
    _round_rect(draw, (2, 2, bubble_w + 2, bubble_h + 2),
                style["corner_radius"],
                fill=style["bg_color"],
                outline=style.get("border_color"),
                width=style.get("border_width", 2))

    # 꼬리 (삼각형)
    if style.get("tail"):
        pos = item.get("position", "")
        if "left" in pos:
            tx = bubble_w // 4
        elif "right" in pos:
            tx = bubble_w * 3 // 4
        else:
            tx = bubble_w // 2
        ty = bubble_h + 2
        draw.polygon([(tx - 8, ty), (tx + 8, ty), (tx, ty + tail_h)],
                     fill=style["bg_color"])
        if style.get("border_color"):
            draw.line([(tx - 8, ty), (tx, ty + tail_h)], fill=style["border_color"], width=2)
            draw.line([(tx + 8, ty), (tx, ty + tail_h)], fill=style["border_color"], width=2)

    # 텍스트
    text_color = override.get("color", style["text_color"])
    if isinstance(text_color, str):
        text_color = tuple(int(text_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    y = pt + 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (bubble_w - lw) // 2 + 2  # center align
        draw.text((x, y), line, font=font, fill=text_color)
        y += line_h

    return canvas


def render_thought_bubble(item, style_base):
    """내면 독백 타입 (B) 렌더"""
    canvas = render_speech_bubble(item, {**style_base, "tail": False})

    if style_base.get("thought_dots"):
        draw = ImageDraw.Draw(canvas)
        w, h = canvas.size
        pos = item.get("position", "")
        if "left" in pos:
            cx = w // 4
        elif "right" in pos:
            cx = w * 3 // 4
        else:
            cx = w // 2
        # 점 3개 (큰→작은)
        for i, (r, dy) in enumerate([(6, 8), (4, 20), (3, 30)]):
            draw.ellipse([cx - r, h - 10 + dy - r, cx - r + 2 * r, h - 10 + dy + r],
                        fill=style_base["bg_color"])

        # 캔버스 확장
        new_canvas = Image.new("RGBA", (w, h + 35), (0, 0, 0, 0))
        new_canvas.paste(canvas, (0, 0), canvas)
        draw2 = ImageDraw.Draw(new_canvas)
        for i, (r, dy) in enumerate([(6, 8), (4, 20), (3, 30)]):
            draw2.ellipse([cx - r, h - 10 + dy - r, cx - r + 2 * r, h - 10 + dy + r],
                         fill=style_base["bg_color"],
                         outline=style_base.get("border_color"), width=1)
        return new_canvas

    return canvas


def render_lower_third(item, style_base):
    """심리학 용어 타입 (C) 렌더 — 용어 + 영어 + 주석(annotation) 3줄 구조"""
    override = item.get("style_override", {})
    text = item["text"]
    lines = text.split("\n")
    annotation = item.get("annotation", "")

    main_size = override.get("font_size_main", style_base["font_size"])
    sub_size = override.get("font_size_sub", style_base.get("font_size_sub", 22))
    anno_size = 20  # 주석은 더 작게

    main_font = _find_font("emphasis", main_size)
    sub_font = _find_font("sub", sub_size)
    anno_font = _find_font("sub", anno_size)

    dummy = Image.new("RGBA", (1, 1))
    dd = ImageDraw.Draw(dummy)

    # 첫 줄 = 한국어 용어, 둘째 줄 = 영어, 셋째 줄 = 주석
    main_bbox = dd.textbbox((0, 0), lines[0], font=main_font)
    main_w = main_bbox[2] - main_bbox[0]
    main_h = main_bbox[3] - main_bbox[1]

    sub_w, sub_h = 0, 0
    if len(lines) > 1:
        sub_bbox = dd.textbbox((0, 0), lines[1], font=sub_font)
        sub_w = sub_bbox[2] - sub_bbox[0]
        sub_h = sub_bbox[3] - sub_bbox[1]

    anno_w, anno_h = 0, 0
    if annotation:
        anno_bbox = dd.textbbox((0, 0), annotation, font=anno_font)
        anno_w = anno_bbox[2] - anno_bbox[0]
        anno_h = anno_bbox[3] - anno_bbox[1]

    pl, pt, pr, pb = style_base["padding"]
    total_w = max(main_w, sub_w, anno_w) + pl + pr
    gap = 6
    total_h = main_h + gap + pt + pb
    if sub_h > 0:
        total_h += sub_h + gap
    if anno_h > 0:
        total_h += anno_h + gap + 4  # 구분선 공간

    # 하단 중앙 배치를 위한 넉넉한 캔버스
    bar_w = min(total_w + 40, TARGET_W - 100)
    canvas = Image.new("RGBA", (bar_w, total_h + 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    bg_color = override.get("bg_color", style_base["bg_color"])
    if isinstance(bg_color, str) and bg_color.startswith("rgba"):
        parts = bg_color.replace("rgba(", "").replace(")", "").split(",")
        bg_color = tuple(int(float(p.strip()) * (255 if i == 3 else 1)) if i == 3 else int(p.strip()) for i, p in enumerate(parts))

    _round_rect(draw, (0, 0, bar_w - 1, total_h + 8),
                style_base["corner_radius"],
                fill=bg_color)

    # 악센트 라인 (좌측)
    draw.rectangle([0, 4, 4, total_h + 4], fill=(255, 200, 50, 220))

    # 용어 (메인)
    y = pt + 2
    main_x = (bar_w - main_w) // 2
    draw.text((main_x, y), lines[0], font=main_font, fill=(255, 255, 255))

    # 영어 (서브)
    if len(lines) > 1:
        y += main_h + gap
        sub_x = (bar_w - sub_w) // 2
        draw.text((sub_x, y), lines[1], font=sub_font, fill=(180, 180, 200))

    # 주석 (annotation) — 구분선 + 작은 텍스트
    if annotation:
        y += (sub_h if sub_h > 0 else main_h) + gap + 2
        # 구분선
        line_margin = 40
        draw.line([(line_margin, y), (bar_w - line_margin, y)], fill=(255, 255, 255, 60), width=1)
        y += 6
        anno_x = (bar_w - anno_w) // 2
        draw.text((anno_x, y), annotation, font=anno_font, fill=(220, 200, 140))  # 따뜻한 노란 톤

    return canvas


def render_emphasis(item, style_base):
    """킬링 라인 타입 (D) 렌더"""
    override = item.get("style_override", {})
    font_size = override.get("font_size", style_base["font_size"])
    font = _find_font("emphasis", font_size)
    text = item["text"]
    lines = text.split("\n")

    dummy = Image.new("RGBA", (1, 1))
    dd = ImageDraw.Draw(dummy)
    line_bboxes = [dd.textbbox((0, 0), line, font=font) for line in lines]
    max_w = max(bbox[2] - bbox[0] for bbox in line_bboxes)
    line_h = max(bbox[3] - bbox[1] for bbox in line_bboxes) + 8
    total_h = line_h * len(lines)

    margin = 20
    canvas = Image.new("RGBA", (max_w + margin * 2, total_h + margin * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    text_color = override.get("color", style_base["text_color"])
    if isinstance(text_color, str):
        text_color = tuple(int(text_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    # 그림자 (shadow)
    if override.get("shadow", style_base.get("shadow")):
        for line_idx, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            x = (canvas.width - lw) // 2
            y = margin + line_idx * line_h
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 180))

    # 메인 텍스트
    for line_idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (canvas.width - lw) // 2
        y = margin + line_idx * line_h
        draw.text((x, y), line, font=font, fill=text_color)

    return canvas


def render_structure_label(item, style_base):
    """구조 라벨 타입 (E) 렌더"""
    font_size = style_base["font_size"]
    font = _find_font("label", font_size)
    text = item["text"]

    dummy = Image.new("RGBA", (1, 1))
    dd = ImageDraw.Draw(dummy)
    bbox = dd.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pl, pt, pr, pb = style_base["padding"]
    canvas = Image.new("RGBA", (tw + pl + pr + 4, th + pt + pb + 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    _round_rect(draw, (0, 0, canvas.width - 1, canvas.height - 1),
                style_base["corner_radius"],
                fill=style_base["bg_color"])
    draw.text((pl + 2, pt + 2), text, font=font, fill=(255, 255, 255, 220))

    return canvas


RENDERERS = {
    "A": ("speech_bubble", render_speech_bubble),
    "B": ("thought_bubble", render_thought_bubble),
    "C": ("lower_third", render_lower_third),
    "D": ("emphasis", render_emphasis),
    "E": ("structure_label", render_structure_label),
}


def get_position(pos_name, overlay_size, canvas_size=(TARGET_W, TARGET_H)):
    """position 이름 → (x, y) 좌표"""
    ow, oh = overlay_size
    cw, ch = canvas_size
    margin = 40

    positions = {
        "top_left": (margin, margin),
        "top_right": (cw - ow - margin, margin),
        "center": ((cw - ow) // 2, (ch - oh) // 2),
        "center_bottom": ((cw - ow) // 2, ch - oh - 120),
        "lower_third": ((cw - ow) // 2, ch - oh - 60),
        "left_bubble": (margin + 60, ch // 2 - oh),
        "right_bubble": (cw - ow - margin - 60, ch // 2 - oh),
        "left_thought": (margin + 40, ch // 2 - oh - 20),
        "right_thought": (cw - ow - margin - 40, ch // 2 - oh - 20),
        "left_label": (cw // 6 - ow // 2, ch // 2 + 100),
        "center_label": (cw // 2 - ow // 2, ch // 2 + 100),
        "right_label": (cw * 5 // 6 - ow // 2, ch // 2 + 100),
    }
    return positions.get(pos_name, ((cw - ow) // 2, (ch - oh) // 2))


def render_overlay_set(overlay_entry, preview_bg=None):
    """하나의 overlay entry → 여러 오버레이 이미지 생성 (시간 기반)"""
    results = []
    clip_id = overlay_entry["clip_id"]
    scene = overlay_entry["scene"]

    for idx, item in enumerate(overlay_entry["items"]):
        otype = item["type"]
        if otype not in RENDERERS:
            print(f"  ⚠ 알 수 없는 타입: {otype}")
            continue

        style_name, renderer = RENDERERS[otype]
        style = STYLES[style_name]
        overlay_img = renderer(item, style)

        results.append({
            "clip_id": clip_id,
            "scene": scene,
            "index": idx,
            "type": otype,
            "text": item["text"][:30],
            "position": item.get("position", "center"),
            "start_ratio": item.get("start_ratio", 0),
            "duration_ratio": item.get("duration_ratio", 1.0),
            "image": overlay_img,
        })

    return results


def save_overlays(manifest_data, target_scenes=None):
    """모든 오버레이 이미지를 개별 PNG로 저장"""
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    total = 0
    for entry in manifest_data["overlays"]:
        scene = entry["scene"]
        clip_id = entry["clip_id"]
        if target_scenes and scene not in target_scenes:
            continue

        results = render_overlay_set(entry)
        for r in results:
            fname = f"{ts}_overlay_{clip_id}_{scene}_{r['index']:02d}_{r['type']}.png"
            out_path = OVERLAY_DIR / fname
            r["image"].save(out_path)
            print(f"  ✅ {fname} ({r['text']})")
            total += 1

    print(f"\n=== {total}개 오버레이 이미지 생성 완료 ===")
    return total


def generate_preview(manifest_data, target_scenes=None):
    """씬 이미지 위에 오버레이를 합성한 프리뷰 생성"""
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    total = 0
    for entry in manifest_data["overlays"]:
        scene = entry["scene"]
        clip_id = entry["clip_id"]
        if target_scenes and scene not in target_scenes:
            continue

        # 배경 씬 이미지 찾기
        portrait = sorted(SCENES_DIR.glob(f"*portrait_{scene}.png"), reverse=True)
        scene_img = sorted(SCENES_DIR.glob(f"*scene_{scene}.png"), reverse=True)
        bg_file = (portrait or scene_img or [None])[0]

        if bg_file:
            bg = Image.open(bg_file).convert("RGBA")
            # 1920x1080으로 리사이즈
            bg = bg.resize((TARGET_W, TARGET_H), Image.LANCZOS)
        else:
            bg = Image.new("RGBA", (TARGET_W, TARGET_H), (40, 40, 40, 255))

        # 모든 오버레이 합성
        results = render_overlay_set(entry)
        for r in results:
            pos = get_position(r["position"], r["image"].size)
            bg.paste(r["image"], pos, r["image"])

        fname = f"{ts}_preview_{clip_id}_{scene}.png"
        out_path = OVERLAY_DIR / fname
        bg.convert("RGB").save(out_path, quality=95)
        print(f"  🖼 {fname}")
        total += 1

    print(f"\n=== {total}개 프리뷰 생성 완료 ===")
    return total


def main():
    if not MANIFEST.exists():
        print(f"매니페스트 없음: {MANIFEST}")
        sys.exit(1)

    with open(MANIFEST) as f:
        manifest = json.load(f)

    # 인자 파싱
    target_scenes = None
    preview = False
    for arg in sys.argv[1:]:
        if arg == "--preview":
            preview = True
        elif arg.startswith("S-"):
            if target_scenes is None:
                target_scenes = set()
            target_scenes.add(arg)

    if preview:
        generate_preview(manifest, target_scenes)
    else:
        save_overlays(manifest, target_scenes)


if __name__ == "__main__":
    main()
