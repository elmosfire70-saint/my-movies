# 현재 프로젝트 성능 검증과 모델 추천

검증일은 2026-10-29이다. 대상은 과거·현재 사진 합성 및 무음 만남 영상이며 캐릭터 시트와 공통 노드의 기존 테스트도 실행했다. 운영 워크플로·모델은 교체하지 않았다.

## 결론

현재 구성은 정상 생성되지만 RTX 3060 12GB·RAM 32GB의 메모리 여유가 작다. 총 시간의 약 54%가 H3 샘플링 노드에 걸리므로 영상 단계가 주 개선 대상이다. Qwen 2.1 Turbo 8단계는 적은 변경으로 시험할 이미지 가속 후보이며, H3 W6A8는 영상 메모리 부담 완화 후보다. 어느 후보도 이 PC에서 비교 실행하지 않았으므로 기존 모델보다 품질·속도가 높다고 확정하지 않는다.

## 현재 환경과 실측

- RTX 3060 12288MiB, RAM 약 32GiB, 드라이버 616.56.
- 실행 시 ComfyUI 0.43.1, 프런트엔드 1.57.4, PyTorch 2.12.1+cu130.
- Qwen Image 2.1 INT8 / 25 steps / CFG 1 / 참조 KV 캐시 auto.
- H3 Ref2VA pruned INT8 / Turbo 4-step v0.1 / 576×1024 / 124프레임 / 24fps.
- 시작 큐 비어 있음, execution_cached 노드 없음. OS 파일 캐시까지 비운 엄격한 cold-start 측정은 아니다. 입력 한 쌍·배경 OFF·고정 seed 한 번의 측정이다.

| 측정 구간 | 시간 |
|---|---:|
| 전체 성공 완료 | 437.511초, 약 7분 18초 |
| 시작부터 합성 PNG 저장까지 | 약 93.85초 |
| Qwen 텍스트·참조 인코딩 | 34.72초 |
| Qwen 샘플링 노드 | 45.24초 |
| Qwen 디코딩 | 4.52초 |
| H3 입력 준비·인코딩 | 43.42초 |
| H3 샘플링 노드 | 238.11초 |
| H3 영상 디코딩 | 57.43초 |
| 영상 저장 | 4.70초 |

구간 시간은 websocket 노드 시작 이벤트 간 차이다. 모델 전송·LoRA 준비 등 해당 호출 안에서 수행되는 비용을 포함하므로 순수 GPU 계산 시간은 아니다. 상세 항목은 부분 합이며 로더·이미지 읽기 등 나머지 시간이 있다.

약 5초 간격 82회 관측에서 GPU 전체 사용 메모리 최대 11667MiB(약 11.39GiB), 시스템 RAM 전체 사용 최대 약 30.65GiB, 남은 RAM 최소 약 1.31GiB였다. ComfyUI 단독 프로세스 메모리나 정확한 순간 최대치는 아니며 다른 앱도 포함한다. 작업은 OOM 없이 성공했다. 현재 H3 모델 파일은 20.97GB, 텍스트 인코더는 15.69GB로 각각 GPU 메모리와 별개이며, 현재 실행 로그의 동적 메모리 로딩을 확인했다. 파일 크기만으로 VRAM 요구량을 계산하지 않는다.

## 출력 검증

작업 ID는 `a071ec12-310f-46cf-86c8-29f89f8339e2`다. PyAV로 영상 전체를 디코딩해 576×1024, 24fps, 124프레임, 5.1667초, 오디오 스트림 0개를 확인했다. 합성 PNG 및 영상 1·62·124번째 프레임을 육안 확인했다. 두 인물과 배경·의상이 유지되고 서로 바라본 뒤 미소 짓는 구도가 보인다. 프레임마다 얼굴과 베레모 주름·휘장 등의 세부는 달라진다. 모든 프레임의 시각 품질이나 얼굴 일치 점수를 평가한 것은 아니다.

측정 폴더는 `output/performance-review/90bf391c-6aaf-482e-8425-ae889b7ffe95`이며 request, job, history, events, memory, metrics와 대표 프레임을 보존했다. 서버가 이후 재시작해 현재 history API에는 작업이 없지만 완료 시 저장한 원본 history와 영상 파일로 검증했다.

