# LLM Fundamentals and Tokenization

## Overview

We establishes the foundations for understanding how a large language model (LLM) transforms raw text into numerical representations and uses those representations to predict the next token.

The work combines practical tokenizer experiments with small educational tensor experiments. The toy Transformer, attention, logits, and autoregressive examples are intended to explain the concepts; they are not implementations of the internal Qwen3.8-27B model.

**Project:** Local AI Assistant  
**Notebook:** `notebooks/01_tokenization.ipynb`

## Learning Objectives

By the end of this section, the learner should be able to:

- Explain the difference between text, tokens, token IDs, embeddings, and hidden states.
- Encode text into token IDs and decode token IDs back into text.
- Explain why token count differs from character and word count.
- Inspect vocabulary and special-token information.
- Describe how token IDs become embedding vectors.
- Interpret basic tensor shapes in a Transformer pipeline.
- Explain self-attention, causal attention, logits, and next-token prediction at a conceptual level.
- Explain autoregressive generation and context-window limits.
- Distinguish educational toy experiments from actual model inference.

## Conceptual Pipeline

The main representation flow introduced in Day 1 is:

```text
Raw Text
   |
   v
Tokenizer
   |
   v
Tokens
   |
   v
Token IDs
   |
   v
Embeddings
   |
   v
Position Information
   |
   v
Transformer Blocks
   |
   v
Hidden States
   |
   v
Language Modeling Head
   |
   v
Logits
   |
   v
Next-Token Prediction
   |
   v
Autoregressive Generation
```

The context window constrains how many tokens can be processed within a supported model context.

## Environment and Model Context

The notebook recorded the following environment information during the work:

| Component | Recorded value |
|---|---|
| Python | `3.13.0` |
| Transformers | `5.18.0` |
| Tokenizers | `0.23.2` |
| PyTorch | `2.14.1+cpu` |
| CUDA availability | `False` |
| Runtime | Ollama |
| Local model identifier | `qwen3.8:27b` |
| Observed tokenizer class | `Qwen3_5Tokenizer` |
| Observed vocabulary size | `248,044` |

These are recorded environment observations from the notebook workflow, not a claim that every dependency version is required for the entire project.

## Tokenization

A token is a unit produced by a tokenizer. Depending on the tokenizer, it can represent a whole word, a subword, punctuation, a number, a symbol, whitespace-related text, or a special token.

Therefore:

```text
1 token is not necessarily 1 word.
1 token is not necessarily 1 character.
```

Token boundaries depend on the tokenizer and model family.

### Basic English Example

Input:

```text
I love machine learning.
```

Observed tokens:

```text
['I', 'Ġlove', 'Ġmachine', 'Ġlearning', '.']
```

Recorded counts:

| Measure | Count |
|---|---:|
| Characters | 24 |
| Words | 4 |
| Tokens | 5 |

The `Ġ` marker in the displayed token strings is part of the tokenizer's token representation and can indicate a preceding space in this tokenizer format.

### Token IDs

Each token maps to an integer identifier in the tokenizer vocabulary.

For the same example, the notebook recorded:

```text
[40, 2854, 5484, 6618, 13]
```

A token is the tokenizer's text unit; a token ID is its integer vocabulary index. They are related but are not the same representation.

### Encoding and Decoding

The notebook explored both directions:

```text
Text
  |
  v
Encode
  |
  v
Token IDs
```

and:

```text
Token IDs
  |
  v
Decode
  |
  v
Text
```

The notebook recorded that the example could be decoded back into its text representation.

## Tokenization Experiments

Token counts were compared across English, Arabic, mixed-language text, source code, numbers, punctuation, and longer text.

| Input category | Recorded observation |
|---|---|
| English: `I love machine learning.` | 24 characters, 4 words, 5 tokens |
| Arabic: `أنا أحب تعلم الذكاء الاصطناعي.` | 30 characters, 5 words, 10 tokens |
| Mixed Arabic and English: `أتعلم Machine Learning باستخدام Python.` | 39 characters, 5 words, 7 tokens |
| Python code: `def add_numbers(a, b): return a + b` | 14 tokens |
| Numbers and punctuation: `The price is 12,500.75 USD! Is it 100% correct?` | 24 tokens |
| Long text | 792 characters, 114 words, 144 tokens |

