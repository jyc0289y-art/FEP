#!/usr/bin/env python3
"""
v3 Phase 2: 듀얼 스타일 캐릭터 포즈 생성
- 스타일 A (SD 귀여운체): img2img + 캐릭터 시트A 참조 + 흰 배경
- 스타일 B (시네마틱 리얼체): txt2img + 그린 스크린
타임스탬프 파일명으로 오염 방지
"""
import sys, time, json, urllib.request, urllib.error, os
from pathlib import Path
from datetime import datetime

COMFYUI_URL = "http://localhost:8188"
COMFYUI_OUTPUT = Path.home() / "developer" / "ComfyUI" / "output"
V3_DIR = Path(__file__).parent / "v3_layers"

# ── 스타일 B (시네마틱 리얼체) 프롬프트 상수 ──
CHAR_SUBIN_B = (
    "young Korean woman in her early 20s with long straight black hair, "
    "wearing a pastel pink cardigan over white top, "
    "confident bright expression with sparkling eyes"
)
CHAR_MINJUN_B = (
    "young Korean man in his early 20s with short black hair, "
    "wearing a gray hoodie"
)
CHAR_JIWOO_B = (
    "young Korean person with soft androgynous features and short messy hair, "
    "wearing a beige oversized sweater and pants, "
    "gentle tired expression"
)
CHAR_KONGI_B = (
    "cute baby with big round eyes and chubby cheeks, "
    "wearing a cute pastel yellow onesie"
)

# ── 스타일 A (SD 귀여운체) 참조 이미지 ──
# ComfyUI input/ 폴더에 복사된 정면 크롭본
STYLE_A_REF = {
    "subin": "char_subin_front.png",
    "minjun": "char_minjun_front.png",
    "jiwoo": "char_jiwoo_front.png",
    "kongi": "char_kongi_front.png",
}

# ── 스타일 B 참조 이미지 (img2img 용) ──
STYLE_B_REF = {
    "subin": "char_subin_styleB.png",
    "minjun": "char_minjun_styleB.png",
    "jiwoo": "char_jiwoo_styleB.png",
    "kongi": "char_kongi_styleB.png",
}

# ── 공통 프롬프트 ──
GREEN_BG = (
    "standing on solid bright green background, pure #00FF00 green screen, "
    "solid uniform vivid green color behind the character, "
    "no environment, no props, no scenery, only flat green background, "
    "the green extends to all edges of the image uniformly"
)

NO_TEXT = (
    "IMPORTANT: absolutely zero text anywhere in the image, "
    "no text, no letters, no words, no writing, no numbers, "
    "no watermark, no logo, no signature, "
    "no speech bubbles, no captions, no labels, "
    "no Korean characters, no Japanese characters, "
    "purely visual illustration with zero typography, "
    "original artwork, no artist signature, no website url"
)

NEGATIVE_PROMPT_B = (
    "text, letters, words, writing, numbers, watermark, logo, signature, "
    "speech bubble, caption, label, UI, Korean text, Japanese text, "
    "hangul, kanji, typography, brand, url, "
    "background scenery, room, furniture, detailed background"
)

NEGATIVE_PROMPT_A = (
    "text, letters, words, writing, numbers, watermark, logo, signature, "
    "speech bubble, caption, label, Korean text, Japanese text, "
    "hangul, typography, character sheet, turnaround, multiple views, "
    "multiple poses, reference sheet"
)

CHAR_STYLE_B = (
    "clean cartoon illustration style, Korean webtoon style, "
    "warm pastel colors, thick clean outlines, "
    "16:9 aspect ratio, "
    "all limbs complete and visible, no cropped body parts, "
    "full body or upper body clearly visible"
)

CHAR_STYLE_A = (
    "cute chibi art style, SD proportion, 2.5 head tall, "
    "Korean webtoon style, warm pastel colors, thick clean outlines, "
    "16:9 aspect ratio, single character in single pose, "
    "all limbs complete and visible"
)


