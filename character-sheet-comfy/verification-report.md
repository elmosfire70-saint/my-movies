# 검증 보고

## 구현 및 설치

- UI 워크플로 3개와 대응 API JSON 3개 생성.
- 설치 위치. `E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\user\default\workflows\Character_Sheet_Local`.
- 추가 커스텀 노드·유료 API 없음. 기존 영상 파일과 워크플로 수정 없음.

## 실행한 검증

작업 위치는 `E:\Codex\movies`이며 Python은 `E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe`다.

1. `python character-sheet-comfy/build_workflows.py` 통과. 15개·37개·12개 노드 그래프 생성.
2. `python -m unittest discover -s character-sheet-comfy -p 'test_*.py' -v` 통과. 3개 테스트. 실행 중 서버의 입력 스키마·필수 필드·enum·범위·연결 타입·비순환성·UI 링크 양방향 연결·참조 역할·고정 seed·비율 보존 설정 검사.
3. `python character-sheet-comfy/verify_composition.py` 통과. 실제 ComfyUI 서버 업로드 및 큐 실행. 서로 다른 종횡비의 4색 PNG를 2304×1152로 합성하고 각 칸 중앙 픽셀 색상·순서 확인. 상세 job ID 및 출력 파일은 `composition-report.json`.

## 미검증 및 진행 중

- `install_models.py`로 공식 모델 다운로드를 시작했다. 다운로드 완료 및 SHA256 통과 전에는 모델 설치 완료로 간주하지 않는다.
- 모델 가중치를 사용하는 인물 생성, 얼굴 동일성·의상 일치·90도 측면·후면·잘림의 육안 평가는 아직 실행하지 않았다.
- VRAM 최대 사용량, 32GB RAM 환경의 안정성, 장당 시간은 측정하지 않았다.
- UI JSON의 구조를 검사했으나 브라우저 캔버스에서의 직접 조작·육안 검사는 하지 않았다.
- 샘플 이미지의 디자인을 위한 레이아웃을 구현했으며 동일한 생성 품질을 입증한 것은 아니다.

## 모델 준비 후 실 생성 확인 절차

얼굴·의상 입력 선택 → 정면 1장 생성 → 얼굴·의상·신발·잘림 확인 → 선택한 정면으로 2단계 실행 → 시점과 외형 일치 육안 검사 → 수정이 필요한 칸만 재생성 → 3단계에서 선택 결과 재합성. 속도 측정 시 기존 큐 및 다른 GPU 작업 유무도 함께 기록한다.
