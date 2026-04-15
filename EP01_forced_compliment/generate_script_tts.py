#!/usr/bin/env python3
"""
FEP EP.01 각본 전체 TTS 생성기
— 각본 MD 파일을 파싱하여 edge-tts로 전체 오디오를 생성
— 대사, 내레이션, 연출 노트, 주석, 감정 지시 등 모든 요소를 읽어줌
— 화자별 음성 구분: 내레이터/수빈/민준/지우 + 시스템(연출노트/주석)

사용법:
  python generate_script_tts.py
"""
import asyncio, re, os, subprocess, tempfile, json
from pathlib import Path
from datetime import datetime

# edge-tts 음성 매핑
VOICES = {
    "내레이터": "ko-KR-InJoonNeural",    # 남성 차분한 톤
    "수빈":     "ko-KR-SunHiNeural",     # 여성 밝은 톤
    "민준":     "ko-KR-InJoonNeural",     # 남성 (내레이터와 같지만 속도 차별화)
    "지우":     "ko-KR-SunHiNeural",      # 여성 (수빈과 같지만 속도 차별화)
    "시스템":   "ko-KR-InJoonNeural",     # 연출 노트/주석 읽기용
}

# edge-tts 속도/피치 조정
VOICE_PARAMS = {
    "내레이터": {"rate": "+0%", "pitch": "+0Hz"},
    "수빈":     {"rate": "+10%", "pitch": "+2Hz"},
    "민준":     {"rate": "-5%", "pitch": "-3Hz"},
    "지우":     {"rate": "+0%", "pitch": "+1Hz"},
    "시스템":   {"rate": "+5%", "pitch": "-2Hz"},
}

BASE_DIR = Path(__file__).parent
SCRIPT_PATH = BASE_DIR / "20260413_075604_EP01_시네마틱_각본.md"
OUTPUT_DIR = BASE_DIR / "audio" / "script_tts"


