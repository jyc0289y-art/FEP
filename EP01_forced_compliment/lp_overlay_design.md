# LivePortrait 멀티캐릭터 오버레이 설계서

> 작성: P21.2wc / 2026-04-13
> 대상: `build_video.py` LP 시스템 확장

---

## 1. 문제 정의

### 현재 시스템 한계

```
[현재] 씬 이미지 전체 → LP → 1캐릭터만 애니메이션
       ┌─────────────────────┐
       │  수빈    민준       │ ← 전체 이미지를 LP에 입력
       │  (움직임) (정지)    │    LP는 첫 감지 얼굴만 처리
       └─────────────────────┘
```

- LivePortrait는 이미지 내 **1개 얼굴**만 감지/애니메이션
- 2인 씬(scene_02, 03, 05, 10, 13, 14 등)에서 한쪽만 움직이고 반대쪽은 정지
- 대사 중인 캐릭터와 LP 애니메이션 대상이 불일치할 수 있음

### 목표 시스템

```
[목표] 씬 이미지 → 캐릭터별 크롭 → 개별 LP → 타임라인 동기화 오버레이
       ┌─────────────────────┐
       │  수빈    민준       │ ← 원본 이미지 (배경 레이어)
       │  ┌───┐  ┌───┐     │
       │  │LP-A│  │LP-B│    │ ← 각 캐릭터 LP 클립을 좌표에 오버레이
       │  └───┘  └───┘     │
       └─────────────────────┘
       타임: 0~5s 수빈 입모양 | 5~8s 민준 입모양 | 8~10s 둘 다 정지
```

---

## 2. 데이터 구조 설계

### 2-1. SCENE_CHARACTERS: 씬별 캐릭터 얼굴 좌표 딕셔너리

```python
# build_video.py 상단, SCENE_EFFECTS/SCENE_BCUTS와 동급 레벨에 배치
#
# 구조: scene_name → [캐릭터 정의, ...]
#   char_id:  캐릭터 식별자 (시리즈 고정: "minjun", "subin", "jiwoo", "narrator")
#   crop:     (x, y, w, h) — 원본 이미지(1920x1080) 기준 얼굴 크롭 영역
#             LP 입력에 적합한 크기 (최소 256x256, 권장 512x512)
#             얼굴 중심 + 어깨선까지 포함 (LP pasteback 품질 향상)
#   overlay:  (x, y, w, h) — LP 출력을 원본 위에 합성할 위치/크기
#             crop과 동일하거나 약간 확장 (블렌딩 마진)
#   driving:  LP 드라이빙 템플릿 (기본값, 타임라인에서 오버라이드 가능)
#   multiplier: LP 모션 강도 (0.0~1.0)

SCENE_CHARACTERS = {
    "scene_02": [
        {
            "char_id": "subin",
            "crop": (120, 80, 512, 512),      # 좌측 수빈 얼굴+어깨
            "overlay": (100, 60, 552, 552),    # 블렌딩 마진 20px
            "driving": "shy.pkl",
            "multiplier": 0.55,
        },
        {
            "char_id": "minjun",
            "crop": (1280, 100, 512, 512),     # 우측 민준 얼굴+어깨
            "overlay": (1260, 80, 552, 552),
            "driving": "aggrieved.pkl",
            "multiplier": 0.50,
        },
    ],
    "scene_03": [
        # ... 동일 패턴
    ],
    # 단일 캐릭터 씬은 등록하지 않음 → 기존 전체 이미지 LP 폴백
}
```

**좌표 결정 방법 (반자동):**

```
1단계: 자동 감지 (보조 스크립트)
  - face_detection (mediapipe/insightface) 으로 씬 이미지의 모든 얼굴 bbox 추출
  - 512x512 크롭 영역 자동 제안 (얼굴 중심 + 상하 패딩)
  - → SCENE_CHARACTERS 초안 JSON 출력

2단계: 수동 검수/조정
  - 자동 제안 좌표를 Pillow 시각화로 확인 (크롭 영역 빨간 박스 표시)
  - 필요 시 좌표 미세 조정 (캐릭터 잘림, 겹침 등)
```

