#!/usr/bin/env python3
"""
FEP EP.01 "강요된 칭찬의 심리학" — v2 시네마틱 빌드 스크립트
v3 레이어 합성 씬(25장) + v2 edge-tts 초벌 오디오(16클립) → 프리뷰 영상

사용법:
  python build_video_v2.py clips        # 오디오 클립별 영상 생성
  python build_video_v2.py longform     # 롱폼 최종 조립
  python build_video_v2.py all          # 전체
  python build_video_v2.py info         # 씬 매핑 + 파일 확인 정보
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# === 설정 ===
BASE_DIR = Path(__file__).parent
V3_SCENES_DIR = BASE_DIR / "v3_layers" / "scenes"
AUDIO_V2_DIR = BASE_DIR / "audio" / "longform_v2"
CLIPS_V2_DIR = BASE_DIR / "clips_v2"
OUTPUT_DIR = BASE_DIR / "output"

FPS = 30
RESOLUTION = "1920x1080"
FADE_DURATION = 0.5
BREATHING_INTENSITY = 0.0


# === v2 시퀀스 매핑 ===
# 각 항목 = 1개 오디오 클립 → 1개 이상의 씬 이미지를 시간 분할 표시
# ratio: 해당 씬이 오디오 전체 시간에서 차지하는 비율 (합계 = 1.0)
# effect: Ken Burns 효과 (zoom_in, zoom_out, pan_left, pan_right, static)
# beat_after: 클립 끝에 추가할 정적 시간(초) — 감정 잔상용
# v2.1: 전체 +0.3초 (템포 여유 확보 — 대사보다 한 템포 빠르다는 피드백 반영)

V2_SEQUENCE = [
    {
        "id": "00_prologue",
        "audio": "S00_S01_prologue.mp3",
        "beat_after": 0.8,
        "segments": [
            # "질문 하나 할게요. 나 예쁘지?" → 블랙 스크린 (목소리만으로 긴장)
            {"scene": "S-00", "ratio": 0.22, "effect": "static"},
            # "솔직하게 대답해 본 적 있나요?... 이건 질문이 아니거든요" → 수빈 거울
            {"scene": "S-01", "ratio": 0.33, "effect": "zoom_in"},
            # "세 사람의 심리를 이야기해 보려고 합니다" → 세 사람 (bookend)
            {"scene": "S-23", "ratio": 0.22, "effect": "static"},
            # 타이틀 카드 3초 홀드
            {"scene": "S-02", "ratio": 0.23, "effect": "static"},
        ]
    },
    {
        "id": "01_siblings",
        "audio": "S03_S06_siblings.mp3",
        "beat_after": 0.8,
        "segments": [
            # "일요일 오후. 민준이는 아무 생각 없이..." → 소파 민준
            {"scene": "S-03", "ratio": 0.15, "effect": "static"},
            # "오빠. 나 예쁘지?" → 수빈 등장
            {"scene": "S-04", "ratio": 0.07, "effect": "static"},
            # "이 순간. 민준이의 머릿속에서는... 지켜보죠" → 민준 리액션
            {"scene": "S-05", "ratio": 0.22, "effect": "zoom_in"},
            # "왜 대답을 안 해?... 나 오늘 진짜 예쁘지?... 끝나지 않았습니다" → 수빈 압박
            {"scene": "S-06", "ratio": 0.56, "effect": "zoom_in"},
        ]
    },
    {
        "id": "02_baby",
        "audio": "S07_S08_baby.mp3",
        "beat_after": 0.8,
        "segments": [
            # "콩아, 이모 예쁘지?" → 수빈+콩이
            {"scene": "S-07", "ratio": 0.55, "effect": "static"},
            # "민준이는 무언가를 감지합니다" → 민준 관찰
            {"scene": "S-08", "ratio": 0.45, "effect": "static"},
        ]
    },
    {
        "id": "03_validation",
        "audio": "S08_validation.mp3",
        "beat_after": 0.8,
        "segments": [
            # "확인 추구 행동... 자기 가치를 외부에서" → 아기 씬 회상 (분석 대상)
            {"scene": "S-07", "ratio": 0.45, "effect": "static"},
            # "대답을 받아내는 행위 자체... 일종의 의식" → 민준 관찰
            {"scene": "S-08", "ratio": 0.55, "effect": "zoom_in"},
        ]
    },
    {
        "id": "04_transition",
        "audio": "S08_transition.mp3",
        "beat_after": 1.3,
        "segments": [
            # "어떤 선택지가 남아있을까요?" → 민준 클로즈업 (2막 예고)
            {"scene": "S-05", "ratio": 1.0, "effect": "zoom_in"},
        ]
    },
    {
        "id": "05_minjun_pov",
        "audio": "S09_S10_minjun_pov.mp3",
        "beat_after": 0.8,
        "segments": [
            # "시간을 되감아볼게요" → 되감기 (수빈 유령 + 민준 선명)
            {"scene": "S-09", "ratio": 0.45, "effect": "static"},
            # "자율성 침해... 본능적으로 불쾌함" → 민준 내면
            {"scene": "S-10", "ratio": 0.55, "effect": "zoom_in"},
        ]
    },
    {
        "id": "06_coerced",
        "audio": "S11_coerced.mp3",
        "beat_after": 0.8,
        "segments": [
            # "질문처럼 들리지만, 동의를 강제... 강요된 동의" → 코너 민준
            {"scene": "S-11", "ratio": 1.0, "effect": "zoom_in"},
        ]
    },
    {
        "id": "07_vending",
        "audio": "S12_vending.mp3",
        "beat_after": 0.8,
        "segments": [
            # "칭찬 자판기... 도구적 관계" → 자판기 메타포
            {"scene": "S-12", "ratio": 1.0, "effect": "static"},
        ]
    },
    {
        "id": "08_dissonance_boundary",
        "audio": "S13_S14_dissonance_boundary.mp3",
        "beat_after": 1.3,
        "segments": [
            # "반발은 딜레마... 인지부조화" → 천사/악마
            {"scene": "S-13", "ratio": 0.50, "effect": "static"},
            # "심리적 경계를 지키는 행위" → 경계선
            {"scene": "S-14", "ratio": 0.50, "effect": "zoom_in"},
        ]
    },
    {
        "id": "09_jiwoo_intro",
        "audio": "S15_S17_jiwoo_intro.mp3",
        "beat_after": 0.8,
        "segments": [
            # "같은 질문. 다른 사람... 솔직하게? 아니면?" → 카페 수빈+지우
            {"scene": "S-15", "ratio": 0.35, "effect": "static"},
            # "관계 유지 동기... 3초면 끝나는 일" → 지우 내면
            {"scene": "S-16", "ratio": 0.35, "effect": "zoom_in"},
            # "어, 예쁘다! 그치?" → 지우 대답
            {"scene": "S-17", "ratio": 0.30, "effect": "static"},
        ]
    },
    {
        "id": "10_rationalize",
        "audio": "S18_rationalize.mp3",
        "beat_after": 0.8,
        "segments": [
            # "뭐, 실제로 안 예쁜 것도 아니니까... 자기 합리화" → 합리화
            {"scene": "S-18", "ratio": 1.0, "effect": "static"},
        ]
    },
    {
        "id": "11_helplessness",
        "audio": "S19_S20_helplessness.mp3",
        "beat_after": 1.3,
        "segments": [
            # "이게 한두 번이 아닙니다... 학습된 무력감" → 다중노출 지우
            {"scene": "S-19", "ratio": 0.50, "effect": "zoom_in"},
            # "지우는 이유를 정확히 설명하지 못합니다" → 지우 현관
            {"scene": "S-20", "ratio": 0.50, "effect": "static"},
        ]
    },
    {
        "id": "12_subin_reversal",
        "audio": "S21_subin_reversal.mp3",
        "beat_after": 1.8,
        "segments": [
            # "아무도 없는 밤... 나르시시즘적 공급" → 수빈 밤
            {"scene": "S-21", "ratio": 1.0, "effect": "zoom_in"},
        ]
    },
    {
        "id": "13_gaslighting",
        "audio": "S22_gaslighting.mp3",
        "beat_after": 0.8,
        "segments": [
            # "가스라이팅 아니야?... 아닙니다" → 가스라이팅≠
            {"scene": "S-22", "ratio": 1.0, "effect": "static"},
        ]
    },
    {
        "id": "14_structure",
        "audio": "S23_structure.mp3",
        "beat_after": 1.3,
        "segments": [
            # "세 가지 심리적 역학... 누구도 나쁜 사람이 아닙니다" → 세 사람 나란히
            {"scene": "S-23", "ratio": 1.0, "effect": "static"},
        ]
    },
    {
        "id": "15_epilogue",
        "audio": "S24_S25_epilogue.mp3",
        "beat_after": 2.3,
        "segments": [
            # "나 예쁘지?라고 묻는 사람이 있나요?... 구독" → 에필로그
            {"scene": "S-24", "ratio": 1.0, "effect": "zoom_out"},
        ]
    },
]


# ── 유틸리티 ──

def run_ffmpeg(args, desc=""):
    cmd = ["ffmpeg", "-y"] + args
    print(f"  → {desc}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ 실패: {result.stderr[-300:]}")
        return False
    return True


def get_duration(filepath):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(filepath)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def _scene_rng(seed_str):
    import hashlib
    h = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    vals = []
    for _ in range(12):
        h, r = divmod(h, 1000003)
        vals.append(r / 1000003)
        h = h ^ (r * 31)
    return vals


def ken_burns_filter(effect, duration, resolution=RESOLUTION, breathing=True, scene_seed=""):
    """Ken Burns + Breathing v6 필터 (build_video.py에서 이식)"""
    w, h = map(int, resolution.split("x"))
    frames = int(float(duration) * FPS)
    iw, ih = w * 2, h * 2
    ires = f"{iw}x{ih}"
    upscale = f"scale={iw}:{ih}:flags=lanczos,"
    downscale = f",scale={w}:{h}:flags=lanczos"

    if breathing:
        bi = BREATHING_INTENSITY
        rng = _scene_rng(scene_seed or "default")
        pz1, pz2 = rng[0] * 6.283, rng[1] * 6.283
        px1, px2 = rng[2] * 6.283, rng[3] * 6.283
        py1, py2 = rng[4] * 6.283, rng[5] * 6.283
        az1 = 0.025 * bi * (0.7 + rng[6] * 0.6)
        az2 = 0.015 * bi * (0.7 + rng[7] * 0.6)
        ax1 = 12.0 * bi * (0.7 + rng[8] * 0.6)
        ax2 = 8.0 * bi * (0.7 + rng[9] * 0.6)
        ay1 = 8.0 * bi * (0.7 + rng[10] * 0.6)
        ay2 = 6.0 * bi * (0.7 + rng[11] * 0.6)
        bz = f"+{az1:.4f}*sin(on*0.05+{pz1:.3f})+{az2:.4f}*sin(on*0.03+{pz2:.3f})"
        raw_dx = f"{ax1:.1f}*sin(on*0.026+{px1:.3f})+{ax2:.1f}*sin(on*0.016+{px2:.3f})"
        dx = f"+max(-30,min(30,{raw_dx}))"
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
    else:
        zp = (f"zoompan=z='1.0{bz}':"
              f"x='{cx}':y='{cy}':"
              f"d={frames}:s={ires}:fps={FPS}")

    return f"{upscale}{zp}{downscale}"


# ── v3 씬 이미지 탐색 ──

def find_v3_scene(scene_id):
    """v3_layers/scenes/ 에서 씬 이미지 찾기.
    portrait_ 버전을 scene_ 버전보다 우선.
    """
    # portrait 우선
    portrait = sorted(V3_SCENES_DIR.glob(f"*portrait_{scene_id}.png"), reverse=True)
    if portrait:
        return portrait[0]
    # scene 버전
    scene = sorted(V3_SCENES_DIR.glob(f"*scene_{scene_id}.png"), reverse=True)
    if scene:
        return scene[0]
    return None


# ── 클립 빌드 ──

def build_single_segment_clip(image, audio, duration, effect, output, scene_seed=""):
    """단일 이미지 + 오디오 → mp4 클립"""
    vf = ken_burns_filter(effect, duration, scene_seed=scene_seed)
    return run_ffmpeg([
        "-loop", "1", "-i", str(image),
        "-i", str(audio),
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-pix_fmt", "yuv420p",
        str(output)
    ], f"single clip ({duration:.1f}s, {effect})")


def build_multi_segment_clip(segments, audio_path, total_duration, output, clip_id):
    """멀티 씬 세그먼트 → 시간 분할 클립
    각 세그먼트를 개별 무음 mp4로 생성 → concat → 오디오 합성
    """
    temp_dir = CLIPS_V2_DIR / f"_temp_{clip_id}"
    temp_dir.mkdir(exist_ok=True)
    seg_files = []

    for i, seg in enumerate(segments):
        seg_duration = total_duration * seg["ratio"]
        image = find_v3_scene(seg["scene"])
        if not image:
            print(f"    ⚠ {seg['scene']}: 이미지 없음, 건너뜀")
            continue

        seg_out = temp_dir / f"seg_{i:02d}.mp4"
        vf = ken_burns_filter(seg["effect"], seg_duration, scene_seed=f"{clip_id}_{seg['scene']}")

        run_ffmpeg([
            "-loop", "1", "-i", str(image),
            "-vf", vf,
            "-t", str(seg_duration),
            "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-an",
            str(seg_out)
        ], f"  seg {i}: {seg['scene']} ({seg_duration:.1f}s)")
        if seg_out.exists():
            seg_files.append(seg_out)

    if not seg_files:
        return False

    # concat 세그먼트들
    concat_list = temp_dir / "concat.txt"
    with open(concat_list, "w") as f:
        for sf in seg_files:
            f.write(f"file '{sf}'\n")

    # concat + 오디오 합성
    run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", str(audio_path),
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-t", str(total_duration),
        "-shortest", "-pix_fmt", "yuv420p",
        str(output)
    ], f"merge {len(seg_files)} segments + audio ({total_duration:.1f}s)")

    # 임시 파일 정리
    for sf in seg_files:
        sf.unlink()
    concat_list.unlink()
    try:
        temp_dir.rmdir()
    except OSError:
        pass

    return output.exists()


def build_silence_clip(duration, output):
    """무음 검정 화면 클립 (비트/정적용)
    edge-tts 오디오와 일치: 24000Hz mono → concat 호환성 보장
    """
    return run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s={RESOLUTION}:d={duration}:r={FPS}",
        "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac", "-ar", "24000", "-ac", "1",
        "-pix_fmt", "yuv420p",
        str(output)
    ], f"beat/silence ({duration:.1f}s)")


def build_clips():
    """Phase 1: 오디오 클립별 영상 생성"""
    print("\n=== v2 씬별 클립 생성 ===")
    CLIPS_V2_DIR.mkdir(exist_ok=True)

    for idx, item in enumerate(V2_SEQUENCE):
        clip_id = item["id"]
        audio_file = AUDIO_V2_DIR / item["audio"]
        output = CLIPS_V2_DIR / f"clip_{idx:02d}_{clip_id}.mp4"

        if not audio_file.exists():
            print(f"  ⚠ {clip_id}: 오디오 없음 ({item['audio']}), 건너뜀")
            continue

        duration = get_duration(audio_file)
        segments = item["segments"]
        print(f"\n[{idx+1}/{len(V2_SEQUENCE)}] {clip_id} ({duration:.1f}s, {len(segments)}씬)")

        if len(segments) == 1:
            # 단일 씬
            image = find_v3_scene(segments[0]["scene"])
            if not image:
                print(f"  ⚠ {segments[0]['scene']}: 이미지 없음")
                continue
            build_single_segment_clip(
                image, audio_file, duration,
                segments[0]["effect"], output,
                scene_seed=f"{clip_id}_{segments[0]['scene']}"
            )
        else:
            # 멀티 씬
            build_multi_segment_clip(segments, audio_file, duration, output, clip_id)

        # 비트(정적) 클립 생성
        beat = item.get("beat_after", 0)
        if beat > 0:
            beat_out = CLIPS_V2_DIR / f"clip_{idx:02d}_{clip_id}_beat.mp4"
            build_silence_clip(beat, beat_out)

    clip_count = len(list(CLIPS_V2_DIR.glob("clip_*.mp4")))
    print(f"\n✓ 클립 생성 완료: {clip_count}개")


def build_longform():
    """Phase 2: 롱폼 영상 조립"""
    print("\n=== v2 롱폼 영상 조립 ===")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # clip_ 파일만 (임시 파일 제외)
    clips = sorted([
        f for f in CLIPS_V2_DIR.glob("clip_*.mp4")
        if "_temp_" not in str(f) and f.name.startswith("clip_")
    ])

    if not clips:
        print("  ✗ 클립이 없습니다. 먼저 'clips' 명령을 실행하세요.")
        return

    # concat 리스트
    concat_file = CLIPS_V2_DIR / "concat_v2.txt"
    with open(concat_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_output = OUTPUT_DIR / f"{ts}_EP01_v2_preview.mp4"

    run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-crf", "18", "-c:a", "aac",
        str(raw_output)
    ], "클립 연결")

    if raw_output.exists():
        dur = get_duration(raw_output)
        size_mb = raw_output.stat().st_size / 1024 / 1024
        print(f"\n✓ v2 프리뷰 완성: {raw_output.name}")
        print(f"  길이: {dur:.0f}초 = {dur/60:.1f}분")
        print(f"  크기: {size_mb:.1f}MB")
        print(f"  해상도: {RESOLUTION}")
    else:
        print("  ✗ 롱폼 생성 실패")


def show_info():
    """씬 매핑 + 파일 확인 정보 표시"""
    print("\n=== v2 빌드 정보 ===\n")

    # 오디오 파일 확인
    print("📁 오디오 (audio/longform_v2/):")
    total_dur = 0
    for item in V2_SEQUENCE:
        audio_path = AUDIO_V2_DIR / item["audio"]
        if audio_path.exists():
            dur = get_duration(audio_path)
            total_dur += dur
            beat = item.get("beat_after", 0)
            total_dur += beat
            status = f"✅ {dur:.1f}s"
            if beat > 0:
                status += f" + {beat:.1f}s beat"
        else:
            status = "❌ 없음"
        print(f"  {item['id']:30s} {item['audio']:42s} {status}")
    print(f"  {'─'*80}")
    print(f"  {'합계':30s} {'':42s} {total_dur:.1f}s = {total_dur/60:.1f}분\n")

    # 씬 이미지 매핑 확인
    print("🖼  씬 이미지 매핑 (v3_layers/scenes/):")
    all_scenes = set()
    missing = []
    for item in V2_SEQUENCE:
        for seg in item["segments"]:
            sid = seg["scene"]
            if sid in all_scenes:
                continue
            all_scenes.add(sid)
            img = find_v3_scene(sid)
            if img:
                print(f"  {sid:8s} → {img.name}")
            else:
                print(f"  {sid:8s} → ❌ 없음")
                missing.append(sid)

    print(f"\n  총 {len(all_scenes)}개 씬 참조, {len(all_scenes)-len(missing)}개 매칭, {len(missing)}개 미싱")
    if missing:
        print(f"  ⚠ 미싱 씬: {', '.join(missing)}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    # breathing 인자
    global BREATHING_INTENSITY
    for i, arg in enumerate(sys.argv):
        if arg == "--breathing" and i + 1 < len(sys.argv):
            BREATHING_INTENSITY = float(sys.argv[i + 1])
            print(f"  Breathing: {BREATHING_INTENSITY}")

    if cmd == "clips":
        build_clips()
    elif cmd == "longform":
        build_longform()
    elif cmd == "all":
        build_clips()
        build_longform()
    elif cmd == "info":
        show_info()
    else:
        print(f"알 수 없는 명령: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
