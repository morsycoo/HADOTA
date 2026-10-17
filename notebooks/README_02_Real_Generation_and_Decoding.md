# Real LLM Generation and Decoding

## Overview

Now we moves from the conceptual and toy experiments to real end-to-end generation with the local `qwen3.8:27b` model through Ollama. The work also uses synthetic PyTorch tensors to demonstrate decoding mathematics when the selected runtime does not expose internal model tensors.

**Project:** Local AI Assistant  
**Notebook:** `notebooks/02_real_generation_and_decoding.ipynb`  
**Benchmark dataset:** `data/generation_benchmark_prompts.json`  
**Engineering observations:** `data/engineering_observations.json`  
**Final summary artifact:** `data/final_summary.md`

A central rule for this day is to distinguish runtime observations from synthetic educational demonstrations and conceptual explanations.

## Learning Objectives

- Run bounded real generation requests against the local model.
- Inspect token counts and available generation metadata.
- Explain logits, softmax probabilities, greedy decoding, and sampling.
- Experiment with temperature, top-k, top-p, and seeded sampling.
- Observe real autoregressive continuation and context growth.
- Distinguish EOS, length limits, stop sequences, and timeouts.
- Understand prefill, decode, KV cache, TTFT, and inter-chunk timing.
- Measure generation behavior while documenting variability and limitations.
- Prepare a reusable benchmark dataset and experiment matrix.

## Environment and Runtime

The worklog recorded this environment:

| Component | Recorded value |
|---|---|
| Operating system | Windows 11 |
| Python | `3.13.0` |
| PyTorch | `2.12.0+cu130` |
| CUDA available in the recorded environment | `True` |
| GPU | NVIDIA GeForce RTX 5070 Laptop GPU |
| CUDA device count | `1` |
| NVIDIA driver | `592.27` |
| Installed CUDA Toolkit | `13.1.115` |
| Transformers | `5.18.0` |
| Tokenizers | `0.23.2` |
| Ollama | `0.35.1` |
| Local model | `qwen3.8:27b` |
| Model ID reported by Ollama | `aaee06c39dcf` |
| Model size reported by Ollama | `17 GB` |

A PyTorch CUDA matrix multiplication using a `4096 × 4096` matrix completed in `0.0120842 s`, with approximately `224 MB` of GPU memory allocated. This confirms that the tested PyTorch CUDA operation ran on the GPU; it does not prove that Ollama used the same execution path.

### Tokenizer Loading

`AutoTokenizer.from_pretrained("Qwen/Qwen3.8-27B")` failed in the recorded environment because Windows Application Control blocked the `pyarrow.lib` DLL. Calling `Qwen3_5Tokenizer.from_pretrained("Qwen/Qwen3.8-27B")` succeeded.

The loaded tokenizer reported a vocabulary size of `248,044`, while the model configuration reported `248,320`, a difference of `276`. The worklog recorded this discrepancy without establishing its cause.

## Real Tokenization Through the Runtime Path

For the prompt:

```text
Machine learning is
```

the tokenizer returned:

```text
Token IDs: [[20943, 6618, 369]]
Token-ID tensor shape: [1, 3]
Token count: 3
Decoded text: Machine learning is
```

The corresponding Ollama prompt-token count was also `3` in the recorded verification experiment.

This validates the basic input path for that example:

```text
Prompt Text
    |
    v
Tokenizer
    |
    v
Token IDs
    |
    v
Runtime / Model Input
```

## Real Model Output vs. Synthetic Logits

The selected high-level Ollama API returned generated text and aggregate metadata, but the tested endpoint did not return a raw logits tensor. Therefore, the notebook kept the following categories separate:

- **Real runtime observations:** generation text, token counts, completion information, timing metadata, streaming chunks, and request behavior.
- **Synthetic demonstrations:** logits, softmax probabilities, candidate rankings, sampling distributions, and simplified generation mechanics.
- **Conceptual descriptions:** internal steps such as the model forward pass and cache use where direct internal tensors were unavailable.

