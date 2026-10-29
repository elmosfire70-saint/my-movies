# 로컬 모델 대안 조사

확인 시각은 2026-10-29 20:07 KST이다. 대상은 RTX 3060 12GB, 시스템 RAM 32GB, 과거·현재 인물 사진과 선택적 배경을 합성한 뒤 약 5초 576×1024 무음 영상을 만드는 작업이다. 이 문서는 모델 제작자·추론 프레임워크 제작자의 문서와 실제 배포 파일을 조사한 결과이다. 모델 설치나 대안 모델의 로컬 추론은 하지 않았다. 파일 크기, 공식 실행 조건, 이 PC의 예상 적합성을 구분한다.

## 추천 순서

| 목적 | 우선 후보 | 이유와 한계 |
|---|---|---|
| 기존 이미지 합성을 적은 변경으로 가속 | Qwen Image 2.1 Turbo INT8 ConvRot 또는 기존 베이스용 공식 Turbo LoRA | 같은 계열의 편집 기능을 유지하며 공식 25단계 기본 템플릿에서 8단계로 줄인다. 전체 실행 시간이 25/8배 빨라진다는 뜻은 아니다. |
| 12GB에 맞는 영상 모델 비교 | Wan2.2 TI2V-5B | ComfyUI 공식 오프로드 조건이 8GB이다. H3보다 얼굴과 두 인물의 관계를 잘 보존하는지는 미검증이다. |
| 현재 H3의 메모리 부담 완화 | Comfy-Org H3 Ref2VA `pruned_w6a8` | 파일이 약 21GB에서 16GB로 작아진다. GPU 12GB에 모두 들어가는 모델은 아니며 3060 커널 호환성과 실제 속도는 확인해야 한다. |
| 새로운 이미지 편집 품질 비교 | Fibo 2.0 Edit Turbo INT8 ConvRot | 4단계, 최대 4개 참조를 지원한다. 프롬프트 구조가 달라 전환 비용이 있고 품질 우위는 이 작업에서 검증되지 않았다. |
| 영상 초안 생성 속도 탐색 | LTX-Video 2B 0.9.8 distilled | 구세대 소형 모델이다. 가벼운 초안 후보이며 최신 H3 품질을 대체한다고 볼 근거는 없다. |

## 이미지 모델

