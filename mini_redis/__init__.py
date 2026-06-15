"""Mini Redis - CLI 기반 인메모리 Key-Value 저장소.

직접 구현한 자료구조(이중 연결 리스트 / 해시맵 / 최소 힙 / 동적 배열)를
조합해 Redis의 핵심 기능(String 명령, LRU 자동 제거, TTL)을 구현한다.
"""

from .engine import MiniRedis, OOMError
from .cli import CLI, repl

__all__ = ["MiniRedis", "OOMError", "CLI", "repl"]
__version__ = "1.0.0"
