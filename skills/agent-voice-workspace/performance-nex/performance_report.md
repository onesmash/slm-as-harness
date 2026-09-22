# Performance Report — agent-voice ARM 线程调优（平台隔离）

- **run_id**: pn-arm-threads-001
- **terminal_state**: `completed`
- **claim_level**: `works`（隔离配置与验证器有命令证据）；性能维度声明为 **`no_material_change`**（基线已最优，无可采纳候选）
- **scope_decision**: scope_in 全部完成（单变量扫描 + 平台隔离配置）；scope_out 未触碰（blocksize/sample_mode/模型/流式）

## 锁定契约

| 项 | 值 |
|---|---|
| 慢路径 | MOSS ONNX CPU 推理（`SessionOptions.intra_op_num_threads`，inter_op=1） |
| 目标指标 | 稳态合成 RTF（synth_seconds / audio_seconds，越低越好） |
| 工作负载 | 5 固定句（短/中/长）× 3 repeats，预热后计时，热态 |
| 环境 | Apple M4 Pro（arm64，8P+4E=12）· macOS 26.6.2 · ORT 1.30.0 · py3.12 |
| 基线 | threads=4（Intel perf-20260922 实测，ARM 上从未验证） |
| 正确性契约 | 全配置输出 PCM 与基线 sha256 bit-exact |

## 测量结果（P50/中位 RTF，n=15/config）

| threads | RTF 中位 | CV | Δ vs t=4 | 显著（>2×CV） | bit-exact |
|---|---|---|---|---|---|
| 1 | 0.2820 | 0.117 | **+31.6%** | ✓ 劣化 | ✓ |
| 2 | 0.2431 | 0.083 | +13.5% | ✗ | ✓ |
| **4（基线）** | **0.2142** | 0.068 | — | — | ✓ |
| 6 | 0.2303 | 0.090 | +7.5% | ✗ | ✓ |
| 8 | 0.2384 | 0.062 | +11.3% | ✗ | ✓ |
| 12（触及 E 核） | 0.2629 | **0.283** | **+22.7%** | ✓ 劣化且方差爆炸 | ✓ |

## 结论

1. **ARM 独立实测：t=4 同样最优**（这是本机验证结论，不是跨平台复用）。两个方向的偏离均显著劣化；t=12 因 E 核调度抖动 CV 爆炸（0.068→0.283），尾部不可控。
2. **无 material change**：运行时线程配置维持 t=4，性能无可采纳候选；本轮价值在证据链与隔离机制。
3. **平台隔离机制落地**（用户核心诉求）：
   - `config.toml [engine.threads]` 按 `{default, x86_64, arm64}` 分段，各平台实测值互不覆盖，来源注释到测量 run_id
   - `moss_engine.resolve_platform_threads()` 按 `platform.machine()` 精确选段，未知平台回退 `default`
   - 隔离断言全过：真实配置两段并存；用户只覆盖 arm64 段时 x86_64 保持不变（deep_merge 递归语义）
   - 未来任一平台重测/换拓扑，只改自己那段；Intel 机器行为零变化

## 正确性与完整性

- 正确性：90/90 请求 bit-exact parity（6 配置 × 15），EV-CORR-001
- 完整性自评（EV-INTEG-001）：单进程串行配置、同负载同序同热态；已披露共存进程（ttsd idle）与局限——`pn_integrity_audit.py` 的 MR-8 收据面向并行隔离 arms，本任务以环境披露+顺序契约替代，未硬造收据

## Open gaps

- t=6/8 中位劣化但未过显著性门槛——若需收紧，建议 runs≥5 重测（受时长预算未做）
- 单机单代（M4 Pro）结论；M 系列其他拓扑（Ultra/Ultra、M3/M5）不自动成立，需按隔离段重测
- 音频输出路径（blocksize/latency）不在本轮 scope

## Next executable action

换下一代 Apple 芯片或更换 Intel 机器时：改 `bench_threads.py` 的 `CONFIGS` 重跑同 harness，只回填对应平台段。
