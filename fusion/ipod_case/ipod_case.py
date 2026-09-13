# -*- coding: utf-8 -*-
"""
iPod Classic case - parametric generator for Autodesk Fusion.

HOW TO RUN
  Fusion -> Utilities tab -> Add-Ins -> "Scripts and Add-Ins" -> Scripts tab
  -> "+" button -> point it at the FOLDER  fusion/ipod_case  -> pick
  "ipod_case" from the list -> Run.

AFTER RUNNING
  Modify -> Change Parameters. Thicknesses and depths are wired to the User
  Parameters, so changing "rear_t" or "hex_depth" rebuilds the model.
  The PROFILES are drawn from explicit coordinates (no sketch dimensions): to
  make one parametric, open the sketch and add the dimensions yourself.

KNOWN DIFFERENCES FROM THE STLs
  The plates here still carry the old finger-grip scallop (grip_scallop: a
  loft over the lower half of each side). generate_case.py replaced it with
  a bevel along each whole side edge, between the corner pads only.

  The frame here still lightens its side walls with a blind pocket
  (frame_pocket). generate_case.py replaced that with a thin waist that
  only keeps full wall thickness around each screw -- porting that
  non-convex outline to Fusion's sketch/loft API was left for a future
  pass. The rear plate's pocket (rear_pocket) is straight-walled here;
  generate_case.py bevels both its rim and its floor edge.
"""

import adsk.core, adsk.fusion, traceback, math

MM = 0.1                                    # the API works in centimetres
def V(e):            return adsk.core.ValueInput.createByString(str(e))
def P3(x, y, z=0.0): return adsk.core.Point3D.create(x*MM, y*MM, z*MM)

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
SCREW_D        = 3.15
SCREW_EDGE_X, SCREW_EDGE_Y = 5.00, 4.50
SCREWS = [(SCREW_EDGE_X, SCREW_EDGE_Y), (W - SCREW_EDGE_X, SCREW_EDGE_Y),
          (SCREW_EDGE_X, H - SCREW_EDGE_Y), (W - SCREW_EDGE_X, H - SCREW_EDGE_Y)]

# Weight-reduction pockets: possible only with 4 screws, since dropping the
# mid pair frees the whole span between the corners on each side wall. Same
# derivation and floor thicknesses as generate_case.py.
FRAME_POCKET_KEEP, FRAME_POCKET_LIP, FRAME_POCKET_CLEAR = 3.00, 2.00, 6.00
REAR_POCKET_KEEP,  REAR_POCKET_CLEAR, REAR_POCKET_R      = 2.50, 3.00, 4.00

FACE_T = 3.501
COUNTERBORE_D, COUNTERBORE_DEPTH           = 6.0, 2.501
SCREEN  = dict(w=51.518, h=39.922, r=2.378, cx=38.40, cy=WALL_BOTTOM + 79.35, ch_z=1.189, off=1.4805)
WHEEL = dict(d=37.99, cx=38.40, cy=WALL_BOTTOM + 31.00, ch_z=0.884, d_out=50.14)

FRAME_T = 14.0
CAVITY     = dict(w=CAVITY_W, h=CAVITY_H, r=CAVITY_R, cx=W / 2.0, cy=WALL_BOTTOM + CAVITY_H / 2.0)
JACK    = dict(d=10.0, x=61.743, z=7.29)
DOCK    = dict(w=28.83, h=7.94, r=2.0, x=38.40, z=7.70)
HOLD    = dict(w=14.0, h=5.0, r=1.5, x=21.84, z=7.29)   # 12.5 x 3.3 switch plus clearance; x set by test print

# Wall openings flare from the cavity outwards with the same slope as the
# screen window chamfer. Each setback is the largest the surroundings allow
# while keeping 1.10 mm of material to the frame edge -- the jack is the
# limiter, because a 10 mm hole in a 14 mm frame leaves only 1.71 mm above it.
CHAMFER_SLOPE = 0.6403
JACK_CHAMF, DOCK_CHAMF, HOLD_CHAMF = 0.60, 1.20, 1.20

REAR_T = 5.0
HEX_AF, HEX_DEPTH                    = 5.846, 2.5
NOTCH = dict(y0=9.53, y1=50.33, r=2.10, z0=0.82, incl=2.324)

WALL_TOP_Y = CAVITY['cy'] + CAVITY['h']/2.0     # 109.2
WALL_BOT_Y = CAVITY['cy'] - CAVITY['h']/2.0     # 5.0


# -------------------------------------------------------------------- helpers
def plane_xy(comp, expr):
    """Plane parallel to XY, offset by the expression (a parameter name works)."""
    pi = comp.constructionPlanes.createInput()
    pi.setByOffset(comp.xYConstructionPlane, V(expr))
    return comp.constructionPlanes.add(pi)


