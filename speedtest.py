from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CHUNK_SIZE = 64 * 1024
USER_AGENT = "speedtest-script/1.0"


def fetch(url: str, timeout: float) -> tuple[int, float]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Accept-Encoding": "identity",
        },
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        size = 0
        while chunk := response.read(CHUNK_SIZE):
            size += len(chunk)
    elapsed = time.perf_counter() - started
    return size, elapsed


def human_bytes(num: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if num < 1000 or unit == "ГБ":
            return f"{num:.2f} {unit}" if unit != "Б" else f"{int(num)} {unit}"
        num /= 1000
    return f"{num:.2f} ГБ"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Замеряет скорость скачивания, делая N последовательных запросов к URL."
    )
    parser.add_argument("url", help="адрес ресурса, например тяжёлая картинка")
    parser.add_argument(
        "-n", "--requests", type=int, default=10,
        help="количество запросов (по умолчанию 10)",
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=30.0,
        help="таймаут одного запроса в секундах (по умолчанию 30)",
    )
    args = parser.parse_args(argv)

    scheme = urllib.parse.urlparse(args.url).scheme
    if scheme not in ("http", "https"):
        parser.error("адрес должен начинаться с http:// или https://")
    if args.requests < 1:
        parser.error("количество запросов должно быть не меньше 1")
    if args.timeout <= 0:
        parser.error("таймаут должен быть положительным")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(f"URL: {args.url}")
    print(f"Запросов: {args.requests}\n")

    total_bytes = 0
    total_time = 0.0
    succeeded = 0

    for i in range(1, args.requests + 1):
        prefix = f"[{i:>2}/{args.requests}]"
        try:
            size, elapsed = fetch(args.url, args.timeout)
        except urllib.error.HTTPError as exc:
            print(f"{prefix} ошибка HTTP {exc.code}: {exc.reason}")
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            print(f"{prefix} ошибка соединения: {reason}")
            continue

        succeeded += 1
        total_bytes += size
        total_time += elapsed
        print(f"{prefix} {human_bytes(size):>10} за {elapsed:.3f} с")

    print()
    if succeeded == 0:
        print("Ни один запрос не завершился успешно — скорость посчитать нельзя.")
        return 1
    if total_bytes == 0:
        print("Сервер вернул пустые ответы — скорость посчитать нельзя.")
        return 1

    avg_time = total_time / succeeded
    mbit_per_s = total_bytes * 8 / total_time / 1_000_000
    mbyte_per_s = total_bytes / total_time / 1_000_000

    print(f"Успешных запросов:   {succeeded} из {args.requests}")
    print(f"Скачано всего:       {human_bytes(total_bytes)} ({total_bytes} байт)")
    print(f"Среднее время:       {avg_time:.3f} с")
    print(f"Скорость скачивания: {mbit_per_s:.2f} Мбит/с ({mbyte_per_s:.2f} МБ/с)")
    return 0 if succeeded == args.requests else 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
        sys.exit(130)