### 2-2. SCENE_TALK_TIMELINE: 대사 타임라인 딕셔너리

```python
# 대사 중인 캐릭터에게만 "말하는" LP 모션(laugh/wink 등)을 적용하고,
# 말하지 않는 캐릭터에게는 "듣는" LP 모션(shy/aggrieved 등)을 적용
#
# 구조: scene_name → [타임라인 세그먼트, ...]
#   t_start, t_end: 시간 범위 (초)
#   active:         이 구간에서 "말하는" 캐릭터 ID 리스트
#                   빈 리스트 = 내레이터 구간 (모든 캐릭터 idle)
#   overrides:      특정 캐릭터의 driving/multiplier 오버라이드 (선택)

SCENE_TALK_TIMELINE = {
    "scene_02": [
        {"t_start": 0.0,  "t_end": 3.5,  "active": ["subin"],
         "overrides": {"subin": {"driving": "laugh.pkl", "multiplier": 0.60}}},
        {"t_start": 3.5,  "t_end": 6.0,  "active": ["minjun"],
         "overrides": {"minjun": {"driving": "shy.pkl", "multiplier": 0.50}}},
        {"t_start": 6.0,  "t_end": 8.2,  "active": ["subin", "minjun"]},  # 동시 대화
        {"t_start": 8.2,  "t_end": 10.0, "active": []},  # 내레이터 해설
    ],
}
```

**타임라인 결정 방법:**

```
1. 각본의 대사 구간 + edge-tts/Typecast 클립 길이 → 시작/종료 시간 계산
2. generate_tts_v2.sh 출력의 클립별 duration 참조
3. 내레이터 구간은 자동으로 active: [] 처리
```

### 2-3. LP_IDLE_MOTION: 비발화 캐릭터 기본 모션

```python
# 말하지 않는 캐릭터에게 적용하는 "듣는 표정" 기본값
# 캐릭터별로 고정하여 시리즈 일관성 유지

LP_IDLE_MOTION = {
    "minjun":  {"driving": "shy.pkl",       "multiplier": 0.25},  # 건조하게 듣기
    "subin":   {"driving": "wink.pkl",      "multiplier": 0.30},  # 가볍게 반응
    "jiwoo":   {"driving": "aggrieved.pkl", "multiplier": 0.20},  # 조용히 관찰
}
```

---

## 3. LP 배치 워크플로우

### 3-1. 처리 파이프라인 전체 흐름

```
┌────────────────────────────────────────────────────────────────┐
│                    LP 멀티캐릭터 배치                            │
│                                                                │
│  Phase A: 크롭 추출                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ scene_02.png │───►│ subin_crop   │    │ minjun_crop  │     │
│  │ (1920x1080)  │───►│ (512x512)    │    │ (512x512)    │     │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘     │
│                             │                    │              │
│  Phase B: 개별 LP 실행                                          │
│                             ▼                    ▼              │
│                    ┌──────────────┐    ┌──────────────┐        │
│                    │ LP(subin,    │    │ LP(minjun,   │        │
│                    │  laugh.pkl)  │    │  aggrieved)  │        │
│                    └──────┬───────┘    └──────┬───────┘        │
│                           │                    │                │
│  Phase C: 타임라인 세그먼트별 LP 클립 선택                        │
│           (active 캐릭터 → talk 모션, 나머지 → idle 모션)        │
│                           │                    │                │
│  Phase D: FFmpeg 오버레이 합성                                   │
│                           ▼                    ▼                │
│                    ┌─────────────────────────────┐              │
│                    │  원본 이미지 + 브리딩 배경    │              │
│                    │  + subin LP @(120,80)        │              │
│                    │  + minjun LP @(1280,100)     │              │
│                    │  + 페더 블렌딩               │              │
│                    └─────────────────────────────┘              │
└────────────────────────────────────────────────────────────────┘
```