def plane_y(comp, y_mm):
    """plano paralelo ao XZ em y = y_mm. O sign do offset do plano XZ depende
    da orientacao da normal, entao conferimos onde o plano caiu e corrigimos."""
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


def hexagon(sk, af, cx, cy):
    rc = af / math.sqrt(3.0)
    p = [(cx + rc*math.cos(math.radians(90+60*i)),
          cy + rc*math.sin(math.radians(90+60*i))) for i in range(6)]
    for i in range(6):
        sk.sketchCurves.sketchLines.addByTwoPoints(P3(*p[i]), P3(*p[(i+1) % 6]))


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


def extrude(comp, profile, dist, op, target=None, start=None):
    ex = comp.features.extrudeFeatures
    ei = ex.createInput(profile, op)
    if start is not None:
        ei.startExtent = adsk.fusion.OffsetStartDefinition.create(V(start))
    _one_side_extent(ei, dist)
    if target is not None and op != adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
        ei.participantBodies = [target]
    return ex.add(ei)


def extrude_symmetric(comp, profile, total, op, target):
    """Used for the wall cuts: goes through both ways, which saves having to
    guess the direction of the plane normal."""
    ex = comp.features.extrudeFeatures
    ei = ex.createInput(profile, op)
    ei.setSymmetricExtent(V(total), True)
    ei.participantBodies = [target]
    return ex.add(ei)


def loft(comp, p1, p2, op, target=None):
    lf = comp.features.loftFeatures
    li = lf.createInput(op)
    li.loftSections.add(p1)
    li.loftSections.add(p2)
    li.isSolid = True
    if target is not None and op != adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
        li.participantBodies = [target]
    return lf.add(li)


NEW_BODY  = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation


# -------------------------------------------------------------------- build
def plate(comp, t_expr):
    """Straight extrusion of the outer footprint -- no decorative edge
    chamfer; face and rear plates now just follow the frame's own outline."""
    sk0 = comp.sketches.add(comp.xYConstructionPlane)
    return extrude(comp, rrect(sk0, W, H, RC, W/2, H/2), t_expr, NEW_BODY).bodies.item(0)


def grip_scallop(comp, body, t_expr, t_val):
    n, outside = NOTCH, 12.0
    flare_depth = n['incl'] * (t_val - n['z0'])
    yc, hh = (n['y0'] + n['y1'])/2.0, n['y1'] - n['y0']
    for mirrored in (False, True):
        def centre(inside):
            c = (inside - outside)/2.0
            return (W - c) if mirrored else c
        ska = comp.sketches.add(plane_xy(comp, '{} mm'.format(n['z0'])))
        pa  = rrect(ska, outside, hh, n['r'], centre(0.0), yc)
        skb = comp.sketches.add(plane_xy(comp, t_expr))
        pb  = rrect(skb, outside + flare_depth, hh, n['r'], centre(flare_depth), yc)
        loft(comp, pa, pb, CUT, body)


def screw_holes_cut(comp, body, t_expr, counterbore=None, hex_socket=None):
    sk = comp.sketches.add(comp.xYConstructionPlane)
    for (x, y) in SCREWS:
        sk.sketchCurves.sketchCircles.addByCenterRadius(P3(x, y), SCREW_D*MM/2.0)
    for i in range(sk.profiles.count):
        extrude(comp, sk.profiles.item(i), '{} + 2 mm'.format(t_expr), CUT,
                body, start='-1 mm')
    if counterbore:
        sk2 = comp.sketches.add(plane_xy(comp, '{} - {}'.format(t_expr, counterbore['p'])))
        for (x, y) in SCREWS:
            sk2.sketchCurves.sketchCircles.addByCenterRadius(P3(x, y), counterbore['d']*MM/2.0)
        for i in range(sk2.profiles.count):
            extrude(comp, sk2.profiles.item(i), '{} + 1 mm'.format(counterbore['p']), CUT, body)
    if hex_socket:
        sk3 = comp.sketches.add(plane_xy(comp, '{} - {}'.format(t_expr, hex_socket['p'])))
        for (x, y) in SCREWS:
            hexagon(sk3, hex_socket['af'], x, y)
        for i in range(sk3.profiles.count):
            extrude(comp, sk3.profiles.item(i), '{} + 1 mm'.format(hex_socket['p']), CUT, body)


