"""Rotor track: a closed circuit built from straights and arcs.

The centreline is sampled into points. Each point stores position, heading,
half-width and curvature; segment i joins point i to point i + 1 (wrapping).
Distance 0 is the start line; the finish line sits FINISH_BACK metres before
it, so the start grid is between the finish and the start.
"""

import math

# (kind, ...): "S", length, [width]   straight
#              "T", radius, degrees, [width]   arc (+ right, - left)
LAYOUT = (
    ("S", 18.0),
    ("T", 6.0, 90),            # fast right sweeper
    ("S", 8.0),
    ("T", 3.0, -40),           # chicane
    ("T", 3.0, 40),
    ("S", 4.0),
    ("T", 4.0, 90),
    ("S", 6.0, 1.8),           # narrow section
    ("T", 2.6, -180, 2.2),     # left hairpin...
    ("S", 6.0),
    ("T", 2.6, 180, 2.2),      # ...straight into a right hairpin
    ("S", 32.404),             # back straight
    ("T", 5.0, 90),
    ("T", 3.5, -50),           # esses
    ("T", 3.5, 100),
    ("T", 3.5, -50),
    ("S", 14.532),
    ("T", 6.0, 90),            # last corner onto the main straight
)

WIDTH = 2.6          # default track width, m
FINISH_BACK = 8.0    # finish line distance before the start line, m
STRAIGHT_STEP = 2.0
ARC_STEP = 0.9
KERB = 0.18          # kerb width outside the track edge on corners, m


def _sample(layout):
    x = z = h = 0.0                      # heading 0 = +z, + turns right
    pts = []                             # (x, z, heading, half_width, curvature)
    for seg in layout:
        if seg[0] == "S":
            length = seg[1]
            half = (seg[2] if len(seg) > 2 else WIDTH) / 2
            n = max(1, int(math.ceil(length / STRAIGHT_STEP)))
            for i in range(n):
                pts.append((x, z, h, half, 0.0))
                x += math.sin(h) * length / n
                z += math.cos(h) * length / n
        else:
            r, deg = seg[1], seg[2]
            half = (seg[3] if len(seg) > 3 else WIDTH) / 2
            total = math.radians(deg)
            n = max(2, int(math.ceil(abs(total) * r / ARC_STEP)))
            dh = total / n
            chord = 2 * r * math.sin(abs(dh) / 2)
            for i in range(n):
                pts.append((x, z, h + dh / 2, half, 1.0 / r))
                x += math.sin(h + dh / 2) * chord
                z += math.cos(h + dh / 2) * chord
                h += dh
    return pts, x, z, h


def build():
    pts, ex, ez, eh = _sample(LAYOUT)
    # close the loop with a straight back to the start line
    dx = -ex
    dz = -ez
    gap = math.sqrt(dx * dx + dz * dz)
    n = max(1, int(math.ceil(gap / STRAIGHT_STEP)))
    h = math.atan2(dx, dz)
    for i in range(n):
        pts.append((ex + dx * i / n, ez + dz * i / n, h, WIDTH / 2, 0.0))
    return pts, (ex, ez, math.degrees(eh), gap)


class Track:
    def __init__(self):
        pts, self.closing = build()
        n = len(pts)
        self.n = n
        self.x = [p[0] for p in pts]
        self.z = [p[1] for p in pts]
        self.half = [p[3] for p in pts]
        self.curv = [p[4] for p in pts]
        # segment direction and left/right edges (averaged corner normals)
        self.dx = []
        self.dz = []
        for i in range(n):
            j = (i + 1) % n
            ux = self.x[j] - self.x[i]
            uz = self.z[j] - self.z[i]
            l = math.sqrt(ux * ux + uz * uz) or 1.0
            self.dx.append(ux / l)
            self.dz.append(uz / l)
        self.lx = []
        self.lz = []
        self.rx = []
        self.rz = []
        self.klx = []
        self.klz = []
        self.krx = []
        self.krz = []
        for i in range(n):
            p = (i - 1) % n
            tx = self.dx[p] + self.dx[i]
            tz = self.dz[p] + self.dz[i]
            l = math.sqrt(tx * tx + tz * tz) or 1.0
            tx /= l
            tz /= l
            # right of heading (tx, tz) is (tz, -tx)
            hw = self.half[i]
            self.rx.append(self.x[i] + tz * hw)
            self.rz.append(self.z[i] - tx * hw)
            self.lx.append(self.x[i] - tz * hw)
            self.lz.append(self.z[i] + tx * hw)
            kw = hw + KERB
            self.krx.append(self.x[i] + tz * kw)
            self.krz.append(self.z[i] - tx * kw)
            self.klx.append(self.x[i] - tz * kw)
            self.klz.append(self.z[i] + tx * kw)
        # cumulative distance along the centreline
        self.s = [0.0] * n
        for i in range(1, n):
            ddx = self.x[i] - self.x[i - 1]
            ddz = self.z[i] - self.z[i - 1]
            self.s[i] = self.s[i - 1] + math.sqrt(ddx * ddx + ddz * ddz)
        ddx = self.x[0] - self.x[n - 1]
        ddz = self.z[0] - self.z[n - 1]
        self.length = self.s[n - 1] + math.sqrt(ddx * ddx + ddz * ddz)
        self.finish = self.length - FINISH_BACK
        # max curvature over the next few metres, for CPU braking
        self.ahead = [0.0] * n
        for i in range(n):
            k = 0.0
            for j in range(10):
                c = self.curv[(i + j) % n]
                if c > k:
                    k = c
            self.ahead[i] = k

    def point_at(self, s):
        """Index of the centreline point at or just before distance s."""
        s %= self.length
        lo = 0
        hi = self.n - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.s[mid] <= s:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def pose_at(self, s, lateral=0.0):
        """World x, z and heading at distance s, offset sideways (+ right)."""
        i = self.point_at(s)
        t = (s % self.length) - self.s[i]
        x = self.x[i] + self.dx[i] * t
        z = self.z[i] + self.dz[i] * t
        x += self.dz[i] * lateral
        z -= self.dx[i] * lateral
        return x, z, math.atan2(self.dx[i], self.dz[i])

    def nearest(self, x, z, i, back=3, fwd=8):
        """Nearest centreline point to (x, z) searching around index i."""
        best = i
        bd = 1e9
        n = self.n
        for k in range(i - back, i + fwd + 1):
            j = k % n
            ddx = x - self.x[j]
            ddz = z - self.z[j]
            d = ddx * ddx + ddz * ddz
            if d < bd:
                bd = d
                best = j
        return best, bd

    def nearest_global(self, x, z):
        best = 0
        bd = 1e9
        for j in range(self.n):
            ddx = x - self.x[j]
            ddz = z - self.z[j]
            d = ddx * ddx + ddz * ddz
            if d < bd:
                bd = d
                best = j
        return best, bd

    def lateral(self, x, z, i):
        """Signed sideways offset of (x, z) from segment i (+ right)."""
        return (x - self.x[i]) * self.dz[i] - (z - self.z[i]) * self.dx[i]
