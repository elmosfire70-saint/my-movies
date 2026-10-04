# 작업 맥락
사용자는 두 모델의 업데이트 확인과 가능한 업데이트 실행을 요청했다. ComfyUI 전체 업그레이드는 이번 모델 업데이트 범위에 포함하지 않는다.

검증 명령은 python model-update-check/check_models.py. ALL_MATCH 8로 통과. Qwen 3개와 H3 5개 구성 파일이 최신 main의 SHA256과 일치한다. 최신 저장소 revision과 각 해시는 verification.json에 기록했다. 기본 샌드박스 네트워크 연결 실패 후 승인된 네트워크 실행으로 검증했다. 모델 파일과 워크플로 변경 및 생성 재실행은 하지 않았다. H3 FL2V용 v1.0 LoRA는 현재 Ref2VA용 v0.1의 교체품으로 취급하지 않는다.