### 3-2. Phase A — 크롭 추출 (`lp_crop_characters.py`)

새 보조 스크립트. SCENE_CHARACTERS의 crop 좌표를 읽어 이미지 크롭.

```
입력: scenes/scene_02_confirmation.png + SCENE_CHARACTERS["scene_02"]
출력: lp_crops/scene_02__subin.png    (512x512)
      lp_crops/scene_02__minjun.png   (512x512)
```

**디렉토리 구조:**

```
EP01_forced_compliment/
├── lp_crops/                    # [신규] 캐릭터별 크롭 이미지
│   ├── scene_02__subin.png
│   ├── scene_02__minjun.png
│   └── ...
├── lp_multi_out/                # [신규] 멀티캐릭터 LP 출력
│   ├── scene_02__subin--laugh.mp4
│   ├── scene_02__subin--shy.mp4      # idle 모션
│   ├── scene_02__minjun--aggrieved.mp4
│   ├── scene_02__minjun--shy.mp4     # idle 모션
│   └── ...
├── liveportrait_out/            # [기존] 단일 캐릭터 LP 출력 (호환 유지)
```

### 3-3. Phase B — 개별 LP 실행 (`lp_multi_batch.py`)

새 배치 스크립트. 기존 `/tmp/fep_liveportrait_batch.py` 패턴을 확장.

```python
# 의사 코드
for scene_name, characters in SCENE_CHARACTERS.items():
    for char in characters:
        crop_img = lp_crops / f"{scene_name}__{char['char_id']}.png"

        # 1) talk 모션 (대사 중 사용)
        run_lp(crop_img, char["driving"], char["multiplier"],
               output=f"{scene_name}__{char['char_id']}--{driving_name}.mp4")

        # 2) idle 모션 (비발화 시 사용)
        idle = LP_IDLE_MOTION[char["char_id"]]
        run_lp(crop_img, idle["driving"], idle["multiplier"],
               output=f"{scene_name}__{char['char_id']}--idle.mp4")
```

**LP 실행 횟수 산정:**

```
멀티캐릭터 씬 수 × 캐릭터 수 × 2 (talk + idle)
예: 6씬 × 2캐릭터 × 2모션 = 24회
씬당 ~50초 → 총 ~20분 (MPS 기준)
```

### 3-4. Phase C — 타임라인 세그먼트별 LP 클립 매핑

SCENE_TALK_TIMELINE을 읽어 각 시간 구간에 어떤 LP 클립을 사용할지 결정.

```
scene_02 타임라인 예시:
  0.0~3.5s: subin=talk(laugh), minjun=idle(shy)
  3.5~6.0s: subin=idle(wink), minjun=talk(shy)
  6.0~8.2s: subin=talk(laugh), minjun=talk(aggrieved)  ← 동시
  8.2~10.0s: subin=idle(wink), minjun=idle(shy)         ← 내레이터
```

### 3-5. Phase D — FFmpeg 오버레이 합성

핵심 합성 전략: **세그먼트별 클립 생성 → concat**

```
세그먼트 0 (0.0~3.5s):
  [배경: 원본+브리딩 3.5s]
  + overlay [subin LP talk, 크롭→루핑→3.5s] @(120,80)
  + overlay [minjun LP idle, 크롭→루핑→3.5s] @(1280,100)
  → seg_00.mp4

세그먼트 1 (3.5~6.0s):
  [배경: 원본+브리딩 2.5s]
  + overlay [subin LP idle] @(120,80)
  + overlay [minjun LP talk] @(1280,100)
  → seg_01.mp4

... → concat → scene_02_final.mp4
```

---

## 4. FFmpeg 오버레이 합성 상세

### 4-1. 단일 세그먼트 합성 필터그래프