### Key Finding

Token count cannot be reliably inferred from character count or word count alone. The tokenizer itself should be used whenever token usage matters, especially for multilingual content, source code, long prompts, and context-window management.

These counts are the observations recorded in the notebook for its specific tokenizer and input examples. They should not be generalized to every model or tokenizer.

## Vocabulary and Special Tokens

The notebook recorded a vocabulary size of:

```text
248,044
```

The vocabulary contains ordinary token entries and special tokens. Special tokens have structural or control-related purposes and are distinct from ordinary text tokens.

The notebook inspected special-token mappings and their IDs. The vocabulary size is relevant to later concepts such as embedding-table dimensions and the number of possible output-token candidates.

## Tokens, Token IDs, Embeddings, and Hidden States

These four concepts should be kept distinct.

### Token

A text unit produced by the tokenizer, such as:

```text
learning
```

### Token ID

An integer identifier associated with a token in the vocabulary.

### Embedding

A numerical vector retrieved for a token ID from an embedding table.

### Hidden State

A context-dependent representation produced by Transformer computation.

The conceptual progression is:

```text
Token
  |
  v
Token ID
  |
  v
Embedding
  |
  v
Transformer Computation
  |
  v
Hidden State
```

An embedding represents a token before the sequence has undergone the full contextual computation. A hidden state reflects Transformer processing and can depend on surrounding tokens.

## Embedding Lookup and Tensor Shapes

Token IDs act as indices into an embedding matrix.

If `V` is the vocabulary size and `D` is the embedding dimension, the conceptual embedding-table shape is:

```text
[V, D]
```

The notebook used the following observed configuration values for a scale calculation:

```text
V = 248,044
D = 5,120
```

The corresponding conceptual matrix shape is:

```text
[248,044, 5,120]
```

For a sequence of five tokens, the embedding output shape was described conceptually as:

```text
[5, 5,120]
```

With a batch dimension:

```text
[1, 5, 5,120]
```

The notebook calculated the theoretical number of entries in this embedding table:

```text
248,044 × 5,120 = 1,269,985,280 parameters
```

Approximate storage estimates recorded in the notebook were:

| Data type | Theoretical memory estimate |
|---|---:|
| FP32 | Approximately 4.73 GB |
| FP16 | Approximately 2.37 GB |

These are theoretical calculations for an embedding table of the stated dimensions. They are not measurements of the full model's loaded memory footprint.

## Position Information

A model must account for token identity and sequence order. For example, `dog bites man` and `man bites dog` contain the same words but express different relationships.

Conceptually:

```text
Token Identity + Position Information
                 |
                 v
        Contextual Processing
```

The exact positional mechanism depends on the model architecture. We focused on the principle that sequence order must be represented during Transformer processing.

## Decoder-Only Transformer

The high-level decoder-only Transformer flow is:

```text
Token IDs
   |
   v
Token Embeddings + Position Information
   |
   v
Transformer Blocks
   |
   v
Final Hidden States
   |
   v
Language Modeling Head
   |
   v
Logits
```

The notebook introduced self-attention, feed-forward networks, normalization, and residual connections as important Transformer components. Exact implementation details can differ between model families.

## Educational Transformer and Attention Experiments

The notebook used small PyTorch tensor experiments to make representation flow easier to inspect. These experiments were educational demonstrations rather than reproductions of Qwen3.8-27B internals.

### Toy Transformer Block

A toy block illustrated stages such as normalization, an attention placeholder, a residual connection, and a feed-forward network.

The recorded conceptual tensor shape was:

```text
[1, 5, 8]
```

The attention component in this particular experiment was explicitly a placeholder, not a real self-attention implementation.

### Toy Self-Attention

The simplified attention experiment followed this flow:

```text
Input
  |
  v
Queries, Keys, Values
  |
  v
Attention Scores
  |
  v
Attention Weights
  |
  v
Attention Output
```

Recorded tensor shapes:

| Tensor | Shape |
|---|---|
| Input | `[1, 4, 8]` |
| Attention weights | `[1, 4, 4]` |
| Output | `[1, 4, 8]` |

