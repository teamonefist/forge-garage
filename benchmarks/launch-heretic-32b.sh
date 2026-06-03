#!/bin/bash
# Launch Qwen3-32B-heretic for benchmarking on GPU 1
# Must stop Grond's MTP service first to free GPU VRAM

MODEL="/vault/models/qwen3-32b-heretic/Qwen3-32B-heretic.Q4_K_M.gguf"
PORT=8085
GPU=1

if [ ! -f "$MODEL" ]; then
    echo "ERROR: Model not found at $MODEL"
    exit 1
fi

echo "Stopping llama-mtp.service to free GPU memory..."
systemctl stop llama-mtp.service
sleep 2

echo "Launching Qwen3-32B-heretic on GPU $GPU, port $PORT..."
CUDA_VISIBLE_DEVICES=$GPU /vault/axiom/tools/llama.cpp/build/bin/llama-server \
    -m "$MODEL" \
    --port $PORT \
    -ngl 99 \
    -c 8192 \
    -fa on \
    -t 12 \
    --reasoning off \
    2>&1 &

SERVER_PID=$!
echo "Server PID: $SERVER_PID"

echo "Waiting for server to be ready..."
until curl -s http://127.0.0.1:$PORT/health 2>/dev/null | grep -q '"ok"'; do
    sleep 2
done

echo "Server ready! GPU memory:"
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
echo ""
echo "Run benchmark with:"
echo "  python3 benchmarks/model_benchmark.py http://127.0.0.1:$PORT 'Qwen3-32B-heretic'"
echo ""
echo "Or compare against Grond:"
echo "  # First restart Grond on the other GPU, then:"
echo "  python3 benchmarks/model_benchmark.py http://127.0.0.1:8081 'Grond-v7' http://127.0.0.1:$PORT 'Qwen3-32B-heretic'"