```
입력:
  [0] 배경 클립 (원본 이미지 + 브리딩, ken_burns_filter 적용)
  [1] 캐릭터A LP 클립 (루핑 + 512x512 스케일)
  [2] 캐릭터B LP 클립 (루핑 + 512x512 스케일)

필터그래프:
  [1:v] scale=552:552:flags=lanczos, format=rgba [a_scaled];
  [2:v] scale=552:552:flags=lanczos, format=rgba [b_scaled];
  [0:v][a_scaled] overlay=x=100:y=60:format=auto [tmp];
  [tmp][b_scaled] overlay=x=1260:y=80:format=auto [out]
```

### 4-2. 페더 블렌딩 (경계 부드럽게)

LP 크롭 영역을 원본 위에 직접 붙이면 경계가 보임. 해결:

```
방법 A: LP --flag-pasteback 활용 (권장)
  - LP 자체의 pasteback이 원본 크롭 영역에 블렌딩 수행
  - 크롭 이미지를 LP에 넣으면 pasteback이 원본 크롭 크기로 결과 반환
  - → 경계 블렌딩이 LP 내장 기능으로 해결됨

방법 B: FFmpeg alphamerge (대안)
  - 크롭 영역 가장자리에 Pillow로 그라디언트 알파 마스크 생성
  - LP 클립에 alphamerge 적용 후 overlay
  - 장점: LP pasteback 품질이 부족할 때 보완
  - 단점: 추가 처리 단계

방법 C: Pillow 원형 블러 마스크 (최종 대안)
  - 크롭 영역 경계 20px에 가우시안 블러 적용
  - 프레임 단위 처리 필요 → 느림, 최후 수단
```

**권장: 방법 A를 기본으로 사용, 경계 아티팩트 발생 시 방법 B 보완**

### 4-3. N캐릭터 확장 (3인 이상)

```python
# FFmpeg overlay는 체인으로 확장 가능
# 3인 씬(scene_14: 수빈+민준+지우):
filter_chain = "[0:v]"
for i, char in enumerate(characters):
    input_idx = i + 1
    x, y, w, h = char["overlay"]
    filter_chain += f"[{input_idx}:v]overlay={x}:{y}:format=auto"
    if i < len(characters) - 1:
        filter_chain += f"[tmp{i}];[tmp{i}]"
filter_chain += "[out]"
```

---

## 5. build_video.py 통합 방안

### 5-1. 기존 시스템과의 호환성

```
판단 로직 (_build_single_clip 수정):

  씬이 SCENE_CHARACTERS에 있는가?
    ├── YES → _build_multichar_lp_clip() [신규]
    └── NO  → 기존 단일 LP 로직 유지
              (find_liveportrait_video → _build_liveportrait_clip)
```

**핵심 원칙: 기존 코드 경로를 변경하지 않고 분기만 추가**

### 5-2. 신규 함수 설계

