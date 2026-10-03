# Telemetry

Persona Training Lab exposes a lightweight Telemetry panel for **operator diagnostics**. It shows a current host snapshot: CPU, RAM, a small process sample and NVIDIA GPU/VRAM/temperature data when the GPU provider succeeds.

The central rule is:

> **Telemetry helps you observe the machine while PTL is running. It is not a persisted research time series and must not be treated as Training Dynamics evidence.**

For the implementation contract and measurement limits, see [Telemetry architecture](../architecture/telemetry.md).

## 1. Where Telemetry lives

Telemetry is one of the shell dock panels alongside Activity and Issues.

By default it shares the lower dock area. The dock can be moved, floated, hidden and restored through the shell like the other dock panels.

Hiding the panel does not reset PTL research state. It only stops the panel's visible auto-refresh timer while hidden.

## 2. What the panel shows

The current panel can display:

```text
CPU utilization
RAM utilization
GPU utilization
VRAM used / total
GPU temperature
top process CPU/RAM sample
last refresh time
semantic availability/load status
```

These values are a current snapshot, not an accumulated historical record.

## 3. CPU

CPU percentage comes from the current psutil sample.

The provider requests:

```text
psutil.cpu_percent(interval=0.1)
```

so each base sample includes a short blocking measurement interval.

The panel also shows the logical CPU-count value reported by the host.

Current CPU semantic threshold:

```text
CPU < 85%   -> normal
CPU >= 85%  -> high_load
```

`high_load` is an operator warning threshold. It is not a Training failure state.

## 4. RAM

RAM values come from the host virtual-memory snapshot:

```text
used bytes
total bytes
percent
```

The current Telemetry service does **not** define a RAM `high_load` semantic threshold.

A high RAM percentage can still be operationally important, but do not invent a machine status that current code does not emit.

## 5. GPU and VRAM

When available, PTL invokes `nvidia-smi` for:

```text
GPU utilization
VRAM used
VRAM total
GPU temperature
```

The current provider parses the **first NVIDIA-SMI output row only**.

That means the panel is not a complete multi-GPU inventory and does not attach a stable GPU device identity to multiple accelerators.

Current GPU semantic threshold:

```text
GPU < 90%   -> normal
GPU >= 90%  -> high_load
```

## 6. `gpu_unavailable` does not mean inference failed

If `nvidia-smi` is missing, times out, returns a non-zero result or produces malformed/unparseable data, the service reports:

```text
gpu_unavailable
```

CPU/RAM/process metrics can still remain usable.

`gpu_unavailable` describes the Telemetry provider only. It does **not** prove:

- that CUDA is unusable;
- that the local model cannot generate;
- that Training cannot run;
- that the machine has no GPU.

Use the Local Models/Training diagnostic surfaces for model-runtime conclusions.

## 7. Process sample

The base provider enumerates host processes best-effort and sorts rows descending by:

```text
(cpu_percent, ram_percent)
```

Production keeps at most:

```text
5 rows
```

This is a small operator-oriented sample, not a complete process inventory.

If process enumeration fails or yields no usable rows, CPU/RAM can still remain available and the process status becomes:

```text
processes_unavailable
```

## 8. Refresh lifecycle

`TelemetryViewModel` starts without performing host collection during application composition.

The visible Telemetry panel owns:

```text
manual Refresh button
30-second auto-refresh timer
refresh on show
timer stop on hide
one in-flight refresh at a time
```

Each collection runs in one owned non-daemon background thread. The worker collects an immutable snapshot and sends it back to the GUI thread, where the view-model and widgets are updated.

The panel prevents overlapping refresh requests with an in-memory `refresh_pending` guard.

## 9. Responsiveness and shutdown boundary

Normal Telemetry provider collection no longer runs on the Qt GUI thread.

The provider calls still have real latency:

```text
psutil CPU interval = 0.1 s
nvidia-smi timeout  = 1.0 s
```

but that waiting occurs in the Telemetry refresh worker instead of blocking normal Qt event processing.

The worker is part of the shell background-shutdown contract. If PTL is closing while a Telemetry sample is still being collected, the shell keeps treating background work as active until that thread actually stops.

The current worker is not force-cancelled in the middle of a provider call; shutdown can briefly wait for the in-flight bounded collection to return.

## 10. Manual refresh

Use **Refresh** when you want an immediate current snapshot.

While a manual refresh is pending, the button is temporarily disabled and its label changes to the localized refreshing state.

A refresh replaces the previous in-memory snapshot. It does not append a historical measurement row.

## 11. Auto refresh

While the panel is visible, the current timer interval is:

```text
30 seconds
```

When the panel is hidden, that timer stops. When the panel is shown again, auto-refresh is restarted and the panel requests a fresh snapshot.

## 12. Main status codes

Current Telemetry machine-semantic codes include:

```text
normal
high_load
gpu_unavailable
processes_unavailable
active
refresh_failed
```

Use these codes when diagnosing behavior. The rendered label is localized presentation.

## 13. Base-provider failure

If the base psutil collection fails entirely, PTL returns a safe fallback snapshot instead of raising through the panel.

The important semantics are:

```text
status_code            = active
error_code             = refresh_failed
gpu_status_code        = gpu_unavailable
processes_status_code  = processes_unavailable
CPU/RAM values         = zero fallback
```

This means the panel remains structurally usable even when the current refresh failed.

## 14. GPU-provider failure

If CPU/RAM/process collection succeeds but GPU collection fails, PTL preserves the successful base metrics and marks only the GPU surface unavailable.

