from __future__ import annotations

import logging
from dataclasses import dataclass
from os import environ
from typing import Optional

from openai import APIError, OpenAI

logger = logging.getLogger(__name__)


@dataclass
class AssistantConfig:
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.4
    max_tokens: int = 600


class AssistantClientError(RuntimeError):
    """Raised when the AI backend cannot produce an answer."""


class AssistantClient:
    def __init__(self, config: AssistantConfig):
        self.config = config
        self._client: Optional[OpenAI] = None

        # initialize client only if API key is available
        if config.api_key and config.api_key.strip():
            try:
                self._client = OpenAI(api_key=config.api_key.strip())

            except Exception as e:
                logger.error("Failed to initialize OpenAI client: %s", e)
                self._client = None

    def is_enabled(self) -> bool:
        """Check if client is properly configured and ready to use."""
        return self._client is not None and self.config.api_key is not None

    def generate(self, system_prompt: str, query: str) -> str:
        """Generate AI response with proper error handling."""

        if not self.is_enabled():
            raise AssistantClientError(
                'Assistant client is disabled \
                    (missing or invalid OPENAI_API_KEY).'
            )

        try:
            # use chat.completions.create instead of responses.create
            completion = self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': query},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            # extract content safely
            if (completion.choices and
                completion.choices[0].message and
                    completion.choices[0].message.content):
                answer = completion.choices[0].message.content.strip()

            else:
                raise AssistantClientError('Empty response from AI model...')

            if not answer:
                raise AssistantClientError('Empty response from AI model...')

            return answer

        except APIError as api_err:
            logger.error('OpenAI API error: %s', api_err)
            raise AssistantClientError(
                f'AI service error: {api_err}') from api_err

        except Exception as e:
            logger.error('Unexpected error in AI client: %s', e)
            raise AssistantClientError(f'AI client error: {e}') from e


def create_assistant_client() -> AssistantClient:
    """
    Factory function to create assistant client with environment configuration.
    """
    api_key: Optional[str] = environ.get('OPENAI_API_KEY')

    # validate API key presence
    if not api_key or not api_key.strip():
        logger.warning(
            'OPENAI_API_KEY not found or empty. AI assistant will be disabled.'
        )

    return AssistantClient(
        AssistantConfig(
            api_key=api_key,
            model=environ.get('ASSISTANT_MODEL', 'gpt-4o-mini'),
            temperature=float(environ.get('ASSISTANT_TEMPERATURE', '0.4')),
            max_tokens=int(environ.get('ASSISTANT_MAX_TOKENS', '600')),
        )
    )


# create singleton instance
jhaptech_assistant_client = create_assistant_client()
