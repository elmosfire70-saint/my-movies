# 영상 모델 변경의 비교 근거

확인일은 2026-10-29이다. 설치·모델 교체·생성 실험은 수행하지 않았으며, 아래 수치는 공개 제작자 및 실험자 기록을 읽어 정리했다. 현재 PC의 기준값은 상위 작업에서 전달받은 측정값이다.

## 판단

**현재 H3 Ref2VA pruned INT8 + Ref2V Turbo 4-step v0.1을 유지한다.** W6A8, Ref2V 4-step v1.0, Wan2.2 TI2V-5B를 기본값으로 바꿀 만큼 조건이 일치하는 속도·품질 비교를 이번 조사 범위에서 찾지 못했다. 이는 모든 공개 벤치마크가 없다는 뜻이 아니다.

기준 PC는 RTX 3060 12GB / RAM 32GB, 출력은 576×1024 / 124프레임 / 약 5.166초이다. 총 437.511초, Qwen 93.85초, H3 입력 43.42초, sampler 238.11초, decode 57.43초, save 4.70초이며, VRAM 관측값 11,667MiB 및 시스템 전체 RAM 30.65GiB이다. 마지막 RAM 값은 H3 프로세스만의 메모리가 아니다.

| 후보 | 확인한 객관적 근거 | 현재 적용 판단 |
|---|---|---|
| W6A8 | 다른 H3 파생 모델에서 동일 seed 4개로 INT8와 W6A8의 BF16 대비 PSNR을 측정한 자료가 있다. 현재 checkpoint의 RTX 3060 통제 비교는 찾지 못했다. | 기본값 교체 보류. 파일 크기 감소만으로 속도 향상을 계산하지 않는다. |
| Ref2V 4-step v1.0 | 배포자가 신규 출시를 공지했다. v0.1과 같은 입력·GPU·seed를 사용한 정량 품질 및 시간 비교는 해당 발표/공식 저장소에서 확인하지 못했다. | 기본값 교체 보류. 둘 다 4-step이라는 사실만으로 속도 향상을 기대하지 않는다. |
| Wan2.2 TI2V-5B | 공식 자료는 720p/24fps T2V·I2V 지원과 24GB급 공식 실행 경로를 설명한다. 현재 H3 Ref2VA와 일치하는 3060/32GB 비교는 찾지 못했다. | H3 대체로 채택하지 않는다. 별도 영상 전용 후보로만 남긴다. |

## 원자료에서 실제로 측정한 것

### 1. W6A8와 INT8의 정량 차이. 현재 checkpoint가 아닌 파생 모델이다.

