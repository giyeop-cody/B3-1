"""보너스 자료구조 테스트: 스택/큐/덱, 이진 트리, BST."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_redis.structures.stack_queue_deque import Stack, Queue, Deque  # noqa: E402
from mini_redis.structures.binary_tree import (  # noqa: E402
    BinaryTree, BinarySearchTree, TreeNode,
)


class TestStack(unittest.TestCase):
    def test_lifo(self):
        s = Stack()
        for v in [1, 2, 3]:
            s.push(v)
        self.assertEqual(s.peek(), 3)
        self.assertEqual(s.pop(), 3)
        self.assertEqual(s.pop(), 2)
        self.assertEqual(s.size(), 1)


class TestQueue(unittest.TestCase):
    def test_fifo(self):
        q = Queue()
        for v in [1, 2, 3]:
            q.enqueue(v)
        self.assertEqual(q.peek(), 1)
        self.assertEqual(q.dequeue(), 1)
        self.assertEqual(q.dequeue(), 2)
        self.assertEqual(q.size(), 1)


class TestDeque(unittest.TestCase):
    def test_both_ends(self):
        d = Deque()
        d.push_back(1)
        d.push_front(0)
        d.push_back(2)
        self.assertEqual(d.peek_front(), 0)
        self.assertEqual(d.peek_back(), 2)
        self.assertEqual(d.pop_front(), 0)
        self.assertEqual(d.pop_back(), 2)
        self.assertEqual(d.size(), 1)


class TestBinaryTree(unittest.TestCase):
    def _sample(self):
        #        1
        #      /   \
        #     2     3
        #    / \
        #   4   5
        root = TreeNode(1)
        root.left = TreeNode(2)
        root.right = TreeNode(3)
        root.left.left = TreeNode(4)
        root.left.right = TreeNode(5)
        return BinaryTree(root)

    def test_traversals(self):
        t = self._sample()
        self.assertEqual(t.preorder(), [1, 2, 4, 5, 3])
        self.assertEqual(t.inorder(), [4, 2, 5, 1, 3])
        self.assertEqual(t.postorder(), [4, 5, 2, 3, 1])
        self.assertEqual(t.level_order(), [1, 2, 3, 4, 5])


class TestBST(unittest.TestCase):
    def test_insert_search_sorted(self):
        bst = BinarySearchTree()
        for v in [5, 3, 8, 1, 4, 7, 9, 2]:
            bst.insert(v)
        self.assertTrue(bst.search(7))
        self.assertFalse(bst.search(6))
        self.assertEqual(bst.sorted_values(), [1, 2, 3, 4, 5, 7, 8, 9])

    def test_delete(self):
        bst = BinarySearchTree()
        for v in [5, 3, 8, 1, 4, 7, 9]:
            bst.insert(v)
        bst.delete(3)  # 자식 2개.
        self.assertFalse(bst.search(3))
        self.assertEqual(bst.sorted_values(), [1, 4, 5, 7, 8, 9])
        bst.delete(9)  # 리프.
        self.assertEqual(bst.sorted_values(), [1, 4, 5, 7, 8])


if __name__ == "__main__":
    unittest.main(verbosity=2)
