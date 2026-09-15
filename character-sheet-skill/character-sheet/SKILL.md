---
name: character-sheet
description: Create and revise consistent single-character reference sheets with built-in ImageGen from photos or text. Supports turnaround, expressions, poses, and outfit variants, six visual styles, individual panel revisions, and versioned local PNG exports. Use for character sheets or 캐릭터 시트; not video generation or a standalone web app.
---

# 캐릭터 시트

## 생성 규칙

내장 `image_gen`만 사용한다. API 키, ComfyUI, 별도 생성 스크립트는 필요 없다. 도구가 없거나 실패하면 상태를 알리고 멈춘다. 외부 API로 자동 전환하지 않는다. 정확한 모델·시드·해상도·장당 비용을 보장하거나 무료 무제한이라고 설명하지 않는다.

1. 한 명의 캐릭터를 대상으로 유형, 스타일, 항목 설명과 참조 역할을 정한다. 충분한 요청에는 질문하지 않는다. 기본값 및 프롬프트는 [references/prompts.md](references/prompts.md)를 읽는다.
2. 로컬 참조는 `view_image`로 먼저 확인한다. 각 사진을 대표 외형, 얼굴, 측면, 후면 등의 역할로 표시한다. 서로 다른 인물이 섞였거나 외형이 상충하면 기준을 물어본다.
3. 텍스트 입력 또는 스타일 변경은 기준 이미지를 먼저 생성하여 보여주고 사용자 선택을 기다린다. 기준 이미지는 프로젝트에 복사하고 `baseline.json`에 설명·스타일·참조 경로·실제 크기·선택 상태를 기록한다. 사용자가 고르기 전 파생 시트를 만들지 않는다. 제공 사진이 명확한 기준이면 추가 승인을 요구하지 않는다.
4. 생성 전에 구성·참조·스타일을 짧게 알린다. 각 칸을 별도 호출로 생성한다. 모든 호출에 동일한 선택 기준 이미지, 관련 참조, 유지할 얼굴·헤어·체형·의상 특징을 명시한다. 앞 칸의 생성물만 이어 참조하지 않는다.
5. 로컬 경로가 모두 있으면 `referenced_image_paths`를 사용한다. 첨부 이미지 경로가 없으면 필요한 이미지를 포함하는 최소 `num_last_images_to_include`를 사용한다(최대 5). 둘을 함께 쓰지 않는다. 모든 필수 참조를 포함할 수 없으면 재첨부를 요청한다. 새 이미지에는 둘 다 생략한다.
6. 도구 반환 이미지는 `generatedImage(result)`로 표시한다. 프로젝트 출력은 반환된 실제 파일 위치에서 복사한다. 파일 경로를 추측하지 않는다. 파일을 확보할 수 없으면 저장 검증이 막혔다고 보고한다.
7. 각 결과를 보고 잘림, 항목 누락, 명백한 외형·의상 불일치를 확인한다. 문제 칸에 한해 자동 재생성은 1회까지 허용한다. 이후 남은 문제를 표시한다. 사용자 요청에 따른 후속 수정은 별도 작업이다. 동일성의 완전 보장을 주장하지 않는다.

## 수정과 저장

- 기본·표정·포즈는 인물과 의상 유지, 의상 변형은 인물 유지. 흰색 배경, 고른 조명, 전신은 신발까지 포함한다. 후면 참조가 없으면 추정임을 기록한다.
- 다음 대화에서는 기존 `manifest.json`과 기준 이미지를 실제로 읽는다. 수정 대상이 불분명하면 확인한다. 수정 대상 및 기준 이미지를 함께 참조하여 요청된 칸만 새로 생성한다.
- 합성은 아래 Python 도구만 사용한다. 이 스킬에서 Python은 PNG 검증, 복사, 비율 유지 리사이즈, 흰 여백 배치와 기록에 한정한다. 인물 내용 편집은 ImageGen으로 한다.
- 기본 저장 루트는 `E:/Codex/movies/output/character-sheets`. 사용자가 지정하면 그 위치를 따른다. 캐릭터별 `v001`, `v002`처럼 새 폴더를 선택한다. 기존 버전은 절대 덮어쓰지 않는다.
- 재생성 시 새 명세에 이전 버전의 변경하지 않은 패널 경로를 그대로 넣고 수정된 패널만 새 경로로 지정한다. `parent_version`에 이전 버전을 기록한다. 스크립트가 모든 선택 패널을 새 버전에 복사하므로 이전 파일과 독립적으로 다시 열 수 있다.

## 내보내기 인터페이스

Pillow가 있는 Python으로 실행한다. 사용 가능한 런타임은 workspace dependency 도구 또는 기존 프로젝트 설정으로 찾는다.

```text
python scripts/assemble_sheet.py request.json --output E:/Codex/movies/output/character-sheets/CHAR_001/v001
```

명세의 상대 경로는 명세 파일 폴더를 기준으로 한다. `type`은 `basic`, `expressions`, `poses`, `outfits` 중 하나다. 기본/의상 4칸, 표정/포즈 6칸을 유지하고 항목 설명은 수정 가능하다.

```json
{
  "character": "CHAR_001",
  "type": "basic",
  "style": "실사",
  "parent_version": null,
  "notes": "후면은 참조 없이 추정",
  "references": [{"role": "선택된 기준 캐릭터", "path": "baseline.png"}],
  "panels": [
    {"label": "얼굴", "path": "face.png", "prompt": "실제 생성 지시", "review": "확인 결과"},
    {"label": "정면", "path": "front.png", "prompt": "실제 생성 지시", "review": "확인 결과"},
    {"label": "왼쪽 측면", "path": "side.png", "prompt": "실제 생성 지시", "review": "확인 결과"},
    {"label": "후면", "path": "rear.png", "prompt": "실제 생성 지시", "review": "확인 결과"}
  ]
}
```

출력은 `sheet.png`, `panels/`, `references/`, `manifest.json`이다. 합성 이미지에는 텍스트를 넣지 않고 항목 이름은 기록에 남긴다. 출력 후 합성 PNG를 열어 잘림과 순서를 확인하고 manifest와 패널도 다시 연다. 생성·기술 검증·사용자 선택 상태를 구분해서 보고한다. 링크와 사용 예를 짧게 제공한다.
