"""최소 힙(Min-Heap) 구현 - TTL 만료 관리용.

TTL(만료) 관리는 "가장 먼저 만료될 키"를 빠르게 찾는 것이 핵심이다.
최소 힙은 루트가 항상 최솟값(가장 이른 만료 시각)이므로 peek O(1),
pop/push O(log n)으로 이 요구를 만족한다.

요소 형태
    ``(expire_at, key)`` 튜플을 저장한다. 파이썬 튜플 비교는 앞 원소부터
    비교하므로 expire_at(만료 시각) 기준으로 자연스럽게 정렬된다.

완전 이진 트리를 배열(여기서는 동적 배열)로 표현한다.
    - 부모(i)  -> 자식: 2i+1, 2i+2
    - 자식(i)  -> 부모: (i-1)//2

lazy deletion 전략
    힙에서 임의 원소를 직접 지우는 것은 비싸다. 대신 만료 시각이 갱신되거나
    키가 삭제되면 힙 엔트리는 그대로 두고, pop 시점에 "현재 유효한 만료
    시각과 일치하는가"를 확인해 stale 엔트리를 버린다(검증은 호출 측에서 수행).
"""

from .dynamic_array import DynamicArray


class MinHeap:
    """``(expire_at, key)`` 요소를 다루는 최소 힙."""

    def __init__(self):
        # 내부 저장소로 동적 배열 사용(인덱스 접근 + 2배 확장).
        self._data = DynamicArray()

    # ------------------------------------------------------------------ #
    # 내부: 상향/하향 정렬
    # ------------------------------------------------------------------ #
    def _heapify_up(self, idx):
        """idx 위치 원소를 부모와 비교하며 위로 끌어올린다. O(log n)."""
        data = self._data
        while idx > 0:
            parent = (idx - 1) // 2
            if data.get(idx) < data.get(parent):
                self._swap(idx, parent)
                idx = parent
            else:
                break

    def _heapify_down(self, idx):
        """idx 위치 원소를 자식과 비교하며 아래로 내린다. O(log n)."""
        data = self._data
        n = data.size()
        while True:
            left = 2 * idx + 1
            right = 2 * idx + 2
            smallest = idx
            if left < n and data.get(left) < data.get(smallest):
                smallest = left
            if right < n and data.get(right) < data.get(smallest):
                smallest = right
            if smallest == idx:
                break
            self._swap(idx, smallest)
            idx = smallest

    def _swap(self, i, j):
        """배열의 i, j 위치 원소를 교환한다."""
        data = self._data
        tmp = data.get(i)
        data.set(i, data.get(j))
        data.set(j, tmp)

    # ------------------------------------------------------------------ #
    # 공개 메서드
    # ------------------------------------------------------------------ #
    def push(self, item):
        """요소를 삽입한다. O(log n).

        :param item: ``(expire_at, key)`` 형태의 비교 가능한 튜플.
        """
        self._data.append(item)
        self._heapify_up(self._data.size() - 1)

    def pop(self):
        """최솟값(가장 이른 만료) 요소를 제거하고 반환한다. O(log n).

        비어 있으면 None을 반환한다.
        """
        n = self._data.size()
        if n == 0:
            return None
        root = self._data.get(0)
        last = self._data.pop()
        if n > 1:
            self._data.set(0, last)
            self._heapify_down(0)
        return root

    def peek(self):
        """제거하지 않고 최솟값 요소를 반환한다. O(1). 비었으면 None."""
        if self._data.size() == 0:
            return None
        return self._data.get(0)

    def size(self):
        """힙에 담긴 요소 개수를 반환한다."""
        return self._data.size()

    def is_empty(self):
        return self._data.size() == 0

    def __len__(self):
        return self._data.size()