```python
# ---- 신규 상수 ----
LP_MULTI_DIR = BASE_DIR / "lp_multi_out"
LP_CROPS_DIR = BASE_DIR / "lp_crops"

# ---- 신규 함수 ----

def find_multichar_lp_videos(scene_name, char_id, motion_type="talk"):
    """멀티캐릭터 LP 출력 영상 탐색.
    motion_type: "talk" (대사 모션) 또는 "idle" (비발화 모션)
    반환: Path 또는 None
    """
    # 패턴: scene_02__subin--laugh.mp4 (talk) / scene_02__subin--idle.mp4
    ...

def _build_multichar_lp_clip(scene_name, image, duration, effect, output,
                              desc="", scene_seed=""):
    """멀티캐릭터 LP 오버레이 클립 생성.

    1. SCENE_CHARACTERS에서 캐릭터 좌표 로드
    2. SCENE_TALK_TIMELINE에서 타임라인 세그먼트 로드
    3. 세그먼트별로:
       a. 배경 클립 생성 (ken_burns_filter)
       b. 각 캐릭터의 LP 클립 선택 (talk/idle)
       c. FFmpeg overlay 합성
    4. 세그먼트 concat → 최종 클립
    """
    characters = SCENE_CHARACTERS.get(scene_name, [])
    timeline = SCENE_TALK_TIMELINE.get(scene_name, [])

    if not characters or not timeline:
        # 폴백: 기존 단일 LP 또는 브리딩
        ...

    segments = []
    for seg_idx, seg in enumerate(timeline):
        seg_dur = seg["t_end"] - seg["t_start"]
        seg_output = TMP_DIR / f"{scene_name}_mcseg_{seg_idx:02d}.mp4"

        # 배경 클립
        bg_clip = TMP_DIR / f"{scene_name}_mcbg_{seg_idx:02d}.mp4"
        _build_single_breathing_clip(image, seg_dur, effect, bg_clip, scene_seed)

        # LP 클립 준비
        lp_inputs = []
        overlay_coords = []
        for char in characters:
            is_active = char["char_id"] in seg.get("active", [])
            motion = "talk" if is_active else "idle"

            # 오버라이드 확인
            overrides = seg.get("overrides", {}).get(char["char_id"], {})

            lp_video = find_multichar_lp_videos(
                scene_name, char["char_id"], motion)
            if lp_video:
                # 루핑 + 크롭 크기 스케일
                lp_clip = TMP_DIR / f"{scene_name}_mc_{char['char_id']}_{seg_idx}.mp4"
                _loop_and_scale_lp(lp_video, seg_dur, char["overlay"], lp_clip)
                lp_inputs.append(lp_clip)
                overlay_coords.append(char["overlay"])

        # FFmpeg 멀티 오버레이 합성
        _ffmpeg_multi_overlay(bg_clip, lp_inputs, overlay_coords, seg_dur, seg_output)
        segments.append(seg_output)

    # concat 세그먼트
    _concat_segments(segments, output)
    ...


def _ffmpeg_multi_overlay(background, lp_clips, coords, duration, output):
    """N개 LP 클립을 배경 위에 순차 overlay."""
    inputs = ["-i", str(background)]
    for clip in lp_clips:
        inputs += ["-i", str(clip)]

    # 필터 체인 동적 구성
    filter_parts = []
    prev = "[0:v]"
    for i, (clip, (x, y, w, h)) in enumerate(zip(lp_clips, coords)):
        scaled = f"[s{i}]"
        out = f"[tmp{i}]" if i < len(lp_clips) - 1 else "[out]"
        filter_parts.append(f"[{i+1}:v]scale={w}:{h}:flags=lanczos{scaled}")
        filter_parts.append(f"{prev}{scaled}overlay={x}:{y}:format=auto{out}")
        prev = f"[tmp{i}]"

    run_ffmpeg(inputs + [
        "-filter_complex", ";".join(filter_parts),
        "-map", "[out]", "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an",
        str(output)
    ], f"multi-overlay ({len(lp_clips)} chars)")
```

### 5-3. _build_single_clip 수정 (최소 변경)

```python
def _build_single_clip(image, duration, effect, output, desc="", scene_seed=""):
    """단일 이미지 → 영상 클립 (무음).
    우선순위: 멀티캐릭터 LP > 단일 LP > 패럴랙스 > 정지이미지+브리딩
    """
    # [신규] 멀티캐릭터 LP: SCENE_CHARACTERS에 등록된 씬
    if USE_LIVEPORTRAIT and "bcut" not in (scene_seed or ""):
        scene_base = "_".join(scene_seed.split("_")[:2]) if scene_seed else ""
        if scene_base in SCENE_CHARACTERS:
            _build_multichar_lp_clip(
                scene_base, image, duration, effect, output, desc, scene_seed)
            return

    # [기존] 단일 LP
    if USE_LIVEPORTRAIT and "bcut" not in (scene_seed or ""):
        scene_base = "_".join(scene_seed.split("_")[:2]) if scene_seed else ""
        lp_video = find_liveportrait_video(scene_base) if scene_base else None
        if lp_video:
            _build_liveportrait_clip(lp_video, duration, output, desc, scene_seed)
            return

    # [기존] 패럴랙스 / 브리딩 폴백
    ...
```

