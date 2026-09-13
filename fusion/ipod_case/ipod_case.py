# -*- coding: utf-8 -*-
"""
iPod Classic case - parametric generator for Autodesk Fusion.

HOW TO RUN
  Fusion -> Utilities tab -> Add-Ins -> "Scripts and Add-Ins" -> Scripts tab
  -> "+" button -> point it at the FOLDER  fusion/ipod_case  -> pick
  "ipod_case" from the list -> Run.

AFTER RUNNING
  Modify -> Change Parameters. The plate and frame extrusions, the pocket
  depths and the rear pocket's rim are wired to the User Parameters, so
  changing "rear_t" or "hex_depth" rebuilds those features.
  Everything else is drawn from coordinates the script computes from the
  constants below when it runs: the outline, the side bevels, the rear pocket's
  floor bevel and the corner entrances. To change those, edit the constants
  and run the script again. The sketches carry no dimensions of their own.

SAME MODEL AS THE STLs
  This builds the same three parts as generate_case.py, which writes the STLs,
  with the same dimensions and derivations: the thin waist with a pad at each
  corner screw, a bevel along each side of both plates between the pads, the
  rear plate's pocket with its rim and floor edge bevelled, and nut pockets
  and counterbores that open to their corner through a flat entrance.
  Keep the two scripts in step: a change to one needs the same change in the
  other. The only intended difference is that Fusion keeps arcs and circles
  exact, where the STLs are tessellated.
"""

import adsk.core, adsk.fusion, traceback, math

MM = 0.1                                    # the API works in centimetres
def V(e):            return adsk.core.ValueInput.createByString(str(e))
def P3(x, y, z=0.0): return adsk.core.Point3D.create(x*MM, y*MM, z*MM)
def mm(v):           return '{:.4f} mm'.format(v)

# ------------------------------------------------------------ user parameters
PARAMS = [
    ('width',        '76.8 mm',   'outer width'),
    ('height',       '110.2 mm',  'outer height'),
    ('corner_r',     '7.5 mm',    'plan-view corner radius'),
    ('screw_d',      '3.15 mm',   'M3 clearance hole'),
    ('face_t',      '3.501 mm',  'face plate thickness'),
    ('counterbore_depth',   '2.501 mm',  'screw head counterbore depth'),
    ('frame_t',     '14 mm',     'frame thickness'),
    ('rear_t',      '5 mm',      'rear plate thickness'),
    ('hex_depth',       '2.5 mm',    'nut pocket depth'),
]

# ------------------------------------------------------------------ geometry
# The cavity is sized to the iPod; the outer height follows from it plus the
# end walls, and everything positioned against the iPod is measured from the
# cavity floor. Same derivation as generate_case.py.
CAVITY_W, CAVITY_H, CAVITY_R = 62.2, 104.2, 6.0
WALL_TOP, WALL_BOTTOM        = 3.0, 3.0          # bottom was 5.0 originally
W, RC = 76.8, 7.5
H     = CAVITY_H + WALL_TOP + WALL_BOTTOM        # 110.2

# Thin waist: the side walls are WALL_SIDE thick between the corners, and a
# pad restores the full W x H corner within PAD_R of each corner arc's centre,
# where the screws need it. Same as outer_profile() in generate_case.py.
WALL_SIDE = 3.0
W_THIN    = CAVITY_W + 2*WALL_SIDE               # 68.2
PAD_R     = 9.5
PAD_CENTERS = [(RC, RC), (W - RC, RC), (RC, H - RC), (W - RC, H - RC)]

SCREW_D        = 3.15
SCREW_EDGE_X, SCREW_EDGE_Y = 5.00, 4.50
SCREWS = [(SCREW_EDGE_X, SCREW_EDGE_Y), (W - SCREW_EDGE_X, SCREW_EDGE_Y),
          (SCREW_EDGE_X, H - SCREW_EDGE_Y), (W - SCREW_EDGE_X, H - SCREW_EDGE_Y)]

# Rear plate pocket, clear of the 4 hex nut pockets. Same derivation and floor
# thickness as generate_case.py.
REAR_POCKET_KEEP,  REAR_POCKET_CLEAR, REAR_POCKET_R      = 2.50, 3.00, 4.00

