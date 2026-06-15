"""이진 트리 / 이진 탐색 트리 구현 (보너스 과제 5.3, 5.4).

- :class:`BinaryTree`       : 일반 이진 트리 + 4가지 순회(전위/중위/후위/레벨).
- :class:`BinarySearchTree` : BST 삽입/탐색/삭제 + 중위 순회 정렬.

"힙이 완전 이진 트리를 배열로 표현한다"는 관점을 트리의 명시적 노드 표현과
대비해 이해하는 데 도움이 된다.

레벨 순회는 직접 구현한 :class:`Queue`(이중 연결 리스트 기반)를 사용한다.
"""

from .stack_queue_deque import Queue


class TreeNode:
    """이진 트리 노드."""

    __slots__ = ("value", "left", "right")

    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None


class BinaryTree:
    """루트 참조를 갖는 일반 이진 트리. 순회 알고리즘을 제공한다."""

    def __init__(self, root=None):
        self.root = root

    def preorder(self):
        """전위 순회(root → left → right) 결과를 리스트로 반환한다."""
        out = []
        self._preorder(self.root, out)
        return out

    def _preorder(self, node, out):
        if node is None:
            return
        out.append(node.value)
        self._preorder(node.left, out)
        self._preorder(node.right, out)

    def inorder(self):
        """중위 순회(left → root → right) 결과를 리스트로 반환한다."""
        out = []
        self._inorder(self.root, out)
        return out

    def _inorder(self, node, out):
        if node is None:
            return
        self._inorder(node.left, out)
        out.append(node.value)
        self._inorder(node.right, out)

    def postorder(self):
        """후위 순회(left → right → root) 결과를 리스트로 반환한다."""
        out = []
        self._postorder(self.root, out)
        return out

    def _postorder(self, node, out):
        if node is None:
            return
        self._postorder(node.left, out)
        self._postorder(node.right, out)
        out.append(node.value)

    def level_order(self):
        """레벨(BFS) 순회 결과를 리스트로 반환한다. 직접 만든 Queue 사용."""
        out = []
        if self.root is None:
            return out
        q = Queue()
        q.enqueue(self.root)
        while not q.is_empty():
            node = q.dequeue()
            out.append(node.value)
            if node.left is not None:
                q.enqueue(node.left)
            if node.right is not None:
                q.enqueue(node.right)
        return out


class BinarySearchTree(BinaryTree):
    """이진 탐색 트리. 중위 순회 시 오름차순 정렬 결과가 나온다."""

    def insert(self, value):
        """값을 BST 규칙에 따라 삽입한다. 평균 O(log n)."""
        self.root = self._insert(self.root, value)

    def _insert(self, node, value):
        if node is None:
            return TreeNode(value)
        if value < node.value:
            node.left = self._insert(node.left, value)
        elif value > node.value:
            node.right = self._insert(node.right, value)
        # 같은 값은 무시(중복 미허용).
        return node

    def search(self, value):
        """값 존재 여부를 반환한다. 평균 O(log n)."""
        node = self.root
        while node is not None:
            if value == node.value:
                return True
            node = node.left if value < node.value else node.right
        return False

    def delete(self, value):
        """값을 삭제한다(세 경우: 리프/자식 1개/자식 2개). 평균 O(log n)."""
        self.root = self._delete(self.root, value)

    def _delete(self, node, value):
        if node is None:
            return None
        if value < node.value:
            node.left = self._delete(node.left, value)
        elif value > node.value:
            node.right = self._delete(node.right, value)
        else:
            # 찾음.
            if node.left is None:
                return node.right
            if node.right is None:
                return node.left
            # 자식 2개: 오른쪽 서브트리의 최솟값(후계자)으로 교체.
            succ = self._min_node(node.right)
            node.value = succ.value
            node.right = self._delete(node.right, succ.value)
        return node

    @staticmethod
    def _min_node(node):
        """서브트리의 최솟값 노드를 반환한다."""
        while node.left is not None:
            node = node.left
        return node

    def sorted_values(self):
        """중위 순회로 정렬된 값 리스트를 반환한다."""
        return self.inorder()
