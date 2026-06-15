"""Mini Redis CLI - 명령어 파싱, 실행, Redis 스타일 출력.

REPL:
    ``mini-redis>`` 프롬프트에서 명령을 읽어 파싱 → 엔진 호출 → 결과 출력.
    ``exit`` / ``quit`` 으로 종료.

출력 규약(Redis 스타일):
    OK / (nil) / (integer) N / (error) ... / "value"
"""

import sys

from .engine import MiniRedis, OOMError


# ---------------------------------------------------------------------- #
# 토큰화: 공백 분리 + 큰따옴표로 감싼 값 지원
# ---------------------------------------------------------------------- #
def tokenize(line):
    """입력 라인을 토큰 리스트로 분해한다.

    규칙:
        - 공백으로 토큰을 분리한다.
        - 큰따옴표(")로 감싼 구간은 공백을 포함해 하나의 토큰으로 본다.
        - 따옴표 안의 ``\\"`` 와 ``\\\\`` 는 이스케이프로 처리한다.

    :raises ValueError: 따옴표가 닫히지 않은 경우.
    """
    tokens = []
    i = 0
    n = len(line)
    while i < n:
        # 선행 공백 스킵.
        while i < n and line[i].isspace():
            i += 1
        if i >= n:
            break
        if line[i] == '"':
            # 따옴표로 감싼 토큰.
            i += 1
            buf = []
            closed = False
            while i < n:
                ch = line[i]
                if ch == "\\" and i + 1 < n and line[i + 1] in ('"', "\\"):
                    buf.append(line[i + 1])
                    i += 2
                    continue
                if ch == '"':
                    closed = True
                    i += 1
                    break
                buf.append(ch)
                i += 1
            if not closed:
                raise ValueError("unbalanced quotes")
            tokens.append("".join(buf))
        else:
            # 일반(공백 없는) 토큰.
            buf = []
            while i < n and not line[i].isspace():
                buf.append(line[i])
                i += 1
            tokens.append("".join(buf))
    return tokens


# ---------------------------------------------------------------------- #
# 에러 메시지 표준
# ---------------------------------------------------------------------- #
def err_unknown(cmd):
    return "(error) ERR unknown command '{}'".format(cmd)


def err_args(cmd):
    return "(error) ERR wrong number of arguments for '{}' command".format(cmd)


ERR_NOT_INT = "(error) ERR value is not an integer or out of range"
ERR_OOM = "(error) OOM command not allowed when used_memory > 'maxmemory'"
ERR_UNBALANCED = "(error) ERR Protocol error: unbalanced quotes in request"