For a causal language model, logits are conceptually shaped as:

```text
[batch_size, sequence_length, vocabulary_size]
```

The next-token scores are taken from the last sequence position:

```python
next_token_logits = logits[:, -1, :]
```

This describes the standard generation mechanism; it is not a claim that raw Qwen logits were extracted through the tested Ollama endpoint.

## Synthetic Logits and Probabilities

A synthetic logits tensor with shape `[1, 3, 10]` was used to demonstrate selecting the final sequence position. Its last-position logits had shape `[1, 10]`.

The three highest synthetic logits were:

| Rank | Synthetic token ID | Logit |
|---:|---:|---:|
| 1 | 5 | 1.0616 |
| 2 | 7 | 0.9817 |
| 3 | 1 | 0.6876 |

Decoding those synthetic IDs produced `&`, `(`, and `"`. These were decoded synthetic token IDs, not predictions from the real Qwen model.

Applying softmax produced the following recorded probabilities:

| Token ID | Synthetic probability |
|---:|---:|
| 0 | 0.099871 |
| 1 | 0.134252 |
| 2 | 0.051655 |
| 3 | 0.011550 |
| 4 | 0.086075 |
| 5 | 0.195146 |
| 6 | 0.096882 |
| 7 | 0.180162 |
| 8 | 0.089439 |
| 9 | 0.054968 |

The probabilities sum to approximately one, subject to displayed rounding.

Key distinctions:

- **Logits** are unnormalized scores.
- **Softmax probabilities** form a normalized distribution over candidates.
- **Decoding** applies a rule to choose the next token from scores or a transformed distribution.

## Decoding Experiments

All numeric results in this section are from synthetic distributions, not the real model's hidden probability distribution.

### Greedy Decoding

Greedy decoding chooses the highest-scoring candidate. On the fixed synthetic distribution, it selected token ID `5`. Reusing the same fixed scores produces the same greedy choice.

### Temperature

Temperature rescales logits before softmax. Lower temperatures generally concentrate probability on high-scoring candidates; higher temperatures generally flatten the distribution.

The synthetic experiment recorded:

| Temperature | Maximum probability |
|---:|---:|
| 0.1 | 0.677329 |
| 0.5 | 0.294854 |
| 0.7 | 0.238114 |
| 1.0 | 0.195146 |
| 1.5 | 0.162286 |

The maximum probability decreased as temperature increased for this particular distribution.

### Top-k Sampling

Top-k retains only the `k` highest-scoring candidates before renormalization and sampling. A synthetic vocabulary of 1,000 candidates was used with seed `42`; the top candidate was ID `701`.

| `k` | Retained candidates | Top-candidate probability after filtering |
|---:|---:|---:|
| 1 | 1 | 1.000000 |
| 5 | 5 | 0.244920 |
| 20 | 20 | 0.095629 |
| 50 | 50 | 0.050730 |
| 100 | 100 | 0.032746 |

For `k=5`, the retained candidates were:

| Rank | Token ID | Probability |
|---:|---:|---:|
| 1 | 701 | 0.244920 |
| 2 | 759 | 0.206493 |
| 3 | 476 | 0.202321 |
| 4 | 691 | 0.182567 |
| 5 | 561 | 0.163699 |

At `k=1`, the only surviving candidate has probability `1.0`.

### Top-p (Nucleus) Sampling

Top-p retains a high-probability candidate set based on cumulative probability. The experiment included the first candidate that crossed the threshold, so the retained mass could be slightly greater than the requested `p`.

| Top-p | Retained candidates | Original probability mass retained | Top-candidate probability after renormalization |
|---:|---:|---:|---:|
| 0.70 | 319 | 0.700075 | 0.017890 |
| 0.90 | 611 | 0.900011 | 0.013916 |
| 0.95 | 744 | 0.950272 | 0.013180 |
| 1.00 | 1000 | 1.000000 | 0.012525 |

