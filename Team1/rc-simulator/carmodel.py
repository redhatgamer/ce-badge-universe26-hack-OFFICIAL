"""Rotor car loader: turns an RC car folder into flat-shaded meshes.

A car folder holds:

  parameters.txt  handling values, model list, wheel positions
  *.obj           meshes in Wavefront OBJ (Y up, -Z forward). Faces with UVs
                  are textured; materials named "..._double" are two-sided.
  car.bmp         texture page (8, 24 or 32 bit uncompressed BMP)

The badge cannot draw textured triangles, so every face is flat shaded with
the average texture colour under it. Faces too small to see are dropped and
the result is cached as JSON so later launches skip the work.

parameters.txt uses +X right, +Y down, +Z forward. OBJ meshes are read into
that same layout so the wheel offsets line up, then the loader flips Y so +Y
is up.
"""

import json
import math
import os
import struct

LOADER_VERSION = 4

CAR_LENGTH = 0.45        # body length on screen, in the sim's metres
MIN_FACE_AREA = 1.5e-5   # m^2; about a pixel at the chase camera distance
BODY_BUDGET = 240        # max faces kept for the body
WHEEL_BUDGET = 40        # max faces kept per wheel
EXTRA_BUDGET = 40        # max faces kept for an extra body part (lights...)

UNIT_TO_MPH = 0.01118    # some files store TopEnd in internal speed units

_l = math.sqrt(0.35 * 0.35 + 0.85 * 0.85 + 0.4 * 0.4)
LIGHT = (-0.35 / _l, 0.85 / _l, -0.4 / _l)   # car space, from above/behind


def shade(rgb, nx, ny, nz, double=False):
    d = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]
    if double:
        d = abs(d)
    k = 0.45 + 0.55 * (d if d > 0 else 0)
    r = int(((rgb >> 16) & 255) * k)
    g = int(((rgb >> 8) & 255) * k)
    b = int((rgb & 255) * k)
    return (r << 16) | (g << 8) | b


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def find_file(folder, name):
    """Case-insensitive lookup of name's basename inside folder."""
    if not name or name.upper() == "NONE":
        return None
    base = name.replace("\\", "/").rsplit("/", 1)[-1].lower()
    try:
        for entry in os.listdir(folder):
            if entry.lower() == base:
                return folder + "/" + entry
    except OSError:
        pass
    return None


def file_size(path):
    try:
        return os.stat(path)[6]
    except OSError:
        return -1


# ---------------------------------------------------------------------------
# parameters.txt
# ---------------------------------------------------------------------------

def _tokens(line):
    out = []
    cur = ""
    quoted = False
    for ch in line:
        if quoted:
            if ch == '"':
                out.append(cur)
                cur = ""
                quoted = False
            else:
                cur += ch
        elif ch == '"':
            if cur:
                out.append(cur)
            cur = ""
            quoted = True
        elif ch == ";":
            break
        elif ch in " \t\r\n,":
            if cur:
                out.append(cur)
                cur = ""
        elif ch == "{" or ch == "}":
            if cur:
                out.append(cur)
                cur = ""
            out.append(ch)
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def _num(v, default=0.0):
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _vec(vals):
    return [_num(vals[i]) if i < len(vals) else 0.0 for i in range(3)]


def _bool(vals):
    return bool(vals) and vals[0].lower() == "true"


