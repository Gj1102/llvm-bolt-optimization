from pathlib import Path
import json

project=Path('llvm-bolt-optimization')
results=project/'results'
data=json.loads((results/'summary.json').read_text())
uncertainty=json.loads((results/'uncertainty.json').read_text())
confirmation=json.loads((results/'confirmation64/uncertainty.json').read_text())
first=next(x for x in uncertainty if x['case']=='correlated' and x['baseline']=='off')
second=next(x for x in confirmation if x['baseline']=='off')
assert first['bootstrap_95_percentile_interval_percent'][0]>0 and second['bootstrap_95_percentile_interval_percent'][0]>0

p=project/'README.md'
text=p.read_text(encoding='utf-8')
start,end=text.index('当前状态：'),text.index('## 文件')
text=text[:start]+'''当前状态：正式版本采用最多 64 轮受限交换，Release 编译、回归测试与本机/容器功能验证已通过。
关联小函数负载的估计距离下降约 6.65%；两轮各 31 次的实验中，配对时间改善中位数分别为 2.44% 和 2.63%，探索性区间均为正。
收益限定于本机这类合成负载；分散调用未显示可靠收益，普通程序未交换函数，CDSort 基线上未确认额外性能收益。
见 [实验报告](results/RESULTS.md)、[独立确认](results/confirmation64/RESULTS.md) 和 [验证清单](results/validation.json)。
原 8 轮版本及不支持稳定收益的旧数据保留在 `results/eight-rounds/` 和 `results/confirmation/`。

'''+text[end:]
start,end=text.index('## Docker'),text.index('## 使用选项')
text=text[:start]+'''## Docker

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

'''+text[end:]
text=text.replace('最多 8 轮扫描','最多 64 轮扫描')
text=text.replace('- `Dockerfile`：Ubuntu 24.04 构建环境与 BOLT、插桩运行库、测试工具。',
                  '- `Dockerfile`：源码编译路线；`Dockerfile.runtime`：已验证的离线运行镜像路线。')
p.write_text(text,encoding='utf-8',newline='\n')

rows=['| 程序 | 关闭中位时间(s) | 开启中位时间(s) | 配对改善中位数 | 估计距离减少 | 交换次数 |',
      '|---|---:|---:|---:|---:|---:|']
for case in ('correlated','dispersed','ordinary'):
    modes={x['mode']:x for x in data if x['case']==case}
    base,on=modes['off'],modes['on']
    pair=next(x for x in uncertainty if x['case']==case and x['baseline']=='off')
    drop=100*(1-on['model_after']/on['model_before']) if on['model_before'] else 0
    rows.append(f"| {case} | {base['median_seconds']:.6f} | {on['median_seconds']:.6f} | {pair['paired_median_gain_percent']:+.2f}% | {drop:.5f}% | {on['swaps']} |")
interpretation='''
## 验证结论：最终 64 轮版本

本轮完整对照为三类程序、五种模式、各 31 次，共 465 次计时；另用运行顺序种子 456，对关联负载独立重跑 31 轮五种模式，共 155 次。
第一次实验的配对改善中位数为 2.44%，探索性 bootstrap 95% 百分位区间为 1.88%–3.13%；独立确认约为 2.63%，区间为 1.21%–4.31%。
这两次测量支持本机所测关联小函数负载相对 exec-count 基线有收益；不表示所有工作负载或机器都加速。

分散调用的配对区间跨越零，未确认收益。普通程序零交换，代码段完全相同，时间差属于噪声，不能归因于本优化。
关联负载在 CDSort 基线上零交换，未确认额外收益。所有开启/关闭对照的 CODE 段大小相同，没有代码体积收益。
两组独立中位数的百分比与“按重复轮次配对”的改善中位数是不同估计量，不应混用；原始 CSV 和 uncertainty.json 均已保留。

bootstrap 依赖重复块相互独立的假设。首轮候选实验期间存在 Docker 准备活动，因此另做了无并行构建、不同顺序种子的确认实验。
未采集硬件 I-Cache miss，不能据此声称缓存未命中已被直接测量。
原 8 轮实现的点估计及其跨零区间作为负面结果保留，没有删除或替换为成功数据。
'''
report=results/'RESULTS.md'
report.write_text(report.read_text(encoding='utf-8')+interpretation,encoding='utf-8',newline='\n')
confirm_report=results/'confirmation64/RESULTS.md'
confirm_report.write_text(confirm_report.read_text(encoding='utf-8')+'''\n独立确认：相对 exec-count 的配对改善中位数 2.63%，探索性区间 1.21%–4.31%；顺序种子 456。该轮未并行构建或安装依赖。CDSort 对照区间跨零，不能声称额外加速。\n''',encoding='utf-8',newline='\n')

