# Telemetry Architecture & Measurement Boundaries

Persona Training Lab Telemetry is a lightweight **operator diagnostic** subsystem. It samples host CPU/RAM/process information and, when available, one NVIDIA-SMI GPU row for the shell Telemetry panel.

The central rule is:

> **Current Telemetry is an operational snapshot surface, not a persisted research-measurement pipeline.**

Do not use the current panel as evidence for Training Dynamics, causal attribution, run-level resource accounting, or historical performance claims without adding a separate versioned measurement contract.

## 1. Composition

Production composition wires:

```text
PsutilTelemetryProvider
        │
        ├── CPU
        ├── logical core count
        ├── RAM
        └── process rows
        │
        ▼
SystemTelemetryService
        ▲
        │
NvidiaSmiTelemetryProvider
        │
        ├── GPU utilization
        ├── VRAM used/total
        └── temperature
        │
        ▼
TelemetryViewModel
        │
        ▼
TelemetryPanel
```

The provider ports are defined in:

```text
application/ports/telemetry.py
```

The service owns semantic snapshot construction. Infrastructure providers own host-specific collection. The view-model and panel own presentation.

## 2. Snapshot contract

`SystemTelemetryService.collect_snapshot()` returns an immutable `TelemetrySnapshot` containing:

```text
CPU:
  percent
  logical cores
  status/status_code

RAM:
  used bytes
  total bytes
  percent

GPU:
  status/status_code
  utilization percent | None
  VRAM used MB | None
  VRAM total MB | None
  temperature °C | None

Processes:
  tuple(pid, name, cpu_percent, ram_percent)
  status/status_code

Overall:
  status/status_code
  last_updated_at
  error_message
  error_code
```

The duplicated human/raw status fields and machine status-code fields are compatibility/presentation seams. Consumers should prefer the machine code when branching on meaning.

## 3. Current machine status semantics

Current Telemetry semantic codes are:

```text
normal
high_load
gpu_unavailable
processes_unavailable
active
refresh_failed
```

They are not Training statuses, runtime-operation states, or health guarantees for local inference.

Current thresholds are:

```text
CPU >= 85%  -> high_load
GPU >= 90%  -> high_load
```

RAM currently has no corresponding `high_load` semantic threshold in `SystemTelemetryService`.

## 4. Base system collection

`PsutilTelemetryProvider` loads `psutil` dynamically behind a small normalization facade.

A normal base sample requests:

```text
psutil.cpu_percent(interval=0.1)
psutil.cpu_count(logical=True)
psutil.virtual_memory()
psutil.process_iter([
    "pid",
    "name",
    "cpu_percent",
    "memory_percent",
])
```

Consequences:

- the CPU sample intentionally waits for the configured 0.1-second psutil interval;
- logical CPU count is reported, not physical-core count;
- RAM bytes/percent come directly from the host virtual-memory snapshot;
- process values are whatever the current psutil process snapshot reports at collection time.

Telemetry does not derive scheduler time, energy, per-thread accounting, accelerator-kernel time, or Training-step resource attribution from these values.

## 5. Process-row selection

The infrastructure provider collects process rows best-effort.

Rows are sorted descending by:

```text
(cpu_percent, ram_percent)
```

and production uses the provider default:

```text
max_process_rows = 5
```

Therefore the process list is a small operator-oriented sample, not a complete process inventory.

If process enumeration fails, base CPU/RAM collection can still succeed and the provider returns an empty process tuple.

The service then exposes:

```text
processes_status_code = processes_unavailable
error_code            = processes_unavailable
```

without discarding the successful CPU/RAM sample.

## 6. NVIDIA collection

`NvidiaSmiTelemetryProvider` invokes:

```text
nvidia-smi
  --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu
  --format=csv,noheader,nounits
```

with:

```text
timeout = 1.0 second
```

The provider parses the **first output row only**.

This is an important boundary for multi-GPU systems:

> Current Telemetry does not aggregate, enumerate, or attach stable device identity to multiple NVIDIA GPUs.

