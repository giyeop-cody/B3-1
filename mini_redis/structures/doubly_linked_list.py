"""이중 연결 리스트(Doubly Linked List) 구현.

LRU 캐시의 "최근 사용 순서"를 표현하기 위해 사용한다. 노드 객체에 대한
직접 참조만 있으면 리스트 중간 노드라도 O(1)에 분리/이동할 수 있다는 점이
핵심이다(해시맵이 key -> Node 매핑을 들고 있으므로 탐색 없이 바로 접근).

설계 포인트: 더미 head/tail 센티넬 노드를 둔다.
    - 경계 조건(빈 리스트, 양 끝 삽입/삭제)에서 None 분기를 없애 코드가 단순해짐.
    - 모든 삽입/삭제/이동 연산을 분기 없이 O(1)로 구현 가능.

front(앞) = head 바로 다음 = "가장 최근 사용(MRU)"
back(뒤)  = tail 바로 이전 = "가장 오래 사용 안 됨(LRU)"
"""


class Node:
    """이중 연결 리스트의 노드.

    :ivar prev: 이전 노드 참조
    :ivar next: 다음 노드 참조
    :ivar data: 노드가 담는 임의의 데이터(LRU에서는 보통 key 문자열)
    """

    __slots__ = ("prev", "next", "data")

    def __init__(self, data=None):
        self.prev = None
        self.next = None
        self.data = data


class DoublyLinkedList:
    """더미 센티넬을 사용하는 이중 연결 리스트. 모든 핵심 연산 O(1)."""

    def __init__(self):
        # 더미 head/tail 센티넬: head <-> tail (빈 상태).
        self._head = Node()  # 실제 데이터 없음(앞쪽 경계).
        self._tail = Node()  # 실제 데이터 없음(뒤쪽 경계).
        self._head.next = self._tail
        self._tail.prev = self._head
        self._size = 0

    # ------------------------------------------------------------------ #
    # 내부 헬퍼: 두 노드 사이에 node 삽입 / node 분리
    # ------------------------------------------------------------------ #
    def _insert_between(self, node, left, right):
        """left와 right 사이에 node를 끼워 넣는다. O(1)."""
        node.prev = left
        node.next = right
        left.next = node
        right.prev = node
        self._size += 1

    def _unlink(self, node):
        """node를 리스트에서 분리한다(좌우를 직접 연결). O(1)."""
        node.prev.next = node.next
        node.next.prev = node.prev
        node.prev = None
        node.next = None
        self._size -= 1

    # ------------------------------------------------------------------ #
    # 삽입
    # ------------------------------------------------------------------ #
    def insert_front(self, data):
        """리스트 맨 앞(MRU 위치)에 새 노드를 추가하고 그 노드를 반환한다. O(1)."""
        node = Node(data)
        self._insert_between(node, self._head, self._head.next)
        return node

    def insert_back(self, data):
        """리스트 맨 뒤(LRU 위치)에 새 노드를 추가하고 그 노드를 반환한다. O(1)."""
        node = Node(data)
        self._insert_between(node, self._tail.prev, self._tail)
        return node

    # ------------------------------------------------------------------ #
    # 삭제
    # ------------------------------------------------------------------ #
    def remove_front(self):
        """맨 앞 노드를 제거하고 그 data를 반환한다. 비었으면 None. O(1)."""
        if self._size == 0:
            return None
        node = self._head.next
        self._unlink(node)
        return node.data

    def remove_back(self):
        """맨 뒤 노드를 제거하고 그 data를 반환한다. 비었으면 None. O(1).

        LRU 캐시에서 "가장 오래 사용되지 않은 키"를 꺼낼 때 사용한다.
        """
        if self._size == 0:
            return None
        node = self._tail.prev
        self._unlink(node)
        return node.data

    def remove_node(self, node):
        """주어진 노드를 리스트에서 제거한다. O(1).

        해시맵을 통해 노드 참조를 바로 알 수 있으므로 탐색이 필요 없다.
        """
        if node is self._head or node is self._tail:
            raise ValueError("cannot remove sentinel node")
        self._unlink(node)
        return node.data

    # ------------------------------------------------------------------ #
    # 이동
    # ------------------------------------------------------------------ #
    def move_to_front(self, node):
        """기존 노드를 맨 앞(MRU)으로 이동시킨다. O(1).

        LRU 캐시에서 키가 조회/갱신될 때 "최근 사용됨"으로 표시하는 핵심 연산.
        분리(unlink) 후 head 바로 뒤에 재삽입한다.
        """
        if node is self._head or node is self._tail:
            raise ValueError("cannot move sentinel node")
        self._unlink(node)
        self._insert_between(node, self._head, self._head.next)

    # ------------------------------------------------------------------ #
    # 조회용
    # ------------------------------------------------------------------ #
    def front_node(self):
        """맨 앞 실제 노드를 반환한다(없으면 None)."""
        if self._size == 0:
            return None
        return self._head.next

    def back_node(self):
        """맨 뒤 실제 노드를 반환한다(없으면 None)."""
        if self._size == 0:
            return None
        return self._tail.prev

    def size(self):
        """노드 개수를 반환한다."""
        return self._size

    def is_empty(self):
        return self._size == 0

    def __len__(self):
        return self._size

    def iter_nodes(self):
        """앞(MRU)에서 뒤(LRU) 순서로 실제 노드 객체를 순회한다.

        센티넬(head/tail)은 건너뛴다. 노드 자체가 필요한 경우(예: 해시맵이
        체인에서 엔트리 노드를 찾아 삭제)에 사용한다.
        """
        cur = self._head.next
        while cur is not self._tail:
            yield cur
            cur = cur.next

    def __iter__(self):
        """앞(MRU)에서 뒤(LRU) 순서로 각 노드의 data를 순회한다."""
        cur = self._head.next
        while cur is not self._tail:
            yield cur.data
            cur = cur.next