## 바로 활용할 개선점

1. 시작 합성 사진을 승인한 뒤 기존 `02_Past_Present_Video`로 영상만 반복 생성한다. 합성 단계를 다시 계산하는 실행에서는 이번 측정의 약 94초 구간을 건너뛸 수 있다. 통합 워크플로 캐시가 이미 살아 있으면 이 차이는 작아진다.
2. `turbo` UI 값은 실제 4단계 스케줄과 LoRA 강도에 연결되지 않았다. 기본 실행은 정상이나 ON/OFF 비교 전에 연결과 테스트를 보강해야 한다.
3. H3의 첫 프레임 VAE 중복 인코딩과 무음 경로의 불필요한 audio VAE 로드가 개선 후보이다. 절감량은 미측정이다. 무작정 참조 입력이나 가이드를 없애면 안 된다.
4. H3 일반 VAEDecode는 이미 내부 타일·시간 청크 처리가 있어 타일 노드로 바꾸는 것만으로 개선된다고 권하지 않는다. 이미지 캐시 역시 이미 적용됐다.

정적 근거와 한계는 [워크플로 감사](workflow-audit.md)에 기록했다.

## 추천할 비교 후보

| 우선 목적 | 후보 | 판단 |
|---|---|---|
| 이미지 합성 가속 | Qwen Image 2.1 Turbo 8-step LoRA | 기존 베이스·인코더·VAE를 재사용하는 첫 비교 후보. 25→8단계이지만 전체 시간 3배 개선이라는 뜻은 아님. |
| H3 메모리 부담 완화 | H3 Ref2VA pruned W6A8 | 배포 파일 약 21→16GB. 현재 로그에 w6a8_int8 native op가 보이지만 실제 해당 파일 추론은 미검증. 속도·얼굴 보존 A/B 필요. |
| H3 화질 비교 | Ref2V Turbo 4-step v1.0 768p | 현재 v0.1보다 새로운 배포 파일. 정확한 권장 스케줄과 저해상도 적용 조건을 확인한 뒤 별도 비교해야 함. |
| 다른 영상 모델 | Wan2.2 TI2V-5B | ComfyUI 공식 8GB+오프로딩 안내로 12GB에 맞는 후보. 현재 H3 4단계보다 빠르거나 얼굴을 잘 유지한다고 입증되지는 않음. |

Qwen Turbo는 [Comfy 공식 안내](https://github.com/Comfy-Org/docs/blob/main/tutorials/image/qwen/qwen-image-2-1.mdx), H3 경량판은 [Comfy-Org 배포 파일](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/main/diffusion_models), 새 Turbo는 [LightX2V 배포 파일](https://huggingface.co/lightx2v/Minimax-h3-Turbo/tree/main), Wan은 [Comfy 공식 실행 조건](https://docs.comfy.org/tutorials/video/wan/wan2_2)을 확인했다. 최신 FLUX·Fibo·LTX 후보와 요구사항은 [모델 조사](model-research.md)에 별도로 기록했다.

10월 4일의 동일 파일 해시 확인은 당시 설치 파일이 배포본과 같다는 뜻이었다. 10월 29일 현재 다른 경량판·가속판·새 LoRA가 없다는 뜻으로 확대해서는 안 된다. 이번에는 후보를 조사했고 대안 모델 다운로드나 변경은 하지 않았다.

## 실행한 검증 명령

아래 `python`은 `E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe`를 사용했다. 시스템 python 별칭은 실행 오류가 나서 사용하지 않았다. 로컬 API 연결은 sandbox 밖에서 승인된 실행으로 수행했다.

```text
python -m unittest discover -s past-present-comfy -p 'test_*.py' -v    # 3 passed
python -m unittest discover -s character-sheet-comfy -p 'test_*.py' -v # 5 passed
python -m unittest test_custom_nodes -v                              # 7 passed
python performance-review/benchmark.py                              # history success
python performance-review/verify_results.py                         # assertions passed
```

단일 실행이므로 장기 안정성·평균 처리량·다른 모델 대비 우위는 아직 검증하지 않았다. 과거 영상 단독 473.904초 및 예전 통합 435.296초 기록은 워크플로·캐시·소프트웨어 조건이 달라 직접 성능 향상률로 비교하지 않았다.