# Bevel along each side edge of both plates' outer face, between the corner
# pads only: 2.324 mm in for every mm down, 0.83 mm down. The rear pocket's rim
# and floor edge get the same bevel.
SIDE_BEVEL_SLOPE, SIDE_BEVEL_H = 2.324, 0.83
REAR_POCKET_BEVEL_SLOPE, REAR_POCKET_BEVEL_H = SIDE_BEVEL_SLOPE, SIDE_BEVEL_H

FACE_T = 3.501
COUNTERBORE_D, COUNTERBORE_DEPTH           = 6.0, 2.501
SCREEN  = dict(w=51.518, h=39.922, r=2.378, cx=38.40, cy=WALL_BOTTOM + 79.35, ch_z=1.189, off=1.4805)
WHEEL = dict(d=37.99, cx=38.40, cy=WALL_BOTTOM + 31.00, ch_z=0.884, d_out=50.14)

FRAME_T = 14.0
CAVITY     = dict(w=CAVITY_W, h=CAVITY_H, r=CAVITY_R, cx=W / 2.0, cy=WALL_BOTTOM + CAVITY_H / 2.0)
JACK    = dict(d=10.0, x=61.743, z=7.29)
DOCK    = dict(w=28.83, h=7.94, r=2.0, x=38.40, z=7.70)
HOLD    = dict(w=14.0, h=5.0, r=1.5, x=21.84, z=8.29)   # 12.5 x 3.3 switch plus clearance; x and z set by test prints

# Wall openings flare from the cavity outwards with the same slope as the
# screen window chamfer. Each setback is the largest the surroundings allow
# while keeping 1.10 mm of material to the frame edge -- the jack is the
# limiter, because a 10 mm hole in a 14 mm frame leaves only 1.71 mm above it.
CHAMFER_SLOPE = 0.6403
JACK_CHAMF, DOCK_CHAMF, HOLD_CHAMF = 0.60, 1.20, 1.20

REAR_T = 5.0
HEX_AF, HEX_DEPTH                    = 5.846, 2.5

# Any wall between a nut pocket or counterbore and the corner thinner than
# this is cut away down to the pocket's floor (see corner_entrance()).
CORNER_WEB_MIN = 1.30

WALL_TOP_Y = CAVITY['cy'] + CAVITY['h']/2.0     # 107.2
WALL_BOT_Y = CAVITY['cy'] - CAVITY['h']/2.0     # 3.0


# ---------------------------------------------------- plan-view geometry (mm)
# Pure geometry, no Fusion calls: these return coordinates for the sketches.

def outline_segments():
    """Waisted outer outline shared by all three parts, counter-clockwise, as
    ('line', start, end) and ('arc', centre, start, sweep_radians) items.

    Each corner is the W x H rounded rectangle's own corner, cut back to the
    pad disc: along each outer edge, the R RC corner arc, a short straight run
    to where the disc crosses the edge, then the disc's R PAD_R arc in to the
    W_THIN waist edge."""
    x_w = (W - W_THIN) / 2.0                       # waist inset from each side
    if PAD_R**2 < RC**2 + x_w**2:
        raise ValueError('PAD_R too small: the pads no longer cover the '
                         'waist\'s own corners, which notches the outline')
    e = math.sqrt(PAD_R**2 - RC**2)                # disc crosses the outer edge
    d = math.sqrt(PAD_R**2 - (RC - x_w)**2)        # disc meets the waist edge
    a_edge, a_waist = math.atan2(e, RC), math.atan2(d, RC - x_w)
    pad_sweep = a_waist - a_edge
    q = math.pi / 2.0

    def pt(c, ang, r):
        return (c[0] + r*math.cos(ang), c[1] + r*math.sin(ang))

    c_br, c_tr, c_tl, c_bl = PAD_CENTERS[1], PAD_CENTERS[3], PAD_CENTERS[2], PAD_CENTERS[0]
    return [
        ('line', (RC, 0.0), (W - RC, 0.0)),
        ('arc', c_br, (W - RC, 0.0), q),
        ('line', (W, RC), (W, RC + e)),
        ('arc', c_br, pt(c_br, a_edge, PAD_R), pad_sweep),
        ('line', (W - x_w, RC + d), (W - x_w, H - RC - d)),
        ('arc', c_tr, pt(c_tr, -a_waist, PAD_R), pad_sweep),
        ('line', (W, H - RC - e), (W, H - RC)),
        ('arc', c_tr, (W, H - RC), q),
        ('line', (W - RC, H), (RC, H)),
        ('arc', c_tl, (RC, H), q),
        ('line', (0.0, H - RC), (0.0, H - RC - e)),
        ('arc', c_tl, pt(c_tl, math.pi + a_edge, PAD_R), pad_sweep),
        ('line', (x_w, H - RC - d), (x_w, RC + d)),
        ('arc', c_bl, pt(c_bl, math.pi - a_waist, PAD_R), pad_sweep),
        ('line', (0.0, RC + e), (0.0, RC)),
        ('arc', c_bl, (0.0, RC), q),
    ]


