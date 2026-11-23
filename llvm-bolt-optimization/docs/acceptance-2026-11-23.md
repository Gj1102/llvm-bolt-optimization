# 验收记录（2026-11-23）

环境：WSL2 Ubuntu 24.04 x86-64，已有 BOLT 二进制 SHA256 `eafbb72ff24799aeb632a1118205ec7f2286feec2d14be2fa52fd972f147f424`。Windows 沙箱内 WSL 服务访问被拒绝，沙箱外可以使用；未更改系统配置。

从项目目录运行，输出目录为单独的临时目录：

```bash
export BOLT=/home/gj/bolt-course-4794/candidate64/bin/llvm-bolt
export WORK=/tmp/bolt-final-acceptance-20261123
python3 scripts/regression.py
python3 scripts/experiment.py prepare
python3 scripts/experiment.py functional
```

命令链最终返回码 0。回归覆盖接受、平局、外部边否决、低计数、用户顺序和无重定位；三种负载功能对照通过。零交换和无 profile 的测试实例，其函数顺序和所有 CODE 段字节在开关两侧一致。该测试不是所有负载性能不回退的证明。

```bash
bash scripts/verify_runtime_image.sh bolt-small-layout:verified
```

返回码 0。现有镜像 ID 为 `sha256:d416a7c6bfc114e969f79e851ee63184a6a656127756be0808847548edd0f1e9`；断网运行 lit（1 项通过）、回归、准备和功能测试，项目文件通过只读挂载提供。该操作不是从零构建镜像，也未验证其他机器的导入。镜像导出及导入见 `docker.md`。

历史实验与本次功能验收分开：本次未重新计时、构建 LLVM 或测量硬件计数器。最初使用的源码目录没有 Git 元数据，且最新主线源码下载曾超时；后续已获取官方固定提交并完成补丁检查，也取得主线相关源码进行范围限定的比较，详见下文。

## 后续验收：官方源码和镜像导出

后续从官方 `https://github.com/llvm/llvm-project.git` 获取固定提交，使用稀疏检出所需的补丁文件；未修改检出内容。以下命令均返回 0（`PATCH` 为正式补丁绝对路径）：

```bash
git fetch --depth=1 --filter=blob:none origin 4794d35597983f112aafad8d72a5469d80163b7c
git checkout --detach 4794d35597983f112aafad8d72a5469d80163b7c
git rev-parse HEAD
# 4794d35597983f112aafad8d72a5469d80163b7c
git apply --check "$PATCH"
```

`git apply --check` 无输出，表示检查通过；没有应用补丁或重新编译。另获取官方 main 提交 `3c34fcd0a6a8434eb4756e85a8f4c6383815daf9` 的相关源码，具体比较范围及结论见 `design.md`。

镜像 `docker image inspect` 显示 OS `linux`、架构 `amd64`、大小 214371088 字节，镜像 ID 与上文一致。以下命令返回 0：

```bash
docker save -o /mnt/d/bolt-course-delivery/bolt-small-layout.tar bolt-small-layout:verified
sha256sum /mnt/d/bolt-course-delivery/bolt-small-layout.tar
# 82af339c355028bc89e95f842d31b43617032a09ae5bef57b8b7e81ea9c66e8c
docker load -i /mnt/d/bolt-course-delivery/bolt-small-layout.tar
# Loaded image: bolt-small-layout:verified
bash scripts/verify_runtime_image.sh bolt-small-layout:verified
```

重新导入后检查到可执行 `/opt/bolt/bin/llvm-bolt`、`tests/generate.py`、`tests/ordinary.c`、`scripts/experiment.py` 和 `scripts/regression.py`；BOLT 版本输出固定提交 SHA。离线验收输出摘要：lit 1/1 通过；accept、tie、external-veto、low-count、用户顺序和无重定位通过；三种负载的功能对照通过，零交换及无 profile 的顺序和 CODE 段检查通过。该镜像导入发生在同一 Docker Engine，不是跨机器验证。

补丁检查记录见 `../results/acceptance-patch-2026-11-23.log`；重新运行的 Docker 测试完整输出见 `../results/acceptance-docker-2026-11-23.log`。
