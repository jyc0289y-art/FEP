#!/usr/bin/env python3
"""
FEP EP.01 — ComfyUI API를 통한 씬 일러스트 생성
FLUX Kontext Dev Q8 GGUF txt2img
모든 텍스트/말풍선/라벨은 후처리로 합성 (다국어 대응)
"""

import json
import urllib.request
import time
import os
from pathlib import Path

COMFYUI_URL = "http://localhost:8188"
COMFYUI_OUTPUT = Path.home() / "developer" / "ComfyUI" / "output"

# 캐릭터 시트 기반 정규 설명
CHAR_SUBIN = (
    "young Korean woman in her early 20s with long straight black hair, "
    "wearing a pastel pink cardigan over white top, "
    "confident bright expression with sparkling eyes"
)
CHAR_MINJUN = (
    "young Korean man in his early 20s with short black hair, "
    "wearing a gray hoodie"
)
CHAR_JIWOO = (
    "young Korean person with short messy hair, "
    "wearing a beige oversized sweater"
)

# 글자 금지 공통 서픽스 (강화)
NO_TEXT = (
    "absolutely no text, no letters, no words, no writing, no numbers, "
    "no watermark, no signature, no speech bubbles with text, "
    "no captions, no labels, no UI elements, "
    "no Korean characters, no Japanese characters, no Chinese characters, "
    "no hangul, no kanji, no hiragana, no katakana, "
    "text-free illustration"
)

# 스타일 공통 서픽스 (신체 완전성 추가)
STYLE = (
    "clean cartoon illustration style, Korean webtoon style, "
    "warm pastel colors, thick clean outlines, "
    "simple minimal background, 16:9 aspect ratio, "
    "safe zone composition with key elements in center third, "
    "all characters with complete visible arms and hands, "
    "no cropped limbs, full upper body visible"
)


def queue_prompt(workflow):
    payload = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def wait_for_completion(prompt_id, timeout=600):
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
                "clip_l": "", "t5xxl": "",
                "guidance": cfg
            }
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": "FEP_scene"}
        }
    }
    return workflow, seed


# === 씬 프롬프트 (텍스트 프리) ===
# 모든 말풍선/라벨/텍스트는 FFmpeg drawtext로 후처리 합성

