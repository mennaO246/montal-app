"""محرك تصميم دواليب المطبخ (مونتال) — بدون أي اعتماد على واجهة."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple

EPS = 1e-6


@dataclass
class Rules:
    base_h: float = 90          # ارتفاع التحتاني
    base_d: float = 50          # عمق التحتاني
    base_d_appliance: float = 60  # عمق التحتاني لو فيه حوض/غسالة/تلاجة
    up_z: float = 150           # بداية العلوي من الأرض
    up_d: float = 38            # عمق العلوي
    up_main: float = 65         # ارتفاع العلوي
    up_stor: float = 25         # ارتفاع التخزين فوق العلوي
    ceiling: float = 245        # ارتفاع السقف
    single_min: float = 33      # أقل عرض لدرفة واحدة
    double_min: float = 65      # أقل عرض لدرفتين
    double_max: float = 75      # أقصى عرض لدرفتين
    corner: float = 70          # مقاس الركنة (ثابتة)

    @property
    def up_top(self) -> float:
        return self.up_z + self.up_main + self.up_stor


@dataclass
class Opening:
    kind: str            # 'door' | 'window'
    start: float
    width: float
    height: float
    sill: float = 0      # ارتفاع بداية الفتحة من الأرض (الباب = 0)

    @property
    def end(self): return self.start + self.width


@dataclass
class Wall:
    name: str
    length: float
    openings: List[Opening] = field(default_factory=list)
    corner_side: str = "none"      # 'left' | 'right' | 'none'
    storage: str = "all"           # 'all' | 'corner' | 'none'
    appliance: bool = False        # حوض/غسالة/تلاجة على الحيطة => عمق 60


@dataclass
class Unit:
    label: str
    x0: float
    w: float
    h: float
    d: float
    z0: float
    kind: str = "unit"      # 'unit' | 'corner' | 'storage'
    doors: int = 1
    has_storage: bool = False   # للعلوي: فوقه وحدة تخزين


@dataclass
class Void:
    x0: float
    w: float
    zone: str        # 'lower' | 'upper'
    reason: str


@dataclass
class WallLayout:
    wall: Wall
    lowers: List[Unit]
    uppers: List[Unit]          # العلوي الأساسي (التخزين مفصول في storages)
    storages: List[Unit]
    voids: List[Void]
    blocked_lower: List[Tuple[float, float, str]]
    blocked_upper: List[Tuple[float, float, str]]
    warnings: List[str]
    errors: List[str]
    checks: dict
    base_d: float


# ---------------------------------------------------------------- helpers
def _merge(iv):
    iv = sorted([(a, b) for a, b in iv if b - a > EPS])
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + EPS:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _free(length, blocked):
    free, cur = [], 0.0
    for a, b in _merge([(max(0, a), min(length, b)) for a, b in blocked]):
        if a - cur > EPS:
            free.append((cur, a))
        cur = max(cur, b)
    if length - cur > EPS:
        free.append((cur, length))
    return free


def _valid(x, r: Rules):
    return (r.single_min - EPS <= x < r.double_min - EPS) or (r.double_min - EPS <= x <= r.double_max + EPS)


def split_width(w: float, r: Rules) -> Optional[List[float]]:
    """أقل عدد وحدات بحيث كل وحدة ضمن حدود الدرف. يرجّع None لو مستحيل."""
    w = round(float(w), 2)
    if w < r.single_min - EPS:
        return None
    for n in range(1, int(w // r.single_min) + 1):
        if w / n > r.double_max + EPS:
            continue
        if float(w).is_integer():
            q, rem = divmod(int(w), n)
            parts = [float(q + 1)] * rem + [float(q)] * (n - rem)
        else:
            q = round(w / n, 1)
            parts = [q] * (n - 1) + [round(w - q * (n - 1), 1)]
        if all(_valid(p, r) for p in parts):
            return parts
    return None


def _doors_for(w, r):
    return 1 if w < r.double_min - EPS else 2


# ---------------------------------------------------------------- core
def build_wall(wall: Wall, r: Rules, number_from=(1, 1), corner_storage: Optional[bool] = None) -> WallLayout:
    L = wall.length
    c = r.corner
    warnings, errors = [], []
    base_d = r.base_d_appliance if wall.appliance else r.base_d
    if corner_storage is None:
        corner_storage = wall.storage != "none"

    corner_iv = None
    if wall.corner_side == "left":
        corner_iv = (0.0, c)
    elif wall.corner_side == "right":
        corner_iv = (L - c, L)
    if corner_iv and L < c:
        errors.append(f"الحيطة {wall.name}: طولها أقل من مقاس الركنة.")
        corner_iv = None

    lower_b, upper_b = [], []
    if corner_iv:
        lower_b.append((*corner_iv, "ركنة"))
        upper_b.append((*corner_iv, "ركنة"))

    for o in wall.openings:
        nm = "باب" if o.kind == "door" else "شباك"
        if o.start < -EPS or o.end > L + EPS:
            errors.append(f"الحيطة {wall.name}: {nm} خارج حدود الحيطة (من {o.start:g} إلى {o.end:g} والطول {L:g}).")
        if corner_iv and o.start < corner_iv[1] - EPS and o.end > corner_iv[0] + EPS:
            errors.append(f"الحيطة {wall.name}: {nm} ({o.start:g}–{o.end:g}) بيتداخل مع الركنة ({corner_iv[0]:g}–{corner_iv[1]:g}).")
        s, e = o.start, o.end
        top = o.sill + o.height
        if o.kind == "door":
            lower_b.append((s, e, "باب"))
            upper_b.append((s, e, "باب (ممنوع دولاب فوقه)"))
        else:
            if o.sill < r.base_h - EPS:
                lower_b.append((s, e, "شباك"))
            if o.sill < r.up_top - EPS and top > r.up_z + EPS:
                upper_b.append((s, e, "شباك (ممنوع دولاب قدامه)"))

    lowers, uppers, storages, voids = [], [], [], []
    li, ui = number_from

    def place(zone, blocked):
        nonlocal li, ui
        for a, b in _free(L, [(x, y) for x, y, _ in blocked]):
            w = round(b - a, 2)
            parts = split_width(w, r)
            if parts is None:
                voids.append(Void(a, w, zone, f"عرض {w:g} سم أقل من {r.single_min:g} (أقل مقاس درفة) — مستحيل تنفيذ وحدة بدون فيلر"))
                continue
            x = a
            for p in parts:
                if zone == "lower":
                    lowers.append(Unit(f"L{li}", x, p, r.base_h, base_d, 0, "unit", _doors_for(p, r)))
                    li += 1
                else:
                    st = wall.storage == "all"
                    u = Unit(f"U{ui}", x, p, r.up_main, r.up_d, r.up_z, "unit", _doors_for(p, r), st)
                    uppers.append(u)
                    if st:
                        storages.append(Unit(f"S{ui}", x, p, r.up_stor, r.up_d, r.up_z + r.up_main, "storage", _doors_for(p, r)))
                    ui += 1
                x += p

    place("lower", lower_b)
    place("upper", upper_b)

    if corner_iv:
        lowers.append(Unit("L-CORNER", corner_iv[0], c, r.base_h, c, 0, "corner", 1))
        uppers.append(Unit("U-CORNER", corner_iv[0], c, r.up_main, r.up_d, r.up_z, "corner", 1, corner_storage))
        if corner_storage:
            storages.append(Unit("S-CORNER", corner_iv[0], c, r.up_stor, r.up_d, r.up_z + r.up_main, "storage", 1))
    lowers.sort(key=lambda u: u.x0); uppers.sort(key=lambda u: u.x0); storages.sort(key=lambda u: u.x0)

    # --- التحقق الحسابي
    def covered(units, blocked, vs):
        u = sum(x.w for x in units)
        bl = [(a, b) for a, b, n in blocked if n != "ركنة"]
        bl = _merge([(max(0, a), min(L, b)) for a, b in bl])
        # ما نحسبش مرتين: المحجوب اللي جوه الركنة اتشال أصلاً بالتحقق من التداخل
        b = sum(y - x for x, y in bl)
        return u, b, sum(v.w for v in vs)

    checks = {}
    for zone, units, blocked in (("lower", lowers, lower_b), ("upper", uppers, upper_b)):
        vs = [v for v in voids if v.zone == zone]
        u, b, v = covered(units, blocked, vs)
        diff = round(L - (u + b + v), 4)
        checks[zone] = dict(units=u, blocked=b, voids=v, wall=L, diff=diff, ok=abs(diff) < 1e-3 and v < EPS)

    for v in voids:
        zn = "التحتاني" if v.zone == "lower" else "العلوي"
        warnings.append(f"الحيطة {wall.name} ({zn}): فراغ {v.w:g} سم من {v.x0:g} لحد {v.x0 + v.w:g} — {v.reason}. "
                        f"الحل: تحريك الفتحة/الركنة المجاورة {r.single_min - v.w:g} سم على الأقل، أو تعديل مكانها.")
    return WallLayout(wall, lowers, uppers, storages, voids, lower_b, upper_b, warnings, errors, checks, base_d)


@dataclass
class Project:
    name: str
    shape: str                 # 'L' | 'straight'
    walls: List[Wall]
    rules: Rules = field(default_factory=Rules)


def build_project(p: Project):
    errors, notes = [], []
    if p.shape == "L":
        if len(p.walls) != 2:
            errors.append("شكل L محتاج حيطتين.")
        elif any(w.corner_side == "none" for w in p.walls):
            errors.append("في شكل L لازم تحددي مكان الركنة في الحيطتين.")
    corner_storage = None
    if p.shape == "L":
        corner_storage = any(w.storage != "none" for w in p.walls)
    layouts, li, ui = [], 1, 1
    for w in p.walls:
        lay = build_wall(w, p.rules, (li, ui), corner_storage)
        li = li + sum(1 for x in lay.lowers if x.kind == "unit")
        ui = ui + sum(1 for x in lay.uppers if x.kind == "unit")
        layouts.append(lay)
    for lay in layouts:
        errors += lay.errors
    if p.shape == "L" and len(layouts) == 2 and not errors:
        d = layouts[0].base_d
        if d > p.rules.corner + EPS or layouts[1].base_d > p.rules.corner + EPS:
            notes.append("عمق التحتاني أكبر من مقاس الركنة — راجعي الركنة.")
        notes.append("الركنة الثابتة 70×70 مع عمق التحتاني 50 بيظهر منها حوالي "
                     f"{p.rules.corner - layouts[0].base_d:g} سم بس من كل ناحية — الوصول لجوّاها محدود.")
    return layouts, errors, notes


def summary(p: Project, layouts: List[WallLayout]):
    seen_corner = False
    lowers = []; uppers = []; stors = []; corners_l = 0; corners_u = 0
    for lay in layouts:
        for u in lay.lowers:
            if u.kind == "corner":
                if p.shape == "L" and seen_corner: continue
                corners_l += 1
            lowers.append(u)
        for u in lay.uppers:
            if u.kind == "corner":
                if p.shape == "L" and seen_corner: continue
                corners_u += 1
            uppers.append(u)
        for u in lay.storages:
            if u.kind == "storage" and u.label == "S-CORNER" and p.shape == "L" and seen_corner: continue
            stors.append(u)
        if any(u.kind == "corner" for u in lay.lowers): seen_corner = True
    return dict(lowers=lowers, uppers=uppers, storages=stors, corners=corners_l,
                total=len(lowers) + len(uppers) + len(stors))


# ---------------------------------------------------------------- save / load
def project_to_dict(p: Project):
    return dict(name=p.name, shape=p.shape, rules=asdict(p.rules),
                walls=[dict(name=w.name, length=w.length, corner_side=w.corner_side, storage=w.storage,
                            appliance=w.appliance, openings=[asdict(o) for o in w.openings]) for w in p.walls])


def project_from_dict(d) -> Project:
    walls = [Wall(w["name"], w["length"], [Opening(**o) for o in w.get("openings", [])],
                  w.get("corner_side", "none"), w.get("storage", "all"), w.get("appliance", False))
             for w in d["walls"]]
    return Project(d.get("name", ""), d.get("shape", "L"), walls, Rules(**d.get("rules", {})))


def ayman_project() -> Project:
    return Project("أيمن", "L", [
        Wall("A", 345, [Opening("door", 0, 90, 90, 0)], "right", "all"),
        Wall("B", 165, [Opening("window", 70, 65, 75, 135)], "left", "corner"),
    ])