Higher thresholds retained more candidates. These counts belong to the tested synthetic distribution.

### Combined Sampling

The combined pipeline was:

1. Scale logits by temperature.
2. Apply top-k filtering.
3. Apply top-p filtering.
4. Normalize the remaining candidates.
5. Sample the next token.

For `temperature=0.7`, `top_k=50`, and `top_p=0.9`, the final synthetic candidate set contained `42` candidates.

| Configuration | Temperature | Top-k | Top-p | Retained candidates | Highest final probability |
|---|---:|---:|---:|---:|---:|
| Conservative | 0.5 | 20 | 0.8 | 12 | 0.200446 |
| Balanced | 0.7 | 50 | 0.9 | 42 | 0.079404 |
| Diverse | 1.0 | 50 | 0.95 | 47 | 0.052844 |
| Broad | 1.5 | 100 | 1.0 | 100 | 0.022471 |

These labels describe the chosen parameter configurations; they do not guarantee output quality.

### Seeded Reproducibility

The synthetic sampler was reset to seed `42` ten times. It selected ID `759` in all ten runs for the same distribution and configuration.

| Check | Result |
|---|---|
| Seed | `42` |
| Repeated resets | 10 |
| Same selected ID | `True` |
| Selected ID | `759` |

A seed supports reproducibility in a controlled setup but does not guarantee bitwise-identical results across different devices, libraries, backends, or implementations.

### Token-Level Sampling Trace

Five sequential samples were taken from a fixed synthetic distribution:

| Step | Selected token ID | Probability in the fixed distribution |
|---:|---:|---:|
| 1 | 759 | 0.062224 |
| 2 | 296 | 0.018913 |
| 3 | 902 | 0.015366 |
| 4 | 902 | 0.015366 |
| 5 | 360 | 0.015923 |

The same distribution was reused at every step. This was not a full autoregressive model trace because the model was not rerun on updated context to calculate new logits.

## Real Autoregressive Generation Through Ollama

A real trace used `qwen3.8:27b`, raw `/api/generate`, `temperature=0.2`, `seed=42`, `num_ctx=4096`, and a maximum of five generated tokens.

Prompt:

```text
Machine learning is
```

| Step | Returned fragment | Token ID recorded in the trace | Context after appending |
|---:|---|---:|---|
| 1 | ` a` | 264 | `Machine learning is a` |
| 2 | ` sub` | 1146 | `Machine learning is a sub` |
| 3 | `field` | 2482 | `Machine learning is a subfield` |
| 4 | ` of` | 314 | `Machine learning is a subfield of` |
| 5 | ` artificial` | 19820 | `Machine learning is a subfield of artificial` |

Final text:

```text
Machine learning is a subfield of artificial
```

The fragments illustrate that decoded token pieces may include leading spaces or partial words. These IDs are observations from the recorded run, not a guarantee about all tokenizer revisions.

The manual trace sent the growing text context to Ollama at each step. It did not inspect or control Ollama's internal KV cache.

## Manual Generation Loop and Stop Conditions

The worklog describes a `generate_autoregressively(...)` helper that repeatedly calls the raw Ollama generation endpoint, collects returned fragments and metadata, appends fragments to the context, and stops at a configured limit or stop condition.

A separate synthetic test used logits of shape `[1, 8, 1000]`. The final-position logits had shape `[1, 1000]`; greedy selection returned ID `913` with probability approximately `0.008692`. Reusing the same synthetic logits repeatedly returned ID `913`, illustrating loop mechanics rather than real inference.

The experiments distinguished several stopping mechanisms:

