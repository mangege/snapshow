#!/bin/bash
# 运行示例脚本
# 用法: ./run_example.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== 预览示例时间线 ==="
python -m img2vid preview demo.yaml

echo ""
echo "=== 生成示例视频 ==="
python -m img2vid generate demo.yaml -o ./output

echo ""
echo "=== 视频已生成到 ./output/demo_video.mp4 ==="