# ══════════════════════════════════════════════
# 캐릭터 포즈 목록 (듀얼 스타일)
# style: "A" = SD 귀여운체, "B" = 시네마틱 리얼체
# ══════════════════════════════════════════════
CHARACTERS = {
    # ── 수빈 스타일 A (프롤로그/코믹/에필로그) ──
    "A_subin_mirror": {
        "style": "A", "char": "subin",
        "prompt": (
            "Same character in same art style, same cute face and hair and pink outfit, "
            "single character, "
            "tilting head with satisfied smile, one hand touching hair, "
            "upper body visible, white background, "
            f"{NO_TEXT}, {CHAR_STYLE_A}"
        ),
        "denoise": 0.80,
        "note": "S-01 거울 자기점검 (프롤로그, 스타일A)"
    },
    "A_subin_entrance": {
        "style": "A", "char": "subin",
        "prompt": (
            "Same character in same art style, same cute face and hair and pink outfit, "
            "single character, "
            "standing with one hand on hip, V sign next to face, "
            "bright excited expression, full body, white background, "
            f"{NO_TEXT}, {CHAR_STYLE_A}"
        ),
        "denoise": 0.80,
        "note": "S-04 수빈 등장 (1막 코믹, 스타일A)"
    },
    "A_subin_cafe": {
        "style": "A", "char": "subin",
        "prompt": (
            "Same character in same art style, same cute face and hair and pink outfit, "
            "single character, "
            "sitting with shopping bags, bright cheerful, gesturing, "
            "upper body, white background, "
            f"{NO_TEXT}, {CHAR_STYLE_A}"
        ),
        "denoise": 0.80,
        "note": "S-15 카페 전환 (스타일A)"
    },

    # ── 민준 스타일 A (코믹/에필로그) ──
    "A_minjun_sofa": {
        "style": "A", "char": "minjun",
        "prompt": (
            "Same character in same art style, same cute face and hair and gray hoodie, "
            "single character, "
            "lying casually relaxed, phone in one hand, lazy posture, "
            "full body, white background, "
            f"{NO_TEXT}, {CHAR_STYLE_A}"
        ),
        "denoise": 0.82,
        "note": "S-03 소파 민준 (1막 평화, 스타일A)"
    },

    # ── 콩이 스타일 A ──
    "A_kongi_sitting": {
        "style": "A", "char": "kongi",
        "prompt": (
            "Same character in same art style, same cute face and yellow onesie, "
            "single character, "
            "sitting on floor, big blank round eyes, drooling, "
            "innocent expression, full body sitting, white background, "
            f"{NO_TEXT}, {CHAR_STYLE_A}"
        ),
        "denoise": 0.78,
        "note": "S-07 아기 (스타일A — but used in B scene, decide later)"
    },

    # ── 자판기 메타포 (스타일A — 코믹씬) ──
    "A_minjun_vending": {
        "style": "A", "char": "minjun",
        "prompt": (
            "Same character in same art style, "
            "single character, "
            "character transformed into cute vending machine shape, "
            "face visible through glass, empty hollow expression, "
            "a cheerful hand pressing button with heart symbol, "
            "comic funny style, white background, "
            f"{NO_TEXT}, {CHAR_STYLE_A}"
        ),
        "denoise": 0.88,
        "note": "S-12 자판기 메타포 (코믹, 스타일A)"
    },

    # ── 수빈 스타일 B (시네마틱) ──
    "B_subin_lean": {
        "style": "B", "char": "subin",
        "prompt": (
            f"Single character: {CHAR_SUBIN_B}, "
            "leaning forward with playful but intimidating expression, "
            "tilting head with demanding look, hands on hips, upper body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-06 수빈 압박"
    },
    "B_subin_baby_crouch": {
        "style": "B", "char": "subin",
        "prompt": (
            f"Single character: {CHAR_SUBIN_B}, "
            "crouching down, both hands cupping her face, "
            "presenting face forward with expectant smile, full body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-07 아기에게 말하기"
    },
    "B_subin_night": {
        "style": "B", "char": "subin",
        "prompt": (
            "Single character: young Korean woman in her early 20s with long straight black hair, "
            "bare face without makeup, wearing simple white t-shirt, no cardigan, "
            "lying down face up, vulnerable fragile expression, "
            "eyes slightly moist, contemplative and lonely, full body lying, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-21 밤 수빈 반전"
    },
    "B_subin_standing": {
        "style": "B", "char": "subin",
        "prompt": (
            f"Single character: {CHAR_SUBIN_B}, "
            "standing straight facing viewer, slightly lonely wistful expression, "
            "arms relaxed at sides, full body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-23 나란히 서기"
    },

    # ── 민준 스타일 B (시네마틱) ──
    "B_minjun_reaction": {
        "style": "B", "char": "minjun",
        "prompt": (
            f"Single character close-up: {CHAR_MINJUN_B}, "
            "subtle conflicted expression, eyes glancing sideways, "
            "slight grimace, face and shoulders only, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-05 리액션 클로즈업"
    },
    "B_minjun_shrink": {
        "style": "B", "char": "minjun",
        "prompt": (
            f"Single character: {CHAR_MINJUN_B}, "
            "sitting leaning back uncomfortably, shrinking away, "
            "defensive body language, upper body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-06 움츠리기"
    },
    "B_minjun_observe": {
        "style": "B", "char": "minjun",
        "prompt": (
            f"Single character: {CHAR_MINJUN_B}, "
            "sitting with phone lowered, watching distance, "
            "analyzing gaze, eyes slightly narrowed, upper body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-08/09 관찰"
    },
    "B_minjun_fatigue": {
        "style": "B", "char": "minjun",
        "prompt": (
            f"Single character close-up: {CHAR_MINJUN_B}, "
            "fatigue and irritation in eyes, tired expression, "
            "face and shoulders only, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-10 내면 피로"
    },
    "B_minjun_cornered": {
        "style": "B", "char": "minjun",
        "prompt": (
            f"Single character: {CHAR_MINJUN_B}, "
            "back against wall, looking slightly upward, "
            "quietly cornered expression, hands at sides, full body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-11/22 코너에 몰림"
    },
    "B_minjun_angel": {
        "style": "B", "char": "minjun",
        "prompt": (
            f"Single character: {CHAR_MINJUN_B}, "
            "tiny angel on left shoulder, tiny dark figure on right shoulder, "
            "exhausted expression caught between, upper body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-13 천사/악마"
    },
    "B_minjun_boundary": {
        "style": "B", "char": "minjun",
        "prompt": (
            f"Single character: {CHAR_MINJUN_B}, "
            "standing behind translucent glowing warm barrier, "
            "calm determined expression, peaceful, full body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-14 경계선"
    },
    "B_minjun_standing": {
        "style": "B", "char": "minjun",
        "prompt": (
            f"Single character: {CHAR_MINJUN_B}, "
            "standing straight facing viewer, firm understanding expression, "
            "arms relaxed at sides, full body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-23 나란히 서기"
    },

    # ── 지우 스타일 B (시네마틱) ──
    "B_jiwoo_cafe": {
        "style": "B", "char": "jiwoo",
        "prompt": (
            f"Single character: {CHAR_JIWOO_B}, "
            "sitting, holding coffee cup with both hands close to chest, "
            "defensive posture, hunched, tired expression, upper body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-15 카페 방어"
    },
    "B_jiwoo_scale": {
        "style": "B", "char": "jiwoo",
        "prompt": (
            f"Single character: {CHAR_JIWOO_B}, "
            "both hands raised palms up as if weighing objects, "
            "contemplative expression, upper body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-16 저울"
    },
    "B_jiwoo_smile": {
        "style": "B", "char": "jiwoo",
        "prompt": (
            f"Single character close-up: {CHAR_JIWOO_B}, "
            "mouth smiling but eyes completely dead and hollow, "
            "strong contrast between smile and empty eyes, "
            "face and shoulders only, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-17 강제 미소"
    },
    "B_jiwoo_window": {
        "style": "B", "char": "jiwoo",
        "prompt": (
            f"Single character: {CHAR_JIWOO_B}, "
            "sitting sipping coffee, gazing to the side, "
            "melancholic profile, upper body seated, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-18 창밖"
    },
    "B_jiwoo_door": {
        "style": "B", "char": "jiwoo",
        "prompt": (
            f"Single character: {CHAR_JIWOO_B}, "
            "standing with back against surface, head tilted back, "
            "arms hanging loosely, exhausted empty eyes staring up, "
            "full body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-20 현관문"
    },
    "B_jiwoo_standing": {
        "style": "B", "char": "jiwoo",
        "prompt": (
            f"Single character: {CHAR_JIWOO_B}, "
            "standing straight, tired but resilient expression, "
            "arms relaxed at sides, full body, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
        "note": "S-23 나란히 서기"
    },
}


# ══════════════════════════════════════════════
# 생성 엔진
# ══════════════════════════════════════════════

LOG = "/tmp/fep_v3_characters.log"
STATE_FILE = "/tmp/fep_v3_characters_state.json"


def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"completed": {}, "failed": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def api_get(path, timeout=10):
    try:
        req = urllib.request.Request(f"{COMFYUI_URL}{path}")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read()), None
    except Exception as e:
        return None, str(e)


def api_post(path, data, timeout=10):
    try:
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            f"{COMFYUI_URL}{path}",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read()), None
    except Exception as e:
        return None, str(e)


def is_job_in_queue(prompt_id):
    data, err = api_get("/queue")
    if err:
        return None
    for item in data.get("queue_running", []):
        if item[1] == prompt_id:
            return "running"
    for item in data.get("queue_pending", []):
        if item[1] == prompt_id:
            return "pending"
    return False


def smart_wait(prompt_id, char_id):
    start = time.time()
    network_errors = 0
    while True:
        elapsed = time.time() - start
        history, err = api_get(f"/history/{prompt_id}")
        if err:
            network_errors += 1
            if network_errors <= 60:
                if network_errors % 10 == 0:
                    log(f"  ⚠️ 네트워크 에러 {network_errors}회 ({char_id})")
                time.sleep(60)
                continue
            else:
                return None, "network_timeout"
        network_errors = 0
        if prompt_id in history:
            return history[prompt_id], "completed"
        queue_status = is_job_in_queue(prompt_id)
        if queue_status is None:
            time.sleep(5)
            continue
        elif queue_status == "running":
            if int(elapsed) % 120 < 6 and elapsed > 10:
                log(f"  ⏳ {char_id} 생성중... ({elapsed:.0f}s)")
            time.sleep(5)
            continue
        elif queue_status == "pending":
            if int(elapsed) % 300 < 11 and elapsed > 10:
                log(f"  ⏳ {char_id} 대기중... ({elapsed:.0f}s)")
            time.sleep(10)
            continue
        else:
            if elapsed < 10:
                time.sleep(2)
                continue
            log(f"  🔴 {char_id} 큐에서 유실됨")
            return None, "lost"


def build_style_B_workflow(prompt_text, filename_prefix, width=1344, height=768,
                           steps=20, cfg=3.5, seed=None):
    """스타일 B: txt2img 그린 스크린"""
    if seed is None:
        seed = int.from_bytes(os.urandom(4), 'big')
    workflow = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux1-kontext-dev-Q8_0.gguf"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp8_e4m3fn_scaled.safetensors", "type": "flux"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncodeFlux", "inputs": {"clip": ["2", 0], "clip_l": prompt_text, "t5xxl": prompt_text, "guidance": cfg}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "ModelSamplingFlux", "inputs": {"model": ["1", 0], "max_shift": 1.15, "base_shift": 0.5, "width": width, "height": height}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["6", 0], "positive": ["4", 0], "negative": ["9", 0], "latent_image": ["5", 0], "seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "CLIPTextEncodeFlux", "inputs": {"clip": ["2", 0], "clip_l": NEGATIVE_PROMPT_B, "t5xxl": NEGATIVE_PROMPT_B, "guidance": cfg}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": filename_prefix}}
    }
    return workflow, seed


def build_style_A_workflow(prompt_text, ref_image, filename_prefix,
                           width=1344, height=768, steps=24, cfg=3.5,
                           denoise=0.80, seed=None):
    """스타일 A: img2img 캐릭터 시트 참조 + 흰 배경"""
    if seed is None:
        seed = int.from_bytes(os.urandom(4), 'big')
    workflow = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux1-kontext-dev-Q8_0.gguf"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp8_e4m3fn_scaled.safetensors", "type": "flux"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "11": {"class_type": "LoadImage", "inputs": {"image": ref_image}},
        "12": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["11", 0]}},
        "13": {"class_type": "VAEEncode", "inputs": {"pixels": ["12", 0], "vae": ["3", 0]}},
        "4": {"class_type": "CLIPTextEncodeFlux", "inputs": {"clip": ["2", 0], "clip_l": prompt_text, "t5xxl": prompt_text, "guidance": cfg}},
        "6": {"class_type": "ModelSamplingFlux", "inputs": {"model": ["1", 0], "max_shift": 1.15, "base_shift": 0.5, "width": width, "height": height}},
        "9": {"class_type": "CLIPTextEncodeFlux", "inputs": {"clip": ["2", 0], "clip_l": NEGATIVE_PROMPT_A, "t5xxl": NEGATIVE_PROMPT_A, "guidance": cfg}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["6", 0], "positive": ["4", 0], "negative": ["9", 0],
            "latent_image": ["13", 0],
            "seed": seed, "steps": steps, "cfg": 1.0,
            "sampler_name": "euler", "scheduler": "simple", "denoise": denoise
        }},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": filename_prefix}}
    }
    return workflow, seed


def collect_to_v3(char_id, comfyui_filename):
    src = COMFYUI_OUTPUT / comfyui_filename
    if not src.exists():
        log(f"  ⚠️ 파일 없음: {src}")
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst_name = f"{ts}_char_{char_id}.png"
    dst = V3_DIR / "characters" / dst_name
    import shutil
    shutil.copy2(str(src), str(dst))
    log(f"  📁 수집: {dst_name}")
    return dst_name


def generate_with_retry(char_id, state, max_retries=3):
    char = CHARACTERS[char_id]
    style = char["style"]
    char_name = char["char"]

    for attempt in range(max_retries):
        ts_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")

        if style == "A":
            ref_image = STYLE_A_REF.get(char_name)
            denoise = char.get("denoise", 0.80)
            workflow, seed = build_style_A_workflow(
                char["prompt"],
                ref_image=ref_image,
                filename_prefix=f"v3_{ts_prefix}_{char_id}",
                denoise=denoise
            )
            log(f"  🎨 스타일A img2img: {ref_image} (denoise={denoise})")
        else:  # style == "B"
            workflow, seed = build_style_B_workflow(
                char["prompt"],
                filename_prefix=f"v3_{ts_prefix}_{char_id}"
            )
            log(f"  🎬 스타일B txt2img (그린스크린)")

        result, err = api_post("/prompt", {"prompt": workflow})
        if err:
            log(f"  큐잉 실패 ({attempt+1}/{max_retries}): {err}")
            time.sleep(30)
            continue

        pid = result["prompt_id"]
        log(f"큐잉: {char_id} (seed: {seed}, attempt: {attempt+1})")
        t = time.time()
        history, status = smart_wait(pid, char_id)
        elapsed = time.time() - t

        if status == "completed" and history:
            job_status = history.get("status", {}).get("status_str", "unknown")
            if job_status == "success":
                for nid, out in history.get("outputs", {}).items():
                    if "images" in out:
                        for img in out["images"]:
                            log(f"✅ {char_id}: {img['filename']} ({elapsed:.0f}s)")
                            collected = collect_to_v3(char_id, img['filename'])
                            return True, elapsed, collected
            else:
                err_msg = ""
                for msg in history.get("status", {}).get("messages", []):
                    if msg[0] == "execution_error":
                        err_msg = msg[1].get("exception_message", "")[:150]
                log(f"❌ {char_id}: ComfyUI 에러 — {err_msg}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue
        elif status == "lost":
            if attempt < max_retries - 1:
                time.sleep(5)
            continue
        elif status == "network_timeout":
            return False, elapsed, None

    log(f"❌ {char_id}: {max_retries}회 시도 실패")
    return False, 0, None


def main():
    total = len(CHARACTERS)
    style_a_count = sum(1 for c in CHARACTERS.values() if c["style"] == "A")
    style_b_count = sum(1 for c in CHARACTERS.values() if c["style"] == "B")

    with open(LOG, "w") as f:
        f.write(f"=== v3 Phase 2: 듀얼 스타일 캐릭터 {total}장 (A:{style_a_count} + B:{style_b_count}) ===\n")

    log(f"시작 — 캐릭터 {total}장 (스타일A:{style_a_count}, 스타일B:{style_b_count})")
    state = load_state()

    data, err = api_get("/queue")
    if err:
        log(f"🔴 ComfyUI 접속 불가: {err}")
        sys.exit(1)

    running = data.get("queue_running", [])
    pending = data.get("queue_pending", [])
    if running or pending:
        log(f"⚠️ 기존 큐: {len(running)} running, {len(pending)} pending — 완료 대기")
        while True:
            data, err = api_get("/queue")
            if err:
                time.sleep(10)
                continue
            if not data.get("queue_running", []) and not data.get("queue_pending", []):
                break
            time.sleep(5)

    completed = 0
    failed = 0
    skipped = 0
    total_time = 0

    for char_id in CHARACTERS:
        if char_id in state["completed"]:
            log(f"⏭️ {char_id}: 이전 완료 — 스킵")
            skipped += 1
            continue

        success, elapsed, filename = generate_with_retry(char_id, state)
        if success:
            state["completed"][char_id] = {
                "time": time.strftime('%H:%M:%S'),
                "elapsed": f"{elapsed:.0f}s",
                "filename": filename,
                "style": CHARACTERS[char_id]["style"]
            }
            completed += 1
            total_time += elapsed
        else:
            state["failed"][char_id] = time.strftime('%H:%M:%S')
            failed += 1

        save_state(state)

    log(f"\n=== 완료: {completed}성공 / {failed}실패 / {skipped}스킵 ===")
    if completed > 0:
        avg = total_time / completed
        log(f"평균 생성 시간: {avg:.0f}s/장")
    log(f"종료: {time.strftime('%H:%M:%S')}")


if __name__ == "__main__":
    if "--reset" in sys.argv:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print("State reset.")
    if "--list" in sys.argv:
        for cid, ch in CHARACTERS.items():
            print(f"  [{ch['style']}] {cid}: {ch['note']}")
    elif "--style" in sys.argv:
        # 특정 스타일만 실행
        idx = sys.argv.index("--style")
        target_style = sys.argv[idx + 1].upper()
        # 임시로 CHARACTERS 필터링
        filtered = {k: v for k, v in CHARACTERS.items() if v["style"] == target_style}
        orig = dict(CHARACTERS)
        CHARACTERS.clear()
        CHARACTERS.update(filtered)
        main()
        CHARACTERS.clear()
        CHARACTERS.update(orig)
    else:
        main()
