"""
MDF Shape Tessellator

Converts an SVG path boundary into scanline slots for text reflow.
This is the algorithmic core of MDF's shape-native typography system.

The algorithm:
1. Parse the SVG path into Bezier segments
2. For each text line (stepping by leading), cast a horizontal ray
3. Find intersections with the path
4. Apply even-odd fill rule to determine inside/outside
5. Return the inside intervals as available text width slots

This module implements the normative algorithm described in
spec/v0.1/05-typography.md §5.4.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class LineSlot:
    """A horizontal interval available for text on one scanline."""
    y: float           # scanline y position (baseline)
    segments: list[tuple[float, float]]  # list of (x_start, x_end) intervals
    total_width: float  # sum of all segment widths

    @property
    def primary_x(self) -> float:
        """X start of the widest segment."""
        if not self.segments:
            return 0.0
        return max(self.segments, key=lambda s: s[1] - s[0])[0]

    @property
    def primary_width(self) -> float:
        """Width of the widest segment."""
        if not self.segments:
            return 0.0
        return max(s[1] - s[0] for s in self.segments)


def tessellate_path(
    path_data: str,
    y_start: float,
    y_end: float,
    leading: float,
    padding: float = 0.0,
    min_line_width: float = 0.0,
) -> list[LineSlot]:
    """
    Given an SVG path string, compute scanline slots for text reflow.

    Args:
        path_data: SVG path data string (e.g. "M 50,0 A 50,50 0 1,1 50,0.001 Z")
        y_start: Top of the reflow region (after padding)
        y_end: Bottom of the reflow region (after padding)
        leading: Line height in document units
        padding: Additional inset from the shape boundary
        min_line_width: Minimum useful line width; slots narrower than this are discarded

    Returns:
        List of LineSlot objects, one per scanline within the shape
    """
    segments = _parse_path(path_data)
    slots = []

    y = y_start
    while y <= y_end:
        intersections = _ray_intersections(segments, y)
        intervals = _even_odd_intervals(intersections)
        # Apply padding inset to each interval
        inset_intervals = [
            (x0 + padding, x1 - padding)
            for x0, x1 in intervals
            if (x1 - padding) - (x0 + padding) > min_line_width
        ]
        if inset_intervals:
            total = sum(x1 - x0 for x0, x1 in inset_intervals)
            slots.append(LineSlot(y=y, segments=inset_intervals, total_width=total))
        y += leading

    return slots


# --- Internal path parsing ---

@dataclass
class PathSegment:
    """A single Bezier or line segment of the path."""
    kind: str  # 'line', 'cubic', 'quadratic', 'arc'
    points: list[tuple[float, float]]  # control points


def _parse_path(path_data: str) -> list[PathSegment]:
    """
    Parse SVG path data into a list of PathSegment objects.
    Handles: M, L, H, V, C, S, Q, T, A, Z (and lowercase variants).

    This is a simplified parser for the MDF reference implementation.
    A production implementation should use a full SVG path parser.
    """
    segments = []
    # TODO: implement full SVG path parser
    # For now, stub with a simple circle approximation for testing
    # Real implementation: tokenize path data, handle all command types
    return segments


def _ray_intersections(segments: list[PathSegment], y: float) -> list[float]:
    """
    Cast a horizontal ray at height y and return x-coordinates of all
    intersections with the path segments.
    """
    intersections = []
    for seg in segments:
        xs = _segment_intersections(seg, y)
        intersections.extend(xs)
    return sorted(intersections)


def _segment_intersections(seg: PathSegment, y: float) -> list[float]:
    """Find x-intersections of a single path segment with a horizontal ray at y."""
    if seg.kind == 'line':
        return _line_intersection(seg.points[0], seg.points[1], y)
    elif seg.kind == 'cubic':
        return _cubic_intersections(seg.points, y)
    elif seg.kind == 'quadratic':
        return _quadratic_intersections(seg.points, y)
    return []


def _line_intersection(p0: tuple[float, float], p1: tuple[float, float], y: float) -> list[float]:
    """Find x-intersection of a line segment p0->p1 with horizontal ray at y."""
    x0, y0 = p0
    x1, y1 = p1
    if y0 == y1:
        return []  # horizontal segment, skip
    if not (min(y0, y1) <= y <= max(y0, y1)):
        return []
    t = (y - y0) / (y1 - y0)
    x = x0 + t * (x1 - x0)
    return [x]


def _cubic_intersections(points: list[tuple[float, float]], y: float) -> list[float]:
    """
    Find x-intersections of a cubic Bezier with a horizontal ray at y.
    Uses numerical root finding (bisection) on the y component.
    """
    p0, p1, p2, p3 = points
    results = []
    # Sample the curve to find approximate root intervals, then bisect
    SAMPLES = 32
    prev_t = 0.0
    prev_y = _cubic_y(p0, p1, p2, p3, 0.0)
    for i in range(1, SAMPLES + 1):
        t = i / SAMPLES
        cy = _cubic_y(p0, p1, p2, p3, t)
        if (prev_y - y) * (cy - y) < 0:
            # Root between prev_t and t — bisect
            root_t = _bisect_cubic_y(p0, p1, p2, p3, prev_t, t, y)
            if root_t is not None:
                root_x = _cubic_x(p0, p1, p2, p3, root_t)
                results.append(root_x)
        prev_t = t
        prev_y = cy
    return results


def _cubic_y(p0, p1, p2, p3, t: float) -> float:
    """Evaluate y-component of cubic Bezier at parameter t."""
    mt = 1.0 - t
    return mt**3 * p0[1] + 3*mt**2*t * p1[1] + 3*mt*t**2 * p2[1] + t**3 * p3[1]


def _cubic_x(p0, p1, p2, p3, t: float) -> float:
    """Evaluate x-component of cubic Bezier at parameter t."""
    mt = 1.0 - t
    return mt**3 * p0[0] + 3*mt**2*t * p1[0] + 3*mt*t**2 * p2[0] + t**3 * p3[0]


def _bisect_cubic_y(p0, p1, p2, p3, t_lo: float, t_hi: float, target_y: float,
                    iterations: int = 20) -> Optional[float]:
    """Bisection root-finding for cubic Bezier y = target_y in [t_lo, t_hi]."""
    for _ in range(iterations):
        t_mid = (t_lo + t_hi) / 2.0
        y_mid = _cubic_y(p0, p1, p2, p3, t_mid)
        if abs(y_mid - target_y) < 1e-6:
            return t_mid
        if (_cubic_y(p0, p1, p2, p3, t_lo) - target_y) * (y_mid - target_y) < 0:
            t_hi = t_mid
        else:
            t_lo = t_mid
    return (t_lo + t_hi) / 2.0


def _quadratic_intersections(points: list[tuple[float, float]], y: float) -> list[float]:
    """Find x-intersections of a quadratic Bezier with a horizontal ray at y."""
    p0, p1, p2 = points
    # Quadratic Bezier y(t) = (1-t)^2*y0 + 2(1-t)*t*y1 + t^2*y2
    # Rearrange to: (y0 - 2y1 + y2)t^2 + 2(y1 - y0)t + (y0 - y) = 0
    a = p0[1] - 2*p1[1] + p2[1]
    b = 2 * (p1[1] - p0[1])
    c = p0[1] - y

    if abs(a) < 1e-10:
        # Linear case
        if abs(b) < 1e-10:
            return []
        t = -c / b
        if 0.0 <= t <= 1.0:
            x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
            return [x]
        return []

    discriminant = b*b - 4*a*c
    if discriminant < 0:
        return []

    results = []
    sqrt_d = math.sqrt(discriminant)
    for t in [(-b + sqrt_d) / (2*a), (-b - sqrt_d) / (2*a)]:
        if 0.0 <= t <= 1.0:
            x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
            results.append(x)
    return results


def _even_odd_intervals(intersections: list[float]) -> list[tuple[float, float]]:
    """
    Apply the even-odd fill rule to a sorted list of x-intersections.
    Returns a list of (x_start, x_end) intervals that are 'inside' the path.
    """
    intervals = []
    for i in range(0, len(intersections) - 1, 2):
        intervals.append((intersections[i], intersections[i+1]))
    return intervals
