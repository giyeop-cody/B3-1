"""스택 / 큐 / 덱 구현 (보너스 과제 5.2).

세 자료구조 모두 직접 구현한 :class:`DoublyLinkedList` 위에서 동작하며,
모든 핵심 연산이 O(1)이다. 개념 설명은 ``docs/STACK_QUEUE_DEQUE.md`` 참고.

- Stack(LIFO): 한쪽 끝에서만 push/pop.
- Queue(FIFO): 한쪽 끝에서 넣고 반대쪽에서 뺀다.
- Deque      : 양쪽 끝 모두에서 넣고 뺄 수 있다.
"""

from .doubly_linked_list import DoublyLinkedList


class Stack:
    """LIFO 스택. 리스트 앞쪽(front)을 top으로 사용한다."""

    def __init__(self):
        self._list = DoublyLinkedList()

    def push(self, item):
        """top에 원소를 쌓는다. O(1)."""
        self._list.insert_front(item)

    def pop(self):
        """top 원소를 꺼내 반환한다. 비었으면 None. O(1)."""
        return self._list.remove_front()

    def peek(self):
        """top 원소를 제거하지 않고 본다. O(1)."""
        node = self._list.front_node()
        return None if node is None else node.data

    def is_empty(self):
        return self._list.is_empty()

    def size(self):
        return self._list.size()


class Queue:
    """FIFO 큐. 뒤(back)로 넣고 앞(front)에서 뺀다."""

    def __init__(self):
        self._list = DoublyLinkedList()

    def enqueue(self, item):
        """큐 뒤에 원소를 넣는다. O(1)."""
        self._list.insert_back(item)

    def dequeue(self):
        """큐 앞에서 원소를 꺼낸다. 비었으면 None. O(1)."""
        return self._list.remove_front()

    def peek(self):
        """큐 맨 앞 원소를 본다. O(1)."""
        node = self._list.front_node()
        return None if node is None else node.data

    def is_empty(self):
        return self._list.is_empty()

    def size(self):
        return self._list.size()


class Deque:
    """양방향 큐(덱). 양쪽 끝에서 삽입/삭제 가능. 모두 O(1)."""

    def __init__(self):
        self._list = DoublyLinkedList()

    def push_front(self, item):
        self._list.insert_front(item)

    def push_back(self, item):
        self._list.insert_back(item)

    def pop_front(self):
        return self._list.remove_front()

    def pop_back(self):
        return self._list.remove_back()

    def peek_front(self):
        node = self._list.front_node()
        return None if node is None else node.data

    def peek_back(self):
        node = self._list.back_node()
        return None if node is None else node.data

    def is_empty(self):
        return self._list.is_empty()

    def size(self):
        return self._list.size()
