# LLM Auto-Fallback Guide

## Overview

NeuroLake's LLM module provides **automatic fallback** across multiple providers:
- **OpenAI** (GPT-4, GPT-3.5-turbo)
- **Anthropic** (Claude 3 Opus, Sonnet, Haiku)
- **Ollama** (Local models: Llama 2, Mistral, etc.)

## How Auto-Fallback Works

```python
if openai_fails:
    try_anthropic()
elif anthropic_fails:
    try_ollama()
elif ollama_fails:
    raise_error("All providers exhausted")
```

## Quick Start

### Basic Fallback Chain

```python
from neurolake.llm import ManagedLLM, LLMConfig

# Configure providers
config = LLMConfig(
    openai_api_key="sk-...",
    anthropic_api_key="sk-ant-...",
    enable_cache=True
)

# Create LLM with fallback chain: OpenAI → Anthropic → Ollama
llm = ManagedLLM(
    primary="openai",
    fallbacks=["anthropic", "ollama"],
    config=config
)

# Auto-fallback in action
response = llm.generate("Explain data lakes")
# If OpenAI fails → tries Anthropic
# If Anthropic fails → tries Ollama
# If all fail → raises error

print(f"Provider used: {response.provider}")
print(f"Cost: ${response.cost:.4f}")
```

## Fallback Strategies

### 1. Cost-Optimized (Cheap → Expensive)

```python
# Try free local model first, fall back to cloud
llm = ManagedLLM(
    primary="ollama",          # Free (local)
    fallbacks=["anthropic", "openai"],  # $$ → $$$
    config=LLMConfig(
        ollama_model="llama2",
        anthropic_model="claude-3-haiku-20240307",  # Cheapest Claude
        openai_model="gpt-3.5-turbo"                # Moderate cost
    )
)
```

**Logs:**
```
INFO: Attempting primary provider: ollama
INFO: ✓ Success with ollama (cost: $0.0000, latency: 234ms)
```

If Ollama fails:
```
WARNING: ✗ ollama failed with ConnectionError: localhost:11434 not reachable
INFO: Fallback 1/2: Trying anthropic (previous providers failed)
INFO: ✓ Success with anthropic (cost: $0.0012, latency: 456ms)
```

### 2. Reliability-First (Most Reliable → Backup)

```python
# Try most reliable provider first
llm = ManagedLLM(
    primary="openai",          # Most reliable uptime
    fallbacks=["anthropic", "ollama"],
    config=LLMConfig(
        openai_model="gpt-4",
        max_retries=5  # More retries for reliability
    )
)
```

### 3. Task-Specific Strategies

```python
# Code generation: OpenAI is best
code_llm = ManagedLLM(
    primary="openai",
    fallbacks=["anthropic", "ollama"],
    config=LLMConfig(openai_model="gpt-4")
)

# Analysis/reasoning: Claude is best
analysis_llm = ManagedLLM(
    primary="anthropic",
    fallbacks=["openai", "ollama"],
    config=LLMConfig(anthropic_model="claude-3-opus-20240229")
)

# Quick queries: Local is fastest
quick_llm = ManagedLLM(
    primary="ollama",
    fallbacks=["openai"],
    config=LLMConfig(ollama_model="llama2")
)
```

## Error Handling

### Automatic Error Types Handled

The fallback system automatically handles:

1. **API Errors** (401, 403, 500)
   ```
   ✗ openai failed with AuthenticationError: Invalid API key
   → Tries next provider
   ```

2. **Rate Limits** (429)
   ```
   ✗ openai failed with RateLimitError: Quota exceeded
   → Tries next provider
   ```

3. **Timeouts**
   ```
   ✗ anthropic failed with TimeoutError: Request timed out after 60s
   → Tries next provider
   ```

4. **Connection Errors**
   ```
   ✗ ollama failed with ConnectionError: localhost:11434 not reachable
   → Tries next provider
   ```

### All Providers Failed

When all providers fail:
```python
try:
    response = llm.generate("Explain AI")
except RuntimeError as e:
    # e.message contains details of all failures
    print(e)
    # RuntimeError: All providers failed after trying: openai, anthropic, ollama.
    # Last error (ConnectionError): Connection refused
```

## Advanced Features

### With Caching

```python
config = LLMConfig(enable_cache=True, cache_ttl=3600)
llm = ManagedLLM(primary="openai", fallbacks=["anthropic"], config=config)

# First call: hits OpenAI, caches result
response1 = llm.generate("What is ML?")

# Second call: hits cache (free, instant)
response2 = llm.generate("What is ML?")
assert response2.cached == True
```

### With Rate Limiting

