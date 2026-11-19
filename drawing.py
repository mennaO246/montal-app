"""رسم الواجهات 2D والمنظور 3D (SVG) من نتيجة المحرك."""
import math, re
from layout import Rules, WallLayout, EPS

FONT = 'font-family="Tahoma, Arial, sans-serif"'


def _fs(svg, k):
    """تكبير كل الخطوط في الـSVG (للموبايل)."""
    if abs(k - 1) < 1e-9:
        return svg
    return re.sub(r'font-size="([\d.]+)"', lambda m: f'font-size="{float(m.group(1))*k:g}"', svg)


def _n(x):
    return f"{x:g}"


# ====================================================================== 2D
def elevation_svg(lay: WallLayout, r: Rules, scale=3.0, fs=1.0) -> str:
    w = lay.wall
    L, CEIL = w.length, r.ceiling
    S = scale
    M = int(40 + 34 * fs)
    ML = int(40 + 52 * fs)
    W = int(L * S + ML + 70); H = int(CEIL * S + M + 50 + 34 * fs)
    X = lambda x: ML + x * S
    Y = lambda z: M + (CEIL - z) * S
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" {FONT} direction="ltr">',
         '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse"><path d="M0,1 L8,4 L0,7 Z" fill="#333"/></marker>'
         '<pattern id="h" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="#c0392b"/></pattern></defs>',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{W/2}" y="{18+22*fs:.0f}" text-anchor="middle" font-size="18" font-weight="bold">الحيطة {w.name} — {_n(L)} سم</text>',
         f'<rect x="{X(0)}" y="{Y(CEIL)}" width="{L*S}" height="{CEIL*S}" fill="#faf7f0" stroke="#000" stroke-width="2"/>',
         f'<line x1="{X(0)-10}" y1="{Y(0)}" x2="{X(L)+10}" y2="{Y(0)}" stroke="#000" stroke-width="3"/>']

    def dim_v(x, z0, z1, txt, xoff=0, color="#333"):
        xx = X(x) + xoff
        o.append(f'<line x1="{xx}" y1="{Y(z0)}" x2="{xx}" y2="{Y(z1)}" stroke="{color}" marker-start="url(#a)" marker-end="url(#a)"/>')
        mid = (Y(z0) + Y(z1)) / 2
        o.append(f'<text x="{xx-4}" y="{mid}" text-anchor="middle" font-size="11" fill="{color}" transform="rotate(-90 {xx-4} {mid})">{txt}</text>')

    for op in w.openings:
        top = op.sill + op.height
        o.append(f'<rect x="{X(op.start)}" y="{Y(top)}" width="{op.width*S}" height="{op.height*S}" fill="#d6eaf8" stroke="#1b4f72" stroke-width="2"/>')
        cx, cy = X(op.start + op.width / 2), Y(op.sill + op.height / 2)
        nm = "باب" if op.kind == "door" else "شباك"
        if op.kind == "window":
            o.append(f'<line x1="{X(op.start)}" y1="{Y(top)}" x2="{X(op.end)}" y2="{Y(op.sill)}" stroke="#1b4f72"/><line x1="{X(op.end)}" y1="{Y(top)}" x2="{X(op.start)}" y2="{Y(op.sill)}" stroke="#1b4f72"/>')
        o.append(f'<text x="{cx}" y="{cy-3*fs:.1f}" text-anchor="middle" font-size="12" fill="#1b4f72" style="paint-order:stroke;stroke:#d6eaf8;stroke-width:3px">{nm} {_n(op.width)}×{_n(op.height)}</text>')
        o.append(f'<text x="{cx}" y="{cy+12*fs:.1f}" text-anchor="middle" font-size="11" fill="#1b4f72" style="paint-order:stroke;stroke:#d6eaf8;stroke-width:3px">{('من الأرض ' + _n(op.sill)) if op.sill > 0 else ('يبدأ ' + _n(op.start))}</text>')
        if op.sill > 0:
            dim_v(op.end, 0, op.sill, f'{_n(op.sill)}', xoff=16 * fs, color="#1b4f72")
        if op.kind == "door":
            o.append(f'<text x="{cx}" y="{Y(top)-6}" text-anchor="middle" font-size="11" fill="#c0392b">لا دولاب فوق الباب</text>')

    for v in lay.voids:
        z0, z1 = (0, r.base_h) if v.zone == "lower" else (r.up_z, r.up_top)
        o.append(f'<rect x="{X(v.x0)}" y="{Y(z1)}" width="{v.w*S}" height="{(z1-z0)*S}" fill="url(#h)" stroke="#c0392b" stroke-dasharray="4"/>')
        cx, cy = X(v.x0 + v.w / 2), Y((z0 + z1) / 2)
        o.append(f'<text x="{cx}" y="{cy}" text-anchor="middle" font-size="11" fill="#c0392b" style="paint-order:stroke;stroke:#fff;stroke-width:3px">فراغ {_n(v.w)}</text>')

    def cab(u, z0, h, fill, label=None):
        corner = u.kind == "corner"
        o.append(f'<rect x="{X(u.x0)}" y="{Y(z0+h)}" width="{u.w*S}" height="{h*S}" fill="{"#f5cba7" if corner else fill}" stroke="#6e2c00" stroke-width="2"/>')
        if not corner:
            for i in range(1, u.doors):
                xx = X(u.x0) + u.w * S * i / u.doors
                o.append(f'<line x1="{xx}" y1="{Y(z0+h)}" x2="{xx}" y2="{Y(z0)}" stroke="#6e2c00"/>')
        cx, cy = X(u.x0 + u.w / 2), Y(z0 + h / 2)
        lab = label or u.label
        if h >= 40:
            o.append(f'<text x="{cx}" y="{cy-2*fs:.1f}" text-anchor="middle" font-size="12" font-weight="bold" fill="#3b1a00">{lab}</text>')
            o.append(f'<text x="{cx}" y="{cy+12*fs:.1f}" text-anchor="middle" font-size="11">{_n(u.w)}×{_n(h)}×{_n(u.d)}</text>')
            if corner:
                o.append(f'<text x="{cx}" y="{cy+26*fs:.1f}" text-anchor="middle" font-size="10" fill="#6e2c00">ركنة ثابتة</text>')
        else:
            o.append(f'<text x="{cx}" y="{cy+3.5*fs:.1f}" text-anchor="middle" font-size="10">{lab} {_n(u.w)}×{_n(h)}</text>')

    for u in lay.lowers: cab(u, 0, r.base_h, "#fdebd0")
    for u in lay.uppers: cab(u, r.up_z, r.up_main, "#fdebd0")
    for u in lay.storages: cab(u, u.z0, r.up_stor, "#fef5e7")

    yb = Y(0) + 12 + 14 * fs
    for u in lay.lowers:
        o.append(f'<line x1="{X(u.x0)}" y1="{yb}" x2="{X(u.x0+u.w)}" y2="{yb}" stroke="#333" marker-start="url(#a)" marker-end="url(#a)"/><text x="{X(u.x0+u.w/2)}" y="{yb-3}" text-anchor="middle" font-size="11">{_n(u.w)}</text>')
    yb2 = yb + 12 + 15 * fs
    o.append(f'<line x1="{X(0)}" y1="{yb2}" x2="{X(L)}" y2="{yb2}" stroke="#000" stroke-width="1.5" marker-start="url(#a)" marker-end="url(#a)"/><text x="{X(L/2)}" y="{yb2-4}" text-anchor="middle" font-size="13" font-weight="bold">الطول الكلي {_n(L)} سم</text>')
    dim_v(0, 0, r.base_h, _n(r.base_h), -14 * fs)
    dim_v(0, r.up_z, r.up_z + r.up_main, _n(r.up_main), -14 * fs)
    dim_v(0, r.up_z + r.up_main, r.up_top, _n(r.up_stor), -14 * fs)
    dim_v(0, 0, r.up_z, f'{_n(r.up_z)} من الأرض', -34 * fs)
    dim_v(0, 0, r.ceiling, f'سقف {_n(r.ceiling)}', -52 * fs)
    o.append('</svg>')
    return _fs("\n".join(o), fs)


