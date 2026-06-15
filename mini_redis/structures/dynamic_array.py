"""동적 배열(Dynamic Array) 구현.

파이썬 ``list``는 사실상 동적 배열이지만, 본 미션은 "고정 길이 배열/인덱스
접근" 수준의 저장소만 허용한다. 따라서 내부적으로 고정 용량의 저장소를 두고,
용량이 가득 차면 2배로 확장하는 동적 배열을 직접 구현한다.

해시맵의 버킷 테이블, 힙의 내부 저장소가 이 동적 배열 위에서 동작한다.

시간 복잡도
    - append : 평균 O(1) (분할 상환), 확장 시 O(n)
    - get/set: O(1)
    - pop    : O(1) (맨 뒤)
"""


class DynamicArray:
    """capacity 2배 확장을 지원하는 동적 배열.

    내부 저장소(``_store``)는 고정 길이 리스트를 흉내 내는 용도로만 사용하며,
    인덱스 기반 접근/대입만 수행한다(키-값 컬렉션으로 사용하지 않음).
    """

    def __init__(self, initial_capacity=8):
        """초기 용량을 가진 빈 동적 배열을 생성한다.

        :param initial_capacity: 최초 내부 저장소 용량(최소 1).
        """
        if initial_capacity < 1:
            initial_capacity = 1
        self._capacity = initial_capacity
        self._size = 0
        # None으로 채운 고정 길이 저장소(인덱스 접근 전용).
        self._store = [None] * self._capacity

    # ------------------------------------------------------------------ #
    # 내부 헬퍼
    # ------------------------------------------------------------------ #
    def _resize(self, new_capacity):
        """내부 저장소를 ``new_capacity`` 크기로 재할당하고 원소를 복사한다."""
        new_store = [None] * new_capacity
        for i in range(self._size):
            new_store[i] = self._store[i]
        self._store = new_store
        self._capacity = new_capacity

    def _check_index(self, index):
        """인덱스 범위를 검사하고 음수 인덱스를 정규화한다."""
        if index < 0:
            index += self._size
        if index < 0 or index >= self._size:
            raise IndexError("DynamicArray index out of range")
        return index

    # ------------------------------------------------------------------ #
    # 공개 메서드
    # ------------------------------------------------------------------ #
    def append(self, value):
        """배열 끝에 원소를 추가한다. 용량 초과 시 2배로 확장한다."""
        if self._size == self._capacity:
            self._resize(self._capacity * 2)
        self._store[self._size] = value
        self._size += 1

    def get(self, index):
        """인덱스 위치의 값을 반환한다. O(1)."""
        index = self._check_index(index)
        return self._store[index]

    def set(self, index, value):
        """인덱스 위치의 값을 덮어쓴다. O(1)."""
        index = self._check_index(index)
        self._store[index] = value

    def pop(self):
        """맨 뒤 원소를 제거하고 반환한다. O(1).

        사용량이 용량의 1/4 이하로 떨어지면 저장소를 절반으로 축소한다.
        """
        if self._size == 0:
            raise IndexError("pop from empty DynamicArray")
        self._size -= 1
        value = self._store[self._size]
        self._store[self._size] = None  # 참조 해제(GC 도움).
        # 메모리 절약을 위한 선택적 축소.
        if 0 < self._size <= self._capacity // 4 and self._capacity > 1:
            self._resize(self._capacity // 2)
        return value

    def remove(self, index):
        """인덱스 위치의 원소를 제거한다(뒤 원소들을 한 칸씩 당김). O(n)."""
        index = self._check_index(index)
        value = self._store[index]
        for i in range(index, self._size - 1):
            self._store[i] = self._store[i + 1]
        self._size -= 1
        self._store[self._size] = None
        return value

    def size(self):
        """현재 원소 개수를 반환한다."""
        return self._size

    def capacity(self):
        """현재 내부 저장소 용량을 반환한다."""
        return self._capacity

    def __len__(self):
        return self._size

    def __iter__(self):
        for i in range(self._size):
            yield self._store[i]

    def __repr__(self):
        items = ", ".join(repr(self._store[i]) for i in range(self._size))
        return "DynamicArray([{}])".format(items)