def parse_script(md_text: str) -> list:
    """
    각본 MD를 파싱하여 TTS 세그먼트 리스트를 반환.
    각 세그먼트: {"speaker": str, "text": str, "type": str}
    type: "dialogue" | "narration" | "direction" | "annotation" | "section"
    """
    segments = []
    lines = md_text.split("\n")
    i = 0

    def add(speaker, text, seg_type):
        text = text.strip()
        if text:
            # 마크다운 볼드/이탤릭 제거
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'\*(.+?)\*', r'\1', text)
            # 이모지 유지 (감정 온도 등)
            segments.append({"speaker": speaker, "text": text, "type": seg_type})

    while i < len(lines):
        line = lines[i].rstrip()

        # 빈 줄 건너뜀
        if not line:
            i += 1
            continue

        # --- 구분선: 짧은 정적
        if line.strip() == "---":
            add("시스템", "...", "pause")
            i += 1
            continue

        # ## 섹션 헤더
        if line.startswith("## "):
            title = line.lstrip("#").strip()
            add("시스템", f"섹션: {title}", "section")
            i += 1
            continue

        # ### 서브섹션 헤더
        if line.startswith("### "):
            title = line.lstrip("#").strip()
            add("시스템", title, "section")
            i += 1
            continue

        # #### 파트 헤더
        if line.startswith("#### "):
            title = line.lstrip("#").strip()
            add("시스템", title, "section")
            i += 1
            continue

        # 테이블 행 (| ... |) — 읽어줌
        if line.strip().startswith("|"):
            # 구분선 행 (|---|---) 건너뜀
            if re.match(r'^\|[\s\-:]+\|', line):
                i += 1
                continue
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if cells:
                table_text = ", ".join(cells)
                add("시스템", table_text, "annotation")
            i += 1
            continue

        # ``` 코드블록 — 감정 곡선 아트 등은 설명만
        if line.strip().startswith("```"):
            block_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block_lines.append(lines[i])
                i += 1
            i += 1  # 닫는 ``` 건너뜀
            # 감정 곡선 차트는 간단히 설명
            block_text = "\n".join(block_lines)
            if "감정 강도" in block_text or "▲" in block_text:
                add("시스템", "감정 곡선 차트가 표시되어 있습니다. 가로축은 시간, 세로축은 감정 강도입니다.", "annotation")
            continue

        # > 인용문 (연출 노트, 감정 지시)
        if line.startswith("> "):
            quote_text = line[2:].strip()
            # 연출 노트
            if quote_text.startswith("**연출 노트"):
                quote_text = quote_text.replace("**연출 노트**:", "연출 노트.")
                quote_text = quote_text.replace("**연출 노트**", "연출 노트.")
                # 다음 줄들도 같은 블록인지 확인
                i += 1
                while i < len(lines) and lines[i].startswith("> "):
                    quote_text += " " + lines[i][2:].strip()
                    i += 1
                add("시스템", quote_text, "direction")
                continue
            # 자막 지시 (📌)
            elif "📌" in quote_text:
                quote_text = quote_text.replace("📌", "").strip()
                quote_text = re.sub(r'\*\*(.+?)\*\*', r'\1', quote_text)
                add("시스템", f"자막 지시: {quote_text}", "annotation")
                i += 1
                continue
            # 감정 온도 등
            else:
                quote_text = re.sub(r'\*\*(.+?)\*\*', r'\1', quote_text)
                add("시스템", quote_text, "direction")
                i += 1
                continue

        # **[S-XX. 씬 제목]** — 씬 헤더
        scene_match = re.match(r'\*\*\[S-(\d+)\.\s*(.+?)\]\*\*', line)
        if scene_match:
            scene_num = scene_match.group(1)
            scene_title = scene_match.group(2)
            add("시스템", f"씬 {scene_num}. {scene_title}", "section")
            i += 1
            continue

        # *(정적/비트/일러스트 지시)*
        stage_match = re.match(r'^\*(.+?)\*$', line)
        if stage_match and not line.startswith("**"):
            direction = stage_match.group(1).strip()
            # 일러스트 지시는 읽어줌
            if direction.startswith("일러스트:") or direction.startswith("🎵"):
                add("시스템", direction, "direction")
            elif "비트" in direction or "정적" in direction:
                # 시간 추출
                time_match = re.search(r'(\d+\.?\d*)\s*초', direction)
                if time_match:
                    add("시스템", f"{time_match.group(1)}초 정적.", "pause")
                else:
                    add("시스템", "짧은 정적.", "pause")
            else:
                add("시스템", direction, "direction")
            i += 1
            continue

        # 화자 대사: **수빈**: / **민준**: / **내레이터**: / **지우**:
        speaker_match = re.match(r'^\*\*(.+?)\*\*\s*:\s*(.*)$', line)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            rest = speaker_match.group(2).strip()

            # 괄호 안 감정 지시 추출
            emotion_match = re.match(r'\((.+?)\)\s*(.*)', rest)
            if emotion_match:
                emotion = emotion_match.group(1)
                dialogue = emotion_match.group(2).strip()
                add("시스템", f"{speaker}, {emotion}", "direction")
                if dialogue:
                    add(speaker, dialogue, "dialogue" if speaker != "내레이터" else "narration")
            elif rest:
                add(speaker, rest, "dialogue" if speaker != "내레이터" else "narration")

            # 다음 줄들이 같은 화자의 대사 연속인지 확인
            i += 1
            while i < len(lines):
                next_line = lines[i].rstrip()
                if not next_line:
                    i += 1
                    continue
                # 다른 화자/지시/헤더면 중단
                if (next_line.startswith("**") or next_line.startswith(">") or
                    next_line.startswith("#") or next_line.startswith("*") or
                    next_line.startswith("|") or next_line.startswith("---")):
                    break
                # 일반 텍스트 → 같은 화자 대사 계속
                clean = next_line.strip()
                if clean:
                    add(speaker, clean, "dialogue" if speaker != "내레이터" else "narration")
                i += 1
            continue

        # 일반 텍스트 (화자 없는 내레이션 등)
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', line.strip())
        clean = re.sub(r'\*(.+?)\*', r'\1', clean)
        if clean and not clean.startswith("#"):
            add("내레이터", clean, "narration")

        i += 1

    return segments


