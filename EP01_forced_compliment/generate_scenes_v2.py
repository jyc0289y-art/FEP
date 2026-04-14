#!/usr/bin/env python3
"""
FEP EP.01 v2 시네마틱 오버홀 — 신규 씬 일러스트 생성
기존 12장 재활용 + 신규 9장 생성
ComfyUI API + FLUX Kontext Dev Q8 GGUF txt2img
"""

import json
import urllib.request
import time
import os
import sys
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
    "young Korean person with soft androgynous features and short messy hair, "
    "wearing a beige oversized sweater and pants, "
    "gentle tired expression"
)

# 글자 금지 공통 서픽스
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

# 네거티브 프롬프트 (텍스트/워터마크 방지)
NEGATIVE_PROMPT = (
    "text, letters, words, writing, numbers, watermark, logo, signature, stamp, seal, "
    "speech bubble, caption, label, UI, Korean text, Japanese text, Chinese text, "
    "hangul, kanji, hiragana, katakana, alphabet, typography, brand, url"
)

# 스타일 공통 서픽스
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
                "clip_l": NEGATIVE_PROMPT, "t5xxl": NEGATIVE_PROMPT,
                "guidance": cfg
            }
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": filename_prefix}
        }
    }
    return workflow, seed


# === v2 신규 씬 프롬프트 ===
# 각본의 일러스트 연출 지시를 정확히 반영
# 주의: "dark/shadow/black" 직접 사용 금지 — 구체적 색상명 사용

