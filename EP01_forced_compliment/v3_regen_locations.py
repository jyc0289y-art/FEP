#!/usr/bin/env python3
"""
v3 로케이션 색감 재생성 — 누리끼리한 석양톤 → 산뜻한 자연광
대상: livingroom_afternoon, bathroom_morning, cafe_sunny, cafe_rainy, minimal_chairs
"""
import sys, time, json, urllib.request, urllib.error, os, shutil
from pathlib import Path
from datetime import datetime

COMFYUI_URL = "http://localhost:8188"
COMFYUI_OUTPUT = Path.home() / "developer" / "ComfyUI" / "output"
V3_DIR = Path(__file__).parent / "v3_layers"
LOC_DIR = V3_DIR / "locations"
LOC_REJECTED = V3_DIR / "locations_rejected"

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

# ✅ 핵심 변경: "warm pastel" → "bright neutral fresh"
BG_STYLE = (
    "clean cartoon illustration style, Korean webtoon style, "
    "bright clean colors with neutral white lighting, "
    "thick clean outlines, 16:9 aspect ratio, "
    "detailed background environment, "
    "no people, completely empty room, no characters, no figures"
)

# ✅ 네거티브에 앰버/석양 톤 명시 차단
NEGATIVE_PROMPT = (
    "text, letters, words, writing, numbers, watermark, logo, signature, "
    "person, people, human, character, figure, face, body, hand, arm, "
    "orange tint, amber tone, golden hour, sunset lighting, sepia filter, "
    "warm orange glow, yellowish, heavy warm filter, brown tint, "
    "oversaturated warm colors"
)

# === 재생성 대상 5개 로케이션 (프롬프트 전면 교체) ===
REGEN_LOCATIONS = {
    "LOC_livingroom_afternoon": {
        "prompt": (
            "Empty cozy living room interior, no people, "
            "comfortable beige sofa with pastel colored cushions in center, "
            "small coffee table with a cup, "
            "bright natural daylight from large window with white sheer curtains, "
            "white walls, light wooden floor, "
            "small green houseplants adding fresh accents, "
            "clean airy atmosphere like a fresh spring afternoon, "
            "neutral white balanced lighting, NOT sunset NOT golden hour, "
            "modern Korean apartment living room, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "거실 — 밝고 산뜻한 자연광 (앰버 제거)"
    },
    "LOC_bathroom_morning": {
        "prompt": (
            "Empty bathroom interior, no people, "
            "large clean mirror on white tiled wall, "
            "white ceramic sink with small skincare bottles, "
            "bright cool morning daylight from frosted window, "
            "white tiles, clean and fresh atmosphere, "
            "mint green or light blue small accent towel, "
            "crisp clean morning feeling, neutral white lighting, "
            "modern Korean apartment bathroom, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "욕실 — 상쾌한 아침 (골든아워 제거)"
    },
    "LOC_cafe_sunny": {
        "prompt": (
            "Empty bright cafe interior window seat, no people, "
            "round wooden table with two chairs near large clean window, "
            "two coffee cups on table, "
            "bright natural daylight streaming through clean glass window, "
            "green trees visible outside, "
            "white walls with exposed light wood accents, "
            "small potted succulent on table, "
            "fresh airy modern Korean cafe, clean and bright atmosphere, "
            "neutral daylight color temperature, NOT golden hour, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "카페 맑음 — 밝고 깨끗한 카페 (앰버 제거)"
    },
    "LOC_cafe_rainy": {
        "prompt": (
            "Empty cafe interior window seat, no people, "
            "round wooden table near large window, "
            "heavy rain falling outside, raindrops streaming down glass, "
            "gray overcast sky visible through wet window, "
            "cool blue-gray atmosphere outside contrasts with soft indoor lighting, "
            "muted cool tones, contemplative mood, "
            "modern Korean cafe, subtle warm lamp inside but cool overall palette, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "카페 비 — 쿨그레이+블루, 비오는 감성"
    },
    "LOC_minimal_chairs": {
        "prompt": (
            "Minimalist bright room with exactly four chairs arranged in a loose circle, "
            "no people, viewed from slightly above, "
            "chair one has a bright pink scarf draped on it, "
            "chair two has a smartphone placed on the seat, "
            "chair three has a coffee cup on it, "
            "chair four is completely empty with soft spotlight, "
            "very clean white floor and pale gray walls, "
            "soft diffused overhead lighting, minimal and contemplative, "
            "bright clean atmosphere, NOT warm NOT amber, "
            f"{NO_TEXT}, {BG_STYLE}"
        ),
        "note": "빈 의자 — 화이트/라이트그레이 미니멀"
    }
}

LOG = "/tmp/fep_v3_regen_locations.log"


def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


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
            f"{COMFYUI_URL}{path}", data=payload,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read()), None
    except Exception as e:
        return None, str(e)


def smart_wait(prompt_id, loc_id):
    start = time.time()
    network_errors = 0
    while True:
        elapsed = time.time() - start
        history, err = api_get(f"/history/{prompt_id}")
        if err:
            network_errors += 1
            if network_errors <= 60:
                time.sleep(60)
                continue
            return None, "network_timeout"
        network_errors = 0
        if prompt_id in history:
            return history[prompt_id], "completed"
        # 큐 확인
        data, _ = api_get("/queue")
        if data:
            running = [i for i in data.get("queue_running", []) if i[1] == prompt_id]
            pending = [i for i in data.get("queue_pending", []) if i[1] == prompt_id]
            if running:
                if int(elapsed) % 60 < 6 and elapsed > 10:
                    log(f"  ⏳ {loc_id} 생성중... ({elapsed:.0f}s)")
            elif pending:
                pass
            elif elapsed > 10:
                return None, "lost"
        time.sleep(5)


def build_workflow(prompt_text, filename_prefix, width=1344, height=768, steps=20, cfg=3.5):
    seed = int.from_bytes(os.urandom(4), 'big')
    workflow = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux1-kontext-dev-Q8_0.gguf"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {
            "clip_name1": "clip_l.safetensors",
            "clip_name2": "t5xxl_fp8_e4m3fn_scaled.safetensors", "type": "flux"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncodeFlux", "inputs": {
            "clip": ["2", 0], "clip_l": prompt_text, "t5xxl": prompt_text, "guidance": cfg}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "ModelSamplingFlux", "inputs": {
            "model": ["1", 0], "max_shift": 1.15, "base_shift": 0.5, "width": width, "height": height}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["6", 0], "positive": ["4", 0], "negative": ["9", 0], "latent_image": ["5", 0],
            "seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "CLIPTextEncodeFlux", "inputs": {
            "clip": ["2", 0], "clip_l": NEGATIVE_PROMPT, "t5xxl": NEGATIVE_PROMPT, "guidance": cfg}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": filename_prefix}}
    }
    return workflow, seed


