"""
LLM Integration Examples

Examples showing auto-fallback across OpenAI, Anthropic, and Ollama.
"""

import logging
from neurolake.llm import ManagedLLM, LLMConfig, LLMFactory

# Setup logging to see fallback behavior
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_1_basic_fallback():
    """
    Example 1: Basic auto-fallback from OpenAI → Anthropic → Ollama

    If OpenAI fails (API error, rate limit, etc.):
        Try Anthropic
    If Anthropic fails:
        Try local Ollama
    If Ollama fails:
        Raise error
    """
    print("=" * 60)
    print("Example 1: Auto-Fallback Chain")
    print("=" * 60)

    config = LLMConfig(
        openai_api_key="sk-...",  # Your key here
        anthropic_api_key="sk-ant-...",  # Your key here
        enable_cache=True
    )

    # Create managed LLM with fallback chain
    llm = ManagedLLM(
        primary="openai",
        fallbacks=["anthropic", "ollama"],
        config=config
    )

    # This will automatically:
    # 1. Try OpenAI first
    # 2. If OpenAI fails → try Anthropic
    # 3. If Anthropic fails → try Ollama
    # 4. If all fail → raise error
    try:
        response = llm.generate("Explain data lakes in 3 sentences")
        print(f"\n✓ Response from {response.provider}:")
        print(f"  {response.text}")
        print(f"  Cost: ${response.cost:.4f}, Latency: {response.latency_ms:.0f}ms")
    except Exception as e:
        print(f"\n✗ All providers failed: {e}")


def example_2_cost_optimized():
    """
    Example 2: Cost-optimized fallback (cheap → expensive)

    Try local Ollama first (free):
        If successful, use it
    If Ollama fails:
        Try Anthropic Claude Haiku (cheapest cloud)
    If Haiku fails:
        Try OpenAI GPT-3.5 (moderate cost)
    If GPT-3.5 fails:
        Try GPT-4 (most expensive, most capable)
    """
    print("\n" + "=" * 60)
    print("Example 2: Cost-Optimized Fallback (Free → Cheap → Expensive)")
    print("=" * 60)

    config = LLMConfig(
        ollama_model="llama2",
        anthropic_model="claude-3-haiku-20240307",
        openai_model="gpt-3.5-turbo"
    )

    # Try free local model first, fall back to cheap cloud models
    llm = ManagedLLM(
        primary="ollama",  # Free local
        fallbacks=["anthropic", "openai"],  # Cheap cloud → expensive cloud
        config=config
    )

    try:
        response = llm.generate("What is machine learning?")
        print(f"\n✓ Response from {response.provider} ({response.model}):")
        print(f"  Cost: ${response.cost:.4f} (saved money by using {response.provider}!)")
    except Exception as e:
        print(f"\n✗ All providers failed: {e}")


def example_3_reliability_first():
    """
    Example 3: Reliability-first fallback (most reliable → backup)

    Try OpenAI first (most reliable, best uptime):
        If successful, use it
    If OpenAI fails:
        Try Anthropic (reliable backup)
    If Anthropic fails:
        Try local Ollama (always available if running)
    """
    print("\n" + "=" * 60)
    print("Example 3: Reliability-First Fallback")
    print("=" * 60)

    config = LLMConfig(
        openai_model="gpt-4",
        anthropic_model="claude-3-opus-20240229",
        enable_cache=True,
        max_retries=5  # More retries for reliability
    )

    llm = ManagedLLM(
        primary="openai",  # Most reliable
        fallbacks=["anthropic", "ollama"],  # Backup + local fallback
        config=config
    )

    try:
        response = llm.generate("Explain neural networks")
        print(f"\n✓ Got response from {response.provider}")
        print(f"  Retries needed: {response.metadata.get('retries', 0)}")
    except Exception as e:
        print(f"\n✗ All providers failed: {e}")


def example_4_specific_use_cases():
    """
    Example 4: Task-specific fallback strategies

    Different tasks have different requirements:
    - Code generation: OpenAI (best at code) → Anthropic → Ollama
    - Analysis: Anthropic (best reasoning) → OpenAI → Ollama
    - Quick queries: Ollama (fastest) → GPT-3.5 → Claude Haiku
    """
    print("\n" + "=" * 60)
    print("Example 4: Task-Specific Fallback Strategies")
    print("=" * 60)

    # For code generation
    code_llm = ManagedLLM(
        primary="openai",  # GPT-4 is excellent at code
        fallbacks=["anthropic", "ollama"],
        config=LLMConfig(openai_model="gpt-4")
    )

    # For analysis/reasoning
    analysis_llm = ManagedLLM(
        primary="anthropic",  # Claude is excellent at reasoning
        fallbacks=["openai", "ollama"],
        config=LLMConfig(anthropic_model="claude-3-opus-20240229")
    )

    # For quick queries
    quick_llm = ManagedLLM(
        primary="ollama",  # Fastest, local
        fallbacks=["openai"],
        config=LLMConfig(
            ollama_model="llama2",
            openai_model="gpt-3.5-turbo"
        )
    )

    print("\nCode generation task:")
    try:
        response = code_llm.generate("Write a Python function to merge two sorted lists")
        print(f"  Used: {response.provider}")
    except Exception as e:
        print(f"  Failed: {e}")

    print("\nAnalysis task:")
    try:
        response = analysis_llm.generate("Analyze the pros and cons of microservices")
        print(f"  Used: {response.provider}")
    except Exception as e:
        print(f"  Failed: {e}")

    print("\nQuick query:")
    try:
        response = quick_llm.generate("What is 2+2?")
        print(f"  Used: {response.provider} (latency: {response.latency_ms:.0f}ms)")
    except Exception as e:
        print(f"  Failed: {e}")


