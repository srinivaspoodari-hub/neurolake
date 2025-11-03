"""
Retry Logic

Implements exponential backoff retry for LLM requests.
"""

import time
import logging
from typing import Callable, TypeVar, Optional, Type, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        retry_on: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retries
            initial_delay: Initial delay in seconds
            backoff_factor: Exponential backoff factor
            max_delay: Maximum delay in seconds
            retry_on: Tuple of exception types to retry on
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.retry_on = retry_on

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt."""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator to retry a function with exponential backoff.

    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def call_api():
            return requests.get("https://api.example.com")

    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Exponential backoff factor
        max_delay: Maximum delay in seconds
        retry_on: Tuple of exception types to retry on
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        max_delay=max_delay,
        retry_on=retry_on
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.retry_on as e:
                    last_exception = e

                    if attempt == config.max_retries:
                        logger.error(
                            f"Max retries ({config.max_retries}) exceeded for {func.__name__}: {e}"
                        )
                        raise

                    delay = config.get_delay(attempt)
                    logger.warning(
                        f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                        f"after {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


class RetryHandler:
    """
    Handler for retrying operations with backoff.

    Example:
        handler = RetryHandler(max_retries=3)

        result = handler.execute(
            lambda: api_call(),
            retry_on=(RateLimitError, TimeoutError)
        )
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0
    ):
        """Initialize retry handler."""
        self.config = RetryConfig(
            max_retries=max_retries,
            initial_delay=initial_delay,
            backoff_factor=backoff_factor,
            max_delay=max_delay
        )

    def execute(
        self,
        func: Callable[..., T],
        *args,
        retry_on: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> T:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            retry_on: Tuple of exceptions to retry on
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception if all retries are exhausted
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except retry_on as e:
                last_exception = e

                if attempt == self.config.max_retries:
                    logger.error(
                        f"Max retries ({self.config.max_retries}) exceeded: {e}"
                    )
                    raise

                delay = self.config.get_delay(attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{self.config.max_retries} "
                    f"after {delay:.1f}s: {e}"
                )
                time.sleep(delay)

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")


__all__ = ["retry_with_backoff", "RetryHandler", "RetryConfig"]
