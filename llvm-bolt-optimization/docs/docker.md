# Docker 复现

## 已验证：离线打包运行镜像

构建宿主机限定 Ubuntu 24.04 x86-64、GCC 13、Python 3.12，且已按固定 SHA 应用补丁并编译 BOLT。
`scripts/package_runtime.sh` 会把工具、插桩运行库、测试辅助文件和已安装的开发工具链复制到仓库外的新目录。
`scripts/package_toolchain.py` 不复制宿主机 glibc；基础镜像必须提供不早于宿主机的 glibc。本次使用官方 Ubuntu 24.04，glibc 2.39。
镜像包含 GCC 私有的 cc1/cc1plus 等程序、开发头文件和链接库；包版本清单为镜像内 `/toolchain-packages.txt`。
历史实验记录保存在仓库 results/，不预装到运行镜像；容器执行后在 WORK 中生成自己的结果。
运行镜像没有 CMake；这不影响 C/C++ 负载编译和测试。需要重新编译 LLVM 时应使用源码构建路线。

```bash
export BOLT=/tmp/bolt-small-layout/build/bin/llvm-bolt
export LLVM_SOURCE=/tmp/bolt-small-layout/llvm-project
export RUNTIME_CONTEXT=/tmp/bolt-runtime-context
bash scripts/package_runtime.sh
# 首次准备基础镜像需要网络，或使用 docker load 导入已校验镜像。
docker image inspect ubuntu:24.04
docker build --network=none -t bolt-small-layout:verified "$RUNTIME_CONTEXT"
docker run --rm --network=none -v "$PWD/results/docker-new:/results" \
  bolt-small-layout:verified bash -c \
  'bash scripts/run_all.sh && python3 scripts/export_results.py "$WORK" /results'
```

本次已实际完成镜像构建与容器功能测试：lit、接受/平局/外部边否决、低计数、用户顺序、无重定位、三类负载与无 profile 检查全部通过。
Docker 内没有再进行性能实验；性能结论来自记录完整的 WSL 测量，避免混淆环境。
镜像 ID 见 `results/docker-runtime-image.json`，构建和测试日志分别为 `docker-runtime-build.log` 与 `docker-runtime-test.log`。
`results/docker-runtime/environment.json` 中的 BOLT SHA256 与原生性能实验匹配。

## 另提供：源码编译镜像

根目录 Dockerfile 从 Ubuntu 24.04 安装依赖，下载固定 LLVM SHA、应用补丁并构建 BOLT。

```bash
docker build --build-arg JOBS=2 -t bolt-small-layout:source .
```

此路线需要软件仓库和 GitHub 网络。虽然同一构建脚本与配置在 WSL 中验证过，本次没有在 Docker 内重编译整个 LLVM。
本机最初的镜像站超时记录保留在 docker-check.log；最终通过官方基础镜像本地加载和离线打包完成运行镜像验证，未修改全局 Docker 配置。

完整 LLVM 源码、编译产物和 Docker 构建上下文都不放进提交目录。只上传课程项目目录即可。
