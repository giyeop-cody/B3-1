# Mini Redis


## 📌 과제 정보

| 항목 | 내용 |
|------|------|
| **과목** | 자료구조와 알고리즘 |
| **난이도** | ★★☆ (Lv.2) |
| **학습 시간** | 80분 |
| **필수 여부** | ✅ 필수 |
| **과제 번호** | 185008 |

직접 구현한 자료구조(이중 연결 리스트 · 해시맵 · 최소 힙 · 동적 배열)만으로
Redis의 핵심 기능을 재현한 **CLI 기반 인메모리 Key-Value 저장소**.

> `dict` / `set` / `collections` 등 내장 컬렉션을 키-값/캐시 저장소로 사용하지
> 않고 모든 핵심 자료구조를 밑바닥부터 구현했다. (Python 3.8+)

## 목차

1. [학습 목표](#1-학습-목표)
2. [미션 요구사항 충족 현황](#2-미션-요구사항-충족-현황)
3. [기능 명세](#3-기능-명세)
4. [실행 방법](#4-실행-방법)
5. [프로젝트 구조](#5-프로젝트-구조)
6. [핵심 설계](#6-핵심-설계)
7. [✅ 필수 증거 (터미널 실행 결과)](#7--필수-증거-터미널-실행-결과)
8. [평가 문항 답변](#8-평가-문항-답변)
9. [테스트](#9-테스트)

---

## 1. 학습 목표

이 프로젝트를 통해 다음을 코드 근거와 함께 스스로 설명할 수 있다.

- **해시맵**의 해시 함수와 충돌 해결 방식(체이닝)을 구현 기반으로 설명할 수 있다.
- **이중 연결 리스트 + 해시맵**을 조합하여 O(1) LRU 추적이 가능한 이유를 설명할 수 있다.
- **힙**이 TTL 만료 시간 관리에 적합한 이유를 설명할 수 있다.
- 메모리 제한 환경에서 **LRU 정책**으로 데이터를 제거하는 전체 흐름(`used_memory` 갱신 포함)을 설명할 수 있다.

---

## 2. 미션 요구사항 충족 현황

### 2.1. 자료구조 직접 구현 (내장 컬렉션 대체 금지)

| 자료구조 | 요구 메서드 | 충족 |
| --- | --- | --- |
| 이중 연결 리스트 | `insert_front` `insert_back` `remove_front` `remove_back` `remove_node` `move_to_front` (모두 O(1)) + 노드 `prev/next/data` | ✅ |
| 해시맵 (체이닝) | `put` `get` `remove` `contains` `keys` `size` + 직접 설계 해시 함수 + 로드팩터 0.75 초과 시 2배 확장 | ✅ |
| 최소 힙 | `push` `pop` `peek` `size` + `_heapify_up` `_heapify_down` + `(expire_at, key)` 요소 | ✅ |

### 2.2. 명령어

| 분류 | 명령어 | 충족 |
| --- | --- | --- |
| String (6) | `SET` `GET` `DEL` `EXISTS` `DBSIZE` `KEYS` | ✅ |
| 메모리 (2) | `CONFIG SET maxmemory` `INFO memory` | ✅ |
| TTL (2) | `EXPIRE` `TTL` | ✅ |
| CLI | `mini-redis>` 프롬프트 REPL, `exit`/`quit` 종료 | ✅ |

### 2.3. 제약사항

| 제약 | 충족 |
| --- | --- |
| `dict` / `set` / `collections` 미사용 | ✅ (디스패치도 if/elif) |
| 각 자료구조 독립 모듈 분리 | ✅ |
| 핵심 클래스/함수 docstring | ✅ |
| 네트워크/영속성/복잡자료형/동시성 미구현 | ✅ (범위 외) |

### 2.4. 보너스 과제

| 과제 | 구현 | 위치 |
| --- | --- | --- |
| 5.1 동적 배열 (2배 확장) | ✅ | `structures/dynamic_array.py` |
| 5.2 스택/큐/덱 + 문서화 | ✅ | `structures/stack_queue_deque.py`, `docs/STACK_QUEUE_DEQUE.md` |
| 5.3 이진 트리 + 4가지 순회 | ✅ | `structures/binary_tree.py` |
| 5.4 이진 탐색 트리(BST) | ✅ | `structures/binary_tree.py` |
| 5.5 Pub/Sub | ✖️ (미구현) | — |

---

## 3. 기능 명세

### 출력 규약 (Redis 스타일)

`OK` · `(nil)` · `(integer) N` · `"value"` · `(empty array)` · `(error) ...`

### 명령어 동작

| 명령어 | 동작 | 반환 |
| --- | --- | --- |
| `SET key value` | 값 저장(메모리 초과 시 LRU 제거, 덮어쓰기 시 TTL 초기화) | `OK` / OOM 에러 |
| `GET key` | 값 조회(성공 시에만 LRU 갱신, 만료 시 삭제 후 nil) | `"value"` / `(nil)` |
| `DEL key` | 삭제(데이터/LRU/TTL 함께 제거) | `(integer) 1/0` |
| `EXISTS key` | 존재 여부(만료 키는 없음 처리) | `(integer) 1/0` |
| `DBSIZE` | 살아있는 키 개수 | `(integer) N` |
| `KEYS` | 전체 키 목록 (`1. "key"` 형식) | 목록 / `(empty array)` |
| `CONFIG SET maxmemory bytes` | 메모리 한계 설정(0=무제한) | `OK` / 정수 에러 |
| `INFO memory` | `used_memory` / `maxmemory` / `evicted_keys` 출력 | 3줄 |
| `EXPIRE key seconds` | 만료 설정(0 이하=즉시 만료, 없는 키=0) | `(integer) 1/0` |
| `TTL key` | 남은 시간 | `N` / `-1`(만료없음) / `-2`(키없음) |

### used_memory 산정 공식

```
used_memory = Σ( len(utf8(key)) + len(utf8(value)) )
```
자료구조(노드/포인터/버킷) 오버헤드는 제외한다.

### 에러 표준

| 상황 | 출력 |
| --- | --- |
| 잘못된 명령 | `(error) ERR unknown command '<cmd>'` |
| 인자 개수 오류 | `(error) ERR wrong number of arguments for '<cmd>' command` |
| 정수 파싱 실패 | `(error) ERR value is not an integer or out of range` |
| 메모리 초과 | `(error) OOM command not allowed when used_memory > 'maxmemory'` |

---

## 4. 실행 방법

```bash
python3 main.py
```

```text
mini-redis> CONFIG SET maxmemory 30
OK
mini-redis> SET user:1 "Alice"
OK
mini-redis> GET user:1
"Alice"
mini-redis> exit
```

값은 **공백 없는 토큰** 또는 **큰따옴표로 감싼 문자열**(`"Alice Smith"`)을 지원한다.

---

## 5. 프로젝트 구조

```
mini_redis/
├── structures/
│   ├── dynamic_array.py        # 동적 배열 (2배 확장)            [보너스 5.1]
│   ├── doubly_linked_list.py   # 이중 연결 리스트 (전 연산 O(1))
│   ├── hash_map.py             # 체이닝 해시맵 (로드팩터 0.75 확장)
│   ├── min_heap.py             # 최소 힙 (TTL 만료 관리)
│   ├── stack_queue_deque.py    # 스택/큐/덱                      [보너스 5.2]
│   └── binary_tree.py          # 이진 트리 + BST                 [보너스 5.3, 5.4]
├── engine.py                   # 핵심 엔진 (store/LRU/메모리/TTL)
├── cli.py                      # 파서 + REPL
└── __init__.py
main.py                         # 진입점
demo_evidence.py                # 필수 증거 재현 스크립트
demo_stress.py                  # 불변식 스트레스 테스트 스크립트
docs/
├── DESIGN.md                   # 설계 + 평가 문항 상세 답변
├── STACK_QUEUE_DEQUE.md        # 스택/큐/덱 개념 문서
└── evidence/                   # 캡처된 터미널 실행 결과
tests/                          # unittest (69개)
```

---

## 6. 핵심 설계

- **O(1) LRU**: 해시맵(`key→Node`, 빠른 조회) + 이중 연결 리스트(사용 순서)를 결합.
  조회/갱신 시 노드를 O(1)에 front로 이동, eviction 시 back에서 O(1)에 제거.
- **체이닝 해시맵**: djb2 계열 해시 함수 직접 설계, 로드 팩터 0.75 초과 시 2배 rehash.
  버킷은 직접 만든 이중 연결 리스트를 재사용.
- **힙 기반 TTL**: `(expire_at, key)` 최소 힙으로 가장 이른 만료를 O(1) peek,
  lazy deletion으로 stale 엔트리 처리.
- **메모리 모델**: `used_memory = Σ(len(utf8(key)) + len(utf8(value)))`, 오버헤드 제외.

자세한 설명은 [`docs/DESIGN.md`](docs/DESIGN.md) 참고.

---

## 7. ✅ 필수 증거 (터미널 실행 결과)

아래 출력은 실제 실행을 리다이렉션으로 캡처한 것이며, `docs/evidence/`에 원본이 보관되어 있다.
모든 증거는 다음 명령으로 재현 가능하다.

```bash
python3 demo_evidence.py     # 증거 ③~⑦
python3 demo_stress.py       # 증거 ⑧ (불변식 스트레스)
python3 -m unittest discover -s tests -v   # 증거 ⑨ (테스트)
```

#### 📎 캡처 원본 파일 (리다이렉션 결과)

| 증거 | 내용 | 원본 파일 |
| --- | --- | --- |
| ① | 미션 전체 시나리오 (REPL) | [scenario_main.txt](docs/evidence/scenario_main.txt) |
| ② | 에러 처리 표준 | [errors.txt](docs/evidence/errors.txt) |
| ③~⑦ | LRU·OOM·TTL·해시맵 데모 | [demo.txt](docs/evidence/demo.txt) |
| ⑧ | 불변식 스트레스(3만 회) | [stress.txt](docs/evidence/stress.txt) |
| ⑨ | 테스트 결과(요약/상세) | [tests.txt](docs/evidence/tests.txt) · [tests_verbose.txt](docs/evidence/tests_verbose.txt) |

### 증거 ①: 미션 전체 시나리오 (REPL)

> 입력: `CONFIG SET maxmemory 30` → `SET user:1/2/3` → `GET user:1` → `INFO memory` → `KEYS` → `EXPIRE user:2 3` → `TTL user:2`

```text
mini-redis> OK
mini-redis> OK
mini-redis> OK
mini-redis> OK
mini-redis> (nil)
mini-redis> used_memory:22
maxmemory:30
evicted_keys:1
mini-redis> 1. "user:2"
2. "user:3"
mini-redis> (integer) 1
mini-redis> (integer) 2
mini-redis>
```

✔ maxmemory(30) 초과로 LRU(`user:1`) 자동 제거 → `GET user:1`이 `(nil)`,
`evicted_keys:1`, `used_memory:22`(Bob 9 + Charlie 13). 미션 예시와 **완전 일치**.

### 증거 ②: 에러 처리 표준

> 입력: `CONFIG SET maxmemory abc` / `GET` / `HELLO` / `CONFIG SET maxmemory -5` / `SET k "unclosed`

```text
mini-redis> (error) ERR value is not an integer or out of range
mini-redis> (error) ERR wrong number of arguments for 'get' command
mini-redis> (error) ERR unknown command 'HELLO'
mini-redis> (error) ERR value is not an integer or out of range
mini-redis> (error) ERR Protocol error: unbalanced quotes in request
mini-redis>
```

✔ 정수 파싱 실패 · 인자 개수 · 잘못된 명령 · 음수 거부 · 따옴표 미닫힘 모두 표준 형식.

### 증거 ③: LRU 자동 제거 (used_memory 갱신 + evicted_keys)

```text
########## 증거 A: LRU 자동 제거 (used_memory 갱신 + evicted_keys) ##########
CONFIG SET maxmemory 30
SET user:1 "Alice"  -> used_memory=11
SET user:2 "Bob"  -> used_memory=20
SET user:3 "Charlie"  -> used_memory=22
GET user:1 -> None  (가장 오래된 키가 제거됨)
INFO memory -> used_memory:22 maxmemory:30 evicted_keys:1
남은 keys -> ['user:2', 'user:3']
```

### 증거 ④: LRU 접근 순서 반영 (GET이 MRU로 승격)

```text
########## 증거 B: LRU 접근순서 반영 (GET이 MRU로 승격) ##########
4키 저장 후 keys=['a', 'b', 'c', 'd'] mem=16
GET a  (a를 MRU로 승격 -> LRU는 b)
SET e xxx (한계초과) -> evict b
결과 keys=['a', 'c', 'd', 'e'], b 존재? 0
```

✔ 접근한 `a`는 보존, 가장 오래된 `b`가 제거됨 → LRU 순서가 접근에 따라 갱신됨.

### 증거 ⑤: OOM (단일 엔트리 초과 시 거부 + 기존값 보존)

```text
########## 증거 C: OOM (단일 엔트리 초과 / 기존값 보존) ##########
SET k abc -> OK (mem=4)
SET k xxxxxxxxxxxxxxxxxxxx -> OOMError 발생 (저장 거부)
GET k -> "abc" (기존값 보존됨)
```

### 증거 ⑥: TTL + 힙 기반 만료

```text
########## 증거 D: TTL + 힙 기반 만료 ##########
EXPIRE k 3 -> 1
TTL k -> 3  (힙 size=1, peek=(1003.0, 'k'))
(1초 경과) TTL k -> 2
(추가 3초 경과) GET k -> None  / TTL k -> -2
DBSIZE 호출 후 힙 정리됨 -> heap size=0
```

✔ 힙 루트(`peek`)에 가장 이른 만료가 위치 → TTL 직후 3, 1초 후 2, 만료 후 `-2`.
DBSIZE 호출 시 힙 기반 lazy 정리로 stale 엔트리 제거.

### 증거 ⑦: 해시맵 로드팩터 0.75 초과 시 2배 확장

```text
########## 증거 E: 해시맵 로드팩터 0.75 초과 시 2배 확장 ##########
초기 capacity=4 (임계 = 4*0.75 = 3)
put a -> size=1 load_factor=0.25 capacity=4
put b -> size=2 load_factor=0.50 capacity=4
put c -> size=3 load_factor=0.75 capacity=4
put d -> size=4 load_factor=0.50 capacity=8
```

✔ load_factor가 0.75일 때는 유지, **초과(4번째 삽입)** 하는 순간 capacity 4→8로 2배 확장.

### 증거 ⑧: 불변식 스트레스 테스트 (3만 회 무작위 연산)

```text
[PASS] 30000회 무작위 연산(SET/GET/DEL/EXPIRE/TTL/KEYS + 시간경과) 불변식 검증 통과
  검증한 불변식:
   1) used_memory >= 0  (음수 불가)
   2) used_memory == 실제 Σ(len(key)+len(value))  (정확한 추적)
   3) store.size == nodes.size == lru.size  (자료구조 정합성)
   4) used_memory <= maxmemory  (한계 준수)
   5) expires의 모든 키가 store에 존재  (고아 엔트리 없음)
  최종 상태: store=16 mem=149 evicted=2824
```

### 증거 ⑨: 전체 테스트 통과

```text
.....................................................................
----------------------------------------------------------------------
Ran 69 tests in 0.009s

OK
```

---

## 8. 평가 문항 답변

평가 문항(`평가문항.md`)의 구술/설명 항목에 대한 답변이다. 더 자세한 내용은 [`docs/DESIGN.md`](docs/DESIGN.md) 참고.

### 항목 2 — 자료구조 설계

**Q2-1. 이중 연결 리스트가 O(1)로 동작하는 구성은?**
노드는 `prev/next/data` 3개 필드를 갖는다. **더미 head/tail 센티넬**을 둬서 빈 리스트·양 끝 경계의 `None` 분기를 제거했다. 핵심은 `_insert_between`과 `_unlink` 두 헬퍼이며, 삽입/삭제/이동 모두 **포인터 4개만 갱신**하므로 O(1)이다. `move_to_front(node)`는 노드 참조를 이미 알고 있으면 위치 탐색 없이 `_unlink` 후 head 뒤 재삽입으로 O(1)에 끝난다.

**Q2-2. 직접 설계한 해시 함수의 입력→인덱스 과정은?**
`hash_map.py::_hash` — djb2 계열 다항식 롤링 해시. 문자열을 입력받아 `h=5381`에서 시작, 각 문자마다 `h = h*33 + ord(c)`(= `(h<<5)+h+ord(c)`)를 누적하고 매 단계 `& 0xFFFFFFFF`로 32비트를 유지한다. 최종 `h % capacity`가 버킷 인덱스다. 5381(소수)·배수 33 조합은 영문/숫자 키 분포가 고른 것으로 알려져 있다.

**Q2-3. 체이닝 충돌 해결 (버킷 내부 구조)은?**
버킷 테이블은 `DynamicArray`이고, **각 버킷은 직접 만든 `DoublyLinkedList`** 다(권장 사항인 "이중 연결 리스트 재사용" 적용). 같은 인덱스로 충돌한 `_Entry(key, value)`들을 그 체인에 매달고, 조회 시 체인을 순회하며 `entry.key == key`로 찾는다. 로드 팩터를 낮게 유지하므로 체인 평균 길이가 상수 → 평균 O(1).

**Q2-4. 로드 팩터 0.75 초과 시 2배 확장 절차는?**
`put`에서 신규 삽입 후 `size > capacity * 0.75`인지 검사 → 초과 시 `_resize(capacity*2)` 호출 → 새 버킷 배열 생성 후 **모든 기존 엔트리를 새 capacity 기준으로 rehash**하여 재배치. (증거 ⑦ 참고)

### 항목 3 — LRU 원리

**Q3-1. 해시맵 + 이중 연결 리스트의 역할과 둘 다 필요한 이유는?**
`_nodes`(해시맵: key→Node)는 "키가 어느 노드인지"를 O(1)에 찾고, `_lru`(이중 연결 리스트)는 "얼마나 최근에 썼는지" 순서(front=MRU, back=LRU)를 유지한다. 리스트만 있으면 노드 탐색이 O(n)이고, 해시맵만 있으면 "가장 오래된 키"를 O(1)에 못 찾는다. 둘을 결합해야 양쪽 모두 O(1).

**Q3-2. O(1) LRU 달성 원리 (조회+갱신)는?**
조회는 `_nodes.get(key)`로 노드 참조 획득(O(1)), 갱신은 `_lru.move_to_front(node)`로 MRU 이동(O(1)), eviction은 `_lru.back_node()`로 LRU 키를 O(1)에 얻어 삭제. (증거 ④ 참고)

### 항목 4 — 동작 흐름 및 심화

**Q4-1. TTL에 힙을 쓰는 이유는?**
TTL 관리의 본질은 "가장 먼저 만료될 키"를 빠르게 찾기다. 최소 힙은 루트가 항상 최소(가장 이른 만료) → `peek` O(1), `push/pop` O(log n). 요소 `(expire_at, key)` 튜플 비교가 만료 시각 우선이라 자연 정렬된다. (증거 ⑥ 참고)

**Q4-2. 메모리 초과 시 eviction 흐름 (단계별)은?**
① 단일 엔트리 `len(key)+len(value)`가 `maxmemory(>0)` 초과면 저장 없이 OOM. ② 저장하며 `used_memory` 갱신(신규 `+size`, 덮어쓰기 `-old +new`). ③ `used_memory > maxmemory`인 동안 `_lru.back_node()`로 가장 오래된 키를 꺼내 `_delete_key`로 제거 + `used_memory` 차감 + `evicted_keys += 1`. ④ 한계 이하가 되면 종료. (증거 ③ 참고)

**Q4-3. GET 명령 전체 흐름은?**
`_ensure_alive(key)`로 존재+TTL 만료 확인 → 만료면 `_delete_key` 후 `None`(**LRU 갱신 안 함**) → 살아있으면 값 조회 후 `_touch_lru`로 MRU 갱신 → 값 반환. CLI는 `"value"` 또는 `(nil)`로 출력.

**Q4-4. LRU 대신 LFU를 구현한다면?**
빈도(frequency) 기준으로 바꾼다. 키별 **접근 횟수 카운터**를 추가하고, 같은 빈도끼리 묶는 **빈도 버킷**(빈도→키 연결 리스트) 또는 `(count, key)` 최소 힙을 둔다. 접근 시 count 증가 + 다음 빈도 버킷으로 이동, eviction은 "최소 빈도 버킷의 가장 오래된 키" 제거 → 빈도 버킷 방식으로 O(1) LFU 가능.

**Q4-5. 데이터가 10만 건으로 늘면 병목과 개선은?**
병목 후보: 해시맵 `_resize`의 일괄 rehash(O(n) 순간 지연), 힙의 stale 엔트리 누적. 개선: **점진적 리해싱**(연산마다 조금씩 이전), 만료 정리를 **능동적 샘플링 + lazy** 조합, 힙 대신 **타이머 휠(timer wheel)** 로 만료 그룹화, 로드팩터/해시 품질 튜닝.

**Q4-6. used_memory에 오버헤드까지 포함하면?**
노드/포인터/버킷 점유까지 세므로 같은 키-값도 used_memory가 커지고 eviction이 잦아지며, 플랫폼/언어 의존으로 값이 비결정적이 된다. 공정한 채점을 위해 **고정 단가 모델**(엔트리당 상수 C 가산)로 플랫폼 의존성 제거, 측정 기준을 명세에 고정, 절대값이 아닌 **공식 일치/상대 비교** 위주 채점이 필요하다.

---

## 9. 테스트

```bash
python3 -m unittest discover -s tests -v
```

총 **69개 테스트** 통과. 구성:

| 분류 | 내용 |
| --- | --- |
| 자료구조 | 동적 배열 · 이중 연결 리스트 · 해시맵(리사이즈/충돌) · 최소 힙 |
| 엔진 | String 명령 · LRU eviction · 메모리 추적 · OOM |
| TTL | EXPIRE/TTL 규칙 · 만료 정리 · 힙 사용 검증 · 덮어쓰기 TTL 초기화 |
| CLI | 파싱 · 출력 형식 · 에러 표준 · 대소문자 · 따옴표 |
| 보너스 | 스택/큐/덱 · 이진 트리 순회 · BST |

TTL 테스트는 가짜 시계(`FakeClock`)를 주입해 `sleep` 없이 결정론적으로 검증한다.

---

## 🚀 실행 방법

### 설치
```bash
pip install -r requirements.txt  # 표준 라이브러리만 사용
```

### 실행
```bash
python mini_redis/main.py
```

---

## 🧪 테스트 방법

### 자동 테스트
```bash
python -m pytest tests/ -v
```

### 수동 테스트
1. `put key value` → 저장 확인
2. `get key` → 값 반환 확인
3. `delete key` → 삭제 확인
4. 대량 데이터 입력 → O(1) 탐색 성능 확인
5. 충돌 상황 → 체이닝/개방주소법 동작 확인