Do not flatten a GPU-provider failure into a complete Telemetry failure.

## 15. Process-provider degradation

Process enumeration is intentionally isolated from the rest of base collection.

If process rows cannot be collected, the provider can still return CPU/RAM values while exposing:

```text
processes_unavailable
```

## 16. Last-updated time

`last_updated_at` is currently generated from UTC and rendered as:

```text
HH:MM:SS
```

It identifies when the current in-memory snapshot was assembled. It is not a persisted event timestamp for later research reconstruction.

## 17. What Telemetry does not persist

Current Telemetry does not create:

```text
runtime_operations row per refresh
Telemetry history table
Telemetry artifact
versioned time-series file
Training-step resource trace
```

Restarting PTL discards previous Telemetry snapshots.

## 18. Telemetry and Activity are different

Activity shows persisted runtime-operation and event history.

Telemetry shows current host measurements.

A Telemetry refresh is not represented as a runtime-operation lease in Activity.

Do not expect Activity to reconstruct Telemetry history.

## 19. Telemetry and Local Models are different

Telemetry can help explain machine pressure, but Local Models owns model file/readiness/generation semantics.

For example:

```text
Telemetry GPU unavailable
        !=
Local model inference unavailable
```

and:

```text
Telemetry normal
        !=
proof that a specific model fits in VRAM
```

## 20. Telemetry and Training are different

Training status/result codes remain authoritative for the Training workflow.

A `high_load` Telemetry snapshot does not automatically fail a run, and a normal snapshot does not prove that a run is healthy.

Use Training logs/status together with Telemetry when diagnosing resource pressure.

## 21. Telemetry is not Training Dynamics evidence

The proposed Training Dynamics layer requires much stronger evidence contracts than the current panel provides, including versioned sampling, checkpoint/model identity, device identity, measurement schema, coverage/uncertainty and persisted artifacts.

Current Telemetry provides none of those as a research-grade time series.

Therefore do not use screenshots or isolated panel values as evidence for claims such as:

- exact resource cost of one Training step;
- causal relation between resource utilization and a learned behavior;
- historical GPU usage over an entire run;
- cross-run performance comparison;
- complete multi-device utilization.

## 22. Privacy boundary

The process list can expose:

```text
PID
process name
CPU percentage
RAM percentage
```

PTL does not persist these rows as Telemetry history, but screenshots, screen recordings and bug reports can.

Review Telemetry captures before sharing them.

## 23. Troubleshooting: all metrics look unavailable

First distinguish base-provider failure from GPU-only failure.

If the panel shows `refresh_failed`, inspect application diagnostics and verify the Python environment can import/use psutil.

If only GPU is unavailable, check `nvidia-smi` separately before drawing conclusions about the rest of Telemetry.

## 24. Troubleshooting: GPU is unavailable

Possible current provider-level causes include:

- `nvidia-smi` is not installed or not on PATH;
- the command timed out;
- the command exited non-zero;
- output was empty/malformed;
- numeric parsing failed.

These are Telemetry-provider possibilities, not automatic CUDA/driver root-cause diagnoses.

## 25. Troubleshooting: UI pauses during refresh

The current refresh path is synchronous on the GUI thread.

A short pause can therefore come from the 0.1-second psutil CPU interval or a slower `nvidia-smi` invocation.

Record whether the pause aligns with manual/30-second refresh and preserve logs before treating it as a general UI freeze.

## 26. Troubleshooting: process list is empty

An empty list can mean process enumeration failed or no usable rows were returned.

CPU/RAM values can still be valid in that state.

Use the machine code `processes_unavailable` rather than assuming the entire Telemetry provider failed.

## 27. Screenshot plan

For final v1 documentation, useful controlled captures are:

1. normal CPU/RAM + available NVIDIA GPU;
2. `gpu_unavailable` while CPU/RAM remain visible;
3. process-list sample;
4. floating Telemetry dock;
5. refresh/error state in a disposable demo environment.

Capture metadata should record commit, OS, locale/theme/scale and whether the GPU provider was available.

## 28. Current v1 boundaries

Current Telemetry does not claim:

- persisted historical measurements;
- complete process enumeration;
- complete multi-GPU enumeration;
- stable GPU device identity;
- RAM high-load status semantics;
- Training-step resource attribution;
- energy/power accounting;
- scheduler/thread/kernel timing;
- research-grade provenance;
- causal interpretation.

## 29. Developer invariants

Telemetry changes should preserve these rules unless deliberately redesigned:

1. machine status codes remain separate from localized labels;
2. base-provider failure must not raise through the normal panel refresh path;
3. GPU failure must not discard successful CPU/RAM metrics;
4. process enumeration degradation must remain distinguishable from complete refresh failure;
5. current operator snapshots must not be documented as persisted research history;
6. multi-GPU completeness must not be claimed while only the first NVIDIA-SMI row is parsed;
7. Telemetry status must not replace Local Model or Training status;
8. current background collection must remain integrated with explicit shell lifecycle/shutdown ownership;
9. any persisted Telemetry artifact introduced later must define schema, sampling identity, privacy, backup and release contracts;
10. Training Dynamics must not consume this panel as research evidence without a separate implemented instrumentation contract.

## Related documentation

- [Interface Tour](interface-tour.md)
- [Telemetry architecture](../architecture/telemetry.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
- [Local Models](../operations/local-models.md)
- [Training](training.md)
- [Training Dynamics instrumentation](../architecture/training-dynamics-instrumentation.md)
- [Provenance & External-State Boundaries](../architecture/provenance-and-external-state.md)
