"""Mini Redis 핵심 엔진.

직접 구현한 자료구조를 조합해 Redis의 핵심 동작을 구현한다.

데이터 모델 (각 책임 분리)
    - ``_store``    : HashMap[key -> value]            (실제 키-값 데이터)
    - ``_nodes``    : HashMap[key -> Node]             (LRU 리스트 내 노드 참조)
    - ``_lru``      : DoublyLinkedList(data=key)       (사용 순서: front=MRU, back=LRU)
    - ``_expires``  : HashMap[key -> expire_at(float)] (키별 만료 시각)
    - ``_ttl_heap`` : MinHeap[(expire_at, key)]        (가장 이른 만료 빠른 탐색)

LRU가 O(1)인 이유
    - 조회: ``_nodes``(해시맵)로 key의 리스트 노드를 O(1)에 찾는다.
    - 갱신: 찾은 노드를 이중 연결 리스트에서 O(1)에 front로 이동한다.
    => 해시맵(빠른 조회) + 이중 연결 리스트(빠른 순서 갱신) 조합이 둘 다 필요.

메모리 산정
    used_memory = Σ( len(utf8(key)) + len(utf8(value)) )
    자료구조 오버헤드는 제외한다.
"""

import time

from .structures.hash_map import HashMap, _MISSING
from .structures.doubly_linked_list import DoublyLinkedList
from .structures.min_heap import MinHeap


def _utf8_len(s):
    """문자열의 UTF-8 인코딩 바이트 길이를 반환한다."""
    return len(s.encode("utf-8"))


class OOMError(Exception):
    """단일 엔트리가 maxmemory를 초과해 저장할 수 없을 때 발생."""