A fixed seed was used to make the experiment reproducible.

### Causal Attention

Autoregressive decoder models must prevent a position from using information from future positions when predicting the next token.

Conceptually:

```text
Position 1 can attend to position 1.
Position 2 can attend to positions 1 and 2.
Position 3 can attend to positions 1, 2, and 3.
```

The toy causal-attention experiment recorded:

```text
Future Attention Weights = 0
Maximum Future Attention Weight = 0
```

This was the observed result of the educational mask experiment, not a measurement of the local model's internal attention tensors.

## Logits and Next-Token Prediction

After Transformer processing, a language-modeling head maps hidden states to vocabulary scores called logits.

```text
Hidden States
     |
     v
Language Modeling Head
     |
     v
Logits
```

Logits are raw scores, not probabilities. A probability distribution can be derived from logits in a subsequent step.

The notebook used a toy language-modeling head with:

```text
Hidden state shape: [1, 3, 4]
Toy vocabulary size: 10
```

The resulting logits shape was:

```text
[1, 3, 10]
```

This shape represents a batch size of one, a sequence length of three, and ten vocabulary scores per position. It was a toy experiment, not the actual Qwen3.8-27B language-modeling head.

## Autoregressive Generation

Autoregressive generation produces text incrementally. Each generated token is appended to the context and becomes available for the next prediction.

```text
Current Context
      |
      v
Predict Next Token
      |
      v
Append Token
      |
      v
Updated Context
      |
      v
Repeat
```

The notebook included a conceptual simulation beginning with:

```text
I love
```

The simulated generated sequence was:

```text
AI
engineering
with
Python
```

This example illustrates the generation loop only. It was not real inference from the Qwen3.8-27B model.

## Context Window

A context window is measured in tokens, not characters or words. The conversation supplied to a model can include a system prompt, user input, chat history, and other prompt content. Generated tokens also consume context capacity according to the model's supported behavior.

The notebook used a toy context limit of ten tokens.

| Stage | Text | Recorded token count |
|---|---|---:|
| Initial context | `I love machine learning` | 4 |
| Updated context | `I love machine learning with Python and deep learning` | 9 |

The updated context remained within the toy limit:

```text
Within Toy Limit = True
```

This was a small demonstration of context growth, not a benchmark of the local model's full context capacity.

## Main Findings

1. Tokenization depends on the tokenizer; tokens do not correspond one-to-one with words or characters.
2. Token IDs are integer vocabulary indices, while embeddings are numerical vectors associated with those IDs.
3. Hidden states differ from token embeddings because they reflect Transformer computation over context.
4. Vocabulary size and embedding dimension determine the conceptual shape and scale of an embedding table.
5. Self-attention mixes information across token positions; causal masking prevents access to future positions in autoregressive prediction.
6. Logits are raw vocabulary scores, not probabilities.
7. Autoregressive generation repeatedly predicts and appends tokens.
8. Context usage must be tracked in tokens rather than estimated from characters or words.
9. Toy tensor experiments help explain shapes and mechanisms but do not prove the internal behavior of the production model.

## Scope and Limitations

- We focused on fundamentals and educational experiments, not model training or fine-tuning.
- The Transformer, attention, logits, and generation simulations were toy demonstrations; they were not a real forward pass through Qwen3.8-27B.
- The recorded tokenizer vocabulary size and token counts apply to the inspected tokenizer and examples.
- The theoretical embedding-table memory calculation is not a measurement of total model memory.
- Exact parity between the local tokenizer and the tokenizer behavior used by Ollama was not independently established during this work.
- Real model generation, decoding behavior, sampling, and performance measurement belong to the subsequent generation and runtime work rather than these toy demonstrations.

## Outcome

We established the conceptual vocabulary and tensor-shape intuition needed to understand how text is represented before and during LLM generation. It covered tokenization, token IDs, vocabulary, special tokens, embeddings, positional information, Transformer blocks, self-attention, causal attention, logits, autoregressive generation, and context windows.

## Handoff to Next

Next, we will move from conceptual and toy demonstrations toward real model generation and decoding.

The next stage should investigate the actual generation path, inspect real generation outputs and available metadata, and distinguish observable runtime behavior from internal model details that the runtime does not expose.