| Case | Recorded outcome | Interpretation |
|---|---|---|
| Synthetic EOS | Sequence `[913, 619, 345, 999, 486]` stopped at synthetic EOS ID `999` at step 4 | Educational EOS handling |
| Synthetic maximum length | A limit of five stopped the loop after five steps | Educational length limit |
| Real one-token generation | `num_predict=1`; one token returned; `done_reason=length` | Generation limit reached |
| Longer real generation without a suitable explicit limit | Timed out at approximately 300 seconds | Timeout, not normal completion |
| Real generation with `num_predict=32` | 32 tokens returned; `done_reason=length` | Configured length limit reached |
| Synthetic application stop sequence | `[345, 486]` stopped at step 4 | Educational application-level stopping |
| Real stop-sequence request | `done_reason=stop`; visible response was newline characters | Runtime reported a stop condition |

Different stop outcomes are not interchangeable. In particular, `done_reason=length` means the length limit ended the request; it does not prove that the model naturally decided its answer was complete.

### Edge Cases

The recorded edge-case experiments included:

| Case | Prompt tokens | Generated tokens | Completion / observation | External time |
|---|---:|---:|---|---:|
| Empty prompt | 0 | 0 | HTTP 200, `done=True`, `done_reason=load`, empty response | 0.0074 s |
| Very short prompt | 1 | 4 | `done_reason=length`; response `", I'm a"` | 1.5950 s |
| Single-token generation | 3 | 1 | `done_reason=length`; response ` a` | 2.8556 s |
| Zero-token generation | — | — | Timed out at approximately 300.0332 s; no response metadata | 300.0332 s |
| Long prompt | 201 | 4 | `done_reason=length`; response ` Machine learning is a` | 3.2137 s |
| Low context (`num_ctx=16`) | 29 | 4 | `done_reason=length`; response `\nThe text above` | 52.3994 s |
| Stop sequence | 11 | 3 | `done_reason=stop`; visible response `\n\n` | 54.0007 s |

The exact internal handling of the low-context case was not inspected. The result does not prove how Ollama truncated or accounted for the context. The zero-token request timed out; no unsupported explanation was assigned to that behavior.

## Input Tokens, Output Tokens, and Generation Metrics

For the real prompt `Machine learning is`, the recorded input count was three tokens. A five-token trace produced five output tokens, giving eight tokens across the input and generated continuation.

A separate bounded experiment recorded:

| `num_predict` | Generated tokens | Input tokens | Input + output count |
|---:|---:|---:|---:|
| 1 | 1 | 3 | 4 |
| 5 | 5 | 3 | 8 |
| 10 | 10 | 3 | 13 |
| 20 | 20 | 3 | 23 |

For bounded experiments, the runtime returned the requested number of tokens. This is not guaranteed for every request because EOS and stop conditions can end generation earlier.

A basic aggregate generation-rate calculation is:

```text
tokens_per_second = output_tokens / generation_time_seconds
```

The worklog recorded several individual runs. They varied, so the values should be treated as observations rather than stable benchmarks.

### Recorded Prefill/Generation Measurements

Three real prompts were tested with a target of 16 output tokens:

| Prompt class | Input tokens | Output tokens | Prompt-evaluation duration | Evaluation/generation duration | Total metadata duration | External latency | Aggregate generation rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Short | 3 | 16 | 0.730082 s | 2.632591 s | 3.517156 s | 3.5265 s | 6.0777 tokens/s |
| Medium | 30 | 16 | 2.144112 s | 2.7001 s | 9.803592 s | 9.8109 s | 5.9258 tokens/s |
| Long | 102 | 16 | 1.667267 s | 4.1659 s | 14.770428 s | 14.7762 s | 3.8407 tokens/s |

Prompt-evaluation duration was non-monotonic in these single runs. The recorded results do not prove that longer prompts require less prefill computation. Runtime overhead, cache state, scheduling, and measurement boundaries can affect individual observations.

A separate prompt-length benchmark produced different results:

| Prompt class | Input tokens | Output tokens | Prompt-evaluation duration | Evaluation/generation duration | Total metadata duration | External latency | Aggregate generation rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Short | 32 | 16 | 2.5473 s | 4.5685 s | 8.1658 s | 8.1765 s | 3.5023 tokens/s |
| Medium | 57 | 16 | 2.3609 s | 2.5675 s | 7.3750 s | 7.3782 s | 6.2318 tokens/s |
| Long | 133 | 16 | 1.4195 s | 3.1352 s | 4.5621 s | 4.5916 s | 5.1033 tokens/s |

