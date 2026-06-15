#!/usr/bin/env python3
"""Mini Redis 실행 진입점.

사용법:
    python3 main.py

``mini-redis>`` 프롬프트에서 명령을 입력한다. ``exit`` 또는 ``quit`` 으로 종료.
"""

from mini_redis.cli import repl


if __name__ == "__main__":
    repl()