def pad_span():
    """(y0, y1): where the bottom and top pads' arcs meet the waist edge. The
    side bevel runs between them."""
    x_w = (W - W_THIN) / 2.0
    d = math.sqrt(PAD_R**2 - (RC - x_w)**2)
    return RC + d, H - RC - d


def side_bevel_triangles(t):
    """(x, z) triangles, left then right, whose extrusion along y cuts the side
    bevel into a plate's outer face at z = t. The bevel plane passes through
    (x_w, t - SIDE_BEVEL_H) on the side and (x_w + SLOPE*H, t) on the face; the
    triangle overshoots both by 1 mm."""
    x_w = (W - W_THIN) / 2.0
    s, h, ext = SIDE_BEVEL_SLOPE, SIDE_BEVEL_H, 1.0
    left = [(x_w - ext, t - h - ext/s), (x_w + s*h + s*ext, t + ext), (x_w - ext, t + ext)]
    return [left, [(W - x, z) for (x, z) in left]]


def hex_points(af, cx, cy):
    """Hexagon with a vertex pointing at +Y, matching the original part."""
    rc = af / math.sqrt(3.0)
    return [(cx + rc*math.cos(math.radians(90+60*i)),
             cy + rc*math.sin(math.radians(90+60*i))) for i in range(6)]


def ray_hits_polygon(pts):
    """(near, far) distances along a ray from (cx, cy) at angle phi to a convex
    polygon, or None if the ray misses it."""
    n = len(pts)
    def hits(cx, cy, phi):
        ux, uy = math.cos(phi), math.sin(phi)
        ts = []
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            ex, ey = bx - ax, by - ay
            den = ux*ey - uy*ex
            if abs(den) < 1e-12:
                continue
            t = ((ax - cx)*ey - (ay - cy)*ex) / den
            u = ((ax - cx)*uy - (ay - cy)*ux) / den
            if t > 0 and -1e-9 <= u <= 1 + 1e-9:
                ts.append(t)
        return (min(ts), max(ts)) if ts else None
    return hits


def ray_hits_circle(r, x, y):
    """Same as ray_hits_polygon() for the circle of radius r at (x, y)."""
    def hits(cx, cy, phi):
        ux, uy = math.cos(phi), math.sin(phi)
        px, py = x - cx, y - cy
        along = px*ux + py*uy
        off2 = px*px + py*py - along*along
        if off2 > r*r or along + math.sqrt(r*r - off2) <= 0:
            return None
        s = math.sqrt(r*r - off2)
        return (along - s, along + s)
    return hits


def corner_entrance(hits, x, y):
    """Flat entrance opening a convex pocket around the screw at (x, y) to its
    corner, wherever the wall between them would be thinner than
    CORNER_WEB_MIN. Same rule as corner_entrance() in generate_case.py.

    Wall thickness is measured along rays from the corner arc's centre, normal
    to the outline there; the entrance is the wedge between the two rays where
    it equals CORNER_WEB_MIN, beyond the pocket. Returned as a quadrilateral
    to sketch over the pocket: from a point inside the pocket, out along one
    ray past the outline, across, and back along the other ray. Together
    with the pocket, it covers exactly the pocket plus the wedge beyond it.
    None if no wall is that thin."""
    ccx, ccy = min(PAD_CENTERS, key=lambda c: math.hypot(c[0] - x, c[1] - y))

    def wall(phi):
        h = hits(ccx, ccy, phi)
        return None if h is None else RC - h[1]

    def thin(phi):
        w = wall(phi)
        return w is not None and w < CORNER_WEB_MIN

    toward = math.atan2(y - ccy, x - ccx)
    step = math.radians(0.25)
    found = [toward + step*k for k in range(-180, 181) if thin(toward + step*k)]
    if not found:
        return None
    if not all(math.cos(p)*(x - ccx) >= 0 and math.sin(p)*(y - ccy) >= 0 for p in found):
        raise ValueError('corner entrance at ({:.2f}, {:.2f}) would run past the corner '
                         'arc; CORNER_WEB_MIN is too large for this pocket'.format(x, y))

    def edge(inside, outside):
        for _ in range(50):
            mid = 0.5*(inside + outside)
            if thin(mid):
                inside = mid
            else:
                outside = mid
        return outside

    reach = RC + 2.0                               # past the outline
    quad = []
    for phi, far_first in ((edge(min(found), min(found) - step), False),
                           (edge(max(found), max(found) + step), True)):
        near, far = hits(ccx, ccy, phi)
        inner = 0.5*(near + far)
        ends = [(ccx + inner*math.cos(phi), ccy + inner*math.sin(phi)),
                (ccx + reach*math.cos(phi), ccy + reach*math.sin(phi))]
        quad += ends[::-1] if far_first else ends
    return quad


def rear_pocket_rect():
    """(w, h, cx, cy) of the rear pocket's nominal wall."""
    hex_rc = HEX_AF / math.sqrt(3.0)              # hex centre -> vertex
    x0 = SCREW_EDGE_X + hex_rc + REAR_POCKET_CLEAR
    y0 = SCREW_EDGE_Y + hex_rc + REAR_POCKET_CLEAR
    return W - 2*x0, H - 2*y0, W/2.0, H/2.0


# -------------------------------------------------------------------- helpers
def plane_xy(comp, expr):
    """Plane parallel to XY, offset by the expression (a parameter name works)."""
    pi = comp.constructionPlanes.createInput()
    pi.setByOffset(comp.xYConstructionPlane, V(expr))
    return comp.constructionPlanes.add(pi)


def plane_y(comp, y_mm):
    """Plane parallel to XZ at y = y_mm. The sign of the XZ plane's offset
    depends on which way its normal points, so check where the plane landed
    and flip it if needed."""
    for sign in (1.0, -1.0):
        pi = comp.constructionPlanes.createInput()
        pi.setByOffset(comp.xZConstructionPlane, V('{} mm'.format(sign*y_mm)))
        pl = comp.constructionPlanes.add(pi)
        if abs(pl.geometry.origin.y - y_mm*MM) < 1e-6:
            return pl
        pl.deleteMe()
    raise RuntimeError('could not place the plane at y={}'.format(y_mm))


def rrect(sk, w, h, r, cx=0.0, cy=0.0):
    """Rounded rectangle on the sketch XY plane."""
    L, A = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    a, b = w/2.0 - r, h/2.0 - r
    L.addByTwoPoints(P3(cx-a, cy-h/2.0), P3(cx+a, cy-h/2.0))
    A.addByCenterStartSweep(P3(cx+a, cy-b), P3(cx+a, cy-h/2.0), math.pi/2)
    L.addByTwoPoints(P3(cx+w/2.0, cy-b), P3(cx+w/2.0, cy+b))
    A.addByCenterStartSweep(P3(cx+a, cy+b), P3(cx+w/2.0, cy+b), math.pi/2)
    L.addByTwoPoints(P3(cx+a, cy+h/2.0), P3(cx-a, cy+h/2.0))
    A.addByCenterStartSweep(P3(cx-a, cy+b), P3(cx-a, cy+h/2.0), math.pi/2)
    L.addByTwoPoints(P3(cx-w/2.0, cy+b), P3(cx-w/2.0, cy-b))
    A.addByCenterStartSweep(P3(cx-a, cy-b), P3(cx-w/2.0, cy-b), math.pi/2)
    return sk.profiles.item(0)


