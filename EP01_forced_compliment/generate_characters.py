#!/usr/bin/env python3
"""
FEP EP.01 — ComfyUI API를 통한 캐릭터 시트 생성
FLUX Kontext Dev FP8 txt2img
"""

import json
import urllib.request
import urllib.error
import time
import uuid
import os
from pathlib import Path

COMFYUI_URL = "http://localhost:8188"
OUTPUT_DIR = Path(__file__).parent
COMFYUI_OUTPUT = Path.home() / "developer" / "ComfyUI" / "output"

def queue_prompt(workflow):
    """ComfyUI에 워크플로우 큐잉"""
    payload = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def wait_for_completion(prompt_id, timeout=600):
    """프롬프트 완료 대기"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{COMFYUI_URL}/history/{prompt_id}")
            resp = urllib.request.urlopen(req)
            history = json.loads(resp.read())
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        time.sleep(2)
    return None


def build_flux_txt2img(prompt_text, width=1344, height=768, steps=20, cfg=3.5, seed=None):
    """FLUX Kontext Dev txt2img 워크플로우 생성"""
    if seed is None:
        seed = int.from_bytes(os.urandom(4), 'big')

    workflow = {
        # 1. UNET 로더 (GGUF)
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "flux1-kontext-dev-Q8_0.gguf"
            }
        },
        # 2. Dual CLIP 로더
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5xxl_fp8_e4m3fn_scaled.safetensors",
                "type": "flux"
            }
        },
        # 3. VAE 로더
        "3": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors"
            }
        },
        # 4. CLIP 텍스트 인코딩 (positive)
        "4": {
            "class_type": "CLIPTextEncodeFlux",
            "inputs": {
                "clip": ["2", 0],
                "clip_l": prompt_text,
                "t5xxl": prompt_text,
                "guidance": cfg
            }
        },
        # 5. Empty Latent
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        },
        # 6. ModelSamplingFlux
        "6": {
            "class_type": "ModelSamplingFlux",
            "inputs": {
                "model": ["1", 0],
                "max_shift": 1.15,
                "base_shift": 0.5,
                "width": width,
                "height": height
            }
        },
        # 7. KSampler
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["6", 0],
                "positive": ["4", 0],
                "negative": ["9", 0],
                "latent_image": ["5", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0
            }
        },
        # 8. VAE Decode
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["3", 0]
            }
        },
        # 9. Empty conditioning (negative)
        "9": {
            "class_type": "CLIPTextEncodeFlux",
            "inputs": {
                "clip": ["2", 0],
                "clip_l": "",
                "t5xxl": "",
                "guidance": cfg
            }
        },
        # 10. Save Image
        "10": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": "FEP_char"
            }
        }
    }
    return workflow, seed


# === 캐릭터 프롬프트 정의 ===

CHARACTERS = {
    "char_B_minjun": {
        "prompt": (
            "Character reference sheet, multiple views (front, 3/4, side, back), "
            "young Korean man in his mid-20s, short neat black hair, "
            "tired/deadpan expression, slightly droopy eyes, "
            "wearing a plain gray hoodie and dark jeans, "
            "clean cartoon illustration style, Korean webtoon style, "
            "warm pastel colors, thick clean outlines, "
            "simple white background, character turnaround sheet, "
            "consistent design across all views, full body, "
            "absolutely no text, no letters, no words, no writing, no watermark, no signature"
        ),
        "output_dir": "characters",  # 시리즈 공용
        "is_series": True,
    },
    "char_A_subin": {
        "prompt": (
            "Character reference sheet, multiple views (front, 3/4, side), "
            "young Korean woman in her early 20s, long straight black hair, "
            "confident bright expression, sparkling eyes, slight smirk, "
            "wearing a pastel pink cardigan over white top, "
            "clean cartoon illustration style, Korean webtoon style, "
            "warm pastel colors, thick clean outlines, "
            "simple white background, character turnaround sheet, "
            "consistent design across all views, full body, "
            "absolutely no text, no letters, no words, no writing, no watermark, no signature"
        ),
        "output_dir": "characters",
        "is_series": False,
    },
    "char_C_kongi": {
        "prompt": (
            "Character illustration, cute Korean baby around 1 year old, "
            "round chubby face, big innocent eyes, blank confused expression, "
            "wearing a soft yellow onesie, sitting pose, "
            "clean cartoon illustration style, Korean webtoon style, "
            "warm pastel colors, thick clean outlines, "
            "simple white background, adorable, chibi proportions, "
            "absolutely no text, no letters, no words, no writing, no watermark, no signature"
        ),
        "output_dir": "characters",
        "is_series": False,
    },
    "char_D_jiwoo": {
        "prompt": (
            "Character reference sheet, multiple views (front, 3/4, side), "
            "young Korean person in mid-20s, androgynous gender-neutral appearance, "
            "short messy hair, awkward forced smile, eyes not smiling, "
            "wearing an oversized plain beige sweater and dark pants, "
            "clean cartoon illustration style, Korean webtoon style, "
            "warm pastel colors, thick clean outlines, "
            "simple white background, character turnaround sheet, "
            "consistent design across all views, full body, "
            "absolutely no text, no letters, no words, no writing, no watermark, no signature"
        ),
        "output_dir": "characters",
        "is_series": False,
    },
}


def generate_character(char_id, char_info, num_variants=2):
    """캐릭터 이미지 생성 (변형 N개)"""
    print(f"\n{'='*50}")
    print(f"  캐릭터 생성: {char_id}")
    print(f"{'='*50}")

    results = []
    for i in range(num_variants):
        print(f"\n  변형 {i+1}/{num_variants} 생성 중...")
        workflow, seed = build_flux_txt2img(
            char_info["prompt"],
            width=1344,  # 16:9에 가까운 FLUX 최적 해상도
            height=768,
            steps=20,
            cfg=3.5
        )
        # filename prefix 설정
        workflow["10"]["inputs"]["filename_prefix"] = f"FEP_{char_id}_v{i+1}"

        try:
            result = queue_prompt(workflow)
            prompt_id = result["prompt_id"]
            print(f"    큐잉 완료 (ID: {prompt_id[:8]}..., seed: {seed})")

            # 완료 대기
            history = wait_for_completion(prompt_id, timeout=600)
            if history:
                # 출력 이미지 찾기
                outputs = history.get("outputs", {})
                for node_id, output in outputs.items():
                    if "images" in output:
                        for img in output["images"]:
                            img_path = COMFYUI_OUTPUT / img["subfolder"] / img["filename"] if img["subfolder"] else COMFYUI_OUTPUT / img["filename"]
                            print(f"    ✓ 생성 완료: {img['filename']}")
                            results.append(str(img_path))
            else:
                print(f"    ✗ 타임아웃")
        except Exception as e:
            print(f"    ✗ 에러: {e}")

    return results


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if target == "all":
        # 민준(B) 먼저, 그 다음 나머지
        order = ["char_B_minjun", "char_A_subin", "char_C_kongi", "char_D_jiwoo"]
    elif target in CHARACTERS:
        order = [target]
    else:
        print(f"사용법: python generate_characters.py [all|char_B_minjun|char_A_subin|char_C_kongi|char_D_jiwoo]")
        sys.exit(1)

    print("FEP EP.01 — 캐릭터 시트 생성")
    print(f"대상: {', '.join(order)}")

    all_results = {}
    for char_id in order:
        results = generate_character(char_id, CHARACTERS[char_id])
        all_results[char_id] = results

    print(f"\n{'='*50}")
    print(f"  전체 완료")
    print(f"{'='*50}")
    for char_id, paths in all_results.items():
        print(f"  {char_id}: {len(paths)}장")
        for p in paths:
            print(f"    → {p}")