def frame_pocket(comp, body):
    """Blind pocket on the outer face of each side wall (see FRAME_POCKET_*
    at the top). Leaves FRAME_POCKET_KEEP of wall to the cavity and a
    FRAME_POCKET_LIP mating lip top and bottom."""
    side_wall = (W - CAVITY['w']) / 2.0
    depth = side_wall - FRAME_POCKET_KEEP
    y0 = SCREW_EDGE_Y + SCREW_D/2.0 + FRAME_POCKET_CLEAR
    y1 = H - y0
    sk = comp.sketches.add(plane_xy(comp, '{} mm'.format(FRAME_POCKET_LIP)))
    L = sk.sketchCurves.sketchLines
    for x0 in (0.0, W - depth):
        pts = [(x0, y0), (x0 + depth, y0), (x0 + depth, y1), (x0, y1)]
        for i in range(4):
            L.addByTwoPoints(P3(*pts[i]), P3(*pts[(i + 1) % 4]))
    for i in range(sk.profiles.count):
        extrude(comp, sk.profiles.item(i),
                'frame_t - {} mm'.format(2*FRAME_POCKET_LIP), CUT, body)


def rear_pocket(comp, body):
    """Single pocket in the rear plate's flat outer face (see REAR_POCKET_*),
    sized to clear the 4 hex nut bosses and the grip scallops on its own."""
    hex_rc = HEX_AF / math.sqrt(3.0)              # hex centre -> vertex
    x0 = SCREW_EDGE_X + hex_rc + REAR_POCKET_CLEAR
    x1 = W - x0
    y0 = SCREW_EDGE_Y + hex_rc + REAR_POCKET_CLEAR
    y1 = H - y0
    sk = comp.sketches.add(plane_xy(comp, '{} mm'.format(REAR_POCKET_KEEP)))
    p = rrect(sk, x1 - x0, y1 - y0, REAR_POCKET_R, (x0 + x1)/2.0, (y0 + y1)/2.0)
    extrude(comp, p, 'rear_t - {} mm + 1 mm'.format(REAR_POCKET_KEEP), CUT, body)


def build_face(root):
    comp = root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
    comp.name = 'face'
    body = plate(comp, 'face_t')

    t = SCREEN
    ska = comp.sketches.add(plane_xy(comp, '{} mm'.format(t['ch_z'])))
    extrude(comp, rrect(ska, t['w'], t['h'], t['r'], t['cx'], t['cy']),
            '{} + 1 mm'.format(t['ch_z']), CUT, body, start='-1 mm')
    sk1 = comp.sketches.add(plane_xy(comp, '{} mm'.format(t['ch_z'])))
    p1  = rrect(sk1, t['w'], t['h'], t['r'], t['cx'], t['cy'])
    sk2 = comp.sketches.add(plane_xy(comp, 'face_t'))
    p2  = rrect(sk2, t['w']+2*t['off'], t['h']+2*t['off'], t['r']+t['off'], t['cx'], t['cy'])
    loft(comp, p1, p2, CUT, body)

    w = WHEEL
    skc = comp.sketches.add(plane_xy(comp, '{} mm'.format(w['ch_z'])))
    skc.sketchCurves.sketchCircles.addByCenterRadius(P3(w['cx'], w['cy']), w['d']*MM/2.0)
    extrude(comp, skc.profiles.item(0), '{} + 1 mm'.format(w['ch_z']), CUT,
            body, start='-1 mm')
    skd = comp.sketches.add(plane_xy(comp, '{} mm'.format(w['ch_z'])))
    skd.sketchCurves.sketchCircles.addByCenterRadius(P3(w['cx'], w['cy']), w['d']*MM/2.0)
    ske = comp.sketches.add(plane_xy(comp, 'face_t'))
    ske.sketchCurves.sketchCircles.addByCenterRadius(P3(w['cx'], w['cy']), w['d_out']*MM/2.0)
    loft(comp, skd.profiles.item(0), ske.profiles.item(0), CUT, body)

    grip_scallop(comp, body, 'face_t', FACE_T)
    screw_holes_cut(comp, body, 'face_t', counterbore=dict(d=COUNTERBORE_D, p='counterbore_depth'))
    return comp


def build_rear(root):
    comp = root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
    comp.name = 'rear'
    body = plate(comp, 'rear_t')
    grip_scallop(comp, body, 'rear_t', REAR_T)
    screw_holes_cut(comp, body, 'rear_t', hex_socket=dict(af=HEX_AF, p='hex_depth'))
    rear_pocket(comp, body)
    return comp


def build_frame(root):
    comp = root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
    comp.name = 'frame'
    sk0 = comp.sketches.add(comp.xYConstructionPlane)
    body = extrude(comp, rrect(sk0, W, H, RC, W/2, H/2), 'frame_t', NEW_BODY).bodies.item(0)

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
    for i in range(sk2.profiles.count):
        extrude(comp, sk2.profiles.item(i), 'frame_t + 2 mm', CUT, body, start='-1 mm')

    frame_pocket(comp, body)
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
                      u'Modify -> Change Parameters to edit dimensions.\n\n'
                      u'The Hold switch window is only cut once you fill in\n'
                      u'the HOLD dict at the top of the script.')
    except:
        if ui:
            ui.messageBox(u'Failed at stage "{}":\n\n{}'.format(stage, traceback.format_exc()))
