"""해시맵(HashMap) 구현 - 체이닝(chaining) 방식 충돌 해결.

내장 ``dict`` 사용이 금지되어 있으므로 키-값 저장소를 직접 구현한다.

구성
    - 버킷 테이블: :class:`DynamicArray` (인덱스 접근 전용, 2배 확장 지원)
    - 각 버킷  : :class:`DoublyLinkedList` (같은 인덱스로 충돌한 엔트리들의 체인)
    - 엔트리  : :class:`_Entry` (key, value 쌍)

해시 함수(직접 설계)
    문자열에 대한 다항식 롤링 해시(djb2 계열). 초기값 5381에서 시작해
    각 문자마다 ``h = h * 33 + ord(c)``를 누적한다. 33이라는 작은 홀수 배수와
    초기값 5381 조합은 영문/숫자 키에서 분포가 고르기로 알려져 있다.
    최종적으로 32비트 마스킹 후 버킷 개수로 나눈 나머지를 인덱스로 쓴다.

로드 팩터
    size / capacity 가 0.75를 초과하면 버킷 수를 2배로 늘리고 전체 rehash 한다.
    이를 통해 체인 평균 길이를 상수로 유지 → 평균 O(1) 조회/삽입/삭제.
"""

from .dynamic_array import DynamicArray
from .doubly_linked_list import DoublyLinkedList


class _Entry:
    """해시맵 버킷 체인에 저장되는 키-값 엔트리."""

    __slots__ = ("key", "value")

    def __init__(self, key, value):
        self.key = key
        self.value = value


# 모듈 내부에서만 쓰는 "찾지 못함" 표식(None을 정상 값으로 저장 가능하게).
_MISSING = object()


class HashMap:
    """체이닝 기반 해시맵.

    공개 메서드: put, get, remove, contains, keys, size
    """

    _LOAD_FACTOR = 0.75

    def __init__(self, initial_capacity=8):
        """초기 버킷 개수를 가진 빈 해시맵을 생성한다."""
        if initial_capacity < 1:
            initial_capacity = 1
        self._capacity = initial_capacity
        self._size = 0
        self._buckets = self._make_buckets(self._capacity)

    # ------------------------------------------------------------------ #
    # 내부 헬퍼
    # ------------------------------------------------------------------ #
    @staticmethod
    def _make_buckets(capacity):
        """capacity개의 빈 버킷(이중 연결 리스트)으로 채운 동적 배열을 만든다."""
        buckets = DynamicArray(capacity)
        for _ in range(capacity):
            buckets.append(DoublyLinkedList())
        return buckets

    def _hash(self, key):
        """직접 설계한 문자열 해시 함수(djb2 계열).

        :param key: 해시 대상(문자열로 변환하여 처리).
        :return: 32비트 부호 없는 정수 해시값.
        """
        if not isinstance(key, str):
            key = str(key)
        h = 5381
        for ch in key:
            # h * 33 + ord(ch)  →  (h << 5) + h 로 빠르게 계산.
            h = ((h << 5) + h) + ord(ch)
            h &= 0xFFFFFFFF  # 32비트로 유지(오버플로 방지/일관성).
        return h

    def _index_for(self, key, capacity):
        """주어진 capacity 기준으로 key의 버킷 인덱스를 계산한다."""
        return self._hash(key) % capacity

    def _find_entry(self, key):
        """key에 해당하는 (버킷, 노드, 엔트리)를 찾는다.

        :return: (bucket, node, entry) 또는 찾지 못하면 (bucket, None, None).
        """
        idx = self._index_for(key, self._capacity)
        bucket = self._buckets.get(idx)
        for node in bucket.iter_nodes():
            entry = node.data
            if entry.key == key:
                return bucket, node, entry
        return bucket, None, None

    def _resize(self, new_capacity):
        """버킷 수를 new_capacity로 늘리고 모든 엔트리를 rehash 한다."""
        old_buckets = self._buckets
        new_buckets = self._make_buckets(new_capacity)
        for bucket in old_buckets:
            for entry in bucket:  # 체인의 각 엔트리.
                idx = self._index_for(entry.key, new_capacity)
                new_buckets.get(idx).insert_back(entry)
        self._buckets = new_buckets
        self._capacity = new_capacity

    # ------------------------------------------------------------------ #
    # 공개 메서드
    # ------------------------------------------------------------------ #
    def put(self, key, value):
        """key에 value를 저장한다. 기존 key면 값만 갱신한다.

        삽입 후 로드 팩터가 0.75를 초과하면 버킷을 2배로 확장한다.
        평균 O(1).
        """
        bucket, node, entry = self._find_entry(key)
        if entry is not None:
            entry.value = value  # 기존 키 갱신.
            return
        bucket.insert_back(_Entry(key, value))
        self._size += 1
        if self._size > self._capacity * self._LOAD_FACTOR:
            self._resize(self._capacity * 2)

    def get(self, key, default=None):
        """key의 값을 반환한다. 없으면 default. 평균 O(1)."""
        _, _, entry = self._find_entry(key)
        if entry is None:
            return default
        return entry.value

    def get_or_missing(self, key):
        """key의 값을 반환하되, 없으면 내부 sentinel(_MISSING)을 반환한다.

        값으로 None을 저장한 경우와 "키 없음"을 구분하기 위해 사용한다.
        """
        _, _, entry = self._find_entry(key)
        if entry is None:
            return _MISSING
        return entry.value

    def remove(self, key):
        """key를 삭제한다. 삭제 성공 시 True, 없으면 False. 평균 O(1)."""
        bucket, node, entry = self._find_entry(key)
        if node is None:
            return False
        bucket.remove_node(node)
        self._size -= 1
        return True

    def contains(self, key):
        """key 존재 여부를 반환한다. 평균 O(1)."""
        _, _, entry = self._find_entry(key)
        return entry is not None

    def keys(self):
        """모든 키를 동적 배열에 담아 반환한다(순서 보장 안 함)."""
        result = DynamicArray(max(self._size, 1))
        for bucket in self._buckets:
            for entry in bucket:
                result.append(entry.key)
        return result

    def items(self):
        """(key, value) 튜플들을 동적 배열에 담아 반환한다."""
        result = DynamicArray(max(self._size, 1))
        for bucket in self._buckets:
            for entry in bucket:
                result.append((entry.key, entry.value))
        return result

    def size(self):
        """저장된 엔트리 개수를 반환한다."""
        return self._size

    def capacity(self):
        """현재 버킷 개수를 반환한다."""
        return self._capacity

    def load_factor(self):
        """현재 로드 팩터(size/capacity)를 반환한다."""
        return self._size / self._capacity

    def __len__(self):
        return self._size

    def __contains__(self, key):
        return self.contains(key)
