from fasthtml.common import H3, Div, P


def _cx(*parts: str | None) -> str:
    return " ".join(part for part in parts if part)


def Card(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        cls=_cx("rounded-lg border bg-card text-card-foreground shadow-sm", cls),
        **kwargs,
    )


def CardHeader(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        cls=_cx("flex flex-col space-y-1.5 p-6", cls),
        **kwargs,
    )


def CardTitle(*children, cls: str | None = None, **kwargs):
    return H3(*children, cls=_cx("font-semibold leading-none tracking-tight", cls), **kwargs)


def CardDescription(*children, cls: str | None = None, **kwargs):
    return P(*children, cls=_cx("text-sm text-muted-foreground", cls), **kwargs)


def CardContent(*children, cls: str | None = None, **kwargs):
    return Div(*children, cls=_cx("p-6 pt-0", cls), **kwargs)


def CardFooter(*children, cls: str | None = None, **kwargs):
    return Div(*children, cls=_cx("flex items-center p-6 pt-0", cls), **kwargs)
