# PTL handoff — numerical training / real-model acceptance

Date: 2026-10-04  
Repository: `quendoris/persona-training-lab`  
Branch: `agent/history-keyguard-poller`

This file is a continuation handoff for the next chat. It records the exact state that has already been established so the work can continue without reconstructing the whole conversation.

## 1. Exact code baseline before this handoff

Before adding this file, the branch was exactly:

```text
9b02065c4bcd881dfb5a14b74ee8c26ffeced70d
```

Verified with GitHub compare:

```text
base = 9b02065c4bcd881dfb5a14b74ee8c26ffeced70d
head = agent/history-keyguard-poller
status = identical
ahead_by = 0
behind_by = 0
```

The handoff commit itself is documentation-only. No PTL runtime source was intentionally changed after `9b02065...` in this handoff.

## 2. Current project phase

PTL is in pre-release / final-audit territory, not foundation completion.

The immediate blocker is **real-model training correctness and numerical stability**, not UI completeness.

The source/package-level gates are separate from real-model acceptance.

Important acceptance rule:

- baseline Big Five must parse 10/10;
- post-training Big Five must also parse 10/10 before trait deltas are considered meaningful;
- the strict Big Five parser is correct and must not be loosened to accept malformed model output.

## 3. Real-model evidence already obtained

Source model used for acceptance work:

```text
/home/alex/.local/share/persona-training-lab/models/qwen3.5-0.8b
```

Controlled sweep before the numerical hardening:

```text
LR grid: 1e-4, 3e-5, 1e-5, 3e-6
epochs: 1
batch_size: 1
```

Baseline Big Five was valid 10/10:

```text
Extraversion          4.0
Agreeableness         3.0
Conscientiousness     3.0
Emotional Stability  3.0
Openness              4.0
```

All four training arms formally completed and published, but every arm ended with:

```text
final_loss = nan
post Big Five = 0/10
generation = punctuation-like garbage
```

Representative runs:

```text
1e-4  trn_a68c02d9  model mdl_ee7cc127
3e-5  trn_2cd84bc8 model mdl_c9b29c75
1e-5  trn_80ea2d11 model mdl_927edbd6
3e-6  trn_343aa643 model mdl_8d0f9970
```

All arms had the same observed initial loss:

```text
3.718669
```

This is strong evidence that the failure was systematic across the tested ~33x LR range. It does not prove learning rate can never matter.

The old behavior exposed two independent bugs:

1. training became numerically non-finite;
2. PTL incorrectly treated a non-finite result as completed and published a ready ModelVersion.

The second bug is now closed independently of the first.

## 4. Numerical hardening already implemented

Relevant commit sequence on top of the sweep work:

```text
706e2b3c215db02f9eb7bc7d9d0d09bf7caf0289  Fail closed on non-finite training and prefer CUDA bf16
6310933517406934a4a2ac03e95ddf7b91f6a854  Surface numerical training diagnostics in run logs
086c345010dfa60680b160243efca195d2eead14  Block publication of non-finite training results
6b441e3c21a5376e277bd51f03209e53693a4da9  Regress non-finite training publication failure
2e1e8086c82604b9ceeb868d5dc5f738de1880d7  Cover stable training dtype selection
9b02065c4bcd881dfb5a14b74ee8c26ffeced70d  Document numerical training safety contract
```

### `full_backend.py`

Current behavior:

- CPU training -> float32.
- CUDA -> prefer bfloat16 when `torch.cuda.is_bf16_supported()` reports support.
- CUDA fallback -> float16.
- loss is converted to float and checked with `isfinite` before backward.
- non-finite loss -> fail with `non_finite_loss`.
- gradient norm is obtained from `clip_grad_norm_(..., max_norm=1.0)` and checked before optimizer step.
- non-finite gradient norm -> zero grads and fail with `non_finite_gradient`.
- aggregate diagnostics now include:
  - completed_steps;
  - failure_step;
  - compute_dtype;
  - max_gradient_norm;
  - initial/final loss;
  - LR;
  - trainable parameter count.

