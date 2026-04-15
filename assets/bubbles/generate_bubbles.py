#!/usr/bin/env python3
"""
FEP 말풍선 에셋 생성기
유기적 구름 형태 말풍선 — v1 일러스트 스타일 참조
투명 PNG로 저장 → 어떤 씬에든 재사용

종류:
  - speech: 대사 말풍선 (둥근 구름 + 꼬리)
  - thought: 내면 독백 (구름 + 점 꼬리)

방향:
  - left: 꼬리가 왼쪽 아래 (왼쪽 캐릭터용)
  - right: 꼬리가 오른쪽 아래 (오른쪽 캐릭터용)
  - center: 꼬리가 가운데 아래

크기:
  - sm: 1~2줄 (짧은 대사)
  - md: 2~3줄 (일반 대사)
  - lg: 3~5줄 (긴 대사/독백)
"""

import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = Path(__file__).parent
random.seed(42)  # 재현 가능

# ── 구름형 말풍선 생성 ──

def draw_cloud_shape(draw, cx, cy, rx, ry, bumps=12, bump_size=0.25, fill=(255,255,255,240), outline=(50,50,50,220), outline_width=3):
    """유기적 구름 모양 — 원 위에 반원 범프를 올리는 방식"""
    points = []
    for i in range(bumps * 4):
        angle = (2 * math.pi * i) / (bumps * 4)
        # 기본 타원
        bx = cx + rx * math.cos(angle)
        by = cy + ry * math.sin(angle)
        # 범프 (부풀림)
        bump_angle = (2 * math.pi * i) / (bumps * 4) * bumps
        bump = 1.0 + bump_size * (0.5 + 0.5 * math.sin(bump_angle))
        # 약간의 랜덤 변형
        noise = 1.0 + random.uniform(-0.03, 0.03)
        bx = cx + rx * bump * noise * math.cos(angle)
        by = cy + ry * bump * noise * math.sin(angle)
        points.append((bx, by))

    draw.polygon(points, fill=fill, outline=outline, width=outline_width)


def draw_speech_tail(draw, tip_x, tip_y, base_x1, base_y1, base_x2, base_y2,
                     fill=(255,255,255,240), outline=(50,50,50,220), outline_width=3):
    """말풍선 꼬리 (삼각형 + 곡선)"""
    draw.polygon([(tip_x, tip_y), (base_x1, base_y1), (base_x2, base_y2)], fill=fill)
    draw.line([(tip_x, tip_y), (base_x1, base_y1)], fill=outline, width=outline_width)
    draw.line([(tip_x, tip_y), (base_x2, base_y2)], fill=outline, width=outline_width)


def draw_thought_dots(draw, positions, fill=(255,255,255,240), outline=(50,50,50,220), outline_width=2):
    """생각 풍선 점 꼬리"""
    for x, y, r in positions:
        draw.ellipse([x-r, y-r, x+r, y+r], fill=fill, outline=outline, width=outline_width)


def create_speech_bubble(width, height, tail_dir="left", bubble_type="speech"):
    """말풍선/생각풍선 생성"""
    # 캔버스 여유 (꼬리 + 안티앨리어싱 공간)
    pad = 60
    tail_space = 50
    canvas_w = width + pad * 2
    canvas_h = height + pad * 2 + tail_space

    # 고해상도로 그린 후 다운스케일 (안티앨리어싱)
    scale = 2
    img = Image.new("RGBA", (canvas_w * scale, canvas_h * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = (canvas_w * scale) // 2
    cy = (pad + height // 2) * scale
    rx = (width // 2 + 15) * scale
    ry = (height // 2 + 12) * scale

    fill = (255, 255, 255, 235)
    outline = (60, 60, 60, 200)
    ow = 4 * scale

    if bubble_type == "thought":
        fill = (245, 245, 255, 220)
        outline = (90, 90, 120, 180)

    # 구름 본체
    bumps = max(8, width // 30)
    bump_size = 0.18 if bubble_type == "speech" else 0.28
    draw_cloud_shape(draw, cx, cy, rx, ry, bumps=bumps, bump_size=bump_size,
                     fill=fill, outline=outline, outline_width=ow)

    # 꼬리
    base_y = (pad + height - 5) * scale
    if bubble_type == "speech":
        if tail_dir == "left":
            tip_x = int(cx - rx * 0.5)
            tip_y = (pad + height + tail_space - 10) * scale
            draw_speech_tail(draw, tip_x, tip_y,
                            int(cx - rx * 0.35), base_y,
                            int(cx - rx * 0.15), base_y,
                            fill=fill, outline=outline, outline_width=ow)
        elif tail_dir == "right":
            tip_x = int(cx + rx * 0.5)
            tip_y = (pad + height + tail_space - 10) * scale
            draw_speech_tail(draw, tip_x, tip_y,
                            int(cx + rx * 0.15), base_y,
                            int(cx + rx * 0.35), base_y,
                            fill=fill, outline=outline, outline_width=ow)
        else:  # center
            tip_x = cx
            tip_y = (pad + height + tail_space - 10) * scale
            draw_speech_tail(draw, tip_x, tip_y,
                            int(cx - rx * 0.08), base_y,
                            int(cx + rx * 0.08), base_y,
                            fill=fill, outline=outline, outline_width=ow)
    else:  # thought — 점 꼬리
        if tail_dir == "left":
            dots = [
                (int(cx - rx * 0.35), base_y + 20 * scale, 14 * scale),
                (int(cx - rx * 0.45), base_y + 42 * scale, 10 * scale),
                (int(cx - rx * 0.50), base_y + 58 * scale, 7 * scale),
            ]
        elif tail_dir == "right":
            dots = [
                (int(cx + rx * 0.35), base_y + 20 * scale, 14 * scale),
                (int(cx + rx * 0.45), base_y + 42 * scale, 10 * scale),
                (int(cx + rx * 0.50), base_y + 58 * scale, 7 * scale),
            ]
        else:
            dots = [
                (cx, base_y + 20 * scale, 14 * scale),
                (cx + 5 * scale, base_y + 42 * scale, 10 * scale),
                (cx + 8 * scale, base_y + 58 * scale, 7 * scale),
            ]
        draw_thought_dots(draw, dots, fill=fill, outline=outline, outline_width=3 * scale)

    # 다운스케일 (안티앨리어싱)
    img = img.resize((canvas_w, canvas_h), Image.LANCZOS)

    # 약간의 블러로 부드러운 엣지
    # 알파 채널만 살짝 블러
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(radius=0.5))
    img = Image.merge("RGBA", (r, g, b, a))

    return img


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 크기 정의 (텍스트 영역 기준, 실제 버블은 더 큼)
    sizes = {
        "sm": (240, 80),    # 1~2줄
        "md": (300, 120),   # 2~3줄
        "lg": (360, 180),   # 3~5줄
    }

    directions = ["left", "right", "center"]
    types = ["speech", "thought"]

    total = 0
    for btype in types:
        for size_name, (w, h) in sizes.items():
            for direction in directions:
                img = create_speech_bubble(w, h, tail_dir=direction, bubble_type=btype)
                fname = f"{btype}_{direction}_{size_name}.png"
                img.save(OUT_DIR / fname)
                print(f"  ✅ {fname} ({img.size[0]}x{img.size[1]})")
                total += 1

    print(f"\n=== {total}개 말풍선 에셋 생성 완료 ===")
    print(f"📁 {OUT_DIR}")


if __name__ == "__main__":
    main()
