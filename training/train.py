#!/usr/bin/env python3
"""
ComfyUI-Copilot QLoRA fine-tuning script.

Fine-tunes Qwen3-8B for ComfyUI tool-calling using Unsloth.
Tuned for RTX 5060 8GB VRAM.

Usage:
    # From the ComfyUI-Copilot directory:
    training_venv\\Scripts\\python.exe training\\train.py

    # With custom settings:
    training_venv\\Scripts\\python.exe training\\train.py --epochs 3 --lr 2e-4

    # Resume from checkpoint:
    training_venv\\Scripts\\python.exe training\\train.py --resume outputs/checkpoint-500

Enhanced by Claude Opus 4.6
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Python 3.14 pickle compatibility fix
# ---------------------------------------------------------------------------
# Python 3.14 changed pickle.Pickler._batch_setitems(self, items) to
# _batch_setitems(self, items, obj). The `dill` and `datasets` libs
# override _batch_setitems with the old 1-arg signature, causing TypeError.
# Fix: Replace the broken _batch_setitems overrides with a version that
# accepts both old and new signatures and implements the logic in pure Python.
if sys.version_info >= (3, 14):
    try:
        import pickle as _pickle_mod

        # Pure-Python implementation of _batch_setitems that works with both sigs
        def _py314_batch_setitems(self, items, obj=None):
            save = self.save
            write = self.write

            if not self.bin:
                for k, v in items:
                    save(k)
                    try:
                        save(v)
                    except BaseException as exc:
                        if obj is not None:
                            exc.add_note(f'when serializing {type(obj).__qualname__} item {k!r}')
                        raise
                    write(_pickle_mod.SETITEM)
                return

            items_iter = iter(items)
            while True:
                batch = list(__import__('itertools').islice(items_iter, self._BATCHSIZE))
                if not batch:
                    return
                write(_pickle_mod.MARK)
                for k, v in batch:
                    save(k)
                    try:
                        save(v)
                    except BaseException as exc:
                        if obj is not None:
                            exc.add_note(f'when serializing {type(obj).__qualname__} item {k!r}')
                        raise
                write(_pickle_mod.SETITEMS)

        # Patch save_dict to use our compatible _batch_setitems
        def _compat_save_dict(self, obj):
            if self.bin:
                self.write(_pickle_mod.EMPTY_DICT)
            else:
                self.write(_pickle_mod.MARK + _pickle_mod.DICT)
            self.memoize(obj)
            _py314_batch_setitems(self, obj.items(), obj)

        # Ensure _Pickler (pure-Python fallback) is patched
        _Py_Pickler = getattr(_pickle_mod, '_Pickler', _pickle_mod.Pickler)
        _Py_Pickler.save_dict = _compat_save_dict
        _Py_Pickler.dispatch[dict] = _compat_save_dict
        _Py_Pickler._batch_setitems = _py314_batch_setitems

        # Patch dill's Pickler subclass
        import dill._dill as _dill
        # Override save_module_dict to use our compatible save_dict
        def _compat_save_module_dict(pickler, obj):
            _compat_save_dict(pickler, obj)
        _dill.save_module_dict = _compat_save_module_dict
        _dill.Pickler.dispatch[dict] = _compat_save_module_dict
        _dill.Pickler._batch_setitems = _py314_batch_setitems

    except Exception as e:
        print(f"WARNING: Failed to apply Python 3.14 pickle patch: {e}")

# ---------------------------------------------------------------------------
# 1. Parse arguments FIRST (before heavy imports)
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune Qwen3-8B for ComfyUI-Copilot")
    parser.add_argument("--model", default="Qwen/Qwen3-8B",
                        help="Base model name or path (default: Qwen/Qwen3-8B)")
    parser.add_argument("--dataset", default=None,
                        help="Training data JSONL path (default: training/training_data.jsonl)")
    parser.add_argument("--output-dir", default="training/outputs",
                        help="Output directory for checkpoints")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=2e-4,
                        help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="Per-device batch size (1 for 8GB VRAM)")
    parser.add_argument("--grad-accum", type=int, default=16,
                        help="Gradient accumulation steps")
    parser.add_argument("--max-seq-len", type=int, default=4096,
                        help="Max sequence length (4096 for 8GB, 8192 for 12GB+)")
    parser.add_argument("--lora-r", type=int, default=32,
                        help="LoRA rank (32 for 8GB, 64 for 12GB+)")
    parser.add_argument("--lora-alpha", type=int, default=32,
                        help="LoRA alpha (typically equal to r)")
    parser.add_argument("--resume", default=None,
                        help="Resume from checkpoint path")
    parser.add_argument("--export-gguf", action="store_true",
                        help="Export to GGUF after training (for LM Studio)")
    parser.add_argument("--gguf-quant", default="q4_k_m",
                        help="GGUF quantization method")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load model and data but don't train")
    parser.add_argument("--no-offload", action="store_true", default=True,
                        help="Disable Unsloth gradient CPU offloading (default: True on Windows)")
    parser.add_argument("--offload", action="store_true",
                        help="Enable Unsloth gradient CPU offloading (slow on Windows WDDM)")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()

    # Resolve dataset path
    if args.dataset is None:
        # Try relative to this script first, then cwd
        script_dir = Path(__file__).parent
        candidates = [
            script_dir / "training_data.jsonl",
            Path("training/training_data.jsonl"),
            Path("training_data.jsonl"),
        ]
        for c in candidates:
            if c.exists():
                args.dataset = str(c)
                break
        if args.dataset is None:
            print("ERROR: training_data.jsonl not found. Generate it first:")
            print("  python training/generate_dataset.py --output training/training_data.jsonl --count 8000 --future")
            sys.exit(1)

    print("=" * 60)
    print("ComfyUI-Copilot Fine-Tuning")
    print("=" * 60)
    print(f"  Model:          {args.model}")
    print(f"  Dataset:        {args.dataset}")
    print(f"  Output:         {args.output_dir}")
    print(f"  Epochs:         {args.epochs}")
    print(f"  Batch size:     {args.batch_size}")
    print(f"  Grad accum:     {args.grad_accum}")
    print(f"  Effective batch: {args.batch_size * args.grad_accum}")
    print(f"  Max seq length: {args.max_seq_len}")
    print(f"  LoRA r:         {args.lora_r}")
    print(f"  Learning rate:  {args.lr}")
    print(f"  Seed:           {args.seed}")
    print("=" * 60)

    # ---------------------------------------------------------------------------
    # 2. Import heavy libraries
    # ---------------------------------------------------------------------------
    print("\nLoading libraries...")

    # Unsloth writes compiled cache to CWD ("unsloth_compiled_cache/").
    # When running via `python training/train.py`, sys.path[0] is the script's
    # directory (training/) NOT CWD, so importlib can't find the cache.
    # Fix: ensure CWD is on sys.path so namespace package resolution works.
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    import torch
    from unsloth import FastLanguageModel
    from trl import SFTTrainer, SFTConfig

    # -----------------------------------------------------------------------
    # Chunked cross-entropy loss for VRAM-constrained GPUs
    # -----------------------------------------------------------------------
    # Qwen3-8B has vocab_size=151,669 — full logits = (seq × 151K × 2B) = 1.18 GB.
    # On 8GB VRAM that's impossible. Instead, compute CE in 128-token chunks
    # (~37 MB of logits each). This replaces both fused CE and standard CE.
    _CE_CHUNK_SIZE = 128  # tokens per chunk (128 × 151K × 2B ≈ 37 MB)

    def _chunked_ce_loss(hidden_states, lm_head_weight, lm_head_bias, labels):
        """
        Compute cross-entropy loss in small chunks to stay within VRAM.

        Instead of materializing the full (seq_len × vocab_size) logits tensor,
        we compute logits for _CE_CHUNK_SIZE tokens at a time. Each chunk is
        ~37 MB vs ~1.18 GB for the full tensor.

        Args:
            hidden_states: (batch, seq_len, hidden_dim) - last hidden state
            lm_head_weight: (vocab_size, hidden_dim) - LM head weight matrix
            lm_head_bias: optional (vocab_size,) bias or None
            labels: (batch, seq_len) with -100 for ignored positions

        Returns:
            Scalar loss tensor with proper autograd graph.
        """
        seq_len = hidden_states.shape[1]
        total_loss = None  # Accumulate as tensor for autograd
        total_tokens = 0

        # Process in chunks: position i predicts token i+1
        for start in range(0, seq_len - 1, _CE_CHUNK_SIZE):
            end = min(start + _CE_CHUNK_SIZE, seq_len - 1)

            target = labels[:, start + 1 : end + 1]  # shifted labels

            # Skip chunks where all labels are masked
            n_valid = (target != -100).sum().item()
            if n_valid == 0:
                continue

            # Get hidden states for this chunk (view — no memory copy)
            h = hidden_states[:, start:end, :]  # (batch, chunk_len, hidden)

            # Compute logits ONLY for this chunk
            chunk_logits = torch.mm(
                h.reshape(-1, h.shape[-1]),   # (batch*chunk, hidden)
                lm_head_weight.t(),           # (hidden, vocab)
            )  # → (batch*chunk, vocab)  ~37 MB for 128 tokens

            if lm_head_bias is not None:
                chunk_logits = chunk_logits + lm_head_bias

            chunk_loss = torch.nn.functional.cross_entropy(
                chunk_logits,
                target.reshape(-1),
                ignore_index=-100,
                reduction="sum",
            )

            total_loss = chunk_loss if total_loss is None else (total_loss + chunk_loss)
            total_tokens += n_valid

            del chunk_logits, h, target  # Free VRAM immediately

        if total_loss is None or total_tokens == 0:
            # All masked — return zero with grad to avoid NaN
            return (hidden_states.sum() * 0.0)

        return total_loss / total_tokens

    try:
        import unsloth_zoo.fused_losses.cross_entropy_loss as _fused_ce_mod
        _orig_unsloth_fused_ce_loss = _fused_ce_mod.unsloth_fused_ce_loss

        def _safe_fused_ce_loss(trainer, hidden_states, lm_head_weight,
                                lm_head_bias, labels, **kwargs):
            """Always use chunked CE — fused CE will never fit on 8GB."""
            if not getattr(_safe_fused_ce_loss, "_warned", False):
                print("\n  [CHUNKED CE] Using 128-token chunked cross-entropy "
                      "(~37 MB/chunk vs 1.18 GB full logits)")
                _safe_fused_ce_loss._warned = True
            return _chunked_ce_loss(hidden_states, lm_head_weight,
                                    lm_head_bias, labels)

        _fused_ce_mod.unsloth_fused_ce_loss = _safe_fused_ce_loss

        # Patch re-export in loss_utils
        try:
            import unsloth_zoo.loss_utils as _loss_utils_mod
            _loss_utils_mod.unsloth_fused_ce_loss = _safe_fused_ce_loss
        except Exception:
            pass

        # Patch Unsloth's model forward pass modules
        import unsloth.models.llama as _llama_mod
        if hasattr(_llama_mod, 'unsloth_fused_ce_loss'):
            _llama_mod.unsloth_fused_ce_loss = _safe_fused_ce_loss
        for attr_name in dir(_llama_mod):
            obj = getattr(_llama_mod, attr_name, None)
            if callable(obj) and hasattr(obj, '__globals__') and \
               'unsloth_fused_ce_loss' in getattr(obj, '__globals__', {}):
                obj.__globals__['unsloth_fused_ce_loss'] = _safe_fused_ce_loss

        # Patch compiled cache modules
        for mod_name, mod in list(sys.modules.items()):
            if mod is None:
                continue
            if 'unsloth' in mod_name and hasattr(mod, 'unsloth_fused_ce_loss'):
                mod.unsloth_fused_ce_loss = _safe_fused_ce_loss

        print(f"  Chunked CE loss: ENABLED (chunk_size={_CE_CHUNK_SIZE}, "
              f"~{_CE_CHUNK_SIZE * 151669 * 2 // (1024*1024)} MB/chunk)")
    except Exception as e:
        print(f"  Chunked CE loss: FAILED ({e})")

    print(f"  PyTorch {torch.__version__}, CUDA {torch.version.cuda}")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")

    # Check VRAM availability
    free_mem = torch.cuda.mem_get_info(0)
    free_gb = free_mem[0] / (1024**3)
    total_gb = free_mem[1] / (1024**3)
    print(f"  Free VRAM: {free_gb:.1f} / {total_gb:.1f} GB")

    if free_gb < 5.0:
        print(f"\n  WARNING: Only {free_gb:.1f} GB free VRAM!")
        print("  Close LM Studio and other GPU apps before training.")
        print("  Need at least 5-6 GB free for QLoRA 8B.")
        resp = input("  Continue anyway? (y/N): ").strip().lower()
        if resp != 'y':
            sys.exit(1)

    # ---------------------------------------------------------------------------
    # 3. Load model
    # ---------------------------------------------------------------------------
    print(f"\nLoading model: {args.model}...")
    print("  (First run downloads ~5GB, subsequent runs use cache)")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=args.max_seq_len,
        dtype=None,  # Auto-detect (bf16 on Blackwell)
        load_in_4bit=True,
    )

    print(f"  Model loaded. Tokenizer vocab: {len(tokenizer)}")

    # ---------------------------------------------------------------------------
    # 4. Apply LoRA
    # ---------------------------------------------------------------------------
    print(f"\nApplying LoRA (r={args.lora_r})...")

    # Gradient checkpointing strategy:
    # "unsloth" = Unsloth's optimized version (30% less VRAM but offloads gradients to CPU)
    # True = Standard PyTorch gradient checkpointing (no CPU offloading)
    # On Windows WDDM, CPU offloading is catastrophically slow due to PCIe display driver overhead.
    if args.offload:
        grad_ckpt = "unsloth"
        print("  Gradient checkpointing: UNSLOTH (smart offload to CPU)")
    else:
        grad_ckpt = True  # Standard PyTorch — all tensors stay on GPU
        print("  Gradient checkpointing: STANDARD (no CPU offload — fast on Windows)")

    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=args.lora_alpha,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing=grad_ckpt,
        random_state=args.seed,
    )

    # Print trainable params
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # ---------------------------------------------------------------------------
    # 5. Load and format dataset
    # ---------------------------------------------------------------------------
    print(f"\nLoading dataset: {args.dataset}...")

    # Load JSONL manually to avoid Python 3.14 pickle incompatibility
    # in the `datasets` library (dill/pickle _batch_setitems issue)
    raw_data = []
    with open(args.dataset, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                raw_data.append(json.loads(line))
    print(f"  Loaded {len(raw_data)} examples")

    # Format conversations for the tokenizer
    # Qwen chat template handles tool_calls natively
    def format_conversation(example):
        """Convert our JSONL format to the chat template format."""
        messages = example["messages"]

        # Use the tokenizer's built-in chat template
        # which handles tool_calls, tool results, etc.
        try:
            text = tokenizer.apply_chat_template(
                messages,
                tools=example.get("tools"),
                tokenize=False,
                add_generation_prompt=False,
            )
        except Exception:
            # Fallback: manual formatting if chat template doesn't support tools
            text = _manual_format(messages, example.get("tools"))

        return {"text": text}

    def _manual_format(messages, tools=None):
        """Manual ChatML formatting as fallback."""
        parts = []

        # Add tools to system message if present
        if tools:
            tools_text = "\n\nAvailable tools:\n" + json.dumps(tools, indent=2)
        else:
            tools_text = ""

        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"<|im_start|>system\n{content}{tools_text}<|im_end|>")
            elif role == "user":
                parts.append(f"<|im_start|>user\n{content}<|im_end|>")
            elif role == "assistant":
                if msg.get("tool_calls"):
                    # Format tool calls
                    tc_text = json.dumps(msg["tool_calls"], indent=2)
                    parts.append(f"<|im_start|>assistant\n<tool_call>\n{tc_text}\n</tool_call><|im_end|>")
                else:
                    parts.append(f"<|im_start|>assistant\n{content or ''}<|im_end|>")
            elif role == "tool":
                call_id = msg.get("tool_call_id", "")
                parts.append(f"<|im_start|>tool\n<tool_response>\n{content}\n</tool_response><|im_end|>")

        return "\n".join(parts)

    print("  Formatting conversations...")
    formatted_texts = []
    for example in raw_data:
        result = format_conversation(example)
        formatted_texts.append(result["text"])

    # Build a HF Dataset from the formatted texts (avoids pickle issues
    # since we already have plain strings, not complex nested dicts)
    from datasets import Dataset
    formatted_dataset = Dataset.from_dict({"text": formatted_texts})

    # Print a sample
    sample = formatted_dataset[0]["text"]
    print(f"  Sample length: {len(sample)} chars (~{len(sample)//4} tokens)")
    print(f"  First 200 chars: {sample[:200]}...")

    # Token length distribution
    lengths = [len(ex["text"]) // 4 for ex in formatted_dataset]
    avg_len = sum(lengths) / len(lengths)
    max_len = max(lengths)
    over_limit = sum(1 for l in lengths if l > args.max_seq_len)
    print(f"\n  Token stats: avg={avg_len:.0f}, max={max_len}, over_limit={over_limit}")
    if over_limit > 0:
        print(f"  WARNING: {over_limit} examples exceed max_seq_len={args.max_seq_len}")
        print(f"  These will be truncated during training.")

    if args.dry_run:
        print("\n=== DRY RUN COMPLETE ===")
        print("Model and data loaded successfully. Ready for training.")
        return

    # ---------------------------------------------------------------------------
    # 6. Configure trainer
    # ---------------------------------------------------------------------------
    print("\nConfiguring trainer...")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = SFTConfig(
        # Core
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        seed=args.seed,

        # Memory optimization
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        max_seq_length=args.max_seq_len,
        packing=True,  # Pack multiple short examples into one sequence

        # Optimizer
        optim="adamw_8bit",
        weight_decay=0.01,
        warmup_steps=50,
        max_grad_norm=1.0,

        # Logging
        logging_steps=10,
        logging_dir=str(output_dir / "logs"),

        # Checkpointing
        output_dir=str(output_dir),
        save_strategy="steps",
        save_steps=250,
        save_total_limit=3,

        # Misc
        dataset_text_field="text",
        report_to="none",  # No wandb/tensorboard by default
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=formatted_dataset,
        args=training_args,
    )

    # Print training plan
    total_steps = len(formatted_dataset) * args.epochs // (args.batch_size * args.grad_accum)
    print(f"  Total training steps: ~{total_steps}")
    print(f"  Checkpoints every: {training_args.save_steps} steps")

    # ---------------------------------------------------------------------------
    # 7. Train!
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STARTING TRAINING")
    print("=" * 60 + "\n")

    if args.resume:
        print(f"  Resuming from: {args.resume}")
        trainer.train(resume_from_checkpoint=args.resume)
    else:
        trainer.train()

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)

    # ---------------------------------------------------------------------------
    # 8. Save final model
    # ---------------------------------------------------------------------------
    final_path = output_dir / "final"
    print(f"\nSaving final LoRA adapter to: {final_path}")
    model.save_pretrained(str(final_path))
    tokenizer.save_pretrained(str(final_path))

    # ---------------------------------------------------------------------------
    # 9. Export to GGUF (optional)
    # ---------------------------------------------------------------------------
    if args.export_gguf:
        gguf_path = output_dir / "gguf"
        print(f"\nExporting to GGUF ({args.gguf_quant}) at: {gguf_path}")
        print("  This may take a few minutes...")
        try:
            model.save_pretrained_gguf(
                str(gguf_path),
                tokenizer,
                quantization_method=args.gguf_quant,
            )
            print(f"  GGUF exported successfully!")
            print(f"  Copy the .gguf file from {gguf_path} to LM Studio's models directory")
        except Exception as e:
            print(f"  GGUF export failed: {e}")
            print("  You can export manually later with:")
            print(f"    model.save_pretrained_gguf('{gguf_path}', tokenizer, "
                  f"quantization_method='{args.gguf_quant}')")

    print("\n" + "=" * 60)
    print("ALL DONE!")
    print("=" * 60)
    print(f"\nFinal adapter saved at: {final_path}")
    print(f"\nNext steps:")
    print(f"  1. Test the model with LM Studio or vLLM")
    print(f"  2. Export to GGUF if not done already:")
    print(f"     training_venv\\Scripts\\python.exe training/train.py --export-gguf")
    print(f"  3. Copy .gguf to LM Studio and test tool calling")


if __name__ == "__main__":
    main()