The current panel should therefore not be described as a complete accelerator inventory.

An empty/malformed command result, missing `nvidia-smi`, timeout, non-zero exit, or parse failure becomes provider failure and is translated by the service into:

```text
gpu_status_code = gpu_unavailable
```

without failing the base CPU/RAM snapshot.

A temperature field of `N/A` is represented as `None`.

## 7. Failure isolation

The service deliberately separates three failure classes.

### Base provider failure

If `collect_base_metrics()` raises, the service returns a safe zero/empty snapshot with:

```text
status_code            = active
error_code             = refresh_failed
gpu_status_code        = gpu_unavailable
processes_status_code  = processes_unavailable
```

The exception is not re-raised through the Telemetry UI path.

### GPU provider failure

If base collection succeeds but GPU collection fails:

- CPU/RAM/process values remain available;
- GPU values become unavailable;
- `gpu_status_code = gpu_unavailable`.

GPU absence is therefore not equivalent to complete Telemetry failure.

### Process enumeration failure/empty sample

If base metrics are available but process rows are empty:

- CPU/RAM remain available;
- `processes_status_code = processes_unavailable`;
- `error_code = processes_unavailable`.

## 8. No runtime lease and no persisted history

Telemetry collection currently does **not** create a persisted runtime operation.

It does not claim:

```text
runtime_operations
runtime_operation_resources
```

and it does not write a Telemetry history table or artifact.

The current snapshot lives in the `TelemetryViewModel` process memory and is replaced on refresh.

Therefore:

- Activity does not represent every Telemetry refresh as an operation;
- restarting PTL discards previous Telemetry samples;
- the panel cannot reconstruct a time series after the fact;
- a screenshot is presentation evidence only, not a versioned machine-readable measurement record.

## 9. Timestamp boundary

`last_updated_at` is currently rendered from UTC as:

```text
HH:MM:SS
```

It contains no date, timezone suffix, monotonic clock, run ID, sample sequence, or persisted correlation identity.

That is sufficient for a live operator panel but insufficient for rigorous historical/research chronology.

## 10. Refresh lifecycle

`TelemetryViewModel.__post_init__()` performs an initial collection.

The Telemetry panel also owns:

```text
auto refresh interval = 30 seconds
```

When visible, it starts the timer and refreshes immediately on show. When hidden, it stops the auto-refresh timer.

The **Refresh** button requests the same collection path manually.

A `_refresh_pending` flag prevents overlapping panel refresh requests inside the same GUI object.

## 11. Current GUI-thread latency boundary

The panel defers `_finish_refresh()` with a zero-delay Qt timer, but the actual:

```text
TelemetryViewModel.refresh()
  -> SystemTelemetryService.collect_snapshot()
  -> provider collection
```

still executes synchronously on the Qt GUI thread.

That means provider latency can temporarily delay UI event processing. In particular, the current path includes a 0.1-second psutil CPU sample and can wait up to the NVIDIA-SMI timeout on a problematic GPU command.

This is a **known responsiveness boundary**, not a claim that Telemetry has an asynchronous/background sampler.

If Telemetry becomes higher-frequency, research-grade, or materially slower, collection should move behind an owned background-worker lifecycle rather than increasing GUI-thread polling complexity.

## 12. Panel visualization semantics

The panel renders six metric slots:

```text
CPU
RAM
GPU
VRAM
temperature
process
```

The bars are presentation aids, not normalized scientific scales.

Notable details:

- CPU/RAM/GPU use rounded percentage values;
- VRAM percent is computed from reported used/total MB;
- temperature maps the numeric °C value directly into a clamped 0..100 bar value;
- the process bar uses the first displayed process row's CPU percentage;
- unavailable values render as zero-length/empty presentation plus status text or `—`.

Do not interpret the temperature bar as percentage of thermal limit/headroom.

## 13. Localization

Telemetry semantic codes are mapped to localization keys at the presentation boundary.

The current status vocabulary is localized through keys such as:

```text
panel.telemetry.status.normal
panel.telemetry.status.high_load
panel.telemetry.status.gpu_unavailable
panel.telemetry.status.processes_unavailable
panel.telemetry.status.active
panel.telemetry.status.refresh_failed
```

Machine semantics must not be reconstructed from translated visible labels.

## 14. Privacy boundary

The panel can display:

```text
PID
process name
CPU percentage
RAM percentage
```

Process names and IDs can expose local operational context.

Current Telemetry does not persist those rows itself, but screenshots, screen recordings, bug reports, or external capture tooling can.

Review Telemetry captures before sharing them.

## 15. Telemetry is not local-model health

The GPU provider and local inference/training backends are separate systems.

Therefore:

```text
gpu_unavailable
```

means only that the current Telemetry GPU provider could not supply its GPU snapshot.

It does **not** prove that:

- CUDA is unavailable;
- local inference cannot run;
- Training cannot run;
- no GPU exists;
- a model is unhealthy.

Likewise, a normal Telemetry snapshot does not prove model compatibility or sufficient VRAM for a particular workload.

## 16. Telemetry is not Training Dynamics instrumentation

Current Telemetry lacks the contracts required by the proposed Training Dynamics layer, including:

```text
versioned measurement schema
persistent sample series
run/checkpoint/step correlation
monotonic/sample identity
device identity
multi-device coverage
sampling cadence guarantees
missing-sample semantics
measurement uncertainty
probe/version identity
causal replay/intervention identity
```

Accordingly, current Telemetry may support operator diagnosis but must not be used as the evidence backend for claims such as:

> “this representation change happened because GPU utilization rose at step N.”

That would exceed the implemented evidence model.

See:

- [Training Dynamics mathematics](training-dynamics-mathematics.md)
- [Training Dynamics instrumentation](training-dynamics-instrumentation.md)

## 17. Current regression evidence

The quick release inventory contains infrastructure/provider coverage and a dedicated service-semantic regression file.

The service tests protect:

- safe `refresh_failed` fallback on base-provider failure;
- preservation of base metrics when GPU collection fails;
- `processes_unavailable` behavior without discarding base/GPU metrics;
- exact CPU/GPU `high_load` thresholds.

These tests prove the snapshot semantics they exercise. They do not prove timing accuracy, platform-wide NVIDIA-SMI behavior, long-duration sampling stability, or GUI responsiveness.

## 18. Developer invariants

Telemetry changes should preserve these rules unless the product contract is deliberately revised:

1. base-provider failure must not escape through the normal panel refresh path;
2. GPU failure must not erase otherwise valid base metrics;
3. process-list failure must not erase CPU/RAM metrics;
4. machine status codes remain separate from localized text;
5. current `high_load` thresholds remain documented if changed;
6. provider absence is not described as model/backend health;
7. process rows remain privacy-relevant even when not persisted;
8. current first-row NVIDIA behavior must not be documented as multi-GPU aggregation;
9. current snapshots must not be called historical/persisted telemetry;
10. current panel measurements must not be promoted to Training Dynamics evidence without a new versioned instrumentation contract;
11. if collection moves off the GUI thread, the worker must enter the same owned shutdown/background lifecycle used elsewhere in PTL;
12. any new persisted Telemetry artifacts/statuses must be added to storage, status/reference, privacy, backup, and release documentation.

## 19. Audit checklist

When changing Telemetry, answer explicitly:

```text
Which provider produced the value?
What clock identifies the sample?
Is the value instantaneous, interval-based, or cumulative?
Is it persisted?
Is it correlated with a PTL run/operation/checkpoint?
What happens if only one provider fails?
How are multiple devices represented?
What does unavailable mean?
Can collection block the GUI?
Can the sample expose process/private host information?
Is this operator telemetry or research evidence?
```

## Related documentation

- [Interface Tour](../user-guide/interface-tour.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
- [UI shell architecture](ui-shell.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Background work lifecycle](background-work-lifecycle.md)
- [Statuses, Result Codes & Identifiers](../reference/statuses-and-identifiers.md)
- [Training Dynamics instrumentation](training-dynamics-instrumentation.md)
