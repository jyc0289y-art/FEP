#!/usr/bin/env python3
"""
v3 Phase 1: 로케이션 마스터 생성
빈 배경(인물 없음)을 생성하여 v3_layers/locations/ 에 저장
타임스탬프 파일명으로 오염 방지
"""
import sys, time, json, urllib.request, urllib.error, os
from pathlib import Path
from datetime import datetime

COMFYUI_URL = "http://localhost:8188"
COMFYUI_OUTPUT = Path.home() / "developer" / "ComfyUI" / "output"
V3_DIR = Path(__file__).parent / "v3_layers"

# 텍스트/워터마크 방지
NO_TEXT = (
    "IMPORTANT: absolutely zero text anywhere in the image, "
    "no text, no letters, no words, no writing, no numbers, no symbols with meaning, "
    "no watermark, no logo, no signature, no stamp, no seal, "
    "no speech bubbles, no thought bubbles, no captions, no labels, no UI elements, "
    "no Korean characters, no Japanese characters, no Chinese characters, "
    "no hangul, no kanji, no hiragana, no katakana, no alphabet letters, "
    "purely visual illustration with zero typography, "
    "original artwork, no artist signature, no website url, no brand marks"
)

NEGATIVE_PROMPT = (
    "text, letters, words, writing, numbers, watermark, logo, signature, stamp, seal, "
    "speech bubble, caption, label, UI, Korean text, Japanese text, Chinese text, "
    "hangul, kanji, hiragana, katakana, alphabet, typography, brand, url, "
    "person, people, human, character, figure, face, body, hand, arm"
)

BG_STYLE = (
    "clean cartoon illustration style, Korean webtoon style, "
    "warm pastel colors, thick clean outlines, "
    "16:9 aspect ratio, detailed background environment, "
    "no people, completely empty room, no characters, no figures"
)