SCENES = {
    "scene_01_title": {
        "prompt": (
            f"{CHAR_SUBIN}, standing in front of a full-length mirror, "
            "confident smirking expression, pointing at her own reflection with one hand, "
            "both arms fully visible, bright pastel bedroom background, "
            "empty clean speech bubble floating near her head with no text inside, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "speech_bubble", "text_ko": "나 예쁘지?", "text_ja": "私かわいいでしょ？", "text_en": "I'm pretty, right?"}
        ],
    },
    "scene_02_confirmation": {
        "prompt": (
            f"{CHAR_SUBIN}, approaching {CHAR_MINJUN}, "
            "she has eager expectant eyes looking up at him, "
            "he looks uncomfortable and avoids eye contact, "
            "both characters with both arms and hands visible, "
            "indoor living room setting, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_03_forced_agreement": {
        "prompt": (
            f"{CHAR_MINJUN}, backed into a corner looking trapped and nervous, "
            f"{CHAR_SUBIN}, standing with arms crossed "
            "waiting for an answer with raised eyebrow, dominant pose, "
            "dramatic spotlight composition, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_04_narcissistic_supply": {
        "prompt": (
            f"{CHAR_SUBIN}, surrounded by multiple "
            "empty floating speech bubbles of various sizes, "
            "satisfied happy glowing expression, sparkle effects around her, "
            "both arms and hands visible, "
            "dreamy pastel background with warm tones, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "bubbles_fill", "text_ko": "예쁘다", "text_ja": "かわいい", "text_en": "Pretty"}
        ],
    },
    "scene_05_baby_question": {
        "prompt": (
            f"{CHAR_SUBIN}, crouching down in front of "
            "a cute baby in yellow onesie sitting on the floor, "
            "she is smiling and pointing at herself with one hand, "
            "both arms and hands visible, "
            "the baby has a blank confused stare with big round eyes, "
            "bright warm living room with simple furniture, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_06_autonomy": {
        "prompt": (
            f"{CHAR_MINJUN}, with a large thought bubble above his head, "
            "inside the thought bubble is an abstract tangle of arrows and swirls, "
            "his expression is frustrated and annoyed, "
            "both arms and hands visible, "
            "muted background colors to emphasize internal conflict, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "thought_bubble", "text_ko": "답이 정해져 있는데\n왜 물어보는 건데...", "text_ja": "答えは決まってるのに\nなんで聞くんだよ...", "text_en": "The answer's already decided...\nWhy even ask?"}
        ],
    },
    "scene_07_vending_machine": {
        "prompt": (
            f"Humorous illustration of {CHAR_MINJUN} transformed into a vending machine shape, "
            "his face visible on the machine looking annoyed, "
            f"{CHAR_SUBIN} pressing a button on the machine with one hand, "
            "colorful cartoon style, comedic composition, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "button_label", "text_ko": "칭찬", "text_ja": "褒め", "text_en": "Compliment"}
        ],
    },
    "scene_08_cognitive_dissonance": {
        "prompt": (
            f"{CHAR_MINJUN}, with a small angel character on one shoulder "
            "and a small devil character on the other shoulder, "
            "the angel gestures encouragingly, the devil shrugs doubtfully, "
            "the man looks conflicted in the middle, "
            "both arms and hands visible, "
            "empty speech bubbles near angel and devil, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "angel_bubble", "text_ko": "그냥 예쁘다고 해", "text_ja": "かわいいって言えよ", "text_en": "Just say she's pretty"},
            {"type": "devil_bubble", "text_ko": "근데 진심은 아닌데...", "text_ja": "でも本心じゃないし...", "text_en": "But it's not sincere..."}
        ],
    },
    "scene_09_boundary": {
        "prompt": (
            f"{CHAR_MINJUN}, standing behind a translucent glowing shield barrier, "
            "protective pose with both arms slightly raised, hands visible, "
            "the barrier has a soft blue glow, peaceful determined expression, "
            "abstract minimal background, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_10_balance": {
        "prompt": (
            f"{CHAR_JIWOO}, "
            "holding a balance scale in both hands, "
            "one side of the scale glows warm orange, "
            "the other side glows cool blue, "
            "the person looks troubled trying to balance them, "
            "both arms and hands clearly visible holding the scale, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "scale_label", "text_ko": ["솔직함", "관계의 평화"], "text_ja": ["正直さ", "関係の平和"], "text_en": ["Honesty", "Peace"]}
        ],
    },
    "scene_11_rationalization": {
        "prompt": (
            f"{CHAR_JIWOO}, "
            "large thought bubble above head showing internal debate, "
            "expression of self-convincing with slight nod, "
            "sweat drop on forehead, both arms visible, "
            "pastel background, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "thought_bubble", "text_ko": "뭐... 실제로 안 예쁜 것도\n아니니까...", "text_ja": "まぁ...実際かわいくない\nわけでもないし...", "text_en": "Well... it's not like\nshe's NOT pretty..."}
        ],
    },
    "scene_12_learned_helplessness": {
        "prompt": (
            f"{CHAR_JIWOO}, looking exhausted and defeated, "
            "behind them are faded ghost-like afterimages of the same person "
            "in the same pose repeating into the background, "
            "empty speech bubble near their mouth, tired eyes, "
            "both arms hanging limply, "
            "desaturated muted colors showing fatigue, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "speech_bubble", "text_ko": "응... 예뻐...", "text_ja": "うん...かわいいよ...", "text_en": "Yeah... you're pretty..."}
        ],
    },
    "scene_13_comparison": {
        "prompt": (
            "Split screen illustration divided vertically in the middle with a thin line, "
            "left side muted purple-gray background showing a stern figure in dark coat "
            "holding puppet control strings downward, menacing but fully visible, "
            f"right side warm pastel background showing {CHAR_SUBIN} asking a question cheerfully "
            "with both hands raised, "
            "clear visual contrast between the two halves, "
            "empty white label box at top of each half, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "split_labels", "text_ko": ["가스라이팅:\n현실 인식 왜곡", "이 상황:\n답 강요"], "text_ja": ["ガスライティング:\n現実認識の歪曲", "この状況:\n答えの強要"], "text_en": ["Gaslighting:\nDistorting reality", "This situation:\nForcing an answer"]}
        ],
    },
    "scene_14_summary": {
        "prompt": (
            "Three characters standing side by side facing the viewer, "
            f"left: {CHAR_SUBIN} in confident pose, "
            f"center: {CHAR_MINJUN} with arms crossed neutral expression, "
            f"right: {CHAR_JIWOO} in awkward stance, "
            "all three with both arms and hands visible, "
            "empty label space above each character, "
            "clean white background, lineup composition, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "character_labels", "text_ko": ["칭찬의 소비자", "칭찬 거래의 거부자", "칭찬의 공급자"], "text_ja": ["褒めの消費者", "褒め取引の拒否者", "褒めの供給者"], "text_en": ["Compliment Consumer", "Compliment Refuser", "Compliment Supplier"]}
        ],
    },
    "scene_15_outro": {
        "prompt": (
            "Cheerful end screen illustration, three characters waving goodbye, "
            f"left: {CHAR_SUBIN}, "
            f"center: {CHAR_MINJUN}, "
            f"right: {CHAR_JIWOO}, "
            "all waving with both hands visible, friendly happy poses, "
            "warm sunset pastel gradient background, "
            "space for subscribe button overlay in lower third, "
            "happy positive atmosphere, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [
            {"type": "cta", "text_ko": "구독 & 좋아요", "text_ja": "チャンネル登録 & いいね", "text_en": "Subscribe & Like"}
        ],
    },
}

# === B컷 (서브 일러스트) — 17초+ 씬의 정지 어색함 해소 ===
# 메인 씬과 같은 에피소드 맥락이지만 다른 앵글/클로즈업/반응샷
BCUT_SCENES = {
    "scene_03b_minjun_awkward": {
        "prompt": (
            f"Close-up of {CHAR_MINJUN}, looking away awkwardly, "
            "slight grimace, hand scratching the back of his neck nervously, "
            "warm pastel background, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_05b_baby_closeup": {
        "prompt": (
            "Close-up of a cute baby with big round confused eyes, "
            "wearing a yellow onesie, tilting head slightly, "
            "blank puzzled expression, drooling slightly, "
            "soft warm blurred living room background, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_06b_thought_tangle": {
        "prompt": (
            "Abstract illustration of tangled arrows and question marks, "
            "swirling confused thought pattern, "
            "warm muted colors, conceptual psychological diagram style, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_10b_scale_tilt": {
        "prompt": (
            "Close-up of a balance scale tilting to one side, "
            "the warm orange side (honesty) is rising up, "
            "the cool blue side (peace) is weighing down heavier, "
            "dramatic lighting, conceptual illustration, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_12b_ghost_repeat": {
        "prompt": (
            f"Side view of {CHAR_JIWOO}, sitting alone slumped over, "
            "multiple faded transparent copies of the same person "
            "stretching into the distance behind them like echoes, "
            "desaturated colors, feeling of repetitive exhaustion, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_14b_subin_solo": {
        "prompt": (
            f"Portrait of {CHAR_SUBIN}, confident pose with arms crossed, "
            "looking directly at viewer with a bright knowing smile, "
            "clean pastel background, upper body visible, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
    "scene_14c_minjun_solo": {
        "prompt": (
            f"Portrait of {CHAR_MINJUN}, arms crossed with a tired neutral expression, "
            "looking slightly to the side, subtle frown, "
            "clean pastel background, upper body visible, "
            "original artwork, no artist signature, no website url, "
            f"{STYLE}, {NO_TEXT}"
        ),
        "text_overlay": [],
    },
}


def generate_all_scenes():
    """모든 씬 일러스트를 ComfyUI 큐에 등록"""
    prompt_ids = []
    for scene_id, scene_info in SCENES.items():
        workflow, seed = build_flux_txt2img(
            scene_info["prompt"],
            width=1344, height=768, steps=20, cfg=3.5
        )
        workflow["10"]["inputs"]["filename_prefix"] = f"FEP_{scene_id}"

        try:
            result = queue_prompt(workflow)
            pid = result["prompt_id"]
            prompt_ids.append((scene_id, pid, seed))
            print(f"큐잉: {scene_id} (seed: {seed})")
        except Exception as e:
            print(f"❌ 큐잉 실패: {scene_id} — {e}")

    print(f"\n총 {len(prompt_ids)}장 큐잉 완료")
    print(f"예상 소요: ~{len(prompt_ids) * 6}분 (1장당 ~6분)")
    print("=" * 50)

    # 순차 완료 대기
    for scene_id, pid, seed in prompt_ids:
        t = time.time()
        history = wait_for_completion(pid, timeout=600)
        elapsed = time.time() - t
        if history:
            status = history.get("status", {}).get("status_str", "unknown")
            if status == "success":
                outputs = history.get("outputs", {})
                for nid, out in outputs.items():
                    if "images" in out:
                        for img in out["images"]:
                            print(f"✅ {scene_id}: {img['filename']} ({elapsed:.0f}s)")
            else:
                for msg in history.get("status", {}).get("messages", []):
                    if msg[0] == "execution_error":
                        print(f"❌ {scene_id}: {msg[1].get('exception_message', '')[:100]}")
        else:
            print(f"⏰ {scene_id}: 타임아웃")


def save_text_overlay_manifest():
    """텍스트 오버레이 매니페스트를 JSON으로 저장 (다국어 대응)"""
    manifest = {}
    for scene_id, scene_info in SCENES.items():
        if scene_info["text_overlay"]:
            manifest[scene_id] = scene_info["text_overlay"]

    out_path = Path(__file__).parent / "text_overlay_manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"텍스트 오버레이 매니페스트 저장: {out_path}")
    return out_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "manifest":
        save_text_overlay_manifest()
    elif len(sys.argv) > 1 and sys.argv[1] in SCENES:
        # 특정 씬만 생성
        scene_id = sys.argv[1]
        scene_info = SCENES[scene_id]
        workflow, seed = build_flux_txt2img(scene_info["prompt"])
        workflow["10"]["inputs"]["filename_prefix"] = f"FEP_{scene_id}"
        result = queue_prompt(workflow)
        pid = result["prompt_id"]
        print(f"큐잉: {scene_id} (seed: {seed})")
        history = wait_for_completion(pid, timeout=600)
        if history and history.get("status", {}).get("status_str") == "success":
            for nid, out in history.get("outputs", {}).items():
                if "images" in out:
                    for img in out["images"]:
                        print(f"✅ {img['filename']}")
    else:
        print("FEP EP.01 — 씬 일러스트 생성 (텍스트 프리)")
        print("텍스트/말풍선은 text_overlay_manifest.json 기반 후처리 합성\n")
        save_text_overlay_manifest()
        print()
        generate_all_scenes()