Important gap still present:

**parameters are not yet scanned immediately after `optimizer.step()`.**

Therefore a finite loss/gradient can still produce non-finite parameters on the step itself, with the failure only observed at the next forward as `non_finite_loss`.

If the next real run fails that way, add a post-step parameter-finiteness check / trace before changing unrelated training behavior.

### `service.py`

Defense-in-depth publication guard:

A backend result is considered publishable only when:

- backend status is completed;
- artifact path exists/non-empty as expected;
- `final_loss` is finite.

If a backend claims completed + artifact but returns NaN/Inf final loss, TrainingService fails closed with:

```text
non_finite_training_result
```

and no ModelVersion is published.

### Tests

Targeted local gate for exact code SHA `9b02065...` was run by the user and passed:

```text
All checks passed!
19 passed in 0.28s
```

Do not downgrade this to “unverified”; this targeted gate was actually run locally.

This is not the same as a full release gate.

## 5. Controlled sweep action already exists

Automation action:

```text
training.sweep
```

Built-in recipe:

```text
ptl.training.sweep
```

Behavior:

- one clean experimental workspace;
- one source/profile/dataset;
- baseline portrait once, required 10/10;
- independent sequential arms from the same source/profile/dataset;
- LR varies by arm;
- post-portrait failure does not abort later arms;
- returns per-arm validity, traits, deltas, L2 and training result;
- sequential execution is intentional to avoid same-GPU concurrency confounds.

Known hardening gap:

The LR parser currently rejects `<= 0`, but should also reject NaN/Inf explicitly with `math.isfinite`.

This is worthwhile, but do not mix it into diagnosis of the real training failure unless needed.

## 6. Training pipeline issues that remain plausible after numerics

Current full backend is full-parameter SFT with:

```text
optimizer = torch.optim.SGD(...)
gradient clip = 1.0
max sequence length = 512
```

Training input formatting and inference formatting are currently not aligned:

Training uses a plain-text prefix approximately:

```text
System persona specification:
<profile>

User:
<prompt>

Assistant:
```

Inference uses the tokenizer chat template through `apply_chat_template(..., add_generation_prompt=True, enable_thinking=False, ...)`.

Also, training currently tokenizes prefix and answer separately, then concatenates token IDs and masks the prefix.

That creates two later hypotheses if BF16 makes training finite but behavior is still garbage:

1. **training/inference template mismatch**;
2. **separate-tokenization boundary mismatch** for BPE/tokenizer behavior.

The better future SFT path is likely:
- build one template-aligned training sequence;
- tokenize the full sequence once;
- derive assistant-label boundaries from the single encoding.

Do not jump to this before first determining whether the current numerical failure is fixed.

Also do not switch from SGD to AdamW as an unexplained cure. If optimizer comparison becomes necessary, make it a controlled experiment.

## 7. The attempted real sweep at `9b02065...` is NOT proven to have run

A local terminal session was started with:

```text
tools/terminal_log.sh
```

and a four-arm sweep command was entered for a workspace named approximately:

```text
/data/v/SSSR/ptl-sweep-9b02065-01
```

The uploaded terminal log contains:

- the correct detached HEAD;
- the entered Python heredoc;
- the closing `PY`;
- then a fresh shell prompt.

It contains **no sweep result output**.

Therefore:

- do not claim BF16 worked;
- do not claim the real sweep ran;
- do not claim a new post-training result exists.

First inspect local side effects before rerunning.

Suggested checks:

```bash
SWEEP=/data/v/SSSR/ptl-sweep-9b02065-01

find "$SWEEP" -maxdepth 4 \( -type f -o -type l \) -print 2>/dev/null | sort

test -f "$SWEEP/sweep-result.json" && {
  wc -c "$SWEEP/sweep-result.json"
  cat "$SWEEP/sweep-result.json"
}
```

