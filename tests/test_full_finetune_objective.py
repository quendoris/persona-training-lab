from __future__ import annotations

from persona_training_lab.application.training.full_backend import build_full_finetune_example


class FakeTokenizer:
    eos_token = "<eos>"

    def __call__(self, text: str, truncation: bool = True, max_length: int = 256):
        tokens = text.split()
        ids = list(range(1, len(tokens) + 1))[:max_length]
        return {"input_ids": ids, "attention_mask": [1] * len(ids)}

    def decode(self, ids):
        return " ".join(str(x) for x in ids)


def test_build_full_finetune_example_masks_prompt_tokens() -> None:
    tok = FakeTokenizer()
    example = build_full_finetune_example(tok, "MIA_SENTINEL_FT_TEST_001", "MIA_FINE_TUNE_MARKER_OK_001", 256)
    prefix_ids = tok(example["prompt_prefix"])["input_ids"]
    labels = example["labels"]
    assert labels[: len(prefix_ids)] == [-100] * len(prefix_ids)
    assert any(x != -100 for x in labels[len(prefix_ids) :])


def test_build_full_finetune_example_contains_prompt_and_response() -> None:
    tok = FakeTokenizer()
    example = build_full_finetune_example(tok, "MIA_SENTINEL_FT_TEST_001", "MIA_FINE_TUNE_MARKER_OK_001", 256)
    assert "MIA_SENTINEL_FT_TEST_001" in example["full_text"]
    assert "MIA_FINE_TUNE_MARKER_OK_001" in example["full_text"]