These are separate individual runs and should not be combined as if they were one controlled experiment. Their non-monotonic timing results reinforce the need for repeated trials and consistent measurement boundaries.

## TTFT and Streaming Chunk Timing

### Time to First Token (TTFT)

TTFT was operationally defined as the elapsed time from starting the HTTP request timer to receiving the first non-empty streamed response chunk. This is a client-observed first-chunk measure, not a pure measurement of Transformer prefill.

| Metric | Short prompt | Long prompt |
|---|---:|---:|
| Input tokens | 3 | 61 |
| TTFT | 2.2298 s | 1.8330 s |
| Generated tokens | 16 | 16 |
| Prompt-evaluation duration | 0.690586 s | 1.621445 s |
| Evaluation/generation duration | 3.151857 s | 2.750920 s |
| Total metadata duration | 5.3681008 s | 4.5805028 s |
| External request latency | 5.3724 s | 4.5844 s |

The long prompt had a lower TTFT in this single pair of runs while its prompt-evaluation duration was higher. This does not establish that longer prompts improve TTFT; repeated controlled trials are required.

### Inter-Chunk Latency

The streaming test produced 16 non-empty chunks for a response beginning:

```text
 a field of computer science that focuses on the development of algorithms that can learn from
```

Recorded summary:

| Metric | Result |
|---|---:|
| TTFT | 0.8707 s |
| Non-empty chunks | 16 |
| Inter-chunk intervals | 15 |
| Mean interval | 164.93 ms |
| Median interval | 0.03 ms |
| Minimum interval | 0.006 ms |
| Maximum interval | 574.97 ms |
| Standard deviation | 249.22 ms |
| Observed stream span | 2.4739 s |
| Generated tokens reported by metadata | 16 |
| `eval_duration` | 2.478445 s |
| Aggregate generation rate | 6.4557 tokens/s |

The interval measurements were calculated from client-observed chunk arrival times. Ollama chunks are not guaranteed to correspond one-to-one with tokenizer tokens, and very small intervals may reflect bursty delivery. These are therefore inter-chunk measurements, not guaranteed token-level ITL measurements.

## Prefill, Decode, and KV Cache

The day introduced this conceptual sequence:

```text
Prompt
  |
  v
Prefill
  |
  v
KV Cache
  |
  v
Decode
  |
  v
Token-by-token generation
```

- **Prefill** processes the input prompt to establish representations needed for generation.
- **Decode** generates the continuation incrementally.
- **KV cache** refers to cached key/value representations that can avoid recomputing prior-token attention states during incremental generation.

The tested Ollama endpoint exposed aggregate metadata such as `prompt_eval_count`, `prompt_eval_cached_count`, `prompt_eval_duration`, `eval_count`, `eval_duration`, and `total_duration`. It did not expose raw logits, hidden states, attention tensors, or internal KV-cache tensors.

A synthetic cache exercise used educational tensors rather than Ollama's internal cache. One example used four illustrative layers; another inspected key and value tensors of shape `(1, 2, 6, 4)`, with a cached sequence length of six. These values are not verified dimensions of the real Qwen3.8-27B model.

A small arithmetic example estimated storage for a synthetic cache with batch size 1, sequence length 100, head dimension 4, and two bytes per value:

| Quantity | Result |
|---|---:|
| Bytes | 12,800 |
| KiB | 12.50 KiB |
| MiB | 0.012207 MiB |

This is only an illustrative calculation, not an estimate of the actual model's cache footprint.

## Separating Model, Decoding, and Runtime

A recorded comparison used the prompt `Machine learning is`:

| Experiment | Temperature | `num_ctx` | `num_predict` | Input tokens | Generated tokens | Done reason | Response | External time |
|---|---:|---:|---:|---:|---:|---|---|---:|
| Baseline | 0 | 4096 | 8 | 3 | 8 | `length` | `a field of computer science that focuses on` | 2.2442 s |
| Decoding changed | 1 | 4096 | 8 | 3 | 8 | `length` | `not a replacement for statistical analysis but a` | 4.6478 s |
| Runtime context changed | 0 | 512 | 8 | 3 | 8 | `length` | Same as baseline | 44.2811 s |

These are individual observations, not reliable general latency estimates.

| Layer | Responsibility |
|---|---|
| Model | Computes next-token scores from the current context. |
| Decoding algorithm | Selects the next token using greedy selection or sampling. |
| Runtime | Executes inference and manages operational concerns such as loading, memory, context, caching, scheduling, and requests. |

Because the API did not expose all internal tensors, some model-internal steps remained conceptual while the external generation and runtime behavior were observed.

## Benchmark Dataset and Experiment Matrix

A JSON benchmark dataset was created and validated at:

`data/generation_benchmark_prompts.json`

Recorded validation results:

| Property | Result |
|---|---:|
| Total prompts | 24 |
| Categories | 6 |
| Prompts per category | 4 |
| Unique IDs | 24 |
| Minimum prompt word count | 9 |
| Maximum prompt word count | 32 |
| Average prompt word count | 16.67 |
| Minimum prompt character count | 50 |
| Maximum prompt character count | 219 |
| Validation | `True` |

Categories:

- `general`
- `reasoning`
- `coding`
- `technical`
- `summarization`
- `creative`

Each record contained `id`, `category`, and `prompt`. The dataset was designed for evaluation and benchmarking, not model training.

The worklog also records a validated experiment matrix. The dataset and matrix are intended to support later controlled benchmarks; individual timing observations should not be treated as a comprehensive performance evaluation.

## Main Findings

1. The local `qwen3.8:27b` model successfully generated real text through Ollama.
2. The tested API exposed useful text, completion, token-count, and aggregate timing metadata, but not raw logits or internal cache tensors.
3. Synthetic experiments made the mechanics of logits, softmax, greedy decoding, temperature, top-k, top-p, and seeded sampling observable without misrepresenting them as real Qwen predictions.
4. Real autoregressive continuation was observed through repeated Ollama requests with an updated text context.
5. `done_reason=length`, `done_reason=stop`, an EOS event, and an external timeout represent different termination mechanisms.
6. TTFT measured at the client is not identical to pure prefill computation time.
7. Stream chunk intervals are not guaranteed to equal token-level ITL.
8. Single-run latency results varied and were sometimes non-monotonic. Controlled repeated trials are needed for robust performance claims.
9. The 24-prompt dataset and experiment matrix provide a reusable foundation for future evaluation.

## Known Limitations

- Raw logits, hidden states, attention tensors, and internal KV-cache tensors were not exposed by the tested Ollama API.
- Synthetic logits and cache tensors are educational examples, not measurements of the real model's internal values.
- Exact tokenizer/model vocabulary parity was not resolved; the observed tokenizer and model vocabulary sizes differed by 276.
- Some experiments were single runs and showed substantial timing variability.
- Client-observed TTFT and inter-chunk timing do not directly expose every internal model operation.
- The manual generation trace repeatedly sent updated context to Ollama and did not verify internal KV-cache reuse.
- The zero-token request timed out in the recorded test; its internal cause was not established.

## Outcome

We established real local generation through Ollama, explored decoding mathematics using explicitly synthetic distributions, recorded real autoregressive continuation, investigated stopping behavior, measured runtime timing metadata and streaming chunk arrival, and documented the boundary between visible runtime behavior and hidden model internals.

The day also produced a validated 24-prompt benchmark dataset and an experiment matrix to support later controlled performance evaluation.

## Handoff to Next

Next, we will build a structured runtime integration layer around Ollama, including centralized configuration, validated request/response contracts, streaming events, runtime errors, conversation orchestration, and context-window management.