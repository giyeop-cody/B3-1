# Mini Redis 설계 문서 (평가 문항 대응)

이 문서는 `평가문항.md`의 각 구술/설명 항목에 대한 답을 코드 근거와 함께 정리한다.

---

## 0. 전체 구조 (모듈 분리)

```
mini_redis/
├── structures/
│   ├── dynamic_array.py        # 동적 배열 (capacity 2배 확장) — 보너스 5.1
│   ├── doubly_linked_list.py   # 이중 연결 리스트 (모든 핵심 연산 O(1))
│   ├── hash_map.py             # 체이닝 해시맵 (로드팩터 0.75 확장)
│   ├── min_heap.py             # 최소 힙 (TTL 만료 관리)
│   ├── stack_queue_deque.py    # 스택/큐/덱 — 보너스 5.2
│   └── binary_tree.py          # 이진 트리 + BST — 보너스 5.3, 5.4
├── engine.py                   # 핵심 엔진 (store/LRU/메모리/TTL 조합)
├── cli.py                      # 파서 + REPL + Redis 스타일 출력
└── __init__.py
main.py                         # 실행 진입점
tests/                          # unittest (58개)
```

각 자료구조는 독립 파일이며, 핵심 클래스/메서드에 docstring을 작성했다.

---

## 항목 2 — 자료구조 설계

### 2-1. 이중 연결 리스트가 O(1)인 이유

`doubly_linked_list.py`

- **더미 센티넬**(`_head`, `_tail`)을 둬서 빈 리스트/양 끝 경계의 `None` 분기를 제거 → 모든 연산이 분기 없이 일정한 포인터 조작으로 끝난다.
- 핵심은 `_insert_between(node, left, right)`과 `_unlink(node)` 두 헬퍼다. 삽입/삭제/이동 모두 이 둘의 조합이고, **포인터 4개만 갱신**하므로 O(1).
- `move_to_front(node)` = `_unlink(node)` 후 head 뒤 재삽입. **노드 참조를 이미 알고 있으면** 리스트 어디에 있든 탐색 없이 O(1)에 이동 가능 → 이것이 LRU의 핵심.

### 2-2. 직접 설계한 해시 함수

`hash_map.py::_hash` — **djb2 계열 다항식 롤링 해시**

- 입력: 문자열 키. (문자열이 아니면 `str()`로 변환)
- 과정: `h = 5381`에서 시작 → 각 문자마다 `h = h*33 + ord(c)` 누적 → 매 단계 `& 0xFFFFFFFF`로 32비트 유지.
- 인덱스: `h % capacity`.
- 5381(소수)과 배수 33(작은 홀수)은 영문/숫자 키에서 분포가 고른 것으로 검증된 상수 조합이다. `h*33`은 `(h<<5)+h`로 계산해 빠르다.

### 2-3. 체이닝 충돌 해결

- 버킷 테이블은 `DynamicArray`이고, **각 버킷은 `DoublyLinkedList`**(직접 만든 이중 연결 리스트 재사용).
- 같은 인덱스로 충돌한 엔트리(`_Entry(key, value)`)들은 해당 버킷 체인에 매단다.
- 조회: 버킷 체인을 순회하며 `entry.key == key` 비교. 로드 팩터를 낮게 유지하므로 체인 평균 길이는 상수 → 평균 O(1).

### 2-4. 로드 팩터 0.75 초과 시 2배 확장

`hash_map.py::put` → `_resize`

1. `put`에서 신규 삽입 후 `size > capacity * 0.75`인지 검사.
2. 초과 시 `_resize(capacity * 2)` 호출.
3. 새 버킷 배열을 만들고 **모든 기존 엔트리를 새 capacity 기준으로 rehash**하여 재배치.
4. 평균적으로 분할 상환 O(1) 유지(가끔 O(n) rehash가 발생하지만 드물다).

---

## 항목 3 — LRU 구현 원리

### 3-1. 해시맵 + 이중 연결 리스트의 역할 (왜 둘 다 필요한가)

`engine.py`

| 자료구조 | 역할 | 단독으로는? |
| --- | --- | --- |
| `_nodes` (HashMap: key→Node) | 키로 **리스트 노드를 O(1)에 찾기** | 리스트만 있으면 노드 찾는 데 O(n) |
| `_lru` (DoublyLinkedList) | **사용 순서 유지**(front=MRU, back=LRU) | 해시맵만 있으면 "가장 오래된 키"를 O(1)에 못 찾음 |

- 해시맵은 "어디 있는지"를, 연결 리스트는 "얼마나 최근에 썼는지"를 담당한다. 둘을 결합해야 양쪽 모두 O(1).

### 3-2. O(1) LRU 달성 원리 (조회 + 갱신)

- **조회**: `_nodes.get(key)` → 해시로 노드 참조 획득 (O(1)).
- **갱신**: `_lru.move_to_front(node)` → 그 노드를 MRU로 이동 (O(1)).
- **제거**: eviction 시 `_lru.back_node()`로 LRU 키를 O(1)에 얻어 삭제.
- 코드: `_touch_lru()`(GET/SET 성공 시 호출), `_evict_until_within_limit()`.

---

## 항목 4 — 동작 흐름 및 심화

### 4-1. TTL에 힙을 쓰는 이유

`min_heap.py`

