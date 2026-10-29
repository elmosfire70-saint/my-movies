# 워크플로 정적 성능 감사

2026-10-29. 실제 소스와 설치된 ComfyUI 구현을 확인했다. 아래 항목의 속도 개선량은 측정하지 않았으며 운영 워크플로를 수정하지 않았다.

## 확인된 개선 후보

1. `past-present-comfy/build_meeting_workflows.py`의 `CodexShotSettings.turbo` 출력은 LoRA와 스케줄러에 연결되지 않는다. `strength_model=1.0`, `steps=4`로 고정되어 있다. CPU 그래프에서 turbo=False로 바꾼 후에도 두 상수가 유지되는 것을 assertion으로 확인했다. 기본 4단계 실행은 정상이나 스위치만 바꾼 품질 비교는 무효다. 다음 수정에서는 설정 출력 연결과 회귀 테스트를 먼저 보강해야 한다.
2. `custom_nodes/codex_video_tools/__init__.py`의 `H3Inputs.run`은 첫 프레임을 참조 이미지와 첫 프레임 가이드로 각각 VAE 인코딩한다. 설치된 `comfy_extras/nodes_minimax_h3.py`의 ReferenceToVideo와 AddGuide 호출에서 확인했다. 두 조건은 역할이 다르므로 하나를 삭제해서는 안 된다. 동일 전처리일 때 latent를 재사용하는 방안은 후보지만 일반 크기·크롭 조건 검증이 필요하다.
3. 현재 사용자 노드는 audio_vae를 필수 입력으로 요구하지만 설치된 native ReferenceToVideo는 오디오 참조가 없는 경우 audio_vae.encode를 호출하지 않는다. 약 605MB 오디오 VAE 파일 로더를 선택 입력으로 바꾸는 후보가 있다. 파일 크기는 RAM 절감량이 아니며, 이 변경으로 H3 내부 음성 잠재의 연산까지 제거되지는 않는다. 따라서 README의 내부 처리에 항상 필요하다는 설명은 현 native 구현에 맞춰 추후 수정할 필요가 있다.
4. Qwen 인코더는 CFG 1에서도 빈 negative를 인코딩한다. CFG 1 샘플러는 negative 추론을 생략한다. 표준 노드 수정이 필요하므로 전체 인코딩 병목이 충분히 클 때만 별도 최적화를 검토한다.

## 이미 적용되어 있는 최적화

- Qwen INT8 모델·텍스트 인코더, 참조 KV 캐시(auto), CFG 1, 참조 최대변 1024, 타일 VAE 디코딩.
- H3 INT8·양자화 텍스트 인코더·Turbo 4단계·BasicGuider, 무음 출력.
- H3의 일반 VAEDecode도 설치된 VAE 구현에서 공간 타일과 시간 청크 스트리밍을 사용한다. 단순히 VAEDecodeTiled로 바꾸는 것은 입증된 개선이 아니다.
- Qwen 참조 KV 캐시는 한 샘플링 실행 안에서 사용한다. ComfyUI 노드 결과 캐시와 구분해야 한다.
- 승인된 합성 사진으로 `02_Past_Present_Video`만 재실행하면 이미지 합성 단계를 건너뛸 수 있다. 통합 워크플로도 입력이 같고 결과 캐시가 유지되면 재사용한다.
- 5초 입력은 H3의 프레임 규칙으로 124프레임, 실제 5.1667초가 된다.

## 검증 범위

실행 중인 ComfyUI 0.43.1을 대상으로 영상 워크플로 테스트 3개, 캐릭터 시트 테스트 5개, 공통 노드 테스트 7개가 통과했다. 이 테스트들은 참조 연결·스키마·무음 경로 등 기능 검증이며 사진 동일성이나 성능 우위를 증명하지 않는다. 기존 테스트에 Turbo 스위치 소비자 연결 검사가 없다는 점도 확인했다.