async def generate_tts_segment(segment: dict, output_path: str):
    """단일 세그먼트를 edge-tts로 생성"""
    import edge_tts

    speaker = segment["speaker"]
    if speaker not in VOICES:
        speaker = "시스템"

    voice = VOICES[speaker]
    params = VOICE_PARAMS[speaker]

    communicate = edge_tts.Communicate(
        text=segment["text"],
        voice=voice,
        rate=params["rate"],
        pitch=params["pitch"],
    )
    await communicate.save(output_path)


def generate_silence(duration_sec: float, output_path: str):
    """무음 오디오 파일 생성"""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(duration_sec),
        "-ar", "24000", "-ac", "1",
        output_path
    ], capture_output=True)


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📖 각본 파일 읽기: {SCRIPT_PATH}")
    md_text = SCRIPT_PATH.read_text(encoding="utf-8")

    # ── 각본 본문만 추출 (메타데이터/감정곡선 설계/듀얼 그림체 매핑/TTS 규칙 섹션 포함) ──
    print("🔍 각본 파싱 중...")
    segments = parse_script(md_text)

    print(f"✅ {len(segments)}개 세그먼트 파싱 완료")

    # 세그먼트별 TTS 생성
    temp_dir = tempfile.mkdtemp(prefix="fep_script_tts_")
    segment_files = []
    total = len(segments)

    for idx, seg in enumerate(segments):
        if idx % 20 == 0:
            print(f"  🔊 [{idx+1}/{total}] {seg['speaker']}: {seg['text'][:40]}...")

        seg_path = os.path.join(temp_dir, f"seg_{idx:04d}.mp3")

        if seg["type"] == "pause":
            # 정적은 무음 생성
            time_match = re.search(r'(\d+\.?\d*)', seg["text"])
            duration = float(time_match.group(1)) if time_match else 0.5
            duration = min(duration, 3.0)  # 최대 3초
            silence_path = os.path.join(temp_dir, f"seg_{idx:04d}_silence.mp3")
            generate_silence(duration, silence_path)
            if os.path.exists(silence_path):
                segment_files.append(silence_path)
            continue

        try:
            await generate_tts_segment(seg, seg_path)
            if os.path.exists(seg_path) and os.path.getsize(seg_path) > 0:
                segment_files.append(seg_path)
        except Exception as e:
            print(f"  ⚠️ 세그먼트 {idx} 실패: {e}")
            continue

    print(f"\n🔗 {len(segment_files)}개 파일 concat 중...")

    # concat 파일 목록 생성
    concat_list = os.path.join(temp_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for fp in segment_files:
            f.write(f"file '{fp}'\n")

    # 최종 concat
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"{ts}_EP01_각본_전체_TTS.mp3"

    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ], capture_output=True, text=True)

    if result.returncode == 0 and output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        # 러닝타임 확인
        probe = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(output_path)
        ], capture_output=True, text=True)
        duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        print(f"\n✅ 각본 TTS 생성 완료!")
        print(f"📁 {output_path}")
        print(f"📊 {size_mb:.1f}MB, {minutes}분 {seconds}초")
    else:
        print(f"\n❌ FFmpeg 에러: {result.stderr[:500]}")

    # 세그먼트 매핑 저장 (디버깅용)
    mapping_path = OUTPUT_DIR / f"{ts}_segment_mapping.json"
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)
    print(f"📋 세그먼트 매핑: {mapping_path}")

    # 임시 파일 정리
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("🧹 임시 파일 정리 완료")


if __name__ == "__main__":
    asyncio.run(main())