NEW_SCENES = {
    # S-03: 민준 소파 — 1막 오프닝, 완벽한 평화
    "v2_S03_minjun_sofa": {
        "prompt": (
            f"{CHAR_MINJUN}, lying casually on a cozy sofa scrolling phone, "
            "completely relaxed lazy posture, one leg on armrest, "
            "coffee cup with steam on side table, "
            "warm golden afternoon sunlight streaming through curtains, "
            "peaceful cozy living room, sunday afternoon atmosphere, "
            "both arms visible, phone in one hand, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-05: 민준 리액션 클로즈업 — 침묵의 연기
    "v2_S05_minjun_reaction": {
        "prompt": (
            f"Close-up portrait of {CHAR_MINJUN}, "
            "subtle conflicted expression, eyes glancing sideways, "
            "slight grimace on lips, phone screen light illuminating face from below, "
            "soft warm background completely blurred, "
            "the expression reads 'what do I do with this', "
            "intimate camera angle, emotional portrait, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-08: 민준 관찰 시선 — 불편함 감지
    "v2_S08_minjun_observing": {
        "prompt": (
            f"{CHAR_MINJUN}, sitting on sofa in background, "
            "phone lowered to lap, watching something in the distance, "
            "playfulness gone from expression, eyes slightly narrowed, "
            "observing analyzing gaze, something clicked in his mind, "
            "warm living room but his expression creates subtle tension, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-15: 카페 수빈+지우 — 2막B 전환점 (v2b: 지우 외형 수정)
    "v2_S15_cafe_subin_jiwoo": {
        "prompt": (
            f"Cafe window seat scene, {CHAR_SUBIN} sitting across from {CHAR_JIWOO}, "
            "subin has shopping bags beside her and bright cheerful expression, "
            "jiwoo holds coffee cup with both hands close to chest defensively, "
            "warm afternoon light through cafe window, "
            "cozy cafe interior with wooden table, "
            "both characters fully visible from waist up, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-17: 지우 어색한 미소 — 순응의 비주얼 (v2b: 눈/입 불일치 강조)
    "v2_S17_jiwoo_forced_smile": {
        "prompt": (
            f"Close-up portrait of {CHAR_JIWOO}, "
            "the mouth corners are turned upward in a practiced polite smile, "
            "but the eyes are completely dead and hollow with no emotion, "
            "strong contrast between the smiling lower face and the empty exhausted upper face, "
            "the eyes look like they want to cry but the mouth keeps smiling, "
            "soft warm cafe background blurred, "
            "emotional portrait showing painful disconnect between smile and dead eyes, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-19: 반복 겹침 — 학습된 무력감 시각화 (v2b: 대사/질문 언급 삭제)
    "v2_S19_repetition_layers": {
        "prompt": (
            f"Artistic multiple exposure composition showing repetition and exhaustion, "
            f"four ghostly transparent overlapping versions of {CHAR_JIWOO} in a cafe, "
            "each layer progressively more faded and desaturated, "
            "first version: slight smile, second: tired expression, "
            "third: blank emotionless face, fourth: hollow empty stare, "
            f"a single bright figure of {CHAR_SUBIN} on the left side in full color contrast, "
            "the repetition creates visual sense of endless cycle and fatigue, "
            "muted pastel colors becoming gray with each layer, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-20: 지우 귀가 — 누적된 피로 (v2b: 포즈 명확화)
    "v2_S20_jiwoo_doorway": {
        "prompt": (
            f"{CHAR_JIWOO}, standing upright with back pressed flat against closed front door, "
            "head tilted back resting on the door, shoes still on feet, "
            "arms hanging loosely at sides, staring at ceiling with empty exhausted eyes, "
            "narrow apartment hallway with only a single dim warm wall lamp, "
            "muted blue-gray color palette, quiet loneliness, "
            "not crying but completely drained of energy, heavy emotional weight, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-21: 수빈 밤 혼자 — 감정적 반전 (v2b: 포즈 명확화)
    "v2_S21_subin_night_alone": {
        "prompt": (
            f"{CHAR_SUBIN} but without her usual confidence, "
            "lying on her back in bed in supine position, face up staring at ceiling, "
            "bare face without makeup, vulnerable fragile expression, "
            "phone placed on the bed beside her casting soft blue light on her face, "
            "the bright pink cardigan from daytime tossed carelessly on bedside chair, "
            "room lit only by phone glow, "
            "muted indigo-gray tones, intimate lonely atmosphere, "
            "eyes slightly moist but not crying, contemplative, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-24: 빈 의자 — 에필로그 여운 (v2b: 4개 의자 강조)
    "v2_S24_empty_chair": {
        "prompt": (
            "Exactly four chairs arranged in a circle viewed from above at slight angle, "
            "chair one has a bright pink scarf draped on it, "
            "chair two has a smartphone placed on the seat, "
            "chair three has a coffee cup on it, "
            "chair four is completely empty with warm golden spotlight falling on it, "
            "four chairs total one two three four, the fourth one is the focus, "
            "no people in the scene, only objects on chairs, "
            "warm gentle atmosphere, clean minimal room, contemplative still life, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # === 신규 누락 씬 ===
    # S-04: 수빈 등장 — 민준 앞에 떡 서기 (1막 코믹 핵심)
    "v2_S04_subin_entrance": {
        "prompt": (
            f"Living room scene, {CHAR_SUBIN} standing confidently in front of {CHAR_MINJUN} who is on the sofa, "
            "subin has one hand on her hip and the other hand making a V sign next to her face, "
            "expectant excited expression demanding attention, "
            "subin is brightly lit center frame while minjun is in the corner looking up awkwardly, "
            "comedic contrast between her energy and his reluctance, "
            "warm living room afternoon light, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-11: 강요된 동의 시각화 — 수빈 밝음 vs 민준 압박
    "v2_S11_coerced_compliance": {
        "prompt": (
            f"Dramatic lighting scene, {CHAR_SUBIN} standing with bright warm spotlight on her smiling face, "
            f"facing {CHAR_MINJUN} whose back is against a wall in muted cool shadow, "
            "subin looks genuinely happy and bright, but the composition feels oppressive, "
            "the bright energy from subin creates paradoxical pressure on minjun, "
            "minjun expression is not angry but quietly cornered, "
            "living room with dramatic split lighting warm versus cool, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-18: 지우 카페 창밖 비 — 자기 합리화
    "v2_S18_jiwoo_rain_window": {
        "prompt": (
            f"{CHAR_JIWOO} sitting alone in a cafe, "
            "sipping coffee while gazing out the window at falling rain, "
            "raindrops streaming down the glass, "
            "reflection of jiwoo's face visible in the wet window surface, "
            "the rain outside mirrors inner emotional state, "
            "warm cafe interior contrasts with gray rainy outside, "
            "contemplative melancholic atmosphere, alone with thoughts, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-01: 거울 앞 수빈 — 프롤로그, 자신감 넘치는 첫 등장
    "v2_S01_subin_mirror": {
        "prompt": (
            f"{CHAR_SUBIN} standing in front of a bathroom mirror, "
            "tilting her head side to side examining her own face with satisfied smile, "
            "warm morning sunlight coming from the left side, "
            "mirror reflection shows her confident glowing face, "
            "bright warm bathroom with clean tiles, "
            "she looks like she truly loves what she sees, self-assured radiant, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-06: 수빈 압박 — 한 발 더 다가서며 고개 기울임
    "v2_S06_subin_pressure": {
        "prompt": (
            f"Living room scene, {CHAR_SUBIN} leaning forward toward {CHAR_MINJUN} on the sofa, "
            "subin tilting her head with playful but slightly intimidating expression, "
            "she is looking down at minjun from a dominant standing position, "
            "minjun shrinks back into the sofa looking uncomfortable, "
            "subin's bright energy fills the frame while minjun is cornered, "
            "comedic but slightly tense atmosphere, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
    # S-09: 민준 내면 되감기 — 같은 거실, 차가운 색감
    "v2_S09_rewind_desaturated": {
        "prompt": (
            f"Same living room as before but completely desaturated cold blue-gray color palette, "
            f"{CHAR_MINJUN} sitting on sofa is the only sharp focused element, "
            f"a blurry frozen silhouette of {CHAR_SUBIN} standing nearby out of focus, "
            "the scene looks like a memory being replayed in slow motion, "
            "cold muted tones, psychological interior perspective, "
            "as if viewing the world through minjun's analytical mind, "
            f"{NO_TEXT}, {STYLE}"
        ),
    },
}


def generate_scene(scene_id):
    """단일 씬 생성"""
    if scene_id not in NEW_SCENES:
        print(f"❌ 알 수 없는 씬: {scene_id}")
        print(f"사용 가능: {', '.join(NEW_SCENES.keys())}")
        return

    scene = NEW_SCENES[scene_id]
    workflow, seed = build_flux_txt2img(
        scene["prompt"],
        filename_prefix=f"FEP_{scene_id}"
    )

    try:
        result = queue_prompt(workflow)
        pid = result["prompt_id"]
        print(f"큐잉: {scene_id} (seed: {seed})")

        history = wait_for_completion(pid, timeout=600)
        if history and history.get("status", {}).get("status_str") == "success":
            for nid, out in history.get("outputs", {}).items():
                if "images" in out:
                    for img in out["images"]:
                        print(f"✅ {scene_id}: {img['filename']}")
        else:
            print(f"❌ {scene_id}: 생성 실패")
    except Exception as e:
        print(f"❌ {scene_id}: {e}")


def generate_all():
    """전체 신규 씬 순차 생성"""
    print(f"=== v2 신규 씬 {len(NEW_SCENES)}장 생성 시작 ===")
    print(f"예상 소요: ~{len(NEW_SCENES) * 6}분 (1장당 ~6분, MPS)\n")

    prompt_ids = []
    for scene_id, scene in NEW_SCENES.items():
        workflow, seed = build_flux_txt2img(
            scene["prompt"],
            filename_prefix=f"FEP_{scene_id}"
        )
        try:
            result = queue_prompt(workflow)
            pid = result["prompt_id"]
            prompt_ids.append((scene_id, pid, seed))
            print(f"큐잉: {scene_id} (seed: {seed})")
        except Exception as e:
            print(f"❌ 큐잉 실패: {scene_id} — {e}")

    print(f"\n총 {len(prompt_ids)}장 큐잉 완료. 순차 대기 시작...\n")

    for scene_id, pid, seed in prompt_ids:
        t = time.time()
        history = wait_for_completion(pid, timeout=600)
        elapsed = time.time() - t
        if history:
            status = history.get("status", {}).get("status_str", "unknown")
            if status == "success":
                for nid, out in history.get("outputs", {}).items():
                    if "images" in out:
                        for img in out["images"]:
                            print(f"✅ {scene_id}: {img['filename']} ({elapsed:.0f}s)")
            else:
                for msg in history.get("status", {}).get("messages", []):
                    if msg[0] == "execution_error":
                        print(f"❌ {scene_id}: {msg[1].get('exception_message', '')[:100]}")
        else:
            print(f"⏰ {scene_id}: 타임아웃")

    print("\n=== 생성 완료 ===")
    print(f"결과물 위치: {COMFYUI_OUTPUT}")
    print("collect_scenes.sh로 수집하세요.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            print("v2 신규 씬 목록:")
            for sid in NEW_SCENES:
                print(f"  {sid}")
        elif sys.argv[1] in NEW_SCENES:
            generate_scene(sys.argv[1])
        else:
            print(f"알 수 없는 인자: {sys.argv[1]}")
            print(f"사용: python {sys.argv[0]} [list | scene_id | (전체 생성)]")
    else:
        generate_all()
