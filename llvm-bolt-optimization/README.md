# LLVM BOLT 小函数局部布局优化

课程项目：在 BOLT 现有函数顺序上，尝试相邻小函数交换；仅在**所有受影响的有效调用边**的加权距离下降时接受。

固定 LLVM main 提交：`4794d35597983f112aafad8d72a5469d80163b7c`（2026-11-10）。
源码：[llvm-project](https://github.com/llvm/llvm-project/tree/4794d35597983f112aafad8d72a5469d80163b7c)。

当前状态：正式版本采用最多 64 轮受限交换，Release 编译、回归测试与本机/容器功能验证已通过。
关联小函数负载的估计距离下降约 6.65%；两轮各 31 次的实验中，配对时间改善中位数分别为 2.44% 和 2.63%，探索性区间均为正。
收益限定于本机这类合成负载；分散调用未显示可靠收益，普通程序未交换函数，CDSort 基线上未确认额外性能收益。
见 [实验报告](results/RESULTS.md)、[独立确认](results/confirmation64/RESULTS.md) 和 [验证清单](results/validation.json)。
原 8 轮版本及不支持稳定收益的旧数据保留在 `results/eight-rounds/` 和 `results/confirmation/`。

## 文件

- `patches/small-function-layout.patch`：应用到上述提交的补丁。
- `Dockerfile`：源码编译路线；`Dockerfile.runtime`：已验证的离线运行镜像路线。
- `scripts/build.sh`：下载固定源码、应用补丁、构建。
- `tests/generate.py`：生成 2048 个关联小函数及 512 个分散调用小函数的 C 程序。
- `tests/ordinary.c`：没有大量热小函数的对照程序。
- `tests/local-swap.s`、`scripts/regression.py`：针对收益、相等收益和外部调用边的回归测试。
- `scripts/experiment.py`：真实插桩采集 profile、功能检查、重复计时与布局指标。
- `results/`：本次验证日志和原始实验结果；`docs/design.md`：设计与局限。

完整 LLVM 源码和编译产物均放在本项目目录外，不需要上传 GitHub。

## Linux / WSL 构建

需要 x86-64 Linux，GCC、CMake、Ninja、Git、Python 3、LLD、binutils。建议至少 8 GiB 内存；内存紧张时使用 `JOBS=2`。

```bash
WORK=/tmp/bolt-small-layout JOBS=2 bash scripts/build.sh
export BOLT=/tmp/bolt-small-layout/build/bin/llvm-bolt
export WORK=/tmp/bolt-experiments
bash scripts/run_all.sh
python3 scripts/export_results.py "$WORK"
python3 scripts/analyze_uncertainty.py results
```

默认每个程序/模式计时 15 次，以 0.4 秒为迭代数校准目标；实际每次时长见 CSV。原始 CSV、JSON、日志和报告位于 `$WORK`。
正式对照使用 `benchmark --repeats 31 --min-seconds 1 --order-seed 123`；独立确认使用 `--repeats 31 --min-seconds 1.5 --order-seed 456`，确认报告只分析关联负载。
源码在 `$WORK/llvm-project`，构建产物在 `$WORK/build`（构建时的 WORK）；实验应使用另一个 WORK。

也可以按阶段执行：

```bash
python3 scripts/regression.py
python3 scripts/run_lit.py
python3 scripts/experiment.py prepare
python3 scripts/experiment.py functional
python3 scripts/experiment.py benchmark --repeats 15 --min-seconds 0.4
```

不需要 `perf` 权限：profile 来自 BOLT 插桩。计时只运行未插桩的原始/优化二进制。若要硬件 I-Cache 数据，需要在支持相应 PMU 事件的宿主机上另外测量。

`run_lit.py` 使用源码自带的 lit 和 `link_fdata.py` 运行补丁内的汇编测试，使用 GCC 链接 LLVM MC 生成的目标文件。可用 `LLVM_SOURCE` 指定源码路径；默认从 BOLT 构建目录推导。它不是整个 `check-bolt` 测试集。

## Docker

本次已验证 `Dockerfile.runtime`：使用官方 Ubuntu 24.04 基础镜像，打包已编译 BOLT、插桩运行库、本机 GCC/Python 工具链和测试文件。
镜像构建及容器功能测试均在 `--network=none` 下通过，镜像名为 `bolt-small-layout:verified`。
完整步骤、适用环境和两条构建路线见 [Docker 说明](docs/docker.md)。

```bash
# 先在 Ubuntu 24.04 x86-64 上通过 scripts/build.sh 完成固定版本构建。
export BOLT=/tmp/bolt-small-layout/build/bin/llvm-bolt
export LLVM_SOURCE=/tmp/bolt-small-layout/llvm-project
export RUNTIME_CONTEXT=/tmp/bolt-runtime-context   # 必须是仓库外的新目录
bash scripts/package_runtime.sh
# 基础镜像需要预先获取；已缓存时，后续操作完全不需要网络。
docker build --network=none -t bolt-small-layout:verified "$RUNTIME_CONTEXT"
docker run --rm --network=none bolt-small-layout:verified
```

根目录 `Dockerfile` 另提供从源码编译 LLVM 的网络构建路线；本次没有在容器内重编译整个 LLVM，不能将其称为该路线完整构建验证通过。
两条路线都不需要把完整 LLVM 源码或二进制提交到 GitHub。

## 使用选项

```bash
gcc -O2 -g -no-pie -Wl,--emit-relocs program.c -o program
"$BOLT" program --instrument --instrumentation-file=/tmp/program.fdata -o program.instrumented
./program.instrumented
"$BOLT" program --data=/tmp/program.fdata --reorder-functions=exec-count \
  --small-function-layout -o program.optimized
./program.optimized
```

`--small-function-layout` 默认关闭；显式关闭用 `--small-function-layout=false`。
仅修改函数顺序，不修改程序逻辑。候选函数最多 128 字节，执行计数至少 100，最多 64 轮扫描。
日志 `weighted-distance-before/after` 是估计布局指标，不是缓存未命中数。
没有有效调用边、候选不合格、用户顺序文件或不支持的排序模式时不执行交换。

## 手动应用补丁

```bash
git -C /path/to/llvm-project checkout 4794d35597983f112aafad8d72a5469d80163b7c
git -C /path/to/llvm-project apply --check "$PWD/patches/small-function-layout.patch"
git -C /path/to/llvm-project apply "$PWD/patches/small-function-layout.patch"
```

上传 GitHub 时只上传本目录。课程对 AI 辅助的要求由提交者自行核实；请理解实现并如实说明使用方式。
