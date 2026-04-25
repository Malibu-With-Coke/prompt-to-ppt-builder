from abc import ABC, abstractmethod
from typing import Any, Mapping


class BaseLLMClient(ABC):
    provider_name = 'unknown'

    @abstractmethod
    def build_json_request(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Mapping[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def invoke_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Mapping[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError
