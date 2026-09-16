"""SMIL timeline helpers.

Every animation shares one duration and repeats indefinitely, so the whole
quest loops seamlessly. No JavaScript: GitHub proxies README images through
camo, which strips scripts but keeps declarative animation.
"""

KEY_DECIMALS = 5


def num(value):
    """Compact coordinate formatting ("-0" collapses to "0")."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def dur_attr(duration):
    return f'dur="{duration:.3f}s" repeatCount="indefinite"'


def _key(t, duration):
    return round(min(max(t / duration, 0.0), 1.0), KEY_DECIMALS)


def _discrete_keys(points, duration):
    """Normalise (t, value) events: sorted, first key 0, equal keys keep the last."""
    keyed = []
    for t, value in sorted(points, key=lambda p: p[0]):
        k = _key(t, duration)
        if keyed and keyed[-1][0] == k:
            keyed[-1] = (k, value)
        elif keyed and keyed[-1][1] == value:
            continue
        else:
            keyed.append((k, value))
    if not keyed or keyed[0][0] > 0:
        first = keyed[0][1] if keyed else "0"
        keyed.insert(0, (0.0, first))
    return keyed


def _linear_keys(points, duration):
    """Normalise (t, value) keyframes for linear interpolation over [0, 1]."""
    step = 10 ** -KEY_DECIMALS
    keyed = []
    for t, value in sorted(points, key=lambda p: p[0]):
        k = _key(t, duration)
        if keyed and k <= keyed[-1][0]:
            k = round(keyed[-1][0] + step, KEY_DECIMALS)  # browsers want strictly increasing keys
        if k > 1:
            continue
        keyed.append((k, value))
    if keyed[0][0] > 0:
        keyed.insert(0, (0.0, keyed[0][1]))
    if keyed[-1][0] < 1:
        keyed.append((1.0, keyed[-1][1]))
    return keyed


def _emit(tag, attr_prefix, keyed, calc, duration):
    values = ";".join(v for _, v in keyed)
    times = ";".join(f"{k:g}" for k, _ in keyed)
    return (
        f'<{tag} {attr_prefix} values="{values}" keyTimes="{times}" '
        f'calcMode="{calc}" {dur_attr(duration)}/>'
    )


def discrete(attr, points, duration):
    return _emit("animate", f'attributeName="{attr}"', _discrete_keys(points, duration), "discrete", duration)


def linear(attr, points, duration):
    return _emit("animate", f'attributeName="{attr}"', _linear_keys(points, duration), "linear", duration)


def translate(points, duration, calc="linear"):
    """points: [(t, x, y)] -> animateTransform."""
    pairs = [(t, f"{num(x)} {num(y)}") for t, x, y in points]
    keyed = _linear_keys(pairs, duration) if calc == "linear" else _discrete_keys(pairs, duration)
    return _emit("animateTransform", 'attributeName="transform" type="translate"', keyed, calc, duration)


def windows(intervals, duration):
    """Opacity 1 inside the [start, end) intervals, 0 elsewhere (discrete)."""
    points = [(0.0, "0")]
    for start, end in sorted(intervals):
        points += [(start, "1"), (end, "0")]
    return discrete("opacity", points, duration)


def motion(path_d, t0, t1, duration):
    """Travel along an SVG path between t0 and t1, parked at the ends otherwise."""
    k0, k1 = _key(t0, duration), _key(t1, duration)
    if k1 <= k0:
        k1 = min(1.0, k0 + 10 ** -KEY_DECIMALS)
    return (
        f'<animateMotion path="{path_d}" keyPoints="0;0;1;1" keyTimes="0;{k0:g};{k1:g};1" '
        f'calcMode="linear" {dur_attr(duration)}/>'
    )


class DiscreteTrack:
    """Builder for a discrete value timeline with looping cycles and overrides."""

    def __init__(self, initial):
        self._events = [(0.0, initial)]

    def value_at(self, t):
        current = self._events[0][1]
        for when, value in self._events:
            if when <= t + 1e-9:
                current = value
            else:
                break
        return current

    def cycle(self, start, end, fps, values, phase=0):
        events, t, i = [], start, phase
        while t < end - 1e-9:
            events.append((t, values[i % len(values)]))
            t, i = t + 1.0 / fps, i + 1
        events.append((end, self.value_at(end)))
        self._events = [e for e in self._events if not (start <= e[0] < end)]
        self._insert(events)

    def override(self, start, end, value):
        resume = self.value_at(end)
        self._events = [e for e in self._events if not (start <= e[0] < end)]
        self._insert([(start, value), (end, resume)])

    def _insert(self, events):
        merged = sorted(self._events + list(events), key=lambda e: e[0])
        self._events = merged

    def events(self):
        return tuple(self._events)
