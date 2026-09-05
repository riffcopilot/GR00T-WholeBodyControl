#!/bin/bash
set -o pipefail
export PATH=/usr/local/cuda/bin:$PATH
export CUDA_HOME=/usr/local/cuda
export CUDAToolkit_ROOT=/usr/local/cuda
export onnxruntime_DIR=/opt/onnxruntime/lib/cmake/onnxruntime
export onnxruntime_ROOT=/opt/onnxruntime
export CMAKE_PREFIX_PATH=/opt/onnxruntime:/usr/lib/aarch64-linux-gnu/cmake:$CMAKE_PREFIX_PATH
export TensorRT_ROOT=/usr
export HAS_ROS2=0
cd ~/GR00T-WholeBodyControl/gear_sonic_deploy
just build 2>&1
echo "BUILD_EXIT=$?"
