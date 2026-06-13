"""CLI: ask a question against the ingested codebase.

Usage: python -m astra.ask "how does authentication work?"
"""

import sys

from astra.answer import answer, format_sources


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python -m astra.ask "<question>"')
    question = " ".join(sys.argv[1:])
    text, hits = answer(question)
    print(text)
    if hits:
        print(format_sources(hits))


if __name__ == "__main__":
    main()