# === 로케이션 프롬프트 ===
LOCATIONS = {
    "LOC_bathroom_morning": {
        "prompt": (
            "Empty bathroom interior, no people, "
            "large mirror on wall reflecting empty room, clean white tiles, "
            "warm golden morning sunlight streaming in from the left side, "
            "toothbrush holder and small cosmetics on shelf, "
            "cozy Korean apartment bathroom, bright and clean atmosphere, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "S-01 수빈 거울 씬 배경"
    },
    "LOC_livingroom_afternoon": {
        "prompt": (
            "Empty cozy living room interior, no people, "
            "comfortable sofa with cushions in center, "
            "coffee table with a steaming coffee cup, "
            "warm golden afternoon sunlight streaming through sheer curtains, "
            "bookshelf and small houseplants, wooden floor, "
            "peaceful sunday afternoon atmosphere, Korean apartment living room, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "S-03/04/06/07/08/11 거실 씬 메인 배경"
    },
    "LOC_livingroom_cold": {
        "prompt": (
            "Empty living room interior, no people, "
            "same layout as cozy living room but completely desaturated cold blue-gray color palette, "
            "sofa with cushions, coffee table, curtains, "
            "all warmth drained from the scene, feels like a faded memory, "
            "muted cool tones, psychological interior perspective, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "S-09 되감기 씬 배경 (차가운 변형)"
    },
    "LOC_cafe_sunny": {
        "prompt": (
            "Empty cafe interior window seat, no people, "
            "wooden table with two chairs facing each other near large window, "
            "warm afternoon sunlight streaming through cafe window, "
            "coffee cups on table, cozy cafe atmosphere, "
            "small potted plant on windowsill, brick wall accent, "
            "warm inviting Korean cafe interior, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "S-15/17/19 카페 씬 메인 배경"
    },
    "LOC_cafe_rainy": {
        "prompt": (
            "Empty cafe interior window seat, no people, "
            "wooden table near large window, "
            "rain falling outside the window, raindrops streaming down the glass, "
            "gray overcast sky visible through wet window, "
            "warm interior contrasts with gray rainy outside, "
            "melancholic contemplative atmosphere, Korean cafe, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "S-18 비오는 카페 씬 배경"
    },
    "LOC_hallway_dim": {
        "prompt": (
            "Empty narrow apartment hallway entrance, no people, "
            "closed front door, shoes on floor near entrance, "
            "only a single dim warm wall lamp providing faint light, "
            "muted blue-gray color palette, quiet lonely atmosphere, "
            "Korean apartment entryway, narrow and cramped, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "S-20 지우 귀가 씬 배경"
    },
    "LOC_bedroom_night": {
        "prompt": (
            "Empty bedroom at night, no people, "
            "bed with rumpled sheets, soft blue phone screen glow on pillow area, "
            "bedside chair with a bright pink cardigan tossed carelessly on it, "
            "room lit only by faint blue phone glow, very dim, "
            "muted indigo-gray tones, intimate lonely atmosphere, "
            "Korean apartment bedroom at night, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "S-21 수빈 밤 씬 배경"
    },
    "LOC_minimal_chairs": {
        "prompt": (
            "Minimalist room with exactly four chairs arranged in a circle, no people, "
            "viewed from above at slight angle, "
            "chair one has a bright pink scarf draped on it, "
            "chair two has a smartphone placed on the seat, "
            "chair three has a coffee cup on it, "
            "chair four is completely empty with warm golden spotlight falling on it, "
            "four chairs total one two three four, clean minimal room, "
            "contemplative still life, warm gentle atmosphere, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "S-24 빈 의자 씬 (인물 없는 완성 씬)"
    }
}

LOG = "/tmp/fep_v3_locations.log"
STATE_FILE = "/tmp/fep_v3_locations_state.json"


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


def smart_wait(prompt_id, loc_id):
    start = time.time()
    network_errors = 0
    while True:
        elapsed = time.time() - start
        history, err = api_get(f"/history/{prompt_id}")
        if err:
            network_errors += 1
            if network_errors <= 60:
                if network_errors % 10 == 0:
                    log(f"  ⚠️ 네트워크 에러 {network_errors}회 ({loc_id})")
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
                log(f"  ⏳ {loc_id} 생성중... ({elapsed:.0f}s)")
            time.sleep(5)
            continue
        elif queue_status == "pending":
            if int(elapsed) % 300 < 11 and elapsed > 10:
                log(f"  ⏳ {loc_id} 대기중... ({elapsed:.0f}s)")
            time.sleep(10)
            continue
        else:
            if elapsed < 10:
                time.sleep(2)
                continue
            log(f"  🔴 {loc_id} 큐에서 유실됨")
            return None, "lost"


def build_flux_txt2img(prompt_text, filename_prefix, width=1344, height=768, steps=20, cfg=3.5, seed=None):
    if seed is None:
        seed = int.from_bytes(os.urandom(4), 'big')
    workflow = {
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": "flux1-kontext-dev-Q8_0.gguf"}
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5xxl_fp8_e4m3fn_scaled.safetensors",
                "type": "flux"
            }
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"}
        },
        "4": {
            "class_type": "CLIPTextEncodeFlux",
            "inputs": {
                "clip": ["2", 0],
                "clip_l": prompt_text,
                "t5xxl": prompt_text,
                "guidance": cfg
            }
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        },
        "6": {
            "class_type": "ModelSamplingFlux",
            "inputs": {
                "model": ["1", 0],
                "max_shift": 1.15, "base_shift": 0.5,
                "width": width, "height": height
            }
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["6", 0],
                "positive": ["4", 0],
                "negative": ["9", 0],
                "latent_image": ["5", 0],
                "seed": seed, "steps": steps, "cfg": 1.0,
                "sampler_name": "euler", "scheduler": "simple",
                "denoise": 1.0
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["3", 0]}
        },
        "9": {
            "class_type": "CLIPTextEncodeFlux",
            "inputs": {
                "clip": ["2", 0],
                "clip_l": NEGATIVE_PROMPT,
                "t5xxl": NEGATIVE_PROMPT,
                "guidance": cfg
            }
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": filename_prefix}
        }
    }
    return workflow, seed


def collect_to_v3(loc_id, comfyui_filename):
    """ComfyUI output에서 v3_layers/locations/로 타임스탬프 파일명으로 복사"""
    src = COMFYUI_OUTPUT / comfyui_filename
    if not src.exists():
        log(f"  ⚠️ 파일 없음: {src}")
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst_name = f"{ts}_loc_{loc_id}.png"
    dst = V3_DIR / "locations" / dst_name

    import shutil
    shutil.copy2(str(src), str(dst))
    log(f"  📁 수집: {dst_name}")
    return dst_name


def generate_with_retry(loc_id, state, max_retries=3):
    loc = LOCATIONS[loc_id]
    for attempt in range(max_retries):
        ts_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        workflow, seed = build_flux_txt2img(
            loc["prompt"],
            filename_prefix=f"v3_{ts_prefix}_{loc_id}"
        )
        result, err = api_post("/prompt", {"prompt": workflow})
        if err:
            log(f"  큐잉 실패 ({attempt+1}/{max_retries}): {err}")
            time.sleep(30)
            continue

        pid = result["prompt_id"]
        log(f"큐잉: {loc_id} (seed: {seed}, attempt: {attempt+1})")

        t = time.time()
        history, status = smart_wait(pid, loc_id)
        elapsed = time.time() - t

        if status == "completed" and history:
            job_status = history.get("status", {}).get("status_str", "unknown")
            if job_status == "success":
                for nid, out in history.get("outputs", {}).items():
                    if "images" in out:
                        for img in out["images"]:
                            log(f"✅ {loc_id}: {img['filename']} ({elapsed:.0f}s)")
                            collected = collect_to_v3(loc_id, img['filename'])
                            return True, elapsed, collected
            else:
                err_msg = ""
                for msg in history.get("status", {}).get("messages", []):
                    if msg[0] == "execution_error":
                        err_msg = msg[1].get("exception_message", "")[:150]
                log(f"❌ {loc_id}: ComfyUI 에러 — {err_msg}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue
        elif status == "lost":
            if attempt < max_retries - 1:
                time.sleep(5)
            continue
        elif status == "network_timeout":
            return False, elapsed, None

    log(f"❌ {loc_id}: {max_retries}회 시도 실패")
    return False, 0, None


def main():
    with open(LOG, "w") as f:
        f.write(f"=== v3 Phase 1: 로케이션 마스터 {len(LOCATIONS)}장 ===\n")

    log(f"시작 — 로케이션 {len(LOCATIONS)}장")
    state = load_state()

    # ComfyUI 접속 확인
    data, err = api_get("/queue")
    if err:
        log(f"🔴 ComfyUI 접속 불가: {err}")
        log("ComfyUI를 먼저 실행하세요: cd ~/developer/ComfyUI && python main.py --listen 0.0.0.0 --port 8188")
        sys.exit(1)

    # 기존 큐 대기
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

    for loc_id in LOCATIONS:
        if loc_id in state["completed"]:
            log(f"⏭️ {loc_id}: 이전 완료 — 스킵")
            skipped += 1
            continue

        success, elapsed, filename = generate_with_retry(loc_id, state)
        if success:
            state["completed"][loc_id] = {
                "time": time.strftime('%H:%M:%S'),
                "elapsed": f"{elapsed:.0f}s",
                "filename": filename
            }
            completed += 1
            total_time += elapsed
        else:
            state["failed"][loc_id] = time.strftime('%H:%M:%S')
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
        for lid, loc in LOCATIONS.items():
            print(f"  {lid}: {loc['note']}")
    else:
        main()
