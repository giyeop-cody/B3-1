"""Mini Redis 단위/통합 테스트.

표준 라이브러리 unittest만 사용한다. 가짜 시계(FakeClock)를 주입해 TTL을
실제 sleep 없이 결정론적으로 검증한다.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_redis.engine import MiniRedis, OOMError  # noqa: E402
from mini_redis.cli import CLI, tokenize  # noqa: E402
from mini_redis.structures.dynamic_array import DynamicArray  # noqa: E402
from mini_redis.structures.doubly_linked_list import DoublyLinkedList  # noqa: E402
from mini_redis.structures.hash_map import HashMap  # noqa: E402
from mini_redis.structures.min_heap import MinHeap  # noqa: E402


class FakeClock:
    """수동으로 진행시키는 가짜 시계."""

    def __init__(self, start=1000.0):
        self.t = start

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


# ====================================================================== #
# 자료구조 테스트
# ====================================================================== #
class TestDynamicArray(unittest.TestCase):
    def test_append_and_get(self):
        a = DynamicArray(2)
        for i in range(10):
            a.append(i)
        self.assertEqual(a.size(), 10)
        self.assertTrue(a.capacity() >= 10)
        for i in range(10):
            self.assertEqual(a.get(i), i)

    def test_set_and_pop(self):
        a = DynamicArray()
        a.append("x")
        a.append("y")
        a.set(0, "z")
        self.assertEqual(a.get(0), "z")
        self.assertEqual(a.pop(), "y")
        self.assertEqual(a.size(), 1)

    def test_remove(self):
        a = DynamicArray()
        for c in "abcd":
            a.append(c)
        a.remove(1)  # remove 'b'
        self.assertEqual(list(a), ["a", "c", "d"])

    def test_capacity_doubles(self):
        a = DynamicArray(2)
        a.append(1)
        a.append(2)
        self.assertEqual(a.capacity(), 2)
        a.append(3)
        self.assertEqual(a.capacity(), 4)


class TestDoublyLinkedList(unittest.TestCase):
    def test_insert_front_back(self):
        dll = DoublyLinkedList()
        dll.insert_front("b")
        dll.insert_front("a")
        dll.insert_back("c")
        self.assertEqual(list(dll), ["a", "b", "c"])

    def test_remove_front_back(self):
        dll = DoublyLinkedList()
        for c in "abc":
            dll.insert_back(c)
        self.assertEqual(dll.remove_front(), "a")
        self.assertEqual(dll.remove_back(), "c")
        self.assertEqual(list(dll), ["b"])

    def test_move_to_front(self):
        dll = DoublyLinkedList()
        n_a = dll.insert_back("a")
        dll.insert_back("b")
        n_c = dll.insert_back("c")
        dll.move_to_front(n_c)
        self.assertEqual(list(dll), ["c", "a", "b"])
        dll.move_to_front(n_a)
        self.assertEqual(list(dll), ["a", "c", "b"])

    def test_remove_node(self):
        dll = DoublyLinkedList()
        dll.insert_back("a")
        n_b = dll.insert_back("b")
        dll.insert_back("c")
        dll.remove_node(n_b)
        self.assertEqual(list(dll), ["a", "c"])

    def test_empty(self):
        dll = DoublyLinkedList()
        self.assertIsNone(dll.remove_front())
        self.assertIsNone(dll.remove_back())
        self.assertTrue(dll.is_empty())


class TestHashMap(unittest.TestCase):
    def test_put_get(self):
        h = HashMap()
        h.put("a", 1)
        h.put("b", 2)
        self.assertEqual(h.get("a"), 1)
        self.assertEqual(h.get("b"), 2)
        self.assertIsNone(h.get("missing"))

    def test_update_existing(self):
        h = HashMap()
        h.put("k", 1)
        h.put("k", 99)
        self.assertEqual(h.get("k"), 99)
        self.assertEqual(h.size(), 1)

    def test_remove_contains(self):
        h = HashMap()
        h.put("k", "v")
        self.assertTrue(h.contains("k"))
        self.assertTrue(h.remove("k"))
        self.assertFalse(h.contains("k"))
        self.assertFalse(h.remove("k"))

    def test_resize_on_load_factor(self):
        h = HashMap(4)
        # 4 * 0.75 = 3 초과 시 확장.
        for i in range(100):
            h.put("key{}".format(i), i)
        self.assertEqual(h.size(), 100)
        for i in range(100):
            self.assertEqual(h.get("key{}".format(i)), i)
        self.assertTrue(h.capacity() > 4)

    def test_keys(self):
        h = HashMap()
        h.put("x", 1)
        h.put("y", 2)
        keys = sorted(list(h.keys()))
        self.assertEqual(keys, ["x", "y"])

    def test_collision_chaining(self):
        # 작은 용량으로 강제 충돌 유발.
        h = HashMap(2)
        for i in range(20):
            h.put(str(i), i)
        for i in range(20):
            self.assertEqual(h.get(str(i)), i)


class TestMinHeap(unittest.TestCase):
    def test_push_pop_order(self):
        heap = MinHeap()
        for v in [5, 3, 8, 1, 9, 2]:
            heap.push((v, "k{}".format(v)))
        out = []
        while not heap.is_empty():
            out.append(heap.pop()[0])
        self.assertEqual(out, [1, 2, 3, 5, 8, 9])

    def test_peek(self):
        heap = MinHeap()
        heap.push((10, "a"))
        heap.push((4, "b"))
        self.assertEqual(heap.peek()[0], 4)
        self.assertEqual(heap.size(), 2)

    def test_empty(self):
        heap = MinHeap()
        self.assertIsNone(heap.pop())
        self.assertIsNone(heap.peek())


# ====================================================================== #
# 엔진 테스트
# ====================================================================== #
class TestEngineString(unittest.TestCase):
    def setUp(self):
        self.r = MiniRedis()

    def test_set_get(self):
        self.assertEqual(self.r.set("k", "v"), "OK")
        self.assertEqual(self.r.get("k"), "v")

    def test_get_missing(self):
        self.assertIsNone(self.r.get("nope"))

    def test_del(self):
        self.r.set("k", "v")
        self.assertEqual(self.r.delete("k"), 1)
        self.assertEqual(self.r.delete("k"), 0)

    def test_exists(self):
        self.r.set("k", "v")
        self.assertEqual(self.r.exists("k"), 1)
        self.assertEqual(self.r.exists("x"), 0)

    def test_dbsize_keys(self):
        self.r.set("a", "1")
        self.r.set("b", "2")
        self.assertEqual(self.r.dbsize(), 2)
        self.assertEqual(sorted(self.r.keys()), ["a", "b"])

    def test_overwrite_updates_memory(self):
        self.r.set("k", "aa")
        before = self.r.used_memory()
        self.r.set("k", "bbbb")
        self.assertEqual(self.r.used_memory(), before - 2 + 4)


class TestEngineMemoryLRU(unittest.TestCase):
    def setUp(self):
        self.r = MiniRedis()

    def test_used_memory_formula(self):
        self.r.set("user:1", "Alice")  # 6 + 5 = 11
        self.assertEqual(self.r.used_memory(), 11)

    def test_lru_eviction(self):
        # 예시 시나리오 재현: maxmemory 30.
        self.r.config_set_maxmemory("30")
        self.r.set("user:1", "Alice")    # 11 -> total 11
        self.r.set("user:2", "Bob")      # 9  -> total 20
        self.r.set("user:3", "Charlie")  # 13 -> total 33 > 30 -> evict LRU(user:1)
        self.assertIsNone(self.r.get("user:1"))
        self.assertEqual(self.r.evicted_keys(), 1)
        self.assertEqual(self.r.used_memory(), 22)  # Bob(9)+Charlie(13)
        self.assertEqual(sorted(self.r.keys()), ["user:2", "user:3"])

    def test_lru_order_respects_access(self):
        self.r.config_set_maxmemory("20")
        self.r.set("a", "11")  # 3
        self.r.set("b", "22")  # 3 -> total 6
        self.r.get("a")        # a becomes MRU
        # 큰 값 추가로 eviction 유발 → b가 LRU여야 함.
        self.r.set("c", "x" * 14)  # 1+14=15 -> total 21 > 20 -> evict b
        self.assertEqual(self.r.get("b"), None)
        self.assertEqual(self.r.get("a"), "11")

    def test_single_entry_exceeds_maxmemory(self):
        self.r.config_set_maxmemory("5")
        with self.assertRaises(OOMError):
            self.r.set("key", "toolongvalue")

    def test_unlimited_when_zero(self):
        self.r.config_set_maxmemory("0")
        for i in range(100):
            self.r.set("k{}".format(i), "v" * 100)
        self.assertEqual(self.r.evicted_keys(), 0)


class TestEngineTTL(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.r = MiniRedis(time_func=self.clock)

    def test_expire_ttl(self):
        self.r.set("k", "v")
        self.assertEqual(self.r.expire("k", "3"), 1)
        self.assertEqual(self.r.ttl("k"), 3)
        self.clock.advance(1)
        self.assertEqual(self.r.ttl("k"), 2)

    def test_expire_missing_key(self):
        self.assertEqual(self.r.expire("nope", "5"), 0)

    def test_ttl_no_expire(self):
        self.r.set("k", "v")
        self.assertEqual(self.r.ttl("k"), -1)

    def test_ttl_missing(self):
        self.assertEqual(self.r.ttl("nope"), -2)

    def test_expired_get_returns_nil(self):
        self.r.set("k", "v")
        self.r.expire("k", "3")
        self.clock.advance(4)
        self.assertIsNone(self.r.get("k"))
        self.assertEqual(self.r.ttl("k"), -2)

    def test_expire_zero_deletes(self):
        self.r.set("k", "v")
        self.assertEqual(self.r.expire("k", "0"), 1)
        self.assertIsNone(self.r.get("k"))

    def test_overwrite_clears_ttl(self):
        self.r.set("k", "v")
        self.r.expire("k", "10")
        self.r.set("k", "new")  # TTL 초기화.
        self.assertEqual(self.r.ttl("k"), -1)

    def test_expired_not_counted_in_dbsize(self):
        self.r.set("a", "1")
        self.r.set("b", "2")
        self.r.expire("a", "2")
        self.clock.advance(3)
        self.assertEqual(self.r.dbsize(), 1)

    def test_expired_removed_from_keys_via_heap(self):
        # KEYS 호출 시 힙 기반 정리로 만료 키가 빠져야 한다.
        self.r.set("a", "1")
        self.r.set("b", "2")
        self.r.expire("a", "2")
        self.clock.advance(3)
        self.assertEqual(sorted(self.r.keys()), ["b"])

    def test_heap_purge_frees_memory(self):
        # 만료 키 정리 시 used_memory도 차감되어야 한다.
        self.r.set("a", "12345")  # 1 + 5 = 6
        self.r.expire("a", "2")
        self.clock.advance(3)
        self.r.dbsize()  # 힙 정리 트리거.
        self.assertEqual(self.r.used_memory(), 0)

    def test_heap_used_for_ttl(self):
        # 힙에 실제로 만료 엔트리가 쌓이는지 확인(내부 구조 검증).
        self.r.set("a", "1")
        self.r.set("b", "2")
        self.r.expire("a", "5")
        self.r.expire("b", "10")
        self.assertEqual(self.r._ttl_heap.size(), 2)
        # 가장 이른 만료가 힙 루트(peek)여야 한다.
        self.assertEqual(self.r._ttl_heap.peek()[1], "a")


# ====================================================================== #
# CLI 테스트
# ====================================================================== #
class TestTokenize(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(tokenize("SET a b"), ["SET", "a", "b"])

    def test_quoted(self):
        self.assertEqual(tokenize('SET k "hello world"'), ["SET", "k", "hello world"])

    def test_escaped_quote(self):
        self.assertEqual(tokenize('SET k "a\\"b"'), ["SET", "k", 'a"b'])

    def test_unbalanced(self):
        with self.assertRaises(ValueError):
            tokenize('SET k "unclosed')

    def test_empty_quoted_value(self):
        self.assertEqual(tokenize('SET k ""'), ["SET", "k", ""])

    def test_tab_separated(self):
        self.assertEqual(tokenize("SET\tk\tv"), ["SET", "k", "v"])


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.cli = CLI()

    def test_set_get_flow(self):
        self.assertEqual(self.cli.execute('SET user:1 "Alice"'), "OK")
        self.assertEqual(self.cli.execute("GET user:1"), '"Alice"')

    def test_get_nil(self):
        self.assertEqual(self.cli.execute("GET nope"), "(nil)")

    def test_integer_replies(self):
        self.cli.execute("SET k v")
        self.assertEqual(self.cli.execute("EXISTS k"), "(integer) 1")
        self.assertEqual(self.cli.execute("DEL k"), "(integer) 1")
        self.assertEqual(self.cli.execute("DBSIZE"), "(integer) 0")

    def test_keys_output(self):
        self.cli.execute("SET a 1")
        self.cli.execute("SET b 2")
        out = self.cli.execute("KEYS")
        self.assertIn('"a"', out)
        self.assertIn('"b"', out)
        # 미션 예시 형식: "1. " 처럼 마침표 사용.
        self.assertRegex(out, r'^\d+\. "')

    def test_keys_format_matches_mission(self):
        self.cli.execute("SET only 1")
        self.assertEqual(self.cli.execute("KEYS"), '1. "only"')

    def test_info_format_no_header(self):
        # 미션 예시: '# Memory' 헤더 없이 3줄만 출력.
        self.cli.execute("CONFIG SET maxmemory 30")
        out = self.cli.execute("INFO memory")
        lines = out.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("used_memory:"))
        self.assertNotIn("# Memory", out)

    def test_keys_empty(self):
        self.assertEqual(self.cli.execute("KEYS"), "(empty array)")

    def test_unknown_command(self):
        self.assertEqual(self.cli.execute("HELLO"), "(error) ERR unknown command 'HELLO'")

    def test_wrong_args(self):
        self.assertEqual(
            self.cli.execute("GET"),
            "(error) ERR wrong number of arguments for 'get' command",
        )

    def test_config_not_int(self):
        self.assertEqual(
            self.cli.execute("CONFIG SET maxmemory abc"),
            "(error) ERR value is not an integer or out of range",
        )

    def test_oom_single_entry(self):
        self.cli.execute("CONFIG SET maxmemory 3")
        self.assertEqual(
            self.cli.execute("SET key value"),
            "(error) OOM command not allowed when used_memory > 'maxmemory'",
        )

    def test_oom_preserves_existing_value(self):
        # 덮어쓰기가 OOM이면 기존 값이 보존되어야 한다.
        self.cli.execute("CONFIG SET maxmemory 10")
        self.cli.execute("SET k abc")  # 4 bytes
        self.assertEqual(
            self.cli.execute("SET k " + "x" * 20),
            "(error) OOM command not allowed when used_memory > 'maxmemory'",
        )
        self.assertEqual(self.cli.execute("GET k"), '"abc"')

    def test_unbalanced_quote_error(self):
        self.assertEqual(
            self.cli.execute('SET k "unclosed'),
            "(error) ERR Protocol error: unbalanced quotes in request",
        )

    def test_negative_maxmemory_error(self):
        self.assertEqual(
            self.cli.execute("CONFIG SET maxmemory -5"),
            "(error) ERR value is not an integer or out of range",
        )

    def test_command_case_insensitive(self):
        self.assertEqual(self.cli.execute("set k v"), "OK")
        self.assertEqual(self.cli.execute("Get k"), '"v"')

    def test_info_memory(self):
        self.cli.execute("CONFIG SET maxmemory 30")
        self.cli.execute('SET user:1 "Alice"')
        out = self.cli.execute("INFO memory")
        self.assertIn("used_memory:11", out)
        self.assertIn("maxmemory:30", out)
        self.assertIn("evicted_keys:0", out)

    def test_full_scenario(self):
        self.assertEqual(self.cli.execute("CONFIG SET maxmemory 30"), "OK")
        self.cli.execute('SET user:1 "Alice"')
        self.cli.execute('SET user:2 "Bob"')
        self.cli.execute('SET user:3 "Charlie"')
        self.assertEqual(self.cli.execute("GET user:1"), "(nil)")
        out = self.cli.execute("INFO memory")
        self.assertIn("used_memory:22", out)
        self.assertIn("evicted_keys:1", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