### 5-4. CLI 확장

```
기존:
  --liveportrait     LivePortrait 단일 캐릭터 모드

추가 (없음):
  --liveportrait 플래그 하나로 단일/멀티 자동 분기
  SCENE_CHARACTERS 등록 여부로 판단하므로 CLI 변경 불필요
```

---

## 6. 대사 타임라인 동기화 상세

### 6-1. 타임라인 데이터 소스

```
각본 (시네마틱 각본.md)
  ↓ 대사 구간 추출
TTS 클립 길이 측정 (edge-tts 또는 Typecast)
  ↓ 시작/종료 시간 계산
SCENE_TALK_TIMELINE 딕셔너리 작성
```

### 6-2. 타이밍 정밀도

```
요구 정밀도: ±0.3초 (사람이 감지하기 어려운 수준)
LP 클립은 루핑이므로 시작점 오프셋 불필요
세그먼트 경계의 전환은 프레임 정확도(1/30초)로 concat
```

### 6-3. 동시 발화 처리

```
active: ["subin", "minjun"] → 두 캐릭터 모두 talk 모션 사용
실제로는 빠르게 번갈아 말하는 경우가 대부분이므로
양쪽 모두 입모양 움직임이 자연스러움
```

### 6-4. 비트(정적) 구간

```
active: [] + 각본의 "비트 1.5초" 표기
→ 모든 캐릭터 idle 모션 (미세한 눈깜빡/숨쉬기)
→ 배경 브리딩만 동작하는 정적 구간
→ 시네마틱 연출 원칙 #6 "감정 잔상" 구현
```

---

## 7. 보조 도구 설계

### 7-1. lp_crop_characters.py (신규)

```
역할: SCENE_CHARACTERS 좌표로 씬 이미지에서 캐릭터 크롭 추출
입력: build_video.py의 SCENE_CHARACTERS + scenes/ 이미지
출력: lp_crops/ 디렉토리에 캐릭터별 크롭 이미지

부가 기능:
  --preview: 원본 이미지에 크롭 영역 빨간 박스 시각화 (검수용)
  --detect:  insightface로 얼굴 자동 감지 → SCENE_CHARACTERS 초안 출력
```

### 7-2. lp_multi_batch.py (신규)

```
역할: 크롭된 캐릭터별 이미지에 LP 배치 실행
입력: lp_crops/ + SCENE_CHARACTERS (driving/multiplier)
출력: lp_multi_out/ 디렉토리에 캐릭터별 LP 영상

실행: PYTORCH_ENABLE_MPS_FALLBACK=1 python lp_multi_batch.py
예상 시간: 24클립 × 50초 = ~20분
```

### 7-3. lp_timeline_preview.py (선택)

```
역할: SCENE_TALK_TIMELINE을 ASCII 타임라인으로 시각화
출력 예:
  scene_02 (10.0s):
  subin  ████████░░░░░░████████░░░░  talk|idle|talk|idle
  minjun ░░░░░░░░██████████████░░░░  idle|talk|talk|idle
         0    2    4    6    8   10
```

---

## 8. 성능/리스크 분석

### 8-1. 처리 시간 추정

```
┌────────────────────────────────┬──────────┬──────────┐
│ 단계                           │ 시간     │ 병목     │
├────────────────────────────────┼──────────┼──────────┤
│ Phase A: 크롭 추출              │ ~5초     │ Pillow   │
│ Phase B: LP 배치 (24클립)       │ ~20분    │ MPS GPU  │
│ Phase C: 타임라인 매핑          │ <1초     │ 딕셔너리 │
│ Phase D: FFmpeg 오버레이 합성    │ ~3분     │ CPU      │
├────────────────────────────────┼──────────┼──────────┤
│ 합계                           │ ~25분    │          │
└────────────────────────────────┴──────────┴──────────┘

비교: 현재 단일 LP 배치 = ~12분 (15씬 × 50초)
추가 비용 = ~13분 (멀티캐릭터 씬의 2번째 캐릭터 + idle 모션)
```

