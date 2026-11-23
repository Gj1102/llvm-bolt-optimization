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

## 已有镜像的验收与交付

在包含本项目的目录中运行 `bash scripts/verify_runtime_image.sh bolt-small-layout:verified`。该脚本将当前项目只读挂载进已有镜像，断网运行 lit、回归和功能测试，包括零交换和无 profile 时的 CODE 段比较；它不运行计时实验。镜像内自带的项目文件可能是较早版本，因此应使用当前工作区运行此脚本。

如需交付现成镜像，可在构建机执行 `docker save -o bolt-small-layout.tar bolt-small-layout:verified`，将 tar 与当前项目一起提供给老师；老师执行 `docker load -i bolt-small-layout.tar`，进入项目目录后运行上述验收脚本。镜像 tar 体积可能很大，仓库当前不包含它，也没有公开的镜像下载地址。另一台机器应为兼容的 Linux x86-64 Docker 环境。

2026-11-23 已导出到构建机的 `D:\bolt-course-delivery\bolt-small-layout.tar`（约 205 MiB），SHA256 为 `82af339c355028bc89e95f842d31b43617032a09ae5bef57b8b7e81ea9c66e8c`。请将此 tar 与项目一起交付；老师可用 `sha256sum bolt-small-layout.tar` 核对后导入。已在同一 Docker Engine 重新导入并通过验收，尚未在另一台机器测试。

`docker run --rm --network=none bolt-small-layout:verified` 使用镜像内打包时的项目版本，并执行计时；若需要当前脚本，请使用上述只读挂载方式。源码 Dockerfile 可从仓库构建，但仍需网络和较长的 LLVM 编译时间；不要将历史运行镜像验证误称为源码镜像构建验证。