- TTL 관리의 본질은 **"가장 먼저 만료될 키"를 빠르게 찾기**다.
- 최소 힙은 루트가 항상 최소(가장 이른 만료 시각) → `peek()` **O(1)**, `push`/`pop` **O(log n)**.
- 요소는 `(expire_at, key)` 튜플. 파이썬 튜플 비교가 `expire_at` 우선이라 자연 정렬된다.
- **lazy deletion**: 만료 시각 갱신/키 삭제 시 힙 엔트리를 즉시 지우지 않고, `_purge_expired_from_heap`에서 루트부터 검사해 "현재 만료시각과 일치하는지" 확인하고 stale/만료 엔트리를 버린다(임의 위치 삭제 비용 회피).
- **실제 호출 시점**: `DBSIZE` / `KEYS`가 `_purge_expired_from_heap()`을 호출해 만료 키를 일괄 정리한다. 또한 `GET`/`EXISTS`/`TTL`/`DEL`은 키 접근 시 `_is_expired`로 개별 만료를 lazy 확인한다. 힙 덕분에 "가장 이른 만료"를 루트에서 O(1)로 확인하고, 만료가 지나지 않았으면 즉시 멈춘다.

### 4-2. 메모리 초과 시 eviction 흐름 (단계별)

`engine.py::set` → `_evict_until_within_limit`

1. **단일 엔트리 검사**: `len(key)+len(value)`가 `maxmemory(>0)`보다 크면 저장 없이 `OOMError`.
2. **저장 + used_memory 갱신**: 신규면 `+entry_size`, 덮어쓰기면 `-old +new`.
3. **eviction 루프**: `maxmemory>0` 이고 `used_memory > maxmemory`인 동안:
   - `_lru.back_node().data`로 **가장 오래된 키** 획득,
   - `_delete_key()`로 store/LRU/TTL에서 제거하고 `used_memory` 차감,
   - `evicted_keys += 1`.
4. `used_memory <= maxmemory`가 되면 종료.

`used_memory = Σ(len(utf8(key)) + len(utf8(value)))` — 자료구조 오버헤드 제외.

### 4-3. GET 명령 전체 흐름

`engine.py::get`

1. `_ensure_alive(key)`: 키 존재 확인 → 있으면 **TTL 만료 검사**.
2. 만료됐으면 → `_delete_key()` 후 `None` 반환 (**LRU 갱신 안 함**).
3. 살아있으면 → 값 조회.
4. `_touch_lru(key)`로 **LRU를 MRU로 갱신** (조회 성공 시에만).
5. 값 반환. CLI는 `"value"` 형태로, 없으면 `(nil)` 출력.

### 4-4. LRU 대신 LFU를 구현한다면?

- LRU는 **최근성(recency)**, LFU는 **빈도(frequency)** 기준 제거.
- 변경점:
  - 각 키에 **접근 횟수 카운터** 추가 (`HashMap: key→count`).
  - 같은 빈도끼리 묶는 **빈도 버킷**(빈도→키들의 연결 리스트) 구조, 또는 `(count, key)` **최소 힙**.
  - 접근 시 count 증가 + 해당 키를 다음 빈도 버킷으로 이동.
  - eviction은 "최소 빈도 버킷의 가장 오래된 키" 제거 → O(1) LFU(빈도 버킷 방식) 가능.

### 4-5. 데이터가 10만 건으로 늘면 병목과 개선

- **병목 후보**:
  - 해시맵 `_resize`의 일괄 rehash(O(n)) — 큰 데이터에서 순간 지연(stop-the-world).
  - 힙에 stale 엔트리가 많이 쌓이면 `_purge_expired_from_heap` 정리 비용 증가.
  - 힙의 stale 엔트리 누적으로 메모리/정리 비용 증가.
- **개선 방향**:
  - **점진적 리해싱**(incremental rehash): 한 번에 다 옮기지 않고 연산마다 조금씩 이전(Redis 실제 방식).
  - 만료 정리를 **능동적 샘플링**(주기적 랜덤 표본 검사) + lazy 조합으로.
  - 해시 함수 품질/로드팩터 튜닝으로 체인 길이 억제.
  - 힙 대신 **시간 버킷(timer wheel)** 으로 만료 그룹화.

### 4-6. used_memory에 오버헤드까지 포함하는 모델로 바꾼다면?

- 달라지는 점: 노드/포인터/버킷/힙 엔트리의 실제 점유까지 세므로 **같은 키-값도 used_memory가 커지고**, eviction이 더 자주 발생한다. 구현/언어/플랫폼에 따라 오버헤드가 달라져 값이 비결정적이 된다.
- 공정한 비교/채점을 위한 보정:
  - **고정 단가 모델** 채택(예: 엔트리당 상수 C 바이트 가산)로 플랫폼 의존성 제거.
  - 측정 기준(노드 크기, 포인터 크기)을 **명세에 못 박기**.
  - 채점은 절대값이 아닌 **상대 비교/공식 일치** 위주로.

---

## 추가: docstring/주석 기준 (항목 3-5 성격)

- **클래스/공개 메서드**: 역할 + 시간복잡도 + 핵심 불변식을 docstring으로.
- **비자명한 내부 로직**(센티넬, lazy deletion, rehash, eviction 루프)에는 "왜" 중심 주석.
- 자명한 getter 등에는 과한 주석을 달지 않아 노이즈를 줄임.

## 추가: 해시 생성 카운터 기반 ↔ 난수 기반 (재현성)

- 본 구현의 해시는 **키 내용 결정론적 함수**라 같은 키는 항상 같은 인덱스 → 테스트/디버깅 재현 용이.
- 만약 시드/난수 기반(예: SipHash with random seed)으로 바꾸면 충돌 공격 방어에는 유리하나, 실행마다 버킷 분포가 달라져 **테스트 재현성과 디버깅이 어려워진다**(고정 시드 주입으로 절충 필요).