```python
config = LLMConfig(
    openai_rpm=60,     # 60 requests per minute
    anthropic_rpm=50   # 50 requests per minute
)

llm = ManagedLLM(primary="openai", fallbacks=["anthropic"], config=config)

# Rate limiter automatically pauses if limit reached
for i in range(100):
    response = llm.generate(f"Query {i}")
    # Automatically throttled to respect rate limits
```

### With Retry Logic

```python
config = LLMConfig(
    max_retries=3,
    retry_delay=1.0,
    backoff_factor=2.0  # 1s, 2s, 4s delays
)

llm = ManagedLLM(primary="openai", config=config)

# Automatically retries transient errors before falling back
response = llm.generate("Explain transformers")
# Tries OpenAI up to 3 times with exponential backoff
# Then falls back to next provider
```

### Streaming with Fallback

```python
from neurolake.llm import LLMFactory

def stream_with_fallback(prompt: str):
    providers = ["openai", "anthropic", "ollama"]

    for provider_name in providers:
        try:
            provider = LLMFactory.create(provider_name)

            for chunk in provider.stream(prompt):
                print(chunk, end="", flush=True)

            return  # Success
        except Exception as e:
            print(f"\n{provider_name} failed, trying next...")
            continue

stream_with_fallback("Write a poem about data")
```

## Monitoring & Stats

### Usage Tracking

```python
llm = ManagedLLM(primary="openai", fallbacks=["anthropic", "ollama"])

# Make some calls
for i in range(10):
    llm.generate(f"Query {i}")

# Get statistics
stats = llm.get_stats()

print(f"Total requests: {stats['usage']['total_requests']}")
print(f"Total cost: ${stats['usage']['total_cost']:.2f}")
print(f"Total tokens: {stats['usage']['total_tokens']}")

# By provider
for provider, data in stats['usage']['by_provider'].items():
    print(f"{provider}: {data['requests']} requests, ${data['cost']:.2f}")

# Cache stats
if 'cache' in stats:
    print(f"Cache hit rate: {stats['cache']['hit_rate']:.1f}%")
```

## Best Practices

### 1. Set Appropriate Fallbacks

```python
# Production: Reliability first
prod_llm = ManagedLLM(
    primary="openai",
    fallbacks=["anthropic", "ollama"]
)

# Development: Cost first
dev_llm = ManagedLLM(
    primary="ollama",
    fallbacks=["openai"]
)
```

### 2. Use Environment Variables

```bash
# .env file
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434
```

```python
# Config reads from environment automatically
config = LLMConfig()  # Loads from env vars
llm = ManagedLLM(primary="openai", fallbacks=["anthropic"], config=config)
```

### 3. Enable Caching for Repeated Queries

```python
config = LLMConfig(
    enable_cache=True,
    cache_ttl=3600  # 1 hour
)
```

### 4. Monitor Costs

```python
# Check stats regularly
stats = llm.get_stats()
if stats['usage']['total_cost'] > 10.0:
    print("Warning: Cost exceeded $10!")
```

## Example Output

### Successful Primary Provider

```
INFO: Attempting primary provider: openai
INFO: ✓ Success with openai (cost: $0.0030, latency: 456ms)
```

### Fallback in Action

```
INFO: Attempting primary provider: openai
WARNING: ✗ openai failed with RateLimitError: Quota exceeded. Falling back to next provider...
INFO: Fallback 1/2: Trying anthropic (previous providers failed)
INFO: ✓ Success with anthropic (cost: $0.0015, latency: 678ms)
```

### All Providers Failed

```
INFO: Attempting primary provider: openai
WARNING: ✗ openai failed with AuthenticationError: Invalid API key. Falling back to next provider...
INFO: Fallback 1/2: Trying anthropic (previous providers failed)
WARNING: ✗ anthropic failed with AuthenticationError: Invalid API key. Falling back to next provider...
INFO: Fallback 2/2: Trying ollama (previous providers failed)
ERROR: ✗ ollama failed with ConnectionError: Connection refused. No more fallbacks available.
ERROR: RuntimeError: All providers failed after trying: openai, anthropic, ollama
```

## Summary

✅ **Automatic fallback** across OpenAI, Anthropic, and Ollama
✅ **Detailed logging** shows which provider succeeded
✅ **Error categorization** for different failure types
✅ **Retry with backoff** before falling back
✅ **Rate limiting** per provider
✅ **Response caching** to reduce costs
✅ **Usage tracking** with cost calculation
✅ **Streaming support** with fallbacks

Use `ManagedLLM` for automatic fallback, or `LLMFactory.create()` for manual control.
