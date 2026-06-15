"""불변식 스트레스 테스트 증거."""
import random
from mini_redis.engine import MiniRedis, OOMError

random.seed(7)
class Clk:
    def __init__(s): s.t = 10000.0
    def __call__(s): return s.t
    def adv(s, x): s.t += x
clk = Clk()
r = MiniRedis(time_func=clk)
r.config_set_maxmemory("150")

def actual_memory():
    return sum(len(k.encode()) + len(v.encode()) for k, v in r._store.items())

N = 30000
for i in range(N):
    op = random.random()
    key = "k%d" % random.randint(0, 25)
    if op < 0.4:
        try: r.set(key, "v" * random.randint(1, 12))
        except OOMError: pass
    elif op < 0.55: r.get(key)
    elif op < 0.65: r.delete(key)
    elif op < 0.78: r.expire(key, str(random.randint(1, 20)))
    elif op < 0.85: r.ttl(key)
    elif op < 0.92: clk.adv(random.randint(1, 8))
    else: r.keys()
    assert r.used_memory() >= 0
    assert r.used_memory() == actual_memory()
    assert r._store.size() == r._nodes.size() == r._lru.size()
    assert r.used_memory() <= 150
    for k, _ in r._expires.items():
        assert r._store.contains(k)

print(f"[PASS] {N}회 무작위 연산(SET/GET/DEL/EXPIRE/TTL/KEYS + 시간경과) 불변식 검증 통과")
print("  검증한 불변식:")
print("   1) used_memory >= 0  (음수 불가)")
print("   2) used_memory == 실제 Σ(len(key)+len(value))  (정확한 추적)")
print("   3) store.size == nodes.size == lru.size  (자료구조 정합성)")
print("   4) used_memory <= maxmemory  (한계 준수)")
print("   5) expires의 모든 키가 store에 존재  (고아 엔트리 없음)")
print(f"  최종 상태: store={r._store.size()} mem={r.used_memory()} evicted={r.evicted_keys()}")
