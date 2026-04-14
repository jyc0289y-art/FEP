#!/bin/bash
# ComfyUI output에서 각 씬의 최신(가장 높은 번호) 파일만 scenes/에 복사
# Usage: bash collect_scenes.sh [--dry-run]

SRC="$HOME/developer/ComfyUI/output"
DST="$(dirname "$0")/scenes"
DRY_RUN=false
[ "$1" = "--dry-run" ] && DRY_RUN=true

mkdir -p "$DST"

SCENES=(
  scene_01_title
  scene_02_confirmation
  scene_03_forced_agreement
  scene_04_narcissistic_supply
  scene_05_baby_question
  scene_06_autonomy
  scene_07_vending_machine
  scene_08_cognitive_dissonance
  scene_09_boundary
  scene_10_balance
  scene_11_rationalization
  scene_12_learned_helplessness
  scene_13_comparison
  scene_14_summary
  scene_15_outro
)

count=0
for s in "${SCENES[@]}"; do
  # 가장 높은 번호(최신 생성본) 선택
  latest=$(ls -v "$SRC"/FEP_${s}_*.png 2>/dev/null | tail -1)
  if [ -n "$latest" ]; then
    fname=$(basename "$latest")
    dst_name="${s}.png"
    if $DRY_RUN; then
      echo "[dry] $fname → $dst_name"
    else
      cp "$latest" "$DST/$dst_name"
      echo "✅ $fname → $dst_name"
    fi
    ((count++))

    # 민준 단독 씬: 구버전(_00001_)도 _alt로 보존 (비교용)
    num=$(echo "$s" | grep -o '[0-9]\+' | head -1)
    if echo "06 08 09" | grep -qw "$num"; then
      old=$(ls -v "$SRC"/FEP_${s}_*.png 2>/dev/null | head -1)
      if [ "$old" != "$latest" ] && [ -n "$old" ]; then
        alt_name="${s}_alt.png"
        if $DRY_RUN; then
          echo "  [dry] $(basename "$old") → $alt_name (민준 구버전)"
        else
          cp "$old" "$DST/$alt_name"
          echo "  ↳ $(basename "$old") → $alt_name (민준 구버전)"
        fi
      fi
    fi
  else
    echo "⬚  $s — not found"
  fi
done

echo ""
echo "Collected: $count / ${#SCENES[@]} (메인)"

# === B컷 수집 ===
BCUTS=(
  scene_03b_minjun_awkward
  scene_05b_baby_closeup
  scene_06b_thought_tangle
  scene_10b_scale_tilt
  scene_12b_ghost_repeat
  scene_14b_subin_solo
  scene_14c_minjun_solo
)

bcount=0
for s in "${BCUTS[@]}"; do
  latest=$(ls -v "$SRC"/FEP_${s}_*.png 2>/dev/null | tail -1)
  if [ -n "$latest" ]; then
    fname=$(basename "$latest")
    dst_name="${s}.png"
    if $DRY_RUN; then
      echo "[dry] B컷 $fname → $dst_name"
    else
      cp "$latest" "$DST/$dst_name"
      echo "✅ B컷 $fname → $dst_name"
    fi
    ((bcount++))
  fi
done

echo ""
echo "Collected: $bcount / ${#BCUTS[@]} (B컷)"
