#!/usr/bin/env python3
"""
v3 재생성: 품질 불량 캐릭터 4장 + 로케이션 1장
문제 목록:
  - A_kongi_sitting: 캐릭터 너무 작음 → denoise 0.88 + 프롬프트 강화
  - B_subin_night: 초록 스필 심함 → 프롬프트에 피부색 강조
  - B_minjun_boundary: 스타일 불일치 → 글로우 제거 + 시네마틱 강조
  - B_jiwoo_door: 너무 작음 → 프레임 비율 명시
  - LOC_bedroom_night: 보라색 인물 존재 → no people 강화
"""
import sys, time, json, urllib.request, os, shutil
from pathlib import Path
from datetime import datetime

COMFYUI_URL = "http://localhost:8188"
COMFYUI_OUTPUT = Path.home() / "developer" / "ComfyUI" / "output"
V3_DIR = Path(__file__).parent / "v3_layers"

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

# ── 캐릭터 프롬프트 상수 ──
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

# ══════════════════════════════════════════════
# 재생성 대상 (수정된 프롬프트)
# ══════════════════════════════════════════════
REGEN_ITEMS = {
    # ── 캐릭터 ──
    "A_kongi_sitting": {
        "type": "char", "style": "A", "char": "kongi",
        "prompt": (
            "Same character in same art style, same cute face and yellow onesie, "
            "single character centered in frame, large character filling most of the image, "
            "baby sitting on floor facing viewer, big blank round eyes, chubby cheeks, "
            "drooling, innocent expression, full body sitting centered, white background, "
            f"{NO_TEXT}, {CHAR_STYLE_A}"
        ),
        "denoise": 0.88,  # 0.78→0.88 올려서 참조 이미지 레이아웃 탈피
        "ref": "char_kongi_front.png",
    },
    "B_subin_night": {
        "type": "char", "style": "B",
        "prompt": (
            "Single character: young Korean woman in her early 20s with long straight black hair, "
            "natural warm skin tone, bare face without makeup, wearing simple white t-shirt, "
            "lying down face up, vulnerable fragile expression, "
            "eyes slightly moist, contemplative and lonely, full body lying, "
            "character has warm peach skin color clearly distinct from background, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
    },
    "B_minjun_boundary": {
        "type": "char", "style": "B",
        "prompt": (
            f"Single character: {CHAR_MINJUN_B}, "
            "standing with arms crossed, calm determined expression, "
            "peaceful confident posture, full body visible, "
            "no special effects, no glow, no aura, no barrier, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
    },
    "B_jiwoo_door": {
        "type": "char", "style": "B",
        "prompt": (
            f"Single character filling 70 percent of frame height: {CHAR_JIWOO_B}, "
            "standing with back against flat surface, head tilted back looking upward, "
            "arms hanging loosely at sides, exhausted empty eyes staring at ceiling, "
            "full body visible from head to feet, character centered in frame, "
            f"{GREEN_BG}, {NO_TEXT}, {CHAR_STYLE_B}"
        ),
    },
    # ── 로케이션 ──
    "LOC_bedroom_night": {
        "type": "location", "style": "loc",
        "prompt": (
            "Dark cozy bedroom at night, single bed with phone glowing on pillow, "
            "dim warm indirect lighting from desk lamp, "
            "empty room with absolutely no people no figures no characters no silhouettes, "
            "no person sitting or standing anywhere, completely empty room, "
            "soft blue-gray atmosphere, minimal furniture, "
            "clean cartoon illustration style, Korean webtoon style, warm muted colors, "
            "16:9 aspect ratio, "
            f"{NO_TEXT}"
        ),
    },
}


# ══════════════════════════════════════════════
# 워크플로우 빌더
# ══════════════════════════════════════════════

def build_txt2img(prompt_text, filename_prefix, width=1344, height=768,
                  steps=20, cfg=3.5, neg=NEGATIVE_PROMPT_B, seed=None):
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
        "9": {"class_type": "CLIPTextEncodeFlux", "inputs": {"clip": ["2", 0], "clip_l": neg, "t5xxl": neg, "guidance": cfg}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": filename_prefix}}
    }
    return workflow, seed


def build_img2img(prompt_text, ref_image, filename_prefix, denoise=0.80,
                  width=1344, height=768, steps=24, cfg=3.5, seed=None):
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


# ══════════════════════════════════════════════
# 실행 로직
# ══════════════════════════════════════════════

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
        req = urllib.request.Request(f"{COMFYUI_URL}{path}", data=payload,
                                    headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read()), None
    except Exception as e:
        return None, str(e)


def wait_for_completion(prompt_id, item_id, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        history, err = api_get(f"/history/{prompt_id}")
        if err:
            time.sleep(5)
            continue
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(5)
    return None


def main():
    print(f"=== v3 재생성: {len(REGEN_ITEMS)}건 ===")

    # ComfyUI 대기
    for i in range(30):
        data, err = api_get("/queue")
        if not err:
            print("✅ ComfyUI 연결됨")
            break
        print(f"⏳ ComfyUI 대기중... ({i+1})")
        time.sleep(5)
    else:
        print("❌ ComfyUI 연결 실패")
        sys.exit(1)

    results = {}
    for item_id, item in REGEN_ITEMS.items():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        if item["style"] == "A":
            workflow, seed = build_img2img(
                item["prompt"], item["ref"],
                filename_prefix=f"v3_regen_{ts}_{item_id}",
                denoise=item.get("denoise", 0.80)
            )
            print(f"\n🎨 [{item_id}] 스타일A img2img (denoise={item.get('denoise', 0.80)})")
        elif item["style"] == "loc":
            neg = (
                "text, letters, words, watermark, signature, "
                "person, people, human, figure, silhouette, character, "
                "man, woman, child, anyone standing sitting"
            )
            workflow, seed = build_txt2img(
                item["prompt"],
                filename_prefix=f"v3_regen_{ts}_{item_id}",
                neg=neg
            )
            print(f"\n🏠 [{item_id}] 로케이션 txt2img")
        else:
            workflow, seed = build_txt2img(
                item["prompt"],
                filename_prefix=f"v3_regen_{ts}_{item_id}"
            )
            print(f"\n🎬 [{item_id}] 스타일B txt2img")

        print(f"   seed: {seed}")

        result, err = api_post("/prompt", {"prompt": workflow})
        if err:
            print(f"   ❌ 큐잉 실패: {err}")
            results[item_id] = "FAILED"
            continue

        pid = result["prompt_id"]
        t = time.time()
        history = wait_for_completion(pid, item_id)
        elapsed = time.time() - t

        if history:
            status = history.get("status", {}).get("status_str", "unknown")
            if status == "success":
                for nid, out in history.get("outputs", {}).items():
                    if "images" in out:
                        for img in out["images"]:
                            src = COMFYUI_OUTPUT / img["filename"]
                            ts2 = datetime.now().strftime("%Y%m%d_%H%M%S")

                            if item["type"] == "location":
                                dst_name = f"{ts2}_loc_{item_id}.png"
                                dst = V3_DIR / "locations" / dst_name
                            else:
                                dst_name = f"{ts2}_char_{item_id}.png"
                                dst = V3_DIR / "characters" / dst_name

                            shutil.copy2(str(src), str(dst))
                            print(f"   ✅ {dst_name} ({elapsed:.0f}s)")
                            results[item_id] = dst_name
            else:
                print(f"   ❌ ComfyUI 에러: {status}")
                results[item_id] = "ERROR"
        else:
            print(f"   ❌ 타임아웃")
            results[item_id] = "TIMEOUT"

    print(f"\n=== 재생성 완료 ===")
    for k, v in results.items():
        icon = "✅" if v not in ("FAILED", "ERROR", "TIMEOUT") else "❌"
        print(f"  {icon} {k}: {v}")


if __name__ == "__main__":
    main()