**Qwen Image 2.1을 먼저 유지·가속한다.** Qwen은 비주얼 생성 부분 7B, 생성·편집 통합, 최대 10개 참조를 공식 설명한다. 두 인물과 배경을 함께 쓰는 요구에 직접 맞는다. [Qwen 공식 발표](https://qwen.ai/blog?id=qwen-image-2.1).

Comfy 공식 문서에는 `qwen_image_2.1_turbo_int8_convrot.safetensors`와 `qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors`가 있다. 별도 Turbo 모델은 고정된 8단계 `ManualSigmas` 경로이며, LoRA는 기존 베이스를 재사용해 8단계·CFG 1로 샘플링하는 경로이다. VAE와 기본 텍스트 인코더를 공유한다. 이미 큰 베이스 파일을 가진 경우 LoRA가 다운로드량을 줄이는 선택이다. 프롬프트 인코딩·참조 처리·가중치 로딩 시간은 남으므로 단계 수만으로 전체 배속을 계산하지 않는다. 인물 정체성·나이 구분·배경 보존을 같은 입력으로 비교해야 한다. [Comfy Qwen 2.1 공식 문서](https://github.com/Comfy-Org/docs/blob/main/tutorials/image/qwen/qwen-image-2-1.mdx).

**Fibo 2.0 Edit Turbo는 새 품질 비교 후보이다.** 제작자는 8B, 4단계·CFG 없음, 최대 4개 참조, 마스크 편집을 명시한다. 구조화된 VGL/JSON 장면 설명을 사용하므로 기존 Qwen 문장을 그대로 넣는 비교는 공정하지 않다. 제작자 모델 카드의 편집 순위는 일반 평가에 관한 주장이지 이 사용자의 얼굴 보존 검증이 아니다. 로컬 비상업용 배포 조건이며 상업용은 별도 조건이다. [Bria 모델 카드](https://huggingface.co/briaai/Fibo-2.0-edit-turbo). Comfy-Org는 Turbo INT8 ConvRot, Qwen3-VL-4B INT8 인코더, FLUX2 VAE를 제공한다. 12GB/32GB에서의 다중 참조 실측은 이번 조사로 확인하지 못했다. [Comfy 공식 패키지](https://huggingface.co/Comfy-Org/Fibo-2.0).

**FLUX.2 Klein 4B는 소형 속도 후보지만 무조건 12GB 상주 모델은 아니다.** 공식 카드는 다중 참조 편집과 약 13GB VRAM, CPU 오프로드 예제를 제공한다. 따라서 12GB에서는 오프로드나 양자화 조건을 붙여야 한다. Qwen보다 인물 합성이 더 정확하다고 단정할 근거는 없다. [BFL 공식 모델 카드](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B).

**최신 FLUX 3 Image Klein도 확인했지만 속도 1순위로 추천하지 않는다.** 공식 모델은 5.6B 이미지 변환기와 별도 Qwen3-VL-4B, 최대 10개 참조, 16단계 distilled이다. 충분한 장면 설명으로 프롬프트를 확장하는 절차를 요구한다. 제작자의 B200·1024²·프롬프트 확장기 제외 기준 최대 GPU 메모리는 BF16 31GB, FP8 26GB, NVFP4 25GB이다. 이는 모든 실행기의 최소 요구량은 아니지만 12GB에서 바로 빠르다는 근거도 아니다. [BFL 공식 모델 카드](https://huggingface.co/black-forest-labs/flux-3-image-klein). Diffusers의 별도 측정도 FP8 약 16.27GiB이며 CPU 오프로드 성능은 미측정이라고 밝힌다. H100의 약 2초 결과를 3060 예상 시간으로 사용하면 안 된다. [Diffusers 공식 통합·측정](https://huggingface.co/blog/flux-3).

## H3를 유지할 때

**양자화 개선과 증류 개선을 분리한다.** Comfy-Org의 현재 Ref2VA 파일 트리에는 `minimax_h3_ref2va_pruned_int8_convrot.safetensors` 약 21GB와 `minimax_h3_ref2va_pruned_w6a8.safetensors` 약 16GB가 있다. 저장량은 약 24% 작지만 GPU 작업 메모리와 동일하지 않으며, 3060에서 지원되는 빠른 W6A8 경로가 있다는 증거를 이번 조사에서 확보하지 못했다. 따라서 설치 전 호환성 확인과 A/B 측정이 필요한 후보로만 둔다. 단순 FP8 pruned 파일은 약 21GB여서 파일 크기 이득도 없다. [Comfy-Org 실제 배포 파일](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/main/diffusion_models).

**Ref2V Turbo v0.1보다 새 파일은 존재한다.** LightX2V 실제 배포 트리에서 `minimax_h3_ref2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors`와 `minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors`를 확인했다. FL2V 계열은 4단계 v1.3까지 보인다. 4단계 Ref2V v1.0은 현재 v0.1과 같은 단계 수의 품질 비교 후보이며, 그 자체로 속도 개선은 아니다. 8단계판도 자동 가속 업그레이드가 아니다. [LightX2V 실제 파일 트리](https://huggingface.co/lightx2v/Minimax-h3-Turbo/tree/main).

주의할 점은 문서와 배포 목록의 시차이다. 현재 ModelTC README의 Ref2VA 표는 v0.1만 설명하며 544p·video/audio shift 12/3·4 NFE를 지정한다. FL2VA의 768p 경로는 shift 6/3을 사용한다. 새 Ref2V 768p 파일의 정확한 스케줄을 이 표에서 추측해 확정하면 안 된다. 기존 576px 출력도 v0.1의 544p 학습 조건과 가깝다. 또한 증류 Ref2VA는 참조 크기 `match`를 권장하므로 불필요하게 참조를 2048px로 키우는 경로는 피하는 비교가 적절하다. [LightX2V 제작자 사양·워크플로](https://github.com/ModelTC/Minimax-H3-Turbo).

**FL2VA와 Ref2VA는 작업이 다르다.** MiniMax 공식 명세에서 FL2VA는 첫·마지막 프레임 입력이고 Ref2VA는 여러 이미지·영상·음성 참조이다. 완성된 합성 사진 한 장을 첫 프레임으로 확실히 유지하며 움직이려면 FL2VA 비교가 타당할 수 있다. 여러 참조를 재해석하는 현재 요구를 유지하려면 Ref2VA를 유지한다. FL2V LoRA를 Ref2VA용 업데이트로 대체해서는 안 된다. [MiniMax 공식 모델 명세](https://huggingface.co/MiniMaxAI/MiniMax-H3).

**FastH3와 FastH3 Omni도 별개이다.** Comfy의 FastH3 8-step V2 설명은 Ref2VA가 증류되지 않았다고 명시한다. [Comfy FastH3 문서](https://docs.comfy.org/tutorials/video/minimax/minimax-h3-fastvideo). 최근 FastH3 Omni 8-step V1은 참조 생성용으로 따로 공개됐지만 공식 로컬 예시는 RTX 5090/NVFP4, RTX 4090/FP8, DGX Spark 중심이다. 3060 12GB/32GB에서 현재 4단계 Ref2VA보다 빠르다고 확인할 자료가 없다. [FastVideo Omni 제작자 카드](https://huggingface.co/FastVideo/FastVideo-FastH3-Omni-8-Step-V1).

Comfy Kitchen은 빠른 TensorCore FP8 경로를 Ada SM 8.9 이상, NVFP4를 Blackwell SM 10.0 이상으로 구분한다. 따라서 Ampere인 3060에 Blackwell의 NVFP4 결과나 Ada의 FP8 배속을 그대로 적용하지 않는다. 양자화 파일을 읽을 수 있는 것과 해당 정밀도로 빠르게 연산하는 것은 다른 조건이다. [Comfy Kitchen 하드웨어 조건](https://github.com/Comfy-Org/comfy-kitchen#quantized-tensors).

## 영상 대체 모델

**Wan2.2 TI2V-5B가 12GB용 첫 비교 대상이다.** ComfyUI 공식 문서는 기본 오프로드 사용 시 8GB VRAM에서 동작할 것으로 명시하고 FP16 5B 모델·UMT5 FP8·Wan2.2 VAE 조합을 제공한다. 기존 합성 사진 한 장을 I2V 입력으로 쓰는 비교가 가능하다. 이 근거는 실행 가능성에 관한 것이며 H3 4단계보다 빠르거나 품질이 높다는 보장은 아니다. [Comfy Wan2.2 5B 공식 실행 안내](https://docs.comfy.org/tutorials/video/wan/wan2_2#wan2-2-ti2v-5b-hybrid-version-workflow-example). Wan 제작자 원본 코드의 720p 단일 GPU 안내는 24GB이고, 약 5초 720p를 9분 이내 생성한다는 수치 역시 3060 실측이 아니다. 실행기가 다르므로 Comfy의 8GB 안내와 모순으로 취급하지 않는다. [Wan 공식 모델 카드](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B).

**LTX-2.5는 최신이지만 이번 PC의 우선 교체 후보에서 제외한다.** 현행 모델은 22B, distilled 고정 8단계, 별도 커스텀 Gemma4-12B 인코더이며 Comfy INT8 ConvRot와 Blackwell NVFP4 배포가 있다. [Lightricks 모델 카드](https://huggingface.co/Lightricks/LTX-2.5). 일반 공식 시스템 요구량은 VRAM 32GB·RAM 32GB이고 [공식 시스템 요구사항](https://docs.ltx.io/open-source-model/getting-started/system-requirements), 별도 Desktop의 로컬 실행 기준은 CUDA VRAM 16GB이다. [LTX Desktop 공식 요구사항](https://github.com/Lightricks/LTX-Desktop#system-requirements). 경로별 요구량이 다르지만 둘 다 12GB를 공식 지원 기준으로 제시하지 않는다. 작은 양자화와 오프로드의 실험 가능성을 불가능이라고 단정하지는 않되, 32GB RAM PC에 확실한 성능 업그레이드로 권하지 않는다.

**LTX-Video 2B 0.9.8 distilled는 초안용 후보이다.** 구세대 공식 카드는 이 모델을 가벼운 VRAM용으로 분류하며 13B distilled보다 품질이 낮다고 설명한다. 영상·인물 품질 우위를 주장할 수 없고, 필요한 해상도·프레임 수에서 3060 실측도 없다. 최신 LTX-2.5와 이름을 혼동하지 않는다. [LTX-Video 공식 모델 목록](https://huggingface.co/Lightricks/LTX-Video#models--workflows).

## 다음 비교에서 확인할 것

현재 모델을 기준으로 같은 두 인물·배경·출력 크기와 3개 입력 사례를 고정한다. 각 후보는 제작자가 지정한 자체 단계·스케줄로 비교하고, 서로 다른 모델에 같은 seed를 썼다는 이유만으로 동일 난이도라고 보지 않는다.

- 첫 실행과 재실행을 나눠 텍스트 인코딩, 모델 로딩/오프로드, 샘플링, VAE 디코딩, 저장 시간을 기록한다.
- 최대 전용 VRAM, 시스템 RAM, 페이지 파일 사용, OOM 여부를 함께 기록한다.
- 이미지 합성은 각 인물의 얼굴·나이·두 사람의 구별·배경 보존을 평가한다.
- 영상은 시작 프레임 보존, 얼굴 변화, 손·포옹 동작, 시간적 흔들림과 실제 MP4 프레임 수·길이를 평가한다.
- 총 처리 시간뿐 아니라 사용 가능한 결과 한 개를 얻기까지의 재시도 횟수를 비교한다.

공식 설명과 배포 파일 확인은 완료했지만 대안 모델의 설치·추론·속도 측정은 수행하지 않았다. 따라서 순위는 하드웨어 적합성과 전환 비용을 고려한 실험 우선순위이며 이 PC에서 검증된 성능 순위가 아니다.
