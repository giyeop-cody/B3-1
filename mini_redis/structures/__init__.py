"""Mini Redis - 직접 구현한 자료구조 모음 패키지.

이 패키지는 학습 목적상 ``dict`` / ``set`` / ``collections`` 등의
내장 컬렉션을 사용하지 않고, 핵심 자료구조를 밑바닥부터 구현한다.

- :mod:`dynamic_array`     : 동적 배열 (capacity 2배 확장)
- :mod:`doubly_linked_list`: 이중 연결 리스트 (모든 핵심 연산 O(1))
- :mod:`hash_map`          : 체이닝 기반 해시맵 (로드 팩터 0.75 확장)
- :mod:`min_heap`          : 최소 힙 (TTL 만료 관리용)
"""