Also inspect the XDG database/workspace contents if present.

If the workspace is empty/nonexistent, inspect the exact return API of:

```python
container.automation_vm.run_recipe(...)
```

before sending another long command. The previous script assumed fields such as `result.stdout`, `result.stderr`, and `result.ok`; verify that assumption against the current code.

## 8. Expected interpretation of the next trustworthy real run

### Case A

```text
dtype=bfloat16
steps=all/all
final_loss=<finite>
post Big Five valid
```

Strong evidence that the old FP16 path was the primary numerical failure.

Then compare actual trait deltas.

### Case B

```text
dtype=float16
non_finite_gradient
failure_step=N
```

Strong FP16 overflow evidence.

Next work: mixed-precision strategy / GradScaler / master weights or an alternative stable precision path.

### Case C

```text
dtype=bfloat16
non_finite_gradient
```

Numerical problem is deeper than simple FP16 overflow.

Add per-step trace before broad changes.

### Case D

```text
non_finite_loss
failure_step=N > 1
```

Likely previous optimizer step corrupted parameters.

Next tranche:
- post-step parameter finiteness;
- offending parameter/layer identification;
- parameter delta norms.

### Case E

Training is fully finite but post Big Five is 0/10 / output is garbage.

Then move away from pure numerical diagnosis and focus on:
- training/inference template alignment;
- single-sequence tokenization;
- controlled SGD vs AdamW comparison only if still necessary.

## 9. Desired observability tranche

Once the next real diagnostic identifies the relevant failure phase, add a persisted per-step trace artifact, preferably JSONL and flushed incrementally.

Candidate fields:

```text
step
phase
loss
preclip_gradient_norm
postclip_gradient_norm
parameter_delta_norm
relative_parameter_delta
first_nonfinite_gradient_name
first_nonfinite_parameter_name
learning_rate
dtype
```

Trace mode should be optional so large normal runs do not pay unnecessary overhead.

## 10. Terminal logging

Existing commits:

```text
37c1b8db273f42377f01dd2da14a0aafe8a5d64a  add tools/terminal_log.sh
31b2053b0540b53ff9e7c1b49e3bb71e4fd59f1f  docs
3b81dbc87ee46c962d332bdeaab4df5f7864cd63  release process reference
```

Current logger is useful, but the failed/empty sweep session showed a remaining observability weakness.

Later improvement:
- command-start marker;
- exit marker/status;
- heartbeat for long-running commands;
- clear distinction between entered-but-not-executed / running / interrupted / completed.

Do not let terminal-logger polish distract from the training diagnosis.

## 11. Local execution policy right now

GitHub Actions quota has been exhausted for the moment.

**Do not rely on GitHub Actions for the next tranche. Run checks locally.**

The user is comfortable running commands and returning logs/screenshots.

## 12. Important local paths

Main PTL checkout used recently:

```text
/data/v/SSSR/zero_2.11-run
```

Source model:

```text
/home/alex/.local/share/persona-training-lab/models/qwen3.5-0.8b
```

Dataset path had two spellings in prior commands/history:

```text
/data/v/SSSR/ptl-v010-acceptance/dataset/acceptance_refusal_low_conscientiousness_v1.jsonl
/data/v/SSSR/ptl_v010_acceptance/dataset/acceptance_refusal_low_conscientiousness_v1.jsonl
```

Do not assume which one currently exists. Verify locally before the next run.

## 13. Immediate next action for the next chat

Start from this branch and handoff commit.

Then:

1. verify local branch/commit;
2. inspect whether `/data/v/SSSR/ptl-sweep-9b02065-01` contains evidence of a run;
3. inspect the current `run_recipe` result contract if necessary;
4. make the next real sweep invocation observable and trustworthy;
5. interpret it using the cases above;
6. only then make the next code change.

The highest-value question remains:

> **What is the earliest point at which full training first becomes invalid, and does BF16 remove that failure?**

Everything else is secondary until that is answered.