def parse_parameters(path):
    p = {"models": {}, "body": {}, "wheels": {}, "spinner": {}}
    stack = []
    with open(path, "r") as f:
        for line in f:
            toks = _tokens(line)
            if not toks:
                continue
            if toks[-1] == "{":
                head = toks[:-1]
                if not head:
                    stack.append(("top", 0))
                else:
                    idx = int(_num(head[1], 0)) if len(head) > 1 else 0
                    stack.append((head[0].lower(), idx))
                continue
            if toks[0] == "}":
                if stack:
                    stack.pop()
                continue

            key = toks[0].lower()
            vals = toks[1:]
            sec, idx = stack[-1] if stack else ("top", 0)

            if sec == "top":
                if key == "name" and vals:
                    p["name"] = vals[0]
                elif key == "model" and vals:
                    filename = vals[-1]
                    for v in vals[:-1]:
                        p["models"][int(_num(v, -1))] = filename
                elif key == "tpage" and vals:
                    p["tpage"] = vals[0]
                elif key in ("topend", "topspeed", "acc", "steerrate", "steermod",
                             "enginerate") and vals:
                    p[key] = _num(vals[0])
            elif sec == "body":
                if key == "modelnum" and vals:
                    p["body"]["model"] = int(_num(vals[0], -1))
                elif key == "offset":
                    p["body"]["offset"] = _vec(vals)
            elif sec == "spinner":
                if key == "modelnum" and vals:
                    p["spinner"]["model"] = int(_num(vals[0], -1))
                elif key == "offset":
                    p["spinner"]["offset"] = _vec(vals)
            elif sec == "wheel":
                w = p["wheels"].setdefault(idx, {})
                if key == "modelnum" and vals:
                    w["model"] = int(_num(vals[0], -1))
                elif key == "offset1":
                    w["offset"] = _vec(vals)
                elif key in ("ispresent", "isturnable"):
                    w[key] = _bool(vals)
                elif key == "steerratio" and vals:
                    w[key] = _num(vals[0])
    return p


# ---------------------------------------------------------------------------
# .obj and .bmp
# ---------------------------------------------------------------------------

def _obj_index(tok, count):
    """OBJ index (1-based, or negative from the end) -> 0-based, -1 if bad."""
    try:
        i = int(tok)
    except ValueError:
        return -1
    i = i - 1 if i > 0 else count + i
    return i if 0 <= i < count else -1


def _read_mtl(path):
    """Material name -> diffuse colour (0xRRGGBB) from a .mtl file."""
    mats = {}
    if not path:
        return mats
    name = None
    try:
        with open(path, "r") as f:
            for line in f:
                t = line.split()
                if len(t) >= 2 and t[0] == "newmtl":
                    name = t[1]
                    mats[name] = 0xFFFFFF
                elif len(t) >= 4 and t[0] == "Kd" and name is not None:
                    c = [min(255, max(0, int(_num(v) * 255 + 0.5))) for v in t[1:4]]
                    mats[name] = (c[0] << 16) | (c[1] << 8) | c[2]
    except OSError:
        pass
    return mats