def outline(sk):
    """The waisted outer outline (outline_segments()) on the sketch XY plane."""
    L, A = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    for seg in outline_segments():
        if seg[0] == 'line':
            L.addByTwoPoints(P3(*seg[1]), P3(*seg[2]))
        else:
            A.addByCenterStartSweep(P3(*seg[1]), P3(*seg[2]), seg[3])
    return sk.profiles.item(0)


def polygon(sk, pts):
    L = sk.sketchCurves.sketchLines
    for i in range(len(pts)):
        L.addByTwoPoints(P3(*pts[i]), P3(*pts[(i + 1) % len(pts)]))


def rrect_on_y_plane(sk, win, y):
    """Rounded rectangle on a sketch parallel to XZ, placed through
    modelToSketchSpace so it does not depend on the local axis orientation.
    `y` is passed in explicitly: Sketch.referencePlane may return a planar face
    or even another sketch, so the coordinate cannot be derived from it."""
    o  = sk.modelToSketchSpace(P3(win['x'], y, win['z']))
    ux = sk.modelToSketchSpace(P3(win['x'] + 1.0, y, win['z']))
    uz = sk.modelToSketchSpace(P3(win['x'], y, win['z'] + 1.0))
    ex, ez = (ux.x-o.x, ux.y-o.y), (uz.x-o.x, uz.y-o.y)
    def pt(dx, dz):
        return adsk.core.Point3D.create(o.x + ex[0]*dx + ez[0]*dz,
                                        o.y + ex[1]*dx + ez[1]*dz, 0.0)
    w, h, r = win['w'], win['h'], win['r']
    a, b = w/2.0 - r, h/2.0 - r
    clockwise = (ex[0]*ez[1] - ex[1]*ez[0]) < 0      # sketch handedness
    sw = -math.pi/2 if clockwise else math.pi/2
    L, A = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    L.addByTwoPoints(pt(-a, -h/2.0), pt(a, -h/2.0))
    A.addByCenterStartSweep(pt(a, -b), pt(a, -h/2.0), sw)
    L.addByTwoPoints(pt(w/2.0, -b), pt(w/2.0, b))
    A.addByCenterStartSweep(pt(a, b), pt(w/2.0, b), sw)
    L.addByTwoPoints(pt(a, h/2.0), pt(-a, h/2.0))
    A.addByCenterStartSweep(pt(-a, b), pt(-a, h/2.0), sw)
    L.addByTwoPoints(pt(-w/2.0, b), pt(-w/2.0, -b))
    A.addByCenterStartSweep(pt(-a, -b), pt(-w/2.0, -b), sw)
    return sk.profiles.item(0)


def flare_wall_opening(comp, body, win, setback, y_int, y_ext, circular=False):
    """Flare opening the window from the inner face (y_int) to the outer one
    (y_ext). The straight bore has already been cut through the whole wall; all
    we remove here is the cone, which is always larger than it."""
    if setback <= 0:
        return
    direction = 1.0 if y_ext > y_int else -1.0
    flare_depth = setback / CHAMFER_SLOPE                       # flare depth
    straight = abs(y_ext - y_int) - flare_depth                  # straight bore before it
    y_a = y_int + direction * straight
    ska = comp.sketches.add(plane_y(comp, y_a))
    skb = comp.sketches.add(plane_y(comp, y_ext))
    if circular:
        ca = ska.modelToSketchSpace(P3(win['x'], y_a, win['z']))
        ska.sketchCurves.sketchCircles.addByCenterRadius(ca, win['d']*MM/2.0)
        cb = skb.modelToSketchSpace(P3(win['x'], y_ext, win['z']))
        skb.sketchCurves.sketchCircles.addByCenterRadius(cb, (win['d']/2.0 + setback)*MM)
        pa, pb = ska.profiles.item(0), skb.profiles.item(0)
    else:
        pa = rrect_on_y_plane(ska, win, y_a)
        larger = dict(win, w=win['w'] + 2*setback, h=win['h'] + 2*setback, r=win['r'] + setback)
        pb = rrect_on_y_plane(skb, larger, y_ext)
    loft(comp, pa, pb, CUT, body)


