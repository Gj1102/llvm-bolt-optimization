# Docker 复现

## 下载并运行已发布的镜像

在兼容的 Linux x86-64（`linux/amd64`）Docker 环境中，从 [GitHub Release](https://github.com/Gj1102/llvm-bolt-optimization/releases/tag/v1.0-course) [下载镜像 tar](https://github.com/Gj1102/llvm-bolt-optimization/releases/download/v1.0-course/bolt-small-layout.tar)。镜像名为 `bolt-small-layout:verified`，文件 SHA256 为：

```text
82af339c355028bc89e95f842d31b43617032a09ae5bef57b8b7e81ea9c66e8c
```

可使用 `sha256sum /path/to/bolt-small-layout.tar` 核对文件。将下列命令中的 `/path/to/bolt-small-layout.tar` 替换为实际下载路径：

```bash
git clone https://github.com/Gj1102/llvm-bolt-optimization.git
cd llvm-bolt-optimization/llvm-bolt-optimization
docker load -i /path/to/bolt-small-layout.tar
bash scripts/verify_runtime_image.sh bolt-small-layout:verified
```

脚本只读挂载当前项目并断网执行 lit、回归和功能测试，不进行性能计时。镜像已在本机 Docker Engine 完成断网测试和重新导入验证；尚未在另一台机器独立验证。源码构建 Dockerfile 的容器内完整编译尚未验证。

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

镜像 tar 不存放在 Git 仓库中；可通过上方 Release 下载，也可在构建机使用 `docker save -o bolt-small-layout.tar bolt-small-layout:verified` 另行导出。

2026-11-23 已在构建机导出约 205 MiB 的镜像 tar，并在同一 Docker Engine 重新导入通过验收。

`docker run --rm --network=none bolt-small-layout:verified` 使用镜像内打包时的项目版本，并执行计时；若需要当前脚本，请使用上述只读挂载方式。源码 Dockerfile 可从仓库构建，但仍需网络和较长的 LLVM 编译时间；不要将历史运行镜像验证误称为源码镜像构建验证。