# ====================================================================== 3D
def iso_svg(layouts, r: Rules, shape="L", S=3.0, fs=1.0) -> str:
    c30, s30 = math.cos(math.radians(30)), 0.5
    A = layouts[0]; B = layouts[1] if (shape == "L" and len(layouts) > 1) else None
    LA = A.wall.length; LB = B.wall.length if B else 90
    CEIL = r.ceiling
    OX = 110 + LA * c30 * S
    W = int(OX + LB * c30 * S + 240); H = int(CEIL * S + (LA + LB) * s30 * S + 190); OY = 95

    def P(u, v, z):
        return (OX + (v - u) * c30 * S, OY + (u + v) * s30 * S - z * S + CEIL * S)

    def uA(x): return LA - x if A.wall.corner_side == "right" else x
    def vB(x): return LB - x if (B and B.wall.corner_side == "right") else x
    def rng(f, a, b):
        p, q = f(a), f(b); return (min(p, q), max(p, q))

    def pts(*ps): return " ".join(f"{x:.1f},{y:.1f}" for x, y in ps)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" {FONT}>',
         '<defs><pattern id="h" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="#c0392b"/></pattern></defs>',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{W/2}" y="30" text-anchor="middle" font-size="20" font-weight="bold">منظور ثلاثي الأبعاد (الأبعاد: عرض × ارتفاع × عمق بالسم)</text>']

    def poly(ps, fill, stroke="#555", sw=1, extra=""):
        o.append(f'<polygon points="{pts(*ps)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')

    poly([P(0, 0, 0), P(LA, 0, 0), P(LA, LB, 0), P(0, LB, 0)], "#ececec", "#999")
    poly([P(0, 0, 0), P(LA, 0, 0), P(LA, 0, CEIL), P(0, 0, CEIL)], "#faf6ee", "#333", 2)
    if B:
        poly([P(0, 0, 0), P(0, LB, 0), P(0, LB, CEIL), P(0, 0, CEIL)], "#f3efe6", "#333", 2)

    def label(x, y, t, fs=12, fill="#1b4f72"):
        o.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="{fs}" fill="{fill}" style="paint-order:stroke;stroke:#fff;stroke-width:3px">{t}</text>')

    # فتحات وفراغات على الحيطة A (v=0) والحيطة B (u=0)
    def wall_items(lay, plane):
        for op in lay.wall.openings:
            a, b = rng(uA if plane == "A" else vB, op.start, op.end)
            z0, z1 = op.sill, op.sill + op.height
            q = [(a, z0), (b, z0), (b, z1), (a, z1)]
            ps = [P(x, 0, z) if plane == "A" else P(0, x, z) for x, z in q]
            poly(ps, "#d6eaf8", "#1b4f72", 2)
            cx, cy = P((a + b) / 2, 0, (z0 + z1) / 2) if plane == "A" else P(0, (a + b) / 2, (z0 + z1) / 2)
            label(cx, cy - 3 * fs, "باب" if op.kind == "door" else "شباك")
            label(cx, cy + 12 * fs, f"{_n(op.width)}×{_n(op.height)}")
        for v in lay.voids:
            a, b = rng(uA if plane == "A" else vB, v.x0, v.x0 + v.w)
            z0, z1 = (0, r.base_h) if v.zone == "lower" else (r.up_z, r.up_top)
            q = [(a, z0), (b, z0), (b, z1), (a, z1)]
            ps = [P(x, 0, z) if plane == "A" else P(0, x, z) for x, z in q]
            poly(ps, "url(#h)", "#c0392b", 1, 'stroke-dasharray="4"')
            cx, cy = P((a + b) / 2, 0, (z0 + z1) / 2) if plane == "A" else P(0, (a + b) / 2, (z0 + z1) / 2)
            label(cx, cy, f"فراغ {_n(v.w)}", 11, "#c0392b")

    wall_items(A, "A")
    if B: wall_items(B, "B")

    boxes = []
    def add(u0, u1, v0, v1, z0, z1, lab, front, nd, col, corner=False, dims=None):
        boxes.append(dict(u0=u0, u1=u1, v0=v0, v1=v1, z0=z0, z1=z1, label=lab, front=front, nd=nd, col=col, corner=corner, dims=dims))

    dA = A.base_d; dB = B.base_d if B else 0
    for u in A.lowers:
        if u.kind == "corner": continue
        a, b = rng(uA, u.x0, u.x0 + u.w)
        add(a, b, 0, dA, 0, r.base_h, u.label, "v", u.doors, "#f6d9b0", dims=(u.w, r.base_h, dA))
    for u in A.uppers:
        if u.kind == "corner": continue
        a, b = rng(uA, u.x0, u.x0 + u.w)
        add(a, b, 0, r.up_d, r.up_z, r.up_z + r.up_main, u.label, "v", u.doors, "#f6d9b0", dims=(u.w, r.up_main, r.up_d))
    for u in A.storages:
        if u.kind == "corner": continue
        a, b = rng(uA, u.x0, u.x0 + u.w)
        add(a, b, 0, r.up_d, u.z0, u.z0 + r.up_stor, u.label, "v", u.doors, "#fbeed8", dims=(u.w, r.up_stor, r.up_d))
    if B:
        for u in B.lowers:
            if u.kind == "corner": continue
            a, b = rng(vB, u.x0, u.x0 + u.w)
            add(0, dB, a, b, 0, r.base_h, u.label, "u", u.doors, "#f6d9b0", dims=(u.w, r.base_h, dB))
        for u in B.uppers:
            if u.kind == "corner": continue
            a, b = rng(vB, u.x0, u.x0 + u.w)
            add(0, r.up_d, a, b, r.up_z, r.up_z + r.up_main, u.label, "u", u.doors, "#f6d9b0", dims=(u.w, r.up_main, r.up_d))
        for u in B.storages:
            if u.kind == "corner": continue
            a, b = rng(vB, u.x0, u.x0 + u.w)
            add(0, r.up_d, a, b, u.z0, u.z0 + r.up_stor, u.label, "u", u.doors, "#fbeed8", dims=(u.w, r.up_stor, r.up_d))
    # الركنة على شكل L
    c = r.corner
    has_corner = any(u.kind == "corner" for u in A.lowers) and B is not None
    corner_stor = any(u.kind == "storage" and u.label == "S-CORNER" for u in A.storages + (B.storages if B else []))
    if has_corner:
        add(0, c, 0, dA, 0, r.base_h, "", "v", 1, "#eab27c", True)
        add(0, dA, dA, c, 0, r.base_h, "", "u", 1, "#eab27c", True)
        add(0, c, 0, r.up_d, r.up_z, r.up_z + r.up_main, "", "v", 1, "#eab27c", True)
        add(0, r.up_d, r.up_d, c, r.up_z, r.up_z + r.up_main, "", "u", 1, "#eab27c", True)
        if corner_stor:
            add(0, c, 0, r.up_d, r.up_z + r.up_main, r.up_top, "", "v", 1, "#f2c9a1", True)
            add(0, r.up_d, r.up_d, c, r.up_z + r.up_main, r.up_top, "", "u", 1, "#f2c9a1", True)
    elif any(u.kind == "corner" for u in A.lowers):   # ركنة بدون حيطة تانية: صندوق عادي
        a, b = rng(uA, *[(u.x0, u.x0 + u.w) for u in A.lowers if u.kind == "corner"][0])
        add(a, b, 0, dA, 0, r.base_h, "ركنة", "v", 1, "#eab27c", True, (c, r.base_h, dA))

    def shade(h, f):
        rr, g, b = [int(h[i:i + 2], 16) for i in (1, 3, 5)]
        return "#%02x%02x%02x" % tuple(int(min(255, k * f)) for k in (rr, g, b))

    boxes.sort(key=lambda b: (b["u0"] + b["v0"], b["z0"]))
    for b in boxes:
        u0, u1, v0, v1, z0, z1, col = b["u0"], b["u1"], b["v0"], b["v1"], b["z0"], b["z1"], b["col"]
        poly([P(u0, v0, z1), P(u1, v0, z1), P(u1, v1, z1), P(u0, v1, z1)], shade(col, 1.04), "#6e2c00", 1.2)
        poly([P(u1, v0, z0), P(u1, v1, z0), P(u1, v1, z1), P(u1, v0, z1)], shade(col, 0.82 if b["front"] == "v" else 1.0), "#6e2c00", 1.2)
        poly([P(u0, v1, z0), P(u1, v1, z0), P(u1, v1, z1), P(u0, v1, z1)], shade(col, 1.0 if b["front"] == "v" else 0.82), "#6e2c00", 1.2)
        for i in range(1, b["nd"] if not b["corner"] else 1):
            if b["front"] == "v":
                uu = u0 + (u1 - u0) * i / b["nd"]; p, q = P(uu, v1, z0), P(uu, v1, z1)
            else:
                vv = v0 + (v1 - v0) * i / b["nd"]; p, q = P(u1, vv, z0), P(u1, vv, z1)
            o.append(f'<line x1="{p[0]:.1f}" y1="{p[1]:.1f}" x2="{q[0]:.1f}" y2="{q[1]:.1f}" stroke="#6e2c00"/>')
        if b["label"] and b["dims"]:
            cx, cy = P((u0 + u1) / 2, v1, (z0 + z1) / 2) if b["front"] == "v" else P(u1, (v0 + v1) / 2, (z0 + z1) / 2)
            wd, h, d = b["dims"]; ds = f"{_n(wd)}×{_n(h)}×{_n(d)}"
            if h >= 40:
                label(cx, cy - 2 * fs, b["label"], 11, "#3b1a00"); label(cx, cy + 12 * fs, ds, 11, "#222")
            else:
                label(cx, cy + 3 * fs, f'{b["label"]} {ds}', 9, "#222")
    if has_corner:
        x, y = P(c / 2, c / 2, r.base_h); label(x, y - 2 * fs, "ركنة ثابتة سفلي", 12, "#3b1a00"); label(x, y + 12 * fs, f"{_n(c)}×{_n(r.base_h)}×{_n(c)}", 11, "#3b1a00")
        top = r.up_top if corner_stor else r.up_z + r.up_main
        x, y = P(c / 2, c / 2 - 10, top); label(x, y - 2 * fs, "ركنة علوي", 12, "#3b1a00"); label(x, y + 12 * fs, f"{_n(c)}×{_n(r.up_main + (r.up_stor if corner_stor else 0))}×{_n(r.up_d)}", 11, "#3b1a00")

    def dline(a, b, txt, off):
        (x1, y1), (x2, y2) = a, b
        o.append(f'<line x1="{x1:.1f}" y1="{y1+off:.1f}" x2="{x2:.1f}" y2="{y2+off:.1f}" stroke="#c0392b" stroke-width="1.5"/>')
        for x, y in ((x1, y1), (x2, y2)):
            o.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y+off:.1f}" stroke="#c0392b" stroke-dasharray="3"/>')
        label((x1 + x2) / 2, (y1 + y2) / 2 + off - 6, txt, 14, "#c0392b")
    dline(P(0, 0, CEIL), P(LA, 0, CEIL), f"طول {A.wall.name} = {_n(LA)}", -26)
    if B: dline(P(0, 0, CEIL), P(0, LB, CEIL), f"طول {B.wall.name} = {_n(LB)}", -26)

    def vline(u, v, z0, z1, txt, dx):
        a, b = P(u, v, z0), P(u, v, z1)
        o.append(f'<line x1="{a[0]+dx:.1f}" y1="{a[1]:.1f}" x2="{b[0]+dx:.1f}" y2="{b[1]:.1f}" stroke="#1a5276" stroke-width="1.5"/>')
        for p in (a, b):
            o.append(f'<line x1="{p[0]:.1f}" y1="{p[1]:.1f}" x2="{p[0]+dx:.1f}" y2="{p[1]:.1f}" stroke="#1a5276" stroke-dasharray="3"/>')
        o.append(f'<text x="{a[0]+dx+(-4 if dx<0 else 4):.1f}" y="{(a[1]+b[1])/2:.1f}" text-anchor="{"end" if dx<0 else "start"}" font-size="13" font-weight="bold" fill="#1a5276" style="paint-order:stroke;stroke:#fff;stroke-width:4px">{txt}</text>')
    vline(LA, 0, 0, CEIL, f"سقف {_n(CEIL)}", -30)
    ve = LB
    vline(0, ve, 0, r.base_h, f"تحتاني {_n(r.base_h)}", 36)
    vline(0, ve, 0, r.up_z, f"{_n(r.up_z)} من الأرض", 100)
    vline(0, ve, r.up_z, r.up_z + r.up_main, f"علوي {_n(r.up_main)}", 36)
    vline(0, ve, r.up_z + r.up_main, r.up_top, f"تخزين {_n(r.up_stor)}", 36)
    o.append('</svg>')
    return _fs("\n".join(o), fs)