def read_obj(path):
    """Read a Wavefront .obj into (polys, verts) for build_part.

    verts: (x, y, z, nx, ny, nz) in parameters.txt axes (Y down, +Z forward).
    polys: (flags, texture, 4 vertex indices, 4 ARGB colours, 4 UV pairs),
    clockwise; flags bit 0 = quad, bit 1 = two-sided, texture -1 = untextured.

    A face is textured when every corner has a UV. Its
    colour, for untextured faces, comes from the vertex colours
    ("v x y z r g b") or else the material's Kd. Faces with more than four
    corners are split into a fan of triangles.
    """
    if not path.lower().endswith(".obj"):
        raise ValueError("car models must be .obj files: " + path)
    folder = path.rsplit("/", 1)[0] if "/" in path else "."
    pos = []
    col = []
    nrm = []
    uvs = []
    faces = []
    mats = {}
    double = False
    kd = 0xFFFFFF
    with open(path, "r") as f:
        for line in f:
            t = line.split()
            if not t:
                continue
            k = t[0]
            if k == "v" and len(t) >= 4:
                pos.append((_num(t[1]), _num(t[2]), _num(t[3])))
                if len(t) >= 7:
                    c = [min(255, max(0, int(_num(v) * 255 + 0.5))) for v in t[4:7]]
                    col.append((c[0] << 16) | (c[1] << 8) | c[2])
                else:
                    col.append(-1)
            elif k == "vn" and len(t) >= 4:
                nrm.append((_num(t[1]), _num(t[2]), _num(t[3])))
            elif k == "vt" and len(t) >= 2:
                uvs.append((_num(t[1]), _num(t[2]) if len(t) > 2 else 0.0))
            elif k == "f" and len(t) >= 4:
                pi = []
                ti = []
                ni = []
                for corner in t[1:]:
                    s = corner.split("/")
                    pi.append(_obj_index(s[0], len(pos)))
                    ti.append(_obj_index(s[1], len(uvs)) if len(s) > 1 and s[1] else -1)
                    ni.append(_obj_index(s[2], len(nrm)) if len(s) > 2 and s[2] else -1)
                if min(pi) >= 0:
                    faces.append((pi, ti, ni, double, kd))
            elif k == "usemtl":
                name = t[1] if len(t) > 1 else ""
                double = "double" in name.lower()
                kd = mats.get(name, 0xFFFFFF)
            elif k == "mtllib" and len(t) > 1:
                mats.update(_read_mtl(find_file(folder, " ".join(t[1:]))))

    # one normal per position: the average of the normals its corners use
    acc = [[0.0, 0.0, 0.0] for _ in pos]
    for pi, ti, ni, _, _ in faces:
        for j in range(len(pi)):
            if ni[j] >= 0:
                a = acc[pi[j]]
                n = nrm[ni[j]]
                a[0] += n[0]
                a[1] += n[1]
                a[2] += n[2]
    verts = []
    for p, a in zip(pos, acc):
        length = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
        if length > 0:
            a = (a[0] / length, a[1] / length, a[2] / length)
        verts.append((p[0], -p[1], -p[2], a[0], -a[1], -a[2]))
    del pos, nrm, acc

    polys = []
    for pi, ti, ni, dbl, kd in faces:
        n = len(pi)
        pieces = [list(range(n))] if n <= 4 else [[0, j, j + 1] for j in range(1, n - 1)]
        for piece in pieces:
            piece.reverse()                 # OBJ counter-clockwise -> clockwise
            idx = [pi[j] for j in piece]
            textured = min(ti[j] for j in piece) >= 0
            colours = []
            uv = []
            for j in piece:
                c = col[pi[j]]
                colours.append(0xFF000000 | (c if c >= 0 else kd))
                if textured:
                    u, v = uvs[ti[j]]
                    uv += [u, 1.0 - v]
                else:
                    uv += [0.0, 0.0]
            while len(idx) < 4:
                idx.append(0)
                colours.append(0)
                uv += [0.0, 0.0]
            kind = (1 if len(piece) == 4 else 0) | (2 if dbl else 0)
            polys.append(tuple([kind, 0 if textured else -1] + idx + colours + uv))
    return polys, verts


