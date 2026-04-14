#!/bin/bash
# FEP EP.01 Scene Generation Monitor v2
# 로그 의존 X — 출력 디렉토리 직접 감지
# Usage: while clear; do bash scene_monitor.sh; sleep 2; done

OUTPUT_DIR="$HOME/developer/ComfyUI/output"
TOTAL=15
TIME_PER_SCENE=240  # ~4min average

# Colors
G='\033[0;32m'  Y='\033[0;33m'  B='\033[0;34m'
C='\033[0;36m'  W='\033[1;37m'  D='\033[0;90m'  N='\033[0m'

# 씬 목록
SCENES=(
  "01:title"
  "02:confirmation"
  "03:forced_agreement"
  "04:narcissistic_supply"
  "05:baby_question"
  "06:autonomy"
  "07:vending_machine"
  "08:cognitive_dissonance"
  "09:boundary"
  "10:balance"
  "11:rationalization"
  "12:learned_helplessness"
  "13:comparison"
  "14:summary"
  "15:outro"
)

# 구 프롬프트 씬(01~08)은 _00001_ 존재 → _00002_가 신 프롬프트
# 신규 씬(09~15)은 _00001_이 신 프롬프트
OLD_PROMPT_SCENES="01 02 03 04 05 06 07 08"

done_count=0
current_scene=""
last_done_time=0

declare -A status_map
declare -A file_map

for entry in "${SCENES[@]}"; do
  num="${entry%%:*}"
  name="${entry##*:}"
  scene_key="scene_${num}_${name}"

  # 신 프롬프트 파일 감지
  if echo "$OLD_PROMPT_SCENES" | grep -qw "$num"; then
    # 01~08: _00002_ 파일이 신 프롬프트
    target="$OUTPUT_DIR/FEP_${scene_key}_00002_.png"
  else
    # 09~15: _00001_ 파일이 신 프롬프트 (구 프롬프트 없음)
    target="$OUTPUT_DIR/FEP_${scene_key}_00001_.png"
  fi

  if [ -f "$target" ]; then
    status_map[$num]="done"
    file_map[$num]="$target"
    ((done_count++))
    ft=$(stat -f %m "$target" 2>/dev/null || echo 0)
    if [ "$ft" -gt "$last_done_time" ]; then
      last_done_time=$ft
    fi
  else
    status_map[$num]="pending"
  fi
done

# 현재 생성 중인 씬 추정: 완료된 씬의 다음 번호
for entry in "${SCENES[@]}"; do
  num="${entry%%:*}"
  if [ "${status_map[$num]}" = "pending" ]; then
    if [ -z "$current_scene" ]; then
      current_scene="$num"
      status_map[$num]="running"
    fi
    break
  fi
done

# ComfyUI 큐 상태
comfyui_info=$(curl -s --connect-timeout 1 http://localhost:8188/queue 2>/dev/null | python3 -c "
import json,sys
try:
  q=json.load(sys.stdin)
  r=len(q.get('queue_running',[]))
  p=len(q.get('queue_pending',[]))
  print(f'{r},{p}')
except: print('0,0')
" 2>/dev/null || echo "0,0")
IFS=',' read -r q_run q_pend <<< "$comfyui_info"

# 진행률
pct=$((done_count * 100 / TOTAL))
bar_len=30
filled=$((pct * bar_len / 100))
empty=$((bar_len - filled))
bar=$(printf "%${filled}s" | tr ' ' '█')
bar_e=$(printf "%${empty}s" | tr ' ' '░')

# ETA
remaining=$((TOTAL - done_count))
if [ "$remaining" -eq 0 ]; then
  eta_str="${G}COMPLETE${N}"
elif [ "$q_run" -eq 0 ] && [ "$q_pend" -eq 0 ]; then
  eta_str="${Y}PAUSED${N}"
else
  eta_min=$(( (remaining * TIME_PER_SCENE) / 60 ))
  eta_str="${Y}~${eta_min}m${N}"
fi

# === 출력 ===
echo ""
echo -e " ${W}╔═══════════════════════════════════════════════╗${N}"
echo -e " ${W}║${C}  FEP EP.01 — Scene Generation Monitor  v2    ${W}║${N}"
echo -e " ${W}╠═══════════════════════════════════════════════╣${N}"
echo -e " ${W}║${N}                                               ${W}║${N}"

# 프로그레스 바
if [ "$pct" -eq 100 ]; then
  printf " ${W}║${N}  ${G}%s${N}  ${G}%3d%%${N} (%d/%d)            ${W}║${N}\n" "${bar}" "$pct" "$done_count" "$TOTAL"
else
  printf " ${W}║${N}  ${G}%s${D}%s${N}  ${W}%3d%%${N} (%d/%d)  ETA %b   ${W}║${N}\n" "${bar}" "${bar_e}" "$pct" "$done_count" "$TOTAL" "$eta_str"
fi

echo -e " ${W}║${N}                                               ${W}║${N}"

# ComfyUI 상태
if [ "$q_run" -gt 0 ]; then
  printf " ${W}║${N}  ComfyUI ${G}●${N} run:${W}%d${N} pend:${W}%d${N}                      ${W}║${N}\n" "$q_run" "$q_pend"
elif [ "$done_count" -eq "$TOTAL" ]; then
  echo -e " ${W}║${N}  ComfyUI ${G}● ALL DONE${N}                          ${W}║${N}"
else
  echo -e " ${W}║${N}  ComfyUI ${D}○ idle${N}                               ${W}║${N}"
fi

echo -e " ${W}╠═══════════════════════════════════════════════╣${N}"

# 씬 목록
for entry in "${SCENES[@]}"; do
  num="${entry%%:*}"
  name="${entry##*:}"
  st="${status_map[$num]}"

  case "$st" in
    done)    icon="${G}✅${N}" ;;
    running) icon="${Y}⏳${N}" ;;
    *)       icon="${D}⬚ ${N}" ;;
  esac

  printf " ${W}║${N}  %b ${W}%s${N}  %-37s${W}║${N}\n" "$icon" "$num" "$name"
done

echo -e " ${W}╠═══════════════════════════════════════════════╣${N}"

# 마지막 생성 시간
if [ "$last_done_time" -gt 0 ]; then
  last_str=$(date -r "$last_done_time" '+%H:%M:%S')
  echo -e " ${W}║${N}  ${D}Last generated: ${last_str}${N}                      ${W}║${N}"
fi

echo -e " ${W}╚═══════════════════════════════════════════════╝${N}"
echo -e "  ${D}$(date '+%H:%M:%S')  |  Ctrl+C to exit${N}"
echo ""
