from collections.abc import Iterable


def _flatten_class_input(value):
    if value is None or value is False:
        return

    if isinstance(value, str):
        for token in value.split():
            if token:
                yield token
        return

    if isinstance(value, dict):
        for key, enabled in value.items():
            if enabled and isinstance(key, str):
                for token in key.split():
                    if token:
                        yield token
        return

    if isinstance(value, Iterable):
        for item in value:
            yield from _flatten_class_input(item)


def cn(*inputs) -> str:
    """Compose class names similarly to clsx + twMerge for common project usage."""
    tokens = []
    for entry in inputs:
        tokens.extend(_flatten_class_input(entry) or [])

    # Keep the last occurrence of identical tokens.
    seen = set()
    merged_reversed = []
    for token in reversed(tokens):
        if token in seen:
            continue
        seen.add(token)
        merged_reversed.append(token)

    return " ".join(reversed(merged_reversed))
