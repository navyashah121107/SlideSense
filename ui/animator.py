"""Animation primitives: easing, tile slides, pulses and win particles.

Role: pure-Python (no pygame) time-based animation helpers. The renderer asks
``AnimationManager.positions()`` where each sliding tile currently is, and
draws ``ParticleSystem.particles`` during the win celebration. Keeping this
free of pygame makes it trivially testable.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Sequence

from utils.config import (
    PARTICLE_GRAVITY,
    PARTICLE_LIFE_MS_MAX,
    PARTICLE_LIFE_MS_MIN,
    PARTICLE_RADIUS_MAX,
    PARTICLE_RADIUS_MIN,
    PARTICLE_SPEED_MAX,
    PARTICLE_SPEED_MIN,
    PARTICLES_PER_BURST,
    SLIDE_DURATION_MS,
    Color,
)

Point = tuple[float, float]
Easing = Callable[[float], float]


def linear(t: float) -> float:
    """Identity easing."""
    return t


def ease_in_out(t: float) -> float:
    """Cubic ease-in-out: slow start, fast middle, slow end."""
    t = max(0.0, min(1.0, t))
    return 4 * t**3 if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between ``a`` and ``b``."""
    return a + (b - a) * t


def pulse(elapsed_ms: float, period_ms: float) -> float:
    """Smooth oscillation between 0 and 1 with the given period."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * (elapsed_ms % period_ms) / period_ms)


@dataclass
class SlideAnimation:
    """One tile sliding from ``start`` to ``end`` (pixel top-left of its cell).

    Attributes:
        tile: Tile value being animated.
        start: Pixel position where the slide begins.
        end: Pixel position where it ends.
        duration_ms: Total duration.
        elapsed_ms: Time consumed so far.
        easing: Easing function applied to linear progress.
    """

    tile: int
    start: Point
    end: Point
    duration_ms: float = SLIDE_DURATION_MS
    elapsed_ms: float = 0.0
    easing: Easing = ease_in_out

    @property
    def progress(self) -> float:
        """Linear progress in 0..1."""
        return min(1.0, self.elapsed_ms / self.duration_ms) if self.duration_ms > 0 else 1.0

    @property
    def finished(self) -> bool:
        """True once the slide has completed."""
        return self.progress >= 1.0

    def update(self, dt_ms: float) -> None:
        """Advance the animation by ``dt_ms`` milliseconds."""
        self.elapsed_ms += dt_ms

    def position(self) -> Point:
        """Current eased pixel position."""
        eased = self.easing(self.progress)
        return (lerp(self.start[0], self.end[0], eased), lerp(self.start[1], self.end[1], eased))


class AnimationManager:
    """Owns all active tile slides, keyed by tile value."""

    def __init__(self) -> None:
        self._slides: dict[int, SlideAnimation] = {}

    def start_slide(
        self, tile: int, start: Point, end: Point, duration_ms: float = SLIDE_DURATION_MS
    ) -> None:
        """Begin (or restart) the slide of ``tile``."""
        self._slides[tile] = SlideAnimation(tile, start, end, duration_ms)

    def update(self, dt_ms: float) -> None:
        """Advance every slide and drop the finished ones."""
        for slide in self._slides.values():
            slide.update(dt_ms)
        self._slides = {t: s for t, s in self._slides.items() if not s.finished}

    def is_animating(self) -> bool:
        """True while any tile is still sliding."""
        return bool(self._slides)

    def positions(self) -> dict[int, Point]:
        """Current pixel position of each sliding tile."""
        return {tile: slide.position() for tile, slide in self._slides.items()}

    def clear(self) -> None:
        """Cancel all animations immediately."""
        self._slides.clear()


@dataclass
class Particle:
    """A single confetti particle (position in pixels, velocity in px/s)."""

    x: float
    y: float
    vx: float
    vy: float
    life_ms: float
    max_life_ms: float
    radius: float
    color: Color

    @property
    def alive(self) -> bool:
        """True while the particle still has life left."""
        return self.life_ms > 0

    @property
    def fade(self) -> float:
        """Remaining life as a fraction 0..1."""
        return max(0.0, self.life_ms / self.max_life_ms)

    def update(self, dt_ms: float) -> None:
        """Integrate motion with gravity."""
        dt = dt_ms / 1000.0
        self.vy += PARTICLE_GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life_ms -= dt_ms


@dataclass
class ParticleSystem:
    """Spawns and updates bursts of particles."""

    rng: random.Random = field(default_factory=random.Random)
    particles: list[Particle] = field(default_factory=list)

    def burst(
        self, x: float, y: float, colors: Sequence[Color], count: int = PARTICLES_PER_BURST
    ) -> None:
        """Emit ``count`` particles radiating from ``(x, y)``."""
        for _ in range(count):
            angle = self.rng.uniform(0, 2 * math.pi)
            speed = self.rng.uniform(PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX)
            life = self.rng.uniform(PARTICLE_LIFE_MS_MIN, PARTICLE_LIFE_MS_MAX)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life_ms=life,
                    max_life_ms=life,
                    radius=self.rng.uniform(PARTICLE_RADIUS_MIN, PARTICLE_RADIUS_MAX),
                    color=self.rng.choice(list(colors)),
                )
            )

    def update(self, dt_ms: float) -> None:
        """Advance all particles and discard the dead ones."""
        for particle in self.particles:
            particle.update(dt_ms)
        self.particles = [p for p in self.particles if p.alive]

    def clear(self) -> None:
        """Remove every particle."""
        self.particles.clear()


if __name__ == "__main__":
    for step in range(0, 11, 2):
        t = step / 10
        print(f"t={t:.1f}  linear={linear(t):.3f}  ease_in_out={ease_in_out(t):.3f}")
    demo = SlideAnimation(tile=1, start=(0, 0), end=(100, 0))
    demo.update(SLIDE_DURATION_MS / 2)
    print("halfway position:", demo.position())
