#!/bin/bash
# EP.01 강요된 칭찬의 심리학 — edge-tts 드래프트 생성
# Voice: ko-KR-InJoonNeural

VOICE="ko-KR-InJoonNeural"
LONGFORM_DIR="audio/longform"
SHORTS_DIR="audio/shorts"

cd "$(dirname "$0")"

echo "=== 롱폼 15씬 TTS 생성 ==="

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_01_intro.mp3" --text \
"여러분 주변에도 이런 사람 있지 않나요? 나한테 예쁘냐고 물어보는데, 사실 답은 이미 정해져 있는 사람."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_02_validation.mp3" --text \
"심리학에서 이걸 확인 추구 행동이라고 합니다. 자기 외모에 대한 확신을 외부에서 얻으려는 행동이에요. 핵심은, 진짜 궁금한 게 아니라는 겁니다. 답이 정해진 질문을 던지는 순간, 이건 질문이 아니라 요구가 됩니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_03_coerced.mp3" --text \
"거절할 수 없는 사회적 압력 속에서 특정 답변을 유도하는 구조. 심리학에서는 이걸 강요된 동의라고 부릅니다. 관계의 맥락상 아니라고 말하기 어렵다는 걸 본인도 알고 있기 때문에, 질문의 형식을 빌렸지만 실질적으로는 동의를 강제하는 겁니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_04_narcissistic.mp3" --text \
"타인의 칭찬이나 긍정적 반응을 통해 자존감을 유지하려는 패턴. 답변의 진정성은 중요하지 않습니다. 예쁘다는 말 자체를 듣는 행위가 목적이에요."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_05_baby.mp3" --text \
"아기에게까지 같은 질문을 합니다. 아기는 동의도 거부도 할 수 없어요. 이 지점에서 질문의 본질이 드러납니다. 이건 질문이 아니라 의식입니다. 대답의 내용이 아니라, 대답을 받아내는 행위 자체에서 심리적 만족을 얻는 구조입니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_06_autonomy.mp3" --text \
"자 그러면, 이 질문을 받는 쪽은 왜 불편할까요? 답이 정해진 질문은 상대의 판단권을 빼앗는 겁니다. 네 의견을 물어보는 것 같지만, 실은 내가 원하는 말을 해라. 이런 구조이기 때문에, 자유의지를 가진 사람으로서 본능적으로 불쾌함을 느낍니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_07_vending.mp3" --text \
"진심이 궁금한 게 아니라, 칭찬 자판기로 쓰이는 느낌입니다. 나라는 사람이 아니라, 나의 기능만 필요한 상황. 심리학에서 말하는 도구적 관계에 대한 거부감이에요."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_08_dissonance.mp3" --text \
"솔직한 답을 하면 관계가 불편해지고, 원하는 답을 해주면 자기 진정성이 훼손됩니다. 이 두 가지 사이에 끼이는 불편함 자체가 대답을 꺼리게 만듭니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_09_boundary.mp3" --text \
"대답해주기 싫다는 감정. 이건 사실 아주 건강한 심리적 반응입니다. 타인의 감정적 필요를 무조건 충족시켜야 한다는 암묵적 압력을 거부하는 것. 이건 진짜 질문이 아니잖아, 라는 걸 직감적으로 감지하고 있는 겁니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_10_relational.mp3" --text \
"그런데 많은 사람들은 이 불편함을 느끼면서도 결국 예쁘다고 답해줍니다. 왜일까요? 이 한마디면 끝나잖아, 라는 계산입니다. 솔직함의 가치보다 관계의 평화를 우선시하는 선택이에요. 단기적으로는 합리적이지만, 반복되면 관계 안에서 자기 목소리를 잃어가는 패턴이 됩니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_11_rationalize.mp3" --text \
"인지부조화를 해소하는 가장 쉬운 방법은 신념을 바꾸는 겁니다. 뭐, 실제로 안 예쁜 것도 아니니까. 답변 후에 오히려 불편함이 줄어드는 이유가 여기 있어요. 본인이 스스로를 설득한 겁니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_12_helplessness.mp3" --text \
"어차피 거절해도 또 물어볼 거잖아. 이런 경험이 쌓이면 저항 자체를 포기합니다. 매번 작은 자기 진정성을 지불하고 관계의 평화를 사는 거래를 하고 있는 거예요. 이게 쌓이면, 그 관계 자체에 대한 은근한 피로감으로 나타납니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_13_gaslighting.mp3" --text \
"많은 분들이 이런 상황을 가스라이팅이라고 부르는데, 정확하지 않습니다. 가스라이팅은 상대의 현실 인식 자체를 왜곡시키는 행위에요. 이 에피소드는 현실 인식을 왜곡하는 게 아니라, 정해진 답을 강요하는 구조입니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_14_summary.mp3" --text \
"나 예쁘지? 라는 다섯 글자 안에, 세 가지 심리적 역학이 동시에 작동합니다. 질문자는 칭찬의 소비자. 거부자는 칭찬 거래의 거부자. 순응자는 칭찬의 공급자. 다섯 글자 안에 이만큼의 심리적 구조가 숨어 있었습니다."

edge-tts --voice "$VOICE" --write-media "$LONGFORM_DIR/scene_15_outro.mp3" --text \
"이런 일상 속 감춰진 심리가 궁금하다면, 구독과 좋아요 부탁드립니다. 다음 에피소드에서 또 만나요."

echo ""
echo "=== 쇼츠 7편 TTS 생성 ==="

edge-tts --voice "$VOICE" --write-media "$SHORTS_DIR/teaser_01.mp3" --text \
"나 예쁘지? 답이 정해진 질문. 대답 안 하면 분위기 이상해지고, 해주자니 내 진심이 아닌데. 이 불편함의 정체, 심리학에 답이 있습니다. 수요일 본편에서 전체 분석."

edge-tts --voice "$VOICE" --write-media "$SHORTS_DIR/teaser_02.mp3" --text \
"많은 사람들이 이런 상황을 가스라이팅이라고 부르는데, 정확하지 않습니다. 그러면 뭐냐고요? 심리학에서는 이걸 강요된 동의라고 합니다. 내일 전체 분석 영상 공개."

edge-tts --voice "$VOICE" --write-media "$SHORTS_DIR/deep_01.mp3" --text \
"수빈이 콩이한테도 나 예쁘지? 하고 물어봅니다. 아기는 동의도 거부도 할 수 없어요. 심리학에서 이걸 확인 추구 행동이라고 합니다. 대답의 내용이 아니라, 대답을 받아내는 행위 자체가 목적인 거죠. 전체 분석은 프로필 영상에서."

edge-tts --voice "$VOICE" --write-media "$SHORTS_DIR/deep_02.mp3" --text \
"나는 칭찬 자판기가 아닌데. 진심이 궁금한 게 아니라, 나라는 사람이 아니라 나의 기능만 필요한 상황. 심리학에서 말하는 도구적 관계에 대한 거부감이에요. 진심이 궁금한 게 아니라, 기능만 필요한 상황에 대한 본능적 반발입니다."

edge-tts --voice "$VOICE" --write-media "$SHORTS_DIR/deep_03.mp3" --text \
"예쁘다고 해줄까, 말까? 솔직한 답을 하면 관계가 불편해지고, 원하는 답을 해주면 자기 진정성이 훼손됩니다. 인지부조화를 해소하는 방법은 두 가지. 행동을 바꾸거나 신념을 바꾸거나. 대부분은 자기 스스로를 설득하는 쪽을 택합니다."

edge-tts --voice "$VOICE" --write-media "$SHORTS_DIR/deep_04.mp3" --text \
"어차피 또 물어볼 거잖아. 이런 경험이 쌓이면 저항 자체를 포기합니다. 매번 자기 진정성을 지불하고 관계의 평화를 사는 거래. 이게 쌓이면 관계 자체에 대한 피로감이 됩니다."

edge-tts --voice "$VOICE" --write-media "$SHORTS_DIR/deep_05.mp3" --text \
"칭찬의 소비자, 거부자, 공급자. 나 예쁘지? 라는 다섯 글자 안에 이 세 가지가 동시에 작동합니다. 다섯 글자 안에 이만큼의 심리적 구조가 숨어 있었습니다. 구독하면 다음 에피소드를 놓치지 않습니다."

echo ""
echo "=== 완료 ==="
echo "롱폼: $(ls -1 $LONGFORM_DIR/*.mp3 2>/dev/null | wc -l)개"
echo "쇼츠: $(ls -1 $SHORTS_DIR/*.mp3 2>/dev/null | wc -l)개"