class MiniRedis:
    """Mini Redis 엔진. 명령어 핸들러(CLI)에서 호출하는 API를 제공한다."""

    def __init__(self, time_func=None):
        """엔진 상태를 초기화한다.

        :param time_func: 현재 시각(초)을 반환하는 함수. 테스트에서 가짜 시계를
                          주입할 수 있도록 의존성을 분리한다. 기본은 time.time.
        """
        self._now = time_func if time_func is not None else time.time

        self._store = HashMap()      # key -> value
        self._nodes = HashMap()      # key -> LRU 노드
        self._lru = DoublyLinkedList()  # front=MRU, back=LRU
        self._expires = HashMap()    # key -> expire_at
        self._ttl_heap = MinHeap()   # (expire_at, key)

        self._maxmemory = 0          # 0 = 무제한
        self._used_memory = 0        # Σ(len(key)+len(value))
        self._evicted_keys = 0       # LRU로 제거된 키 누적 수

    # ================================================================== #
    # 만료(expiry) 처리
    # ================================================================== #
    def _is_expired(self, key):
        """key가 만료 시각을 가지고 있고 이미 지났는지 판단한다(삭제하지 않음)."""
        exp = self._expires.get_or_missing(key)
        if exp is _MISSING:
            return False
        return exp <= self._now()

    def _ensure_alive(self, key):
        """key가 존재하고 살아있으면 True. 만료됐으면 삭제 후 False 반환.

        모든 키 기반 명령은 실행 전에 이 함수로 "만료 여부"를 먼저 확인한다.
        """
        if not self._store.contains(key):
            return False
        if self._is_expired(key):
            self._delete_key(key)  # 만료 → lazy 삭제.
            return False
        return True

    def _purge_expired_from_heap(self):
        """힙 루트의 stale/만료 엔트리를 정리한다(능동적 정리).

        lazy deletion: 힙에는 갱신/삭제된 stale 엔트리가 남을 수 있으므로,
        루트가 (a) 현재 만료시각과 불일치하거나 (b) 키가 사라졌으면 버린다.
        실제 만료된(현재시각 지난) 살아있는 키는 삭제 처리한다.
        """
        now = self._now()
        while not self._ttl_heap.is_empty():
            expire_at, key = self._ttl_heap.peek()
            current = self._expires.get_or_missing(key)
            if current is _MISSING or current != expire_at:
                # stale 엔트리(만료시각 변경/삭제됨) → 버린다.
                self._ttl_heap.pop()
                continue
            if expire_at <= now:
                # 실제로 만료됨 → 키 삭제.
                self._ttl_heap.pop()
                if self._store.contains(key):
                    self._delete_key(key)
                continue
            break  # 루트가 아직 만료 전 → 더 볼 것 없음.

    # ================================================================== #
    # 내부: 키 삭제 / 메모리 갱신 / LRU
    # ================================================================== #
    def _delete_key(self, key):
        """데이터/LRU/TTL 모든 구조에서 key 엔트리를 제거한다.

        used_memory도 함께 차감한다. 힙 엔트리는 lazy deletion으로 남겨둔다.
        :return: 실제로 삭제했으면 True.
        """
        value = self._store.get_or_missing(key)
        if value is _MISSING:
            return False
        # 메모리 차감.
        self._used_memory -= (_utf8_len(key) + _utf8_len(value))
        # 데이터 삭제.
        self._store.remove(key)
        # LRU 노드 삭제.
        node = self._nodes.get_or_missing(key)
        if node is not _MISSING:
            self._lru.remove_node(node)
            self._nodes.remove(key)
        # TTL 메타 삭제(힙 엔트리는 lazy).
        if self._expires.contains(key):
            self._expires.remove(key)
        return True

    def _touch_lru(self, key):
        """key를 MRU(front)로 이동시킨다. 조회/갱신 성공 시 호출. O(1)."""
        node = self._nodes.get_or_missing(key)
        if node is not _MISSING:
            self._lru.move_to_front(node)

    def _evict_until_within_limit(self):
        """used_memory가 maxmemory 이하가 될 때까지 LRU 키를 제거한다."""
        if self._maxmemory <= 0:
            return
        while self._used_memory > self._maxmemory and not self._lru.is_empty():
            lru_key = self._lru.back_node().data  # 가장 오래된 키.
            self._delete_key(lru_key)
            self._evicted_keys += 1

    # ================================================================== #
    # String 명령
    # ================================================================== #
    def set(self, key, value):
        """SET key value. 성공 시 'OK'.

        흐름:
            1) 단일 엔트리 크기가 maxmemory(>0) 초과면 OOMError.
            2) 기존 키면 값/메모리 교체하고 TTL 초기화(삭제).
            3) 신규 키면 저장 + LRU front 삽입.
            4) used_memory 갱신 후 maxmemory 초과 시 LRU eviction.
        """
        entry_size = _utf8_len(key) + _utf8_len(value)
        if self._maxmemory > 0 and entry_size > self._maxmemory:
            # 단일 엔트리 자체가 한계 초과 → 저장 불가.
            raise OOMError()

        existing = self._store.get_or_missing(key)
        if existing is not _MISSING:
            # 덮어쓰기: 메모리 조정 + TTL 초기화.
            self._used_memory -= (_utf8_len(key) + _utf8_len(existing))
            self._store.put(key, value)
            self._used_memory += entry_size
            if self._expires.contains(key):
                self._expires.remove(key)  # 덮어쓰면 TTL 삭제.
            self._touch_lru(key)
        else:
            # 신규.
            self._store.put(key, value)
            self._used_memory += entry_size
            node = self._lru.insert_front(key)
            self._nodes.put(key, node)

        self._evict_until_within_limit()
        return "OK"

    def get(self, key):
        """GET key. 값이 있으면 그 문자열, 없거나 만료면 None.

        흐름: TTL 확인 → 만료면 삭제 후 None(LRU 갱신 안 함) →
              살아있으면 값 반환 + LRU 갱신.
        """
        if not self._ensure_alive(key):
            return None
        value = self._store.get(key)
        self._touch_lru(key)  # 조회 성공 시에만 LRU 갱신.
        return value

    def delete(self, key):
        """DEL key. 삭제했으면 1, 없으면 0."""
        # 만료된 키는 '없는 키'로 취급.
        if not self._store.contains(key):
            return 0
        if self._is_expired(key):
            self._delete_key(key)
            return 0
        self._delete_key(key)
        return 1

    def exists(self, key):
        """EXISTS key. 존재하고 살아있으면 1, 아니면 0."""
        return 1 if self._ensure_alive(key) else 0

    def dbsize(self):
        """DBSIZE. 살아있는 키 개수. 호출 시 힙으로 만료분을 먼저 정리한다."""
        self._purge_expired_from_heap()
        return self._store.size()

    def keys(self):
        """KEYS. 살아있는 모든 키를 리스트(파이썬 list)로 반환한다.

        힙을 이용해 만료된 키를 먼저 정리하므로 만료된 키는 목록에서 빠진다.
        """
        self._purge_expired_from_heap()
        result = []
        for k in self._store.keys():
            result.append(k)
        return result

    # ================================================================== #
    # 메모리 관리
    # ================================================================== #
    def config_set_maxmemory(self, value_str):
        """CONFIG SET maxmemory bytes. 성공 시 'OK'.

        :raises ValueError: 정수 파싱 실패 또는 음수.
        """
        n = _parse_nonneg_int(value_str)
        self._maxmemory = n
        # 한계가 줄었으면 즉시 eviction 적용.
        self._evict_until_within_limit()
        return "OK"

    def info_memory(self):
        """INFO memory. 3개 항목 문자열 리스트를 반환한다."""
        return [
            "used_memory:{}".format(self._used_memory),
            "maxmemory:{}".format(self._maxmemory),
            "evicted_keys:{}".format(self._evicted_keys),
        ]

    # ================================================================== #
    # TTL 관리
    # ================================================================== #
    def expire(self, key, seconds_str):
        """EXPIRE key seconds. 설정 성공 1, 키 없음 0.

        seconds <= 0 이면 즉시 만료(존재하면 삭제 후 1).
        :raises ValueError: 정수 파싱 실패.
        """
        seconds = _parse_int(seconds_str)
        if not self._ensure_alive(key):
            return 0
        if seconds <= 0:
            self._delete_key(key)
            return 1
        expire_at = self._now() + seconds
        self._expires.put(key, expire_at)
        self._ttl_heap.push((expire_at, key))  # 힙으로 빠른 만료 탐색.
        return 1

    def ttl(self, key):
        """TTL key. 없으면 -2, 만료시각 없으면 -1, 있으면 남은 초(올림 아닌 정수)."""
        if not self._ensure_alive(key):
            return -2
        exp = self._expires.get_or_missing(key)
        if exp is _MISSING:
            return -1
        remaining = exp - self._now()
        if remaining < 0:
            remaining = 0
        # 예시(설정 3 → 직후 TTL 2)와 맞추기 위해 int()로 내림 처리.
        return int(remaining)

    # ================================================================== #
    # 진단용 헬퍼(테스트/디버깅)
    # ================================================================== #
    def used_memory(self):
        return self._used_memory

    def evicted_keys(self):
        return self._evicted_keys

    def maxmemory(self):
        return self._maxmemory


# ---------------------------------------------------------------------- #
# 정수 파싱 헬퍼
# ---------------------------------------------------------------------- #
def _parse_int(s):
    """문자열을 정수로 파싱한다. 실패 시 ValueError."""
    try:
        return int(s)
    except (TypeError, ValueError):
        raise ValueError("not an integer")


def _parse_nonneg_int(s):
    """문자열을 0 이상 정수로 파싱한다. 실패/음수면 ValueError."""
    n = _parse_int(s)
    if n < 0:
        raise ValueError("must be non-negative")
    return n
