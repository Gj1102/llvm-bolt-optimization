# LLVM BOLT 小函数局部布局优化

本项目是系统优化课程作业，基于 LLVM BOLT 优化二进制中的函数布局，研究关联小函数密集调用时的局部性。新增默认关闭的 `--small-function-layout` 选项：在已有函数顺序上尝试相邻小函数交换，仅在受影响的有效调用边的加权距离下降时接受。

HFSort 和 CDSort 已经利用调用关系及函数大小进行布局。本项目的增量是在现有排序结果上进行受限局部修正，并检查交换对调用图中受影响边的整体距离收益；不声称提出全新的通用布局算法。具体比较范围见[设计文档](llvm-bolt-optimization/docs/design.md)。

## 课程交付物

1. **代码 Patch**：[small-function-layout.patch](llvm-bolt-optimization/patches/small-function-layout.patch)，适用于固定 LLVM 提交 `4794d35597983f112aafad8d72a5469d80163b7c`。
2. **Docker 运行镜像**：[Release 页面](https://github.com/Gj1102/llvm-bolt-optimization/releases/tag/v1.0-course) · [下载 bolt-small-layout.tar](https://github.com/Gj1102/llvm-bolt-optimization/releases/download/v1.0-course/bolt-small-layout.tar)。镜像 `bolt-small-layout:verified` 面向 `linux/amd64`，包含 llvm-bolt、测试负载和脚本。
3. **设计文档**：[问题、设计、实现、实验与局限](llvm-bolt-optimization/docs/design.md)。

## 导入镜像并验证

在 Linux x86-64 Docker 环境中下载上述镜像文件，并核对 SHA256：

```text
82af339c355028bc89e95f842d31b43617032a09ae5bef57b8b7e81ea9c66e8c
```

```bash
git clone https://github.com/Gj1102/llvm-bolt-optimization.git
cd llvm-bolt-optimization/llvm-bolt-optimization
docker load -i /path/to/bolt-small-layout.tar
bash scripts/verify_runtime_image.sh bolt-small-layout:verified
```

将 `/path/to/bolt-small-layout.tar` 替换为实际下载路径。验收脚本以只读方式挂载当前项目，并断网运行 lit、回归和功能测试，不运行计时实验。镜像已在本机 Docker Engine 断网运行并重新导入验证，**尚未在另一台机器独立验证**；更多说明见 [Docker 复现](llvm-bolt-optimization/docs/docker.md)。

## 实验结果与适用范围

在所测机器的合成关联小函数负载上，相对 exec-count 基线，两轮各 31 次重复实验的配对时间改善中位数分别为 **2.44%** 和 **2.63%**，估计调用距离下降约 6.65%。分散调用负载未确认可靠收益；普通程序没有发生交换；关联负载在 CDSort 基线上未确认额外收益。

这些结果受机器、虚拟化和测量噪声限制；探索性统计区间依赖重复轮次独立等假设。加权距离是模型指标，并非实测 CPU 指令缓存未命中率，也不能保证所有负载不发生性能回退。原始数据、统计区间和失败或无收益结果见[实验报告](llvm-bolt-optimization/results/RESULTS.md)。

## 项目目录

- [llvm-bolt-optimization/](llvm-bolt-optimization/)：正式项目，包括补丁、构建文件、测试脚本与负载。
- [设计文档](llvm-bolt-optimization/docs/design.md) · [Docker 说明](llvm-bolt-optimization/docs/docker.md) · [验收记录](llvm-bolt-optimization/docs/acceptance-2026-11-23.md)。
- [实验结果与原始数据](llvm-bolt-optimization/results/) · [内层项目 README](llvm-bolt-optimization/README.md)。
