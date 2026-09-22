# 로컬 얼굴·의상 턴어라운드 생성기

얼굴 클로즈업과 의상 참고 사진 두 장을 입력한다. Qwen Image Edit 2511이 정면 기준 캐릭터를 만들고, 선택된 정면을 기준으로 측면·후면·얼굴 클로즈업을 만든다. 결과는 **정면 | 측면 | 후면 | 큰 얼굴** 순서의 가로 시트와 개별 PNG다. 유료 API·외부 이미지 전송·별도 커스텀 노드를 사용하지 않는다.

## 설치

실행 중인 ComfyUI에 기본 Qwen Edit Plus, CFGNorm, ImageStitch 노드가 있어야 한다. 현재 PC에는 있다. 모델 3개는 약 30.2GB다. 아래 설치기는 공식 파일을 이어받고 SHA256을 확인한 후 최종 파일명으로 바꾼다. 기존 모델은 덮어쓰지 않는다.

```powershell
& 'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe' E:\Codex\movies\character-sheet-comfy\install_models.py 'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI'
```

모델 다운로드 후 ComfyUI에서 새로고침한다. 선택 목록에 모델이 없으면 작업이 없는 상태에서 ComfyUI를 재시작한다. 기존 서버의 실행 설정을 강제로 변경하지 않는다. 12GB VRAM에서는 기본 스마트 메모리 관리를 사용하고, 메모리 부족 시 ComfyUI 실행 옵션에 `--lowvram`을 적용한다. `--highvram`은 사용하지 않는다. RAM 32GB에서도 다른 대용량 작업은 종료하는 것이 좋다. 페이지 파일 부족 시 메모리 오류가 날 수 있다.

## 1. 얼굴과 의상으로 정면 만들기

`workflows/01_Face_Outfit_Anchor.json`을 ComfyUI에 드래그한다.

1. **얼굴 클로즈업**에 선명한 정면 얼굴을 넣는다. 의상은 이 사진에서 가져오지 않는다.
2. **의상 참조**에 신발까지 보이는 한 명의 전신 사진을 넣는다. 얼굴은 무시한다. 여러 명이면 기본 프롬프트는 가운데 인물을 지정하지만 미리 해당 인물만 자르는 편이 명확하다.
3. `front · 지시문`에서 필요한 헤어스타일, 모자 위치, 의상 상세를 추가한다. 프롬프트는 영어로 기본 작성했지만 한국어 요구를 추가할 수 있다.
4. 실행 후 얼굴·의상·손·신발·잘림을 확인한다. 마음에 드는 정면 PNG를 저장한다. 얼굴이나 옷이 틀리면 이 단계에서 지시문 또는 seed를 바꿔 다시 만든다.

정면 기본 크기는 512×1152, 20 steps / CFG 4 / Euler / simple / flow shift 3.1이다. Lightning LoRA를 사용하지 않는 품질 우선 설정이다. 40 steps는 비교용으로 늘릴 수 있으나 무조건 더 좋은 결과를 보장하지 않는다.

## 2. 선택한 정면으로 시트 만들기

`workflows/02_Character_Turnaround.json`을 연다.

1. **선택한 정면 PNG**에 1단계 결과를 넣는다. ComfyUI 출력 파일은 노드 업로드 버튼으로 입력한다.
2. 나머지 두 LoadImage에 1단계에서 사용한 **같은 얼굴과 의상 원본**을 넣는다.
3. 실행하면 측면 512×1152, 후면 512×1152, 클로즈업 768×1152를 개별 생성·저장하고 정면과 합친다.
4. 기본 정면을 사용하면 시트는 2304×1152다. 모든 칸은 자르거나 늘이지 않고 연결한다. 출력 비율이 다른 정면을 넣으면 정면의 비율을 보존하므로 최종 폭도 달라진다.

SaveImage 기본 위치는 **ComfyUI/output/character-sheets/날짜/**다. 파일명에 자동 번호가 붙어 이전 결과를 보존하며 PNG에 워크플로와 프롬프트가 기록된다. `E:\Codex\movies\output`과는 다른 위치다. 입력 원본은 별도로 보관한다. 장기 작업은 얼굴·의상·선택된 정면·워크플로 JSON을 같은 캐릭터 폴더에 복사해 두는 것이 좋다.

## 한 칸만 수정하기

같은 세션에서 한 시점의 지시문 또는 seed만 수정하면 ComfyUI 캐시가 유효한 나머지 분기는 재사용한다. 캐시가 사라진 뒤에는 이를 보장하지 않는다.

확실히 한 칸만 생성하려면 2단계에서 해당 칸의 SaveImage만 남기고 **다른 SaveImage와 최종 시트 SaveImage를 Mute**한다. Bypass가 아닌 Mute다. 이렇게 하면 출력에 연결되지 않은 생성 분기는 실행되지 않는다. 기존 칸을 보존하고 `03_Assemble_Selected_Views.json`에 네 개의 선택 결과를 넣어 합친다. 3단계에는 생성 모델이 없어 재합성만 수행한다.

## 품질과 성능의 범위

- 첨부 예시의 배치를 구현했지만 결과 인물의 외형은 입력 사진으로 결정한다. 예시 사진을 자동으로 신원 참조로 사용하지 않는다.
- 모델이 각 시점을 새로 그리므로 얼굴, 체형, 옷의 작은 디테일과 인물 크기가 완전히 일치하지 않을 수 있다. 자동 합성이 인물 높이를 인식해 보정하지는 않는다.
- 후면에 보이지 않는 재봉선·무늬는 추정이다. 정확한 상품·유니폼 후면이 필요하면 후면 의상 사진으로 해당 분기의 image3 참조를 바꾼다.
- 신발이 없는 의상 사진은 모델이 신발을 추정한다. 손에 든 물건은 기본에서 제외한다.
- 12GB GPU에 모델 전체가 올라가지 않으므로 RAM 오프로딩이 발생한다. 속도 및 최고 화질 순위는 보장하지 않는다. 먼저 기준 정면 한 장으로 실행 시간을 확인한다.
- 사진 입력을 바꾸면 정면부터 다시 만든다. 고해상도 출력이 필요하면 각 EmptySD3LatentImage의 크기를 같은 배율로 늘리되 메모리 부담도 증가한다. 3단계 합성 높이도 함께 조정한다.

## 개발 검증

```powershell
& 'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe' character-sheet-comfy/build_workflows.py
& 'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe' -m unittest discover -s character-sheet-comfy -p 'test_*.py' -v
```

UI JSON은 화면에서 사용하며 `.api.json`은 자동화 제출용이다. 예시 파일명은 입력 사진을 선택하기 전에는 존재하지 않으므로 그대로 큐에 제출하지 않는다.

## 설계 근거

- [Carat 설명](https://carat.im/blog/character-sheet-generator)의 대표 전신 → 시트 흐름을 적용했다.
- [ComfyUI 공식 Qwen Edit 2511 안내](https://blog.comfy.org/p/qwen-image-edit-2511-and-qwen-image)와 [공식 템플릿](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_image_edit_2511.json)의 참조 인코딩·flow shift·CFG 정규화 설정을 확인했다.
- [공식 배포 모델](https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI)은 Apache 2.0으로 표시되어 있다. 창작물 이용 시 입력 사진과 의상 디자인에 대한 권리는 별도로 확인해야 한다.
