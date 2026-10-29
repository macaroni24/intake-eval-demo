import json
import sys

from .pipeline import run_intake


def main() -> None:
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        print('Usage: python -m intake "your customer message"')
        sys.exit(1)
    result = run_intake(text)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