p=project/'docs/design.md'
text=p.read_text(encoding='utf-8')
text=text.replace('最多扫描 8 轮','最多扫描 64 轮').replace('固定 8 轮','固定 64 轮').replace('8 轮也无法','64 轮也无法')
start,end=text.index('## 本次实测结论'),text.index('## 局限')
text=text[:start]+'''## 本次实测结论（2026-11-11）

最终版本将扫描上限从 8 提高为 64，仍只接受加权调用距离严格下降的相邻交换，没有引入新算法或额外优化选项。
较低上限过早限制了搜索；关联负载的交换数从 13967 增至 42935，距离减少从约 1.97% 增至约 6.65%。
超过上限仍可能有更好排列，本项目没有搜索最优布局。

Ubuntu 24.04 / WSL2、GCC 13.3、Release 且启用断言的 BOLT 完成编译及全部功能验证；容器内同样通过回归与 48 组输出对照。

'''+ '\n'.join(rows)+'\n'+interpretation+'''
Docker 不足通过独立的离线运行镜像路线解决：官方 Ubuntu 基础镜像经 SHA256 校验后本地加载，已安装的工具链从宿主机打包进镜像。
断网构建和断网容器测试均通过。完整源码编译已经在 WSL 中验证；不声称在容器内重新编译了整个 LLVM。

'''+text[end:]
p.write_text(text,encoding='utf-8',newline='\n')

(project/'docs/docker.md').write_text('''# Docker 复现

## 已验证：离线打包运行镜像

构建宿主机限定 Ubuntu 24.04 x86-64、GCC 13、Python 3.12，且已按固定 SHA 应用补丁并编译 BOLT。
`scripts/package_runtime.sh` 会把工具、插桩运行库、测试辅助文件和已安装的开发工具链复制到仓库外的新目录。
`scripts/package_toolchain.py` 不复制宿主机 glibc；基础镜像必须提供不早于宿主机的 glibc。本次使用官方 Ubuntu 24.04，glibc 2.39。
镜像包含 GCC 私有的 cc1/cc1plus 等程序、开发头文件和链接库；包版本清单为镜像内 `/toolchain-packages.txt`。
运行镜像没有 CMake；这不影响 C/C++ 负载编译和测试。需要重新编译 LLVM 时应使用源码构建路线。

```bash
export BOLT=/tmp/bolt-small-layout/build/bin/llvm-bolt
export LLVM_SOURCE=/tmp/bolt-small-layout/llvm-project
export RUNTIME_CONTEXT=/tmp/bolt-runtime-context
bash scripts/package_runtime.sh
# 首次准备基础镜像需要网络，或使用 docker load 导入已校验镜像。
docker image inspect ubuntu:24.04
docker build --network=none -t bolt-small-layout:verified "$RUNTIME_CONTEXT"
docker run --rm --network=none -v "$PWD/results/docker-new:/results" \\
  bolt-small-layout:verified bash -c \\
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
''',encoding='utf-8',newline='\n')

(results/'benchmark-settings.json').write_text(json.dumps({'repeats':31,'order_seed':123,
    'min_seconds_target':1,'cpu':0,'max_refinement_rounds':64,
    'source':'candidate64 experiment command; original rows preserved'},indent=2)+'\n')
for name in ('lit.log','functional.json'):
    import shutil
    shutil.copy2(results/'release-functional'/name,results/name)
shutil.copytree(results/'release-functional/regression',results/'regression',dirs_exist_ok=True)
print('Updated final 64-round documentation and validation evidence')
