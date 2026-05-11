"""
LLM 클라이언트 래퍼
OpenAI 형식으로 통일해 호출
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


class LLMClient:
    """LLM 클라이언트"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 구성되지 않음")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        채팅 요청 전송
        
        Args:
            messages: 메시지 목록
            temperature: 온도 매개변수
            max_tokens: 최대 토큰 수
            response_format: 응답 형식（예: JSON 모드）
            
        Returns:
            모델 응답 텍스트
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 일부 모델（예: MiniMax M2.5）은 content에 <think> 사고 내용이 포함될 수 있어 제거해야 함
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        채팅 요청을 전송하고 JSON을 반환
        
        Args:
            messages: 메시지 목록
            temperature: 온도 매개변수
            max_tokens: 최대 토큰 수
            
        Returns:
            파싱된 JSON 객체
        """
        first_error: Optional[Exception] = None

        try:
            response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            return self._parse_json_text(response)
        except Exception as err:
            # 일부 OpenAI-compatible 프록시/모델은 response_format=json_object를
            # 완전히 지원하지 않아 실패할 수 있으므로 일반 텍스트 모드로 한 번 더 시도
            first_error = err

        try:
            fallback_response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=None
            )
            return self._parse_json_text(fallback_response)
        except Exception as fallback_error:
            raise ValueError(
                f"LLM JSON 호출 실패 (json_mode_error={first_error}, fallback_error={fallback_error})"
            ) from fallback_error

    def _parse_json_text(self, response_text: str) -> Dict[str, Any]:
        """모델 응답 텍스트에서 JSON 객체를 추출/파싱"""
        cleaned_response = response_text.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        # 우선 원문 전체를 JSON으로 파싱 시도
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            pass

        # 모델이 앞뒤 설명을 섞어 보낸 경우 첫 JSON 객체 영역을 추출
        start = cleaned_response.find('{')
        end = cleaned_response.rfind('}')
        if start >= 0 and end > start:
            candidate = cleaned_response[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        raise ValueError(f"LLM이 반환한 JSON 형식이 유효하지 않음: {cleaned_response}")
