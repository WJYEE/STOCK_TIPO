# 이미지 에셋

| 용도 | 경로 | 비고 |
|---|---|---|
| 표지 | `assets/cover.png` | 사용자 제공 고양이 원본(변경 없음) |
| 질문 장면 12장 | `assets/scenes/q01_*.png`~`q12_*.png` | 약 354×109(3.2:1), 경로는 `data/questions.json`의 `scene` |
| 결과 6종 | `assets/results/{id}.png` | 177×153, 하단에 잘린 라벨 띠를 제거함. 경로는 `data/characters.json`의 `image` |
| 캐릭터 단독 | `assets/characters/{id}.png` | 현재 미사용 |
| 기타 | `assets/ui/`, `reference_sheet.png` | 참고용(미사용) |

- 캐릭터 ID: hamster, fox, cat, rabbit, bear, penguin
- 질문·선택지·결과 설명은 이미지가 아닌 Streamlit 텍스트로 표시. 일부 이미지에 구워진 글자(CAFE, SALE 등)는 장식 요소.
- 이미지가 없거나 열리지 않으면 이모지 플레이스홀더로 대체.
- 해상도가 낮아(원본 시트 크롭) 큰 화면에서 약간 흐릴 수 있음 → 고해상도 원본이 있으면 같은 파일명으로 교체(앱 수정 불필요).
