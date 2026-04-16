#!/bin/bash
# S03_S06_siblings.mp3 재생성 — 대사 전환 지점에 무음 삽입
# 문제: "응. 응이 뭐야." 가 한 사람이 "응응이뭐야"라고 하는 것처럼 들림
# 해결: 화자 전환 지점에서 TTS를 분할하고 0.4초 무음 삽입

VOICE="ko-KR-InJoonNeural"
DIR="audio/longform_v2"
TEMP_DIR="audio/longform_v2/_temp_siblings"

cd "$(dirname "$0")"
mkdir -p "$TEMP_DIR"

echo "=== S03_S06_siblings.mp3 대사 간격 수정 ==="

# Part 1: 내레이터 도입 + 수빈 첫 질문
echo "[1/6] 내레이터 도입"
edge-tts --voice "$VOICE" --write-media "$TEMP_DIR/part1.mp3" --text \
"일요일 오후. 민준이는 아무 생각 없이 폰을 보고 있었습니다. 세상 평화롭죠. 오빠. 나 예쁘지?"

# Part 2: 내레이터 해설 (이 순간 ~ 지켜보죠)
echo "[2/6] 내레이터 해설"
edge-tts --voice "$VOICE" --write-media "$TEMP_DIR/part2.mp3" --text \
"이 순간. 민준이의 머릿속에서는 여러 가지 생각이 동시에 지나갑니다. 하지만 일단은, 이 장면을 좀 더 지켜보죠."

# Part 3: 수빈 "왜 대답을 안 해?" + 민준 "응."
echo "[3/6] 수빈 재촉 + 민준 응답"
edge-tts --voice "$VOICE" --write-media "$TEMP_DIR/part3.mp3" --text \
"왜 대답을 안 해? 응."

# ★ 여기에 0.4초 무음 삽입 (민준→수빈 화자 전환)

# Part 4: 수빈 "응이 뭐야. 제대로 말해." + 민준 "예뻐." + 수빈 반응
echo "[4/6] 수빈 재촉 + 민준 대답 + 수빈 확인"
edge-tts --voice "$VOICE" --write-media "$TEMP_DIR/part4.mp3" --text \
"응이 뭐야. 제대로 말해. 예뻐. 그치? 나 오늘 진짜 예쁘지?"

# Part 5: 내레이터 마무리
echo "[5/6] 내레이터 마무리"
edge-tts --voice "$VOICE" --write-media "$TEMP_DIR/part5.mp3" --text \
"여기까지는, 흔한 남매의 일상처럼 보입니다. 근데, 수빈이는 여기서 끝나지 않았습니다."

# 0.4초 무음 파일 생성
echo "[6/6] 무음 + 병합"
ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t 0.4 -c:a libmp3lame -q:a 2 "$TEMP_DIR/silence_04.mp3" 2>/dev/null
# 0.2초 무음 (짧은 비트)
ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t 0.2 -c:a libmp3lame -q:a 2 "$TEMP_DIR/silence_02.mp3" 2>/dev/null

# concat 리스트 — 화자 전환 지점에 무음 삽입
cat > "$TEMP_DIR/concat.txt" << 'EOF'
file 'part1.mp3'
file 'silence_02.mp3'
file 'part2.mp3'
file 'silence_02.mp3'
file 'part3.mp3'
file 'silence_04.mp3'
file 'part4.mp3'
file 'silence_02.mp3'
file 'part5.mp3'
EOF

# 기존 파일 백업
if [ -f "$DIR/S03_S06_siblings.mp3" ]; then
    TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
    cp "$DIR/S03_S06_siblings.mp3" "$DIR/S03_S06_siblings_backup_${TIMESTAMP}.mp3"
    echo "  → 기존 파일 백업: S03_S06_siblings_backup_${TIMESTAMP}.mp3"
fi

# 병합
ffmpeg -y -f concat -safe 0 -i "$TEMP_DIR/concat.txt" -c:a libmp3lame -q:a 2 -ar 24000 -ac 1 "$DIR/S03_S06_siblings.mp3" 2>/dev/null

# 결과 확인
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$DIR/S03_S06_siblings.mp3")
echo ""
echo "✓ 완료: S03_S06_siblings.mp3 (${DURATION}s)"

# 임시 파일 정리
rm -rf "$TEMP_DIR"

echo "=== 대사 간격 수정 완료 ==="