class CommandError(Exception):
    """핸들러에서 표준 에러 문자열을 던질 때 사용."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------- #
# 명령 디스패치
# ---------------------------------------------------------------------- #
class CLI:
    """엔진을 감싸 명령 문자열을 받아 출력 문자열을 돌려주는 어댑터."""

    def __init__(self, engine=None):
        self.engine = engine if engine is not None else MiniRedis()

    def execute(self, line):
        """한 줄 명령을 실행하고 출력할 문자열(없으면 None)을 반환한다."""
        try:
            tokens = tokenize(line)
        except ValueError:
            # 따옴표가 닫히지 않은 입력 — Redis와 동일한 프로토콜 에러 반환.
            return ERR_UNBALANCED
        if not tokens:
            return None

        cmd = tokens[0].upper()
        args = tokens[1:]

        # 종료.
        if cmd in ("EXIT", "QUIT"):
            raise SystemExit(0)

        try:
            return self._dispatch(cmd, tokens[0], args)
        except CommandError as e:
            return e.message
        except OOMError:
            return ERR_OOM

    def _dispatch(self, cmd, raw_cmd, args):
        """명령어를 해당 핸들러로 라우팅한다.

        if/elif 체인을 쓰는 이유: 학습 제약상 ``dict``를 쓰지 않기 위함이며,
        명령 종류가 소수라 분기 비용도 무시할 수 있다.
        """
        if cmd == "SET":
            return self._cmd_set(args)
        if cmd == "GET":
            return self._cmd_get(args)
        if cmd == "DEL":
            return self._cmd_del(args)
        if cmd == "EXISTS":
            return self._cmd_exists(args)
        if cmd == "DBSIZE":
            return self._cmd_dbsize(args)
        if cmd == "KEYS":
            return self._cmd_keys(args)
        if cmd == "CONFIG":
            return self._cmd_config(args)
        if cmd == "INFO":
            return self._cmd_info(args)
        if cmd == "EXPIRE":
            return self._cmd_expire(args)
        if cmd == "TTL":
            return self._cmd_ttl(args)
        return err_unknown(raw_cmd)

    # -------------------------- String 명령 -------------------------- #
    def _cmd_set(self, args):
        if len(args) != 2:
            raise CommandError(err_args("set"))
        return self.engine.set(args[0], args[1])

    def _cmd_get(self, args):
        if len(args) != 1:
            raise CommandError(err_args("get"))
        value = self.engine.get(args[0])
        if value is None:
            return "(nil)"
        return '"{}"'.format(value)

    def _cmd_del(self, args):
        if len(args) != 1:
            raise CommandError(err_args("del"))
        return "(integer) {}".format(self.engine.delete(args[0]))

    def _cmd_exists(self, args):
        if len(args) != 1:
            raise CommandError(err_args("exists"))
        return "(integer) {}".format(self.engine.exists(args[0]))

    def _cmd_dbsize(self, args):
        if len(args) != 0:
            raise CommandError(err_args("dbsize"))
        return "(integer) {}".format(self.engine.dbsize())

    def _cmd_keys(self, args):
        if len(args) != 0:
            raise CommandError(err_args("keys"))
        keys = self.engine.keys()
        if not keys:
            return "(empty array)"
        lines = []
        for idx, k in enumerate(keys, start=1):
            # 미션 예시 형식: 1. "user:2"
            lines.append('{}. "{}"'.format(idx, k))
        return "\n".join(lines)

    # -------------------------- 메모리 명령 -------------------------- #
    def _cmd_config(self, args):
        # CONFIG SET maxmemory <bytes>
        if len(args) < 1:
            raise CommandError(err_args("config"))
        sub = args[0].upper()
        if sub == "SET":
            if len(args) != 3:
                raise CommandError(err_args("config|set"))
            param = args[1].lower()
            if param != "maxmemory":
                raise CommandError(
                    "(error) ERR Unknown CONFIG parameter '{}'".format(args[1])
                )
            try:
                return self.engine.config_set_maxmemory(args[2])
            except ValueError:
                raise CommandError(ERR_NOT_INT)
        elif sub == "GET":
            if len(args) != 2:
                raise CommandError(err_args("config|get"))
            if args[1].lower() == "maxmemory":
                return '1) "maxmemory"\n2) "{}"'.format(self.engine.maxmemory())
            return "(empty array)"
        raise CommandError(
            "(error) ERR Unknown CONFIG subcommand '{}'".format(args[0])
        )

    def _cmd_info(self, args):
        # INFO [memory] — 미션 예시 형식에 맞춰 헤더 없이 3개 항목만 출력.
        if len(args) == 0 or args[0].lower() == "memory":
            return "\n".join(self.engine.info_memory())
        # 다른 섹션은 미지원 — memory 정보로 대체.
        return "\n".join(self.engine.info_memory())

    # --------------------------- TTL 명령 ---------------------------- #
    def _cmd_expire(self, args):
        if len(args) != 2:
            raise CommandError(err_args("expire"))
        try:
            result = self.engine.expire(args[0], args[1])
        except ValueError:
            raise CommandError(ERR_NOT_INT)
        return "(integer) {}".format(result)

    def _cmd_ttl(self, args):
        if len(args) != 1:
            raise CommandError(err_args("ttl"))
        return "(integer) {}".format(self.engine.ttl(args[0]))


def repl(input_stream=None, output_stream=None):
    """대화형 REPL을 실행한다.

    :param input_stream: 입력 스트림(기본 sys.stdin). 테스트 시 주입 가능.
    :param output_stream: 출력 스트림(기본 sys.stdout).
    """
    istream = input_stream if input_stream is not None else sys.stdin
    ostream = output_stream if output_stream is not None else sys.stdout
    cli = CLI()

    def emit(text):
        if text is not None:
            ostream.write(text + "\n")
            ostream.flush()

    while True:
        ostream.write("mini-redis> ")
        ostream.flush()
        line = istream.readline()
        if not line:  # EOF.
            ostream.write("\n")
            break
        line = line.rstrip("\n")
        try:
            emit(cli.execute(line))
        except SystemExit:
            break


if __name__ == "__main__":
    repl()