[WAS의 Singularity v2 pruned 제작자 비교](https://huggingface.co/WAS/Minimax-h3_Singularity_v2_pruned)는 1344×768, 124프레임, 24fps, Euler/simple, 6 steps, DMAD 4-step LoRA 0.7, PyTorch attention 조건이다. seed 42~45의 4개 결과를 같은 seed의 BF16 영상과 프레임별 비교했다.

| 형식 | seed 42 | seed 43 | seed 44 | seed 45 | 평균 PSNR |
|---|---:|---:|---:|---:|---:|
| pruned INT8 ConvRot r2 | 23.3 | 24.9 | 28.2 | 28.0 | 26.1dB |
| pruned W6A8 r2 | 23.5 | 24.2 | 24.3 | 25.8 | 24.4dB |

공개 페이지에 GPU, 생성시간, 다수 프롬프트 표본 수는 명시되지 않았다. 4 seed를 4개의 독립적인 장면 평가로 취급할 수 없다. 이 결과는 해당 파생 모델에서 INT8가 평균적으로 BF16 픽셀에 더 가까웠다는 근거이며, 현재 Comfy-Org Ref2VA 품질 점수나 인간 선호도, 얼굴 보존율, 움직임 자연스러움의 점수가 아니다. 1.7dB 차이를 품질 저하율로 환산하지 않는다.

### 2. RTX 3060에서 H3가 실제로 실행된 시간. RAM과 경로가 다르다.

[Ajay의 실행 기록](https://github.com/Ajay9o9/runs-on-a-3060/blob/main/video/minimax-h3.md)은 RTX 3060 12GB, **RAM 64GB**, Ubuntu, ComfyUI 0.31.0, FL2VA pruned INT8 ConvRot 및 Larry Turbo 4-step LoRA를 사용한다. 출력은 864×480 / 243프레임 / 24fps / 10.125초와 음성이다. 단일 기준 실행은 407초, 다른 장면 5클립 배치의 평균은 약 370초이다. 이는 동일 조건의 반복 5회가 아니다. 기록은 32GB RAM을 시험하지 않았다고 명시한다. 현재 Ref2VA 437.511초 대비 몇 % 빠르다는 결론은 낼 수 없다.

### 3. Sunwood의 3060 실행 기록. 캐시·해상도·스텝 차이가 크다.

[GPU baseline 기록](https://github.com/Sunwood-ai-labs/minimax-h3-experiment-lab/blob/main/experiments/01-baseline/gpu-baseline/README.md)은 3060에서 864×480 / 124프레임 / 25 steps를 cold 425.526초, warm 270.289초로 기록한다. 1280×704에서는 T2V 961.655초, I2V 800.840초이다. Dynamic VRAM, CPU offload, SageAttention, EasyCache를 함께 사용했다. 각 행은 개별 실행이며 평균·분산이 없다. 조건이 여러 개 달라 현재 4-step Ref2VA와 직접 비교하거나 특정 최적화의 효과를 분리할 수 없다. 검은 프레임 없음 및 MP4 유효성은 품질 동등성을 의미하지 않는다.

### 4. Ref2VA 6-step 대 20-step의 수치. 새 Ref4 v1.0 비교가 아니다.

[Sunwood 6 대 20 steps 기록](https://github.com/Sunwood-ai-labs/minimax-h3-experiment-lab/blob/main/experiments/03-reference-conditioned/ref2va-6v20/README.md)은 RTX 4090, 약 128GiB 호스트 RAM, 1344×768 / 158프레임, pruned INT8 Ref2VA, FL2V LightX2V 4-step v0.1 LoRA 0.8, er_sde/simple, EasyCache 조건이다. T2V·I2V 각각 한 seed에서 두 스텝 수를 비교했다.

| 모드 | 6 steps Comfy 실행 | 20 steps Comfy 실행 | SSIM | PSNR |
|---|---:|---:|---:|---:|
| T2V | 459.42초 | 659초 | 0.683275 | 14.406153dB |
| I2V | 294.42초 | 691초 | 0.684799 | 14.455215dB |

이는 공식 Ref2V 4-step v0.1 대 v1.0 비교가 아니다. FL2V 이름의 LoRA를 Ref2VA에 쓴 이 실험을 권장 조합으로 승격하지 않는다. 원작성자도 SSIM/PSNR이 동일 화질을 입증하지 않는다고 설명한다.

### 5. 새 Ref2V 4-step v1.0의 공식 발표 범위.

[LightX2V의 신규 LoRA 발표](https://huggingface.co/lightx2v/Minimax-h3-Turbo/discussions/57)는 Ref2V 4-step v1.0과 8-step v1.1의 배포를 확인해 준다. **video shift 6 권고는 FL2V에만 해당한다고 명시**하므로 Ref2V에 그대로 옮기면 안 된다. 발표에 v0.1 대비 통제 점수나 표본 수가 없다. [공식 GitHub 사양표](https://github.com/ModelTC/Minimax-H3-Turbo)는 조사 시점에도 Ref2VA 4-step v0.1과 shift 12/3을 기술하므로, 신규 발표와 기존 문서의 버전 차이도 유의해야 한다. 댓글의 호평·실패담은 통제 비교로 집계하지 않았다.

### 6. Wan2.2 TI2V-5B의 공식 범위.

[Wan 공식 저장소](https://github.com/Wan-Video/Wan2.2#computational-efficiency-on-different-gpus)는 warm-up 후 여러 sample의 평균으로 GPU 성능을 보고하지만 정확한 n은 밝히지 않는다. 5B 단일 GPU 조건은 model offload, dtype 변환, T5 CPU이며 prompt extension은 제외한다. [공식 모델 카드](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B)는 720p/24fps T2V·I2V와 24GB급 GPU 공식 명령을 설명한다. 이는 ComfyUI 최적화 경로에서 12GB 실행이 불가능하다는 뜻도, 3060에서 현재 H3보다 빠르다는 뜻도 아니다. TI2V의 일반 T2V·첫 프레임 I2V 계약을 H3의 다중 참조와 네이티브 오디오 계약과 동일하게 취급하지 않는다.

## 근거 수준을 낮춰 별도 기록한 자료

[STB의 직접 사용 기록](https://note.com/stb_note/n/ndc9a486d4959)은 RTX 5090 32GB / RAM 64GB, 768×1152 / 141프레임 / 20 steps에서 INT8와 W6A8를 각각 약 120초로 보고한다. T2V 두 문제에서 BF16 대비 PSNR은 INT8 21.2·21.8, W6A8 14.9·17.0이다. 그러나 작성자는 AI 작성임과 원본 비교 스크립트 소실을 명시하고, 정확한 checkpoint·seed·반복 수가 충분하지 않다. 재현 가능한 검증을 대신할 수 없으므로 추천 결정의 핵심 근거에서 제외했다.

## 채택을 다시 판단할 수 있는 최소 조건

새 모델의 작은 파일이나 공개 시연만으로 교체하지 않는다. 현재 입력·출력 크기·프레임·seed·sampler·shift·캐시를 고정하고 한 항목만 바꾼 결과에서 총시간과 단계별 시간, 시스템 RAM, 실패율을 비교해야 한다. 얼굴·의상·참조 일치, 동작, 음성 유지 여부는 시간과 별도로 판정해야 한다. 이번 요청은 조사이므로 이 로컬 비교를 실행하지 않았다.

검증은 위 링크의 실제 내용과 표본/설정 확인으로 수행했다. 코드 변경이 없어 소프트웨어 테스트는 실행하지 않았다.
