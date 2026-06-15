"""필수 증거 캡처용 데모 스크립트."""
from mini_redis.engine import MiniRedis, OOMError
from mini_redis.structures.hash_map import HashMap

class Clk:
    def __init__(s): s.t = 1000.0
    def __call__(s): return s.t
    def adv(s, x): s.t += x

print("########## 증거 A: LRU 자동 제거 (used_memory 갱신 + evicted_keys) ##########")
r = MiniRedis()
r.config_set_maxmemory("30")
print("CONFIG SET maxmemory 30")
for k, v in [("user:1","Alice"),("user:2","Bob"),("user:3","Charlie")]:
    r.set(k, v)
    print(f'SET {k} "{v}"  -> used_memory={r.used_memory()}')
print(f'GET user:1 -> {r.get("user:1")}  (가장 오래된 키가 제거됨)')
print(f'INFO memory -> used_memory:{r.used_memory()} maxmemory:{r.maxmemory()} evicted_keys:{r.evicted_keys()}')
print(f'남은 keys -> {sorted(r.keys())}')

print()
print("########## 증거 B: LRU 접근순서 반영 (GET이 MRU로 승격) ##########")
r = MiniRedis(); r.config_set_maxmemory("16")
for k in ["a","b","c","d"]: r.set(k, "xxx")   # 각 4바이트 = 16
print(f'4키 저장 후 keys={sorted(r.keys())} mem={r.used_memory()}')
r.get("a"); print('GET a  (a를 MRU로 승격 -> LRU는 b)')
r.set("e","xxx"); print(f'SET e xxx (한계초과) -> evict b')
print(f'결과 keys={sorted(r.keys())}, b 존재? {r.exists("b")}')

print()
print("########## 증거 C: OOM (단일 엔트리 초과 / 기존값 보존) ##########")
r = MiniRedis(); r.config_set_maxmemory("10")
r.set("k", "abc"); print(f'SET k abc -> OK (mem={r.used_memory()})')
try:
    r.set("k", "x"*20)
except OOMError:
    print('SET k xxxxxxxxxxxxxxxxxxxx -> OOMError 발생 (저장 거부)')
print(f'GET k -> "{r.get("k")}" (기존값 보존됨)')

print()
print("########## 증거 D: TTL + 힙 기반 만료 ##########")
clk = Clk(); r = MiniRedis(time_func=clk)
r.set("k","v")
print(f'EXPIRE k 3 -> {r.expire("k","3")}')
print(f'TTL k -> {r.ttl("k")}  (힙 size={r._ttl_heap.size()}, peek={r._ttl_heap.peek()})')
clk.adv(1); print(f'(1초 경과) TTL k -> {r.ttl("k")}')
clk.adv(3); print(f'(추가 3초 경과) GET k -> {r.get("k")}  / TTL k -> {r.ttl("k")}')
r.dbsize(); print(f'DBSIZE 호출 후 힙 정리됨 -> heap size={r._ttl_heap.size()}')

print()
print("########## 증거 E: 해시맵 로드팩터 0.75 초과 시 2배 확장 ##########")
h = HashMap(4)
print(f'초기 capacity={h.capacity()} (임계 = 4*0.75 = 3)')
for key in ["a","b","c","d"]:
    h.put(key, 1)
    print(f'put {key} -> size={h.size()} load_factor={h.load_factor():.2f} capacity={h.capacity()}')