### 8-2. 리스크와 완화

```
┌─────────────────────────────┬───────────────────────────────────────┐
│ 리스크                       │ 완화                                  │
├─────────────────────────────┼───────────────────────────────────────┤
│ LP가 크롭 이미지의 얼굴을    │ 크롭 크기를 512x512 이상으로 유지     │
│ 감지하지 못함                │ + 얼굴이 중앙에 오도록 패딩 조정       │
├─────────────────────────────┼───────────────────────────────────────┤
│ overlay 경계 아티팩트         │ LP --flag-pasteback 기본 사용         │
│ (크롭↔원본 불일치)           │ + 필요 시 알파 마스크 블렌딩 추가      │
├─────────────────────────────┼───────────────────────────────────────┤
│ 세그먼트 경계에서 모션 불연속  │ 세그먼트 간 0.1초 크로스페이드 삽입   │
│ (talk→idle 전환 시 끊김)      │ 또는 동일 LP 클립에서 오프셋 연속 재생 │
├─────────────────────────────┼───────────────────────────────────────┤
│ LP 만화체 얼굴 미감지        │ 크롭 후에도 미감지 시 → 브리딩 폴백   │
│ (현재 EP01에서 1/15 실패)     │ 해당 캐릭터만 정지, 나머지는 LP 유지  │
├─────────────────────────────┼───────────────────────────────────────┤
│ 타임라인 작성 노동 비용       │ 각본에서 자동 추출 스크립트 검토      │
│                              │ (Phase 1에서는 수동 작성 허용)         │
└─────────────────────────────┴───────────────────────────────────────┘
```

### 8-3. 폴백 전략

```
레벨 1: 멀티캐릭터 LP 성공 → 타임라인 동기화 오버레이
레벨 2: 일부 캐릭터 LP 실패 → 성공한 캐릭터만 오버레이 + 나머지 정지
레벨 3: 모든 캐릭터 LP 실패 → 기존 단일 LP 시도
레벨 4: 단일 LP도 실패 → 정지 이미지 + 브리딩 (현재 동작)
```

---

## 9. 구현 우선순위

```
Phase 1 (MVP — EP.02 적용 목표):
  ✦ SCENE_CHARACTERS 딕셔너리 구조 확정
  ✦ lp_crop_characters.py 구현
  ✦ lp_multi_batch.py 구현
  ✦ _build_multichar_lp_clip 기본 구현 (타임라인 없이 전체 talk)
  ✦ _build_single_clip 분기 추가

Phase 2 (타임라인 동기화):
  ✦ SCENE_TALK_TIMELINE 딕셔너리 구조 확정
  ✦ 세그먼트별 talk/idle 분기 구현
  ✦ 세그먼트 간 크로스페이드

Phase 3 (자동화/품질):
  ✦ 얼굴 자동 감지 (--detect)
  ✦ 타임라인 프리뷰 도구
  ✦ 각본→타임라인 반자동 변환
```

---

## 10. 에피소드 공용 재사용 설계

```
에피소드별 교체 항목:
  1. SCENE_CHARACTERS   — 씬별 캐릭터 좌표 (이미지마다 다름)
  2. SCENE_TALK_TIMELINE — 대사 타임라인 (각본마다 다름)

에피소드 공통 유지 항목:
  1. LP_IDLE_MOTION      — 캐릭터별 기본 idle 모션 (시리즈 고정)
  2. _build_multichar_lp_clip()  — 합성 로직
  3. _ffmpeg_multi_overlay()     — FFmpeg 파이프라인
  4. lp_crop_characters.py       — 크롭 도구
  5. lp_multi_batch.py           — 배치 도구
```

이 설계는 기존 build_video.py의 패턴(딕셔너리 교체로 에피소드 전환)을 그대로 따르며, `SCENE_BCUTS`, `SHORTS_CONFIG`과 동일한 수준의 재사용성을 목표로 한다.