class Texture:
    def __init__(self, path):
        with open(path, "rb") as f:
            d = f.read()
        if d[0:2] != b"BM":
            raise ValueError("not a BMP: " + path)
        self.data = d
        self.offset = struct.unpack_from("<I", d, 10)[0]
        dib = struct.unpack_from("<I", d, 14)[0]
        w, h = struct.unpack_from("<ii", d, 18)
        self.bpp = struct.unpack_from("<H", d, 28)[0]
        comp = struct.unpack_from("<I", d, 30)[0]
        if self.bpp not in (8, 24, 32) or comp not in (0, 3):
            raise ValueError("unsupported BMP format")
        self.w = w
        self.h = abs(h)
        self.bottom_up = h > 0
        self.stride = ((w * self.bpp + 31) // 32) * 4
        self.palette = 14 + dib

    def sample(self, u, v):
        x = int(u * self.w) % self.w
        y = int(v * self.h) % self.h
        if self.bottom_up:
            y = self.h - 1 - y
        d = self.data
        if self.bpp == 8:
            i = self.palette + d[self.offset + y * self.stride + x] * 4
        else:
            i = self.offset + y * self.stride + x * (self.bpp // 8)
        return d[i + 2], d[i + 1], d[i]


# ---------------------------------------------------------------------------
# Mesh building
# ---------------------------------------------------------------------------

def _face_colour(poly, n_idx, tex):
    tpage = poly[1]
    if tpage >= 0 and tex is not None:
        uv = poly[10:18]
        cu = 0.0
        cv = 0.0
        for k in range(n_idx):
            cu += uv[2 * k]
            cv += uv[2 * k + 1]
        cu /= n_idx
        cv /= n_idx
        samples = [tex.sample(cu, cv)]
        for k in range(n_idx):
            samples.append(tex.sample((uv[2 * k] + cu) * 0.5, (uv[2 * k + 1] + cv) * 0.5))
    else:
        samples = [((c >> 16) & 255, (c >> 8) & 255, c & 255) for c in poly[6:6 + n_idx]]
    n = len(samples)
    r = sum(s[0] for s in samples) // n
    g = sum(s[1] for s in samples) // n
    b = sum(s[2] for s in samples) // n
    return (r << 16) | (g << 8) | b


def build_part(polys, verts, scale, tex, budget):
    """Convert one mesh to a part: local verts in metres, Y up, shaded faces."""
    pos = [(v[0] * scale, -v[1] * scale, v[2] * scale) for v in verts]
    nrm = [(v[3], -v[4], v[5]) for v in verts]
    nv = len(pos)

    faces = []
    for poly in polys:
        quad = poly[0] & 1
        idx = poly[2:6] if quad else poly[2:5]
        if max(idx) >= nv:
            continue
        p0 = pos[idx[0]]
        p1 = pos[idx[1]]
        p2 = pos[idx[2]]
        if quad:
            p3 = pos[idx[3]]
            e1 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
            e2 = (p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2])
        else:
            e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length == 0:
            continue
        nx /= length
        ny /= length
        nz /= length
        # orient by the stored vertex normals, whatever the winding
        vx = sum(nrm[i][0] for i in idx)
        vy = sum(nrm[i][1] for i in idx)
        vz = sum(nrm[i][2] for i in idx)
        dot = nx * vx + ny * vy + nz * vz
        if dot < 0:
            nx, ny, nz = -nx, -ny, -nz
        double = bool(poly[0] & 2) or dot == 0
        rgb = shade(_face_colour(poly, len(idx), tex), nx, ny, nz, double)
        faces.append((length * 0.5, list(idx), nx, ny, nz, rgb, double))

    faces = [f for f in faces if f[0] >= MIN_FACE_AREA]
    if len(faces) > budget:
        faces.sort(key=lambda f: f[0], reverse=True)
        faces = faces[:budget]

    # keep only vertices that are still used
    remap = {}
    out_verts = []
    out_faces = []
    for _, idx, nx, ny, nz, rgb, double in faces:
        new = []
        for i in idx:
            if i not in remap:
                remap[i] = len(remap)
                out_verts.extend(pos[i])
            new.append(remap[i])
        out_faces.append([new, nx, ny, nz, rgb, 1 if double else 0])
    return {"verts": out_verts, "faces": out_faces, "polys": len(polys)}


def _top_end(params):
    """Top speed in mph, whichever unit the file uses."""
    v = params.get("topend") or 0.0
    if v > 200:
        v *= UNIT_TO_MPH
    if not 5 <= v <= 100:
        v = params.get("topspeed") or 0.0
    return v if 5 <= v <= 100 else None


def _model_path(folder, params, num):
    if num is None or num < 0:
        return None
    return find_file(folder, params["models"].get(num))


def load_car(folder, cache_path=None):
    params_path = find_file(folder, "parameters.txt")
    if params_path is None:
        raise OSError("no parameters.txt in " + folder)
    params = parse_parameters(params_path)

    body_path = _model_path(folder, params, params["body"].get("model", 0))
    if body_path is None:
        raise OSError("body model not found in " + folder)
    tex_path = find_file(folder, params.get("tpage"))

    wheels = []
    for i in sorted(params["wheels"]):
        w = params["wheels"][i]
        if w.get("ispresent", True) and "offset" in w:
            wheels.append((w, _model_path(folder, params, w.get("model", -1))))

    key = "%d|%s|%d|%d|%s" % (
        LOADER_VERSION, folder, file_size(params_path), file_size(body_path),
        ",".join(str(file_size(p)) for _, p in wheels if p))
    key += "|%d" % (file_size(tex_path) if tex_path else -1)
    key += "|%d" % file_size(_model_path(folder, params, params["spinner"].get("model", -1)) or "")

    if cache_path:
        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)
            if cached.get("key") == key:
                return cached
        except (OSError, ValueError):
            pass

    tex = None
    if tex_path and tex_path.lower().endswith(".bmp"):
        try:
            tex = Texture(tex_path)
        except (OSError, ValueError) as e:
            print("rc-simulator: texture skipped:", e)

    polys, verts = read_obj(body_path)
    zs = [v[2] for v in verts]
    length = (max(zs) - min(zs)) if zs else 0
    scale = CAR_LENGTH / length if length > 0 else 0.005

    parts = []
    body = build_part(polys, verts, scale, tex, BODY_BUDGET)
    off = params["body"].get("offset", [0.0, 0.0, 0.0])
    body["pivot"] = [off[0] * scale, -off[1] * scale, off[2] * scale]
    body["steer"] = 0.0
    parts.append(body)
    del polys, verts

    spin_path = _model_path(folder, params, params["spinner"].get("model", -1))
    if spin_path:
        polys, verts = read_obj(spin_path)
        extra = build_part(polys, verts, scale, tex, EXTRA_BUDGET)
        so = params["spinner"].get("offset", [0.0, 0.0, 0.0])
        extra["pivot"] = [(off[0] + so[0]) * scale, -(off[1] + so[1]) * scale,
                          (off[2] + so[2]) * scale]
        extra["steer"] = 0.0
        parts.append(extra)
        del polys, verts

    # steering: normalise SteerRatio so the front turnable wheels read +1
    turn = [w for w, _ in wheels if w.get("isturnable")]
    max_ratio = max([abs(w.get("steerratio", 0.0)) for w in turn] + [0.0])
    front_sign = 1.0
    if turn:
        front = max(turn, key=lambda w: w["offset"][2])
        front_sign = -1.0 if front.get("steerratio", 0.0) < 0 else 1.0

    for w, path in wheels:
        if path is None:
            continue
        polys, verts = read_obj(path)
        part = build_part(polys, verts, scale, tex, WHEEL_BUDGET)
        o = w["offset"]
        part["pivot"] = [o[0] * scale, -o[1] * scale, o[2] * scale]
        ratio = w.get("steerratio", 0.0)
        part["steer"] = (front_sign * ratio / max_ratio) if (w.get("isturnable") and max_ratio) else 0.0
        parts.append(part)
        del polys, verts
    tex = None

    # sit the lowest point of the car on the ground
    ymin = 0.0
    xs = []
    zs = []
    first = True
    for part in parts:
        px, py, pz = part["pivot"]
        v = part["verts"]
        for i in range(0, len(v), 3):
            y = v[i + 1] + py
            if first or y < ymin:
                ymin = y
                first = False
            xs.append(v[i] + px)
            zs.append(v[i + 2] + pz)
    for part in parts:
        part["pivot"][1] -= ymin

    # wheelbase from the turnable vs fixed wheels
    front_z = [w["offset"][2] for w, _ in wheels if w.get("isturnable")]
    rear_z = [w["offset"][2] for w, _ in wheels if not w.get("isturnable")]
    wheelbase = 0.0
    if front_z and rear_z:
        wheelbase = abs(sum(front_z) / len(front_z) - sum(rear_z) / len(rear_z)) * scale

    result = {
        "key": key,
        "name": params.get("name") or folder.rstrip("/").rsplit("/", 1)[-1] or "car",
        "tune": {
            "steer_rate": params.get("steerrate"),
            "steer_mod": params.get("steermod"),
            "engine_rate": params.get("enginerate"),
            "top_end": _top_end(params),
            "acc": params.get("acc"),
            "max_steer": max_ratio if turn else None,
            "wheelbase": wheelbase or None,
        },
        "shadow": [min(xs), max(xs), min(zs), max(zs)] if xs else [-0.2, 0.2, -0.25, 0.25],
        "parts": parts,
        "faces": sum(len(p["faces"]) for p in parts),
        "polys": sum(p["polys"] for p in parts),
    }

    if cache_path:
        try:
            with open(cache_path, "w") as f:
                json.dump(result, f)
        except OSError:
            pass
    return result
