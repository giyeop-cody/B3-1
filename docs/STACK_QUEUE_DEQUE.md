# 스택 / 큐 / 덱 (Stack / Queue / Deque)

> 보너스 과제 5.2 문서. 구현은 `mini_redis/structures/stack_queue_deque.py`.

세 자료구조 모두 직접 구현한 **이중 연결 리스트**(`DoublyLinkedList`) 위에서 동작하며, 핵심 연산이 모두 **O(1)** 이다.

---

## 1. 스택 (Stack) — LIFO

**Last In, First Out.** 가장 마지막에 넣은 것이 가장 먼저 나온다.

| 연산 | 설명 | 복잡도 |
| --- | --- | --- |
| `push(x)` | top에 추가 | O(1) |
| `pop()` | top 제거·반환 | O(1) |
| `peek()` | top 확인 | O(1) |

- **구현**: 리스트의 앞쪽(front)을 top으로 사용 → `insert_front` / `remove_front`.
- **활용**: 함수 호출 스택, 괄호 검사, DFS, 실행 취소(undo), **커맨드 히스토리 역추적**.

```
push(1) push(2) push(3)   →   [3, 2, 1]   (top=3)
pop() → 3                 →   [2, 1]
```

---

## 2. 큐 (Queue) — FIFO

**First In, First Out.** 먼저 넣은 것이 먼저 나온다.

| 연산 | 설명 | 복잡도 |
| --- | --- | --- |
| `enqueue(x)` | 뒤(back)에 추가 | O(1) |
| `dequeue()` | 앞(front) 제거·반환 | O(1) |
| `peek()` | 앞 확인 | O(1) |

- **구현**: 뒤로 넣고(`insert_back`) 앞에서 뺀다(`remove_front`).
- **활용**: BFS(레벨 순회), 작업 스케줄링, **Pub/Sub 구독자별 메시지 버퍼**.

```
enqueue(1) enqueue(2) enqueue(3)   →   front[1, 2, 3]back
dequeue() → 1                      →   front[2, 3]back
```

---

## 3. 덱 (Deque) — Double-Ended Queue

양쪽 끝 모두에서 삽입·삭제가 가능한 일반화된 큐.

| 연산 | 설명 | 복잡도 |
| --- | --- | --- |
| `push_front(x)` / `push_back(x)` | 양 끝 삽입 | O(1) |
| `pop_front()` / `pop_back()` | 양 끝 삭제 | O(1) |
| `peek_front()` / `peek_back()` | 양 끝 확인 | O(1) |

- **구현**: 이중 연결 리스트의 앞/뒤 연산을 그대로 노출.
- **특징**: 스택으로도, 큐로도 쓸 수 있는 상위 호환.
- **활용**: 슬라이딩 윈도우 최댓값, 양방향 작업 큐, **LRU 캐시의 사용 순서 리스트**(본 프로젝트의 `_lru`가 사실상 덱처럼 동작: front=MRU, back=LRU).

```
push_back(1) push_front(0) push_back(2)   →   [0, 1, 2]
pop_front() → 0,  pop_back() → 2          →   [1]
```

---

## 4. 본 프로젝트와의 연결

- **LRU 추적**: `_lru`(이중 연결 리스트)는 "앞에 넣고 뒤에서 빼는" 덱 형태로, 가장 오래 안 쓴 키를 `remove_back`으로 O(1)에 꺼낸다.
- **레벨 순회**: `BinaryTree.level_order`는 직접 만든 `Queue`로 BFS를 수행한다.
- **확장 가능성**: Pub/Sub(보너스 5.5)를 구현한다면 구독자별 메시지 버퍼를 `Queue`로 재활용할 수 있다.
