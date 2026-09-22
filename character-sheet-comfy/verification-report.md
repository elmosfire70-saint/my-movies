# 검증 보고

## 현재 배포 모델. Qwen Image 2.1

- 생성 모델·텍스트 인코더·VAE 세 파일 다운로드 및 SHA256 검증 통과. 합계 17,283,091,112바이트.
- 2511 FP8 Mixed 생성 모델 파일 삭제 및 부재 확인. 이전 인코더·VAE는 남겨 두었다.
- `python character-sheet-comfy/build_workflows.py` 성공. 2.1용 14개·32개·12개 노드 워크플로 생성.
- `python -m unittest discover -s character-sheet-comfy -p 'test_*.py' -v` 4개 통과. 2.1 전용 잠재공간 출력 연결, 참조 역할과 캔버스, CFG 1 / 25 steps, UI 연결 검증 포함.
- 설치 폴더의 세 UI JSON과 소스 파일 SHA256 일치 확인.
- `python output/character-sheets/QWEN21_VALIDATION/run.py submit`와 `status` 실행 성공. 정면 512×1152 / 25단계 / CFG 1 생성·타일 디코딩·PNG 저장 완료. 서버 이력의 시작·완료 차이 **146.066초**. prompt_id `f8111c90-07a3-4bea-90bb-5e1ca115e59e`.
- `output/character-sheets/QWEN21_VALIDATION/front-13-0.png`를 열어 얼굴 참조 반영, 군복·스카프·베레모, 두 신발을 포함한 전신, 회색 배경 확인. 원본과 완벽한 얼굴·패치 동일성을 주장하지 않는다.
- 실제 생성 RGBA의 알파 범위 244~255를 확인해 최종 그래프에 표준 RGB 분리 노드를 추가했다. 최종 그래프를 서버에 재제출하여 생성 노드 1~12 캐시 재사용 및 RGB 저장 성공 확인. prompt_id `b2615df9-4243-42b6-928b-ef14527b93aa`. `front-rgb.png`가 RGB / 512×1152이고 기존 생성 이미지의 RGB 픽셀과 정확히 같은지 Pillow assertion으로 검사해 통과했다. 변경 후 단위 테스트 4개 및 설치 파일 해시 일치를 다시 확인했다.
- 2.1의 측면·후면·클로즈업 전체 실 생성은 아직 미검증이다. 이전 2511 정면 548초와 설정이 다르므로 146초와의 차이를 모델 자체 속도 향상 배율로 단정하지 않는다.

아래는 교체 전 2511 모델의 검증 기록이다.

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

- `install_models.py` 정상 종료. 세 파일 크기 및 SHA256 검증 통과 로그를 확인했다. 실행 중 서버가 모델을 인식한다.
- `python output/character-sheets/COMFY_VALIDATION/run_validation.py anchor` 실행 성공. 실제 기본값 20 steps / CFG 4 / 512×1152를 사용했다. 제출·완료 시각 차이 547.998초. prompt_id `9b066a7a-0616-4dca-8bfb-27368d445010`.
- `python output/character-sheets/COMFY_VALIDATION/run_validation.py status anchor`로 이력과 PNG 회수. 얼굴·올리브 군복·붉은 스카프·낮은 베레모 반영, 전신과 두 신발 잘림 없음 확인. 얼굴과 패치 세부 형태는 원본과 차이가 있으므로 동일성 보장으로 해석하지 않는다.
- 실행 중 관측 RAM 약 29.7GiB, VRAM 약 10.9GB. 최대 사용량은 미측정이다. 정면 단일 실행은 메모리 오류 없이 완료했으나 장기 안정성 검증은 아니다.
- ComfyUI 브라우저에서 설치 폴더와 세 워크플로 목록, 정면 워크플로 로딩을 확인했다. 사진 미선택 템플릿에는 두 LoadImage 오류가 표시되며 사진 선택이 필요하다. 누락된 모델·노드 오류와 구분했다.
- 측면·후면·클로즈업 생성 및 최종 시트 육안 검증은 진행 중이다.
- 샘플 이미지의 디자인을 위한 레이아웃을 구현했으며 동일한 생성 품질을 입증한 것은 아니다.

## 모델 준비 후 실 생성 확인 절차

얼굴·의상 입력 선택 → 정면 1장 생성 → 얼굴·의상·신발·잘림 확인 → 선택한 정면으로 2단계 실행 → 시점과 외형 일치 육안 검사 → 수정이 필요한 칸만 재생성 → 3단계에서 선택 결과 재합성. 속도 측정 시 기존 큐 및 다른 GPU 작업 유무도 함께 기록한다.