def example_5_custom_fallback_logic():
    """
    Example 5: Manual fallback with error handling

    For cases where you need custom logic:
    - Different prompts for different providers
    - Error categorization (rate limit vs API error)
    - Custom retry strategies
    """
    print("\n" + "=" * 60)
    print("Example 5: Manual Fallback with Custom Logic")
    print("=" * 60)

    config = LLMConfig()

    def generate_with_custom_fallback(prompt: str) -> str:
        """
        Custom fallback logic with provider-specific handling.
        """
        # Try OpenAI first
        try:
            print("  Trying OpenAI...")
            provider = LLMFactory.create("openai", config=config)
            response = provider.generate(prompt, temperature=0.7)
            print(f"  ✓ OpenAI succeeded")
            return response.text

        except Exception as openai_error:
            print(f"  ✗ OpenAI failed: {openai_error}")

            # If rate limited, wait and retry
            if "rate_limit" in str(openai_error).lower():
                print("  Rate limited - waiting before Anthropic...")
                import time
                time.sleep(5)

            # Try Anthropic with modified prompt
            try:
                print("  Trying Anthropic...")
                provider = LLMFactory.create("anthropic", config=config)

                # Anthropic prefers different prompt format
                modified_prompt = f"Please provide a detailed answer: {prompt}"

                response = provider.generate(modified_prompt, temperature=0.7)
                print(f"  ✓ Anthropic succeeded")
                return response.text

            except Exception as anthropic_error:
                print(f"  ✗ Anthropic failed: {anthropic_error}")

                # Try local Ollama as last resort
                try:
                    print("  Trying local Ollama...")
                    provider = LLMFactory.create("ollama", config=config)

                    # Ollama might need simpler prompts
                    simple_prompt = prompt.split(".")[0]  # Just first sentence

                    response = provider.generate(simple_prompt, temperature=0.7)
                    print(f"  ✓ Ollama succeeded")
                    return response.text

                except Exception as ollama_error:
                    print(f"  ✗ Ollama failed: {ollama_error}")
                    raise RuntimeError(
                        f"All providers failed:\n"
                        f"  OpenAI: {openai_error}\n"
                        f"  Anthropic: {anthropic_error}\n"
                        f"  Ollama: {ollama_error}"
                    )

    try:
        result = generate_with_custom_fallback("Explain transformers in AI")
        print(f"\n  Final result: {result[:100]}...")
    except Exception as e:
        print(f"\n  All fallbacks exhausted: {e}")


def example_6_streaming_with_fallback():
    """
    Example 6: Streaming responses with fallback

    All providers support streaming, fallback works the same way.
    """
    print("\n" + "=" * 60)
    print("Example 6: Streaming with Auto-Fallback")
    print("=" * 60)

    config = LLMConfig()

    def stream_with_fallback(prompt: str):
        """Stream from primary provider, fall back if needed."""
        providers_to_try = [
            ("openai", LLMFactory.create("openai", config=config)),
            ("anthropic", LLMFactory.create("anthropic", config=config)),
            ("ollama", LLMFactory.create("ollama", config=config)),
        ]

        for provider_name, provider in providers_to_try:
            try:
                print(f"\n  Streaming from {provider_name}...")
                print("  Response: ", end="", flush=True)

                for chunk in provider.stream(prompt):
                    print(chunk, end="", flush=True)

                print(f"\n  ✓ Completed with {provider_name}")
                return  # Success

            except Exception as e:
                print(f"\n  ✗ {provider_name} failed: {e}")
                continue

        print("\n  ✗ All providers failed for streaming")

    stream_with_fallback("Write a haiku about data lakes")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("NeuroLake LLM Auto-Fallback Examples")
    print("=" * 60)
    print("\nThese examples show how to use auto-fallback across:")
    print("  • OpenAI (GPT-4, GPT-3.5)")
    print("  • Anthropic (Claude 3 Opus, Sonnet, Haiku)")
    print("  • Ollama (Local models)")
    print("\nPattern: if provider_1_fails → try provider_2 → try provider_3")
    print("=" * 60)

    # Run examples
    # example_1_basic_fallback()
    # example_2_cost_optimized()
    # example_3_reliability_first()
    # example_4_specific_use_cases()
    # example_5_custom_fallback_logic()
    # example_6_streaming_with_fallback()

    print("\nUncomment the examples above to run them!")