def main():
    with open(LOG, "w") as f:
        f.write(f"=== 로케이션 색감 재생성 — {len(REGEN_LOCATIONS)}장 ===\n")

    log(f"시작 — {len(REGEN_LOCATIONS)}장 재생성")

    # ComfyUI 접속 대기
    for i in range(30):
        data, err = api_get("/queue")
        if not err:
            log("ComfyUI 접속 확인")
            break
        time.sleep(5)
    else:
        log("🔴 ComfyUI 접속 불가")
        sys.exit(1)

    # 기존 파일을 rejected로 이동
    LOC_REJECTED.mkdir(parents=True, exist_ok=True)
    for loc_id in REGEN_LOCATIONS:
        old_files = list(LOC_DIR.glob(f"*{loc_id}*"))
        for f in old_files:
            dst = LOC_REJECTED / f.name
            shutil.move(str(f), str(dst))
            log(f"📦 기존 → rejected: {f.name}")

    completed = 0
    for loc_id, loc in REGEN_LOCATIONS.items():
        ts_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        workflow, seed = build_workflow(loc["prompt"], f"v3_{ts_prefix}_{loc_id}")
        result, err = api_post("/prompt", {"prompt": workflow})
        if err:
            log(f"❌ {loc_id} 큐잉 실패: {err}")
            continue

        pid = result["prompt_id"]
        log(f"큐잉: {loc_id} (seed: {seed})")

        t = time.time()
        history, status = smart_wait(pid, loc_id)
        elapsed = time.time() - t

        if status == "completed" and history:
            job_status = history.get("status", {}).get("status_str", "unknown")
            if job_status == "success":
                for nid, out in history.get("outputs", {}).items():
                    if "images" in out:
                        for img in out["images"]:
                            src = COMFYUI_OUTPUT / img['filename']
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            dst = LOC_DIR / f"{ts}_loc_{loc_id}.png"
                            shutil.copy2(str(src), str(dst))
                            log(f"✅ {loc_id}: {dst.name} ({elapsed:.0f}s) — {loc['note']}")
                            completed += 1
            else:
                log(f"❌ {loc_id}: 생성 실패")
        else:
            log(f"❌ {loc_id}: {status}")

    log(f"\n=== 완료: {completed}/{len(REGEN_LOCATIONS)} ===")


if __name__ == "__main__":
    main()
