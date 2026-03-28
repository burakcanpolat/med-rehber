"""
Modal deployment script for MedGemma vLLM server.

Deploys google/medgemma-1.5-4b-it on Modal with:
- HuggingFace model cache volume (avoids re-downloading on cold start)
- vLLM compilation cache volume (faster subsequent cold starts)
- OpenAI-compatible API endpoint (/v1/chat/completions)

Usage:
    modal deploy scripts/modal_medgemma.py

Prerequisites:
    1. Modal account: https://modal.com/signup
    2. Modal CLI: uv tool install modal && modal setup
    3. HuggingFace token: modal secret create huggingface-token HF_TOKEN=hf_xxx
"""

import subprocess

import modal

# ---------------------------------------------------------------------------
# App & resources
# ---------------------------------------------------------------------------

app = modal.App("medgemma-vllm")

MODEL_NAME = "google/medgemma-1.5-4b-it"
GPU_TYPE = "A10G"  # 24GB VRAM — sufficient for 4B parameter model
VLLM_PORT = 8000
MINUTES = 60

# Volumes
hf_cache_vol = modal.Volume.from_name("medgemma-hf-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)

# Container image with vLLM
# Use CUDA devel base image (Modal's recommended pattern for vLLM)
# All versions pinned to tested combination — prevents future breakage from upstream updates
# Last verified: 2026-03-27
vllm_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.0-devel-ubuntu22.04", add_python="3.12"
    )
    .entrypoint([])
    .pip_install(
        "vllm==0.13.0",
        "transformers==4.57.6",
        "torch==2.9.0",
        "huggingface_hub[hf_xet]==0.36.2",
    )
)


# ---------------------------------------------------------------------------
# vLLM server function
# ---------------------------------------------------------------------------

@app.function(
    image=vllm_image,
    gpu=GPU_TYPE,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    secrets=[modal.Secret.from_name("huggingface-token")],
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
)
@modal.concurrent(max_inputs=10)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve():
    cmd = [
        "vllm", "serve", MODEL_NAME,
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--served-model-name", MODEL_NAME,
        "--dtype", "bfloat16",
        "--max-model-len", "32768",
        "--enforce-eager",
        "--gpu-memory-utilization", "0.90",
        "--limit-mm-per-prompt", '{"image": 85}',
        "--uvicorn-log-level", "warning",
    ]
    subprocess.Popen(cmd)


if __name__ == "__main__":
    print("This script is meant to be deployed with Modal:")
    print("  modal deploy scripts/modal_medgemma.py")
    print()
    print("To check deployment status:")
    print("  modal app list")