def all_profiles(sk):
    """Every profile of a sketch, for one feature over all of them. Where the
    sketch's loops overlap, the union of the loops is what gets extruded."""
    coll = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        coll.add(sk.profiles.item(i))
    return coll


def _one_side_extent(ei, dist):
    """setOneSideExtent + DistanceExtentDefinition is the current API form (the
    official extrude sample uses it). setDistanceExtent is the older form, still
    documented. Try the new one and fall back to the old."""
    v = V(dist)
    try:
        d = adsk.fusion.DistanceExtentDefinition.create(v)
        ei.setOneSideExtent(d, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    except Exception:
        ei.setDistanceExtent(False, v)


def _participants(target):
    return list(target) if isinstance(target, (list, tuple)) else [target]


def extrude(comp, profile, dist, op, target=None, start=None):
    """`profile` is one Profile or an ObjectCollection of them; `target` one
    body or a list of bodies."""
    ex = comp.features.extrudeFeatures
    ei = ex.createInput(profile, op)
    if start is not None:
        ei.startExtent = adsk.fusion.OffsetStartDefinition.create(V(start))
    _one_side_extent(ei, dist)
    if target is not None and op != adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
        ei.participantBodies = _participants(target)
    return ex.add(ei)


def extrude_symmetric(comp, profile, total, op, target=None):
    """Goes through both ways, which saves having to guess the direction of the
    plane normal. Used for the wall cuts and the side bevel cutters."""
    ex = comp.features.extrudeFeatures
    ei = ex.createInput(profile, op)
    ei.setSymmetricExtent(V(total), True)
    if target is not None and op != adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
        ei.participantBodies = _participants(target)
    return ex.add(ei)


def loft(comp, p1, p2, op, target=None):
    lf = comp.features.loftFeatures
    li = lf.createInput(op)
    li.loftSections.add(p1)
    li.loftSections.add(p2)
    li.isSolid = True
    if target is not None and op != adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
        li.participantBodies = _participants(target)
    return lf.add(li)


def combine_cut(comp, target, tools):
    """Remove the tool bodies from `target`, consuming them."""
    coll = adsk.core.ObjectCollection.create()
    for b in tools:
        coll.add(b)
    ci = comp.features.combineFeatures.createInput(target, coll)
    ci.operation = CUT
    ci.isKeepToolBodies = False
    return comp.features.combineFeatures.add(ci)


NEW_BODY  = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation


# -------------------------------------------------------------------- build
def plate(comp, t_expr):
    """Straight extrusion of the waisted outline."""
    sk0 = comp.sketches.add(comp.xYConstructionPlane)
    return extrude(comp, outline(sk0), t_expr, NEW_BODY).bodies.item(0)


def side_bevels(comp, body, t):
    """Bevel along both side edges of a plate's outer face (z = t), between
    the corner pads only. Each cutter is a triangle extruded along the waist
    edge a little past both pads, then cut back by the pads' discs so the bevel
    stops on each pad's arc and no pad loses material."""
    y0, y1 = pad_span()
    y_mid = (y0 + y1) / 2.0
    sk = comp.sketches.add(plane_y(comp, y_mid))
    for tri in side_bevel_triangles(t):
        pts = [sk.modelToSketchSpace(P3(x, y_mid, z)) for (x, z) in tri]
        for i in range(3):
            sk.sketchCurves.sketchLines.addByTwoPoints(pts[i], pts[(i + 1) % 3])
    tools = [extrude_symmetric(comp, sk.profiles.item(i), mm(y1 - y0 + 2.0), NEW_BODY).bodies.item(0)
             for i in range(sk.profiles.count)]

    skp = comp.sketches.add(comp.xYConstructionPlane)
    for (px, py) in PAD_CENTERS:
        skp.sketchCurves.sketchCircles.addByCenterRadius(P3(px, py), PAD_R*MM)
    extrude(comp, all_profiles(skp), mm(t + 3.0), CUT, tools, start='-1 mm')

    combine_cut(comp, body, tools)


def screw_holes_cut(comp, body, t_expr, counterbore=None, hex_socket=None):
    """Screw holes, plus either a counterbore or a hex nut pocket at each one
    on the outer face -- each with its corner entrance, cut down to the same
    floor as the pocket itself."""
    sk = comp.sketches.add(comp.xYConstructionPlane)
    for (x, y) in SCREWS:
        sk.sketchCurves.sketchCircles.addByCenterRadius(P3(x, y), SCREW_D*MM/2.0)
    extrude(comp, all_profiles(sk), '{} + 2 mm'.format(t_expr), CUT, body, start='-1 mm')

    for pocket in (counterbore, hex_socket):
        if not pocket:
            continue
        sk2 = comp.sketches.add(plane_xy(comp, '{} - {}'.format(t_expr, pocket['p'])))
        for (x, y) in SCREWS:
            if pocket is counterbore:
                sk2.sketchCurves.sketchCircles.addByCenterRadius(P3(x, y), pocket['d']*MM/2.0)
                hits = ray_hits_circle(pocket['d']/2.0, x, y)
            else:
                pts = hex_points(pocket['af'], x, y)
                polygon(sk2, pts)
                hits = ray_hits_polygon(pts)
            entrance = corner_entrance(hits, x, y)
            if entrance:
                polygon(sk2, entrance)
        extrude(comp, all_profiles(sk2), '{} + 1 mm'.format(pocket['p']), CUT, body)


def rear_pocket(comp, body):
    """Single pocket in the rear plate's flat outer face, clear of the 4 nut
    pockets, with its rim and floor edge bevelled: the wall runs in from the
    floor, straight, then out to the mouth."""
    pw, ph, cx, cy = rear_pocket_rect()
    h = REAR_POCKET_BEVEL_H
    w = REAR_POCKET_BEVEL_SLOPE * h
    z_floor, z_a = REAR_POCKET_KEEP, REAR_POCKET_KEEP + h
    if z_a > REAR_T - h:
        raise ValueError('rear pocket too shallow for two bevels of REAR_POCKET_BEVEL_H')

    def ring(z_expr, grow):
        sk = comp.sketches.add(plane_xy(comp, z_expr))
        return rrect(sk, pw + 2*grow, ph + 2*grow, REAR_POCKET_R + grow, cx, cy)

    extrude(comp, ring(mm(z_a), 0.0), 'rear_t - {} + 1 mm'.format(mm(z_a)), CUT, body)
    loft(comp, ring(mm(z_floor), -w), ring(mm(z_a), 0.0), CUT, body)
    loft(comp, ring('rear_t - {}'.format(mm(h)), 0.0), ring('rear_t', w), CUT, body)


def build_face(root):
    comp = root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
    comp.name = 'face'
    body = plate(comp, 'face_t')
    side_bevels(comp, body, FACE_T)

    # Straight bore from 1 mm below the inner face to 1 mm into the chamfer,
    # then the chamfer as a loft; the overlap keeps the two cuts from meeting on
    # one plane. (The bore used to start 1 mm below the chamfer plane instead of
    # below z = 0, which left a 0.19 mm skin across the screen window.)
    t = SCREEN
    ska = comp.sketches.add(comp.xYConstructionPlane)
    extrude(comp, rrect(ska, t['w'], t['h'], t['r'], t['cx'], t['cy']),
            '{} mm + 2 mm'.format(t['ch_z']), CUT, body, start='-1 mm')
    sk1 = comp.sketches.add(plane_xy(comp, '{} mm'.format(t['ch_z'])))
    p1  = rrect(sk1, t['w'], t['h'], t['r'], t['cx'], t['cy'])
    sk2 = comp.sketches.add(plane_xy(comp, 'face_t'))
    p2  = rrect(sk2, t['w']+2*t['off'], t['h']+2*t['off'], t['r']+t['off'], t['cx'], t['cy'])
    loft(comp, p1, p2, CUT, body)

    w = WHEEL
    skc = comp.sketches.add(comp.xYConstructionPlane)
    skc.sketchCurves.sketchCircles.addByCenterRadius(P3(w['cx'], w['cy']), w['d']*MM/2.0)
    extrude(comp, skc.profiles.item(0), '{} mm + 2 mm'.format(w['ch_z']), CUT,
            body, start='-1 mm')
    skd = comp.sketches.add(plane_xy(comp, '{} mm'.format(w['ch_z'])))
    skd.sketchCurves.sketchCircles.addByCenterRadius(P3(w['cx'], w['cy']), w['d']*MM/2.0)
    ske = comp.sketches.add(plane_xy(comp, 'face_t'))
    ske.sketchCurves.sketchCircles.addByCenterRadius(P3(w['cx'], w['cy']), w['d_out']*MM/2.0)
    loft(comp, skd.profiles.item(0), ske.profiles.item(0), CUT, body)

    screw_holes_cut(comp, body, 'face_t', counterbore=dict(d=COUNTERBORE_D, p='counterbore_depth'))
    return comp


def build_rear(root):
    comp = root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
    comp.name = 'rear'
    body = plate(comp, 'rear_t')
    side_bevels(comp, body, REAR_T)
    screw_holes_cut(comp, body, 'rear_t', hex_socket=dict(af=HEX_AF, p='hex_depth'))
    rear_pocket(comp, body)
    return comp


def build_frame(root):
    comp = root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
    comp.name = 'frame'
    sk0 = comp.sketches.add(comp.xYConstructionPlane)
    body = extrude(comp, outline(sk0), 'frame_t', NEW_BODY).bodies.item(0)

    sk1 = comp.sketches.add(comp.xYConstructionPlane)
    rrect(sk1, CAVITY['w'], CAVITY['h'], CAVITY['r'], CAVITY['cx'], CAVITY['cy'])
    extrude(comp, sk1.profiles.item(0), 'frame_t + 2 mm', CUT, body, start='-1 mm')

    # headphone jack, mid top wall
    y_mid_top = (WALL_TOP_Y + H) / 2.0
    skj = comp.sketches.add(plane_y(comp, y_mid_top))
    c = skj.modelToSketchSpace(P3(JACK['x'], y_mid_top, JACK['z']))
    skj.sketchCurves.sketchCircles.addByCenterRadius(c, JACK['d']*MM/2.0)
    extrude_symmetric(comp, skj.profiles.item(0), '12 mm', CUT, body)
    flare_wall_opening(comp, body, JACK, JACK_CHAMF, WALL_TOP_Y, H, circular=True)

    # dock connector, mid bottom wall
    skd = comp.sketches.add(plane_y(comp, WALL_BOT_Y/2.0))
    extrude_symmetric(comp, rrect_on_y_plane(skd, DOCK, WALL_BOT_Y/2.0), '12 mm', CUT, body)
    flare_wall_opening(comp, body, DOCK, DOCK_CHAMF, WALL_BOT_Y, 0.0)

    # Hold switch, top wall
    if HOLD:
        skh = comp.sketches.add(plane_y(comp, y_mid_top))
        extrude_symmetric(comp, rrect_on_y_plane(skh, HOLD, y_mid_top), '12 mm', CUT, body)
        flare_wall_opening(comp, body, HOLD, HOLD_CHAMF, WALL_TOP_Y, H)

    sk2 = comp.sketches.add(comp.xYConstructionPlane)
    for (x, y) in SCREWS:
        sk2.sketchCurves.sketchCircles.addByCenterRadius(P3(x, y), SCREW_D*MM/2.0)
    extrude(comp, all_profiles(sk2), 'frame_t + 2 mm', CUT, body, start='-1 mm')
    return comp


# ----------------------------------------------------------------------- run
def run(context):
    ui, stage = None, 'start'
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.unitsManager.defaultLengthUnits = 'mm'
        root = design.rootComponent

        stage = 'parameters'
        for name, expr, com in PARAMS:
            if design.userParameters.itemByName(name) is None:
                design.userParameters.add(name, V(expr), 'mm', com)

        for stage, fn in (('face', build_face), ('frame', build_frame), ('rear', build_rear)):
            fn(root)

        ui.messageBox(u'iPod case generated: three components.\n\n'
                      u'Modify -> Change Parameters edits the thicknesses and\n'
                      u'depths. The outline, bevels and corner entrances come\n'
                      u'from the constants at the top of the script.')
    except:
        if ui:
            ui.messageBox(u'Failed at stage "{}":\n\n{}'.format(stage, traceback.format_exc()))
