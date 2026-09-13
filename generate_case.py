#!/usr/bin/env python3
"""
Parametric generator for the iPod Classic case - v2

Rebuilds the three parts from dimensions measured off the original STLs, with
these changes:
  * 6 screws instead of 4
  * 5.00 mm rear plate, so an M3 x 20 screw ends flush
  * opening for the Hold switch
  * flared (countersunk) wall openings for jack, dock and Hold

All dimensions in millimetres. Edit the parameters and run again:

    python3 generate_case.py [output_dir]

Requires manifold3d and numpy.
"""
import math
import manifold3d as m3
from manifold3d import Manifold, CrossSection, JoinType

m3.set_min_circular_angle(3.0)
m3.set_min_circular_edge_length(0.25)

OVERLAP = 1e-3        # how far tool pieces overlap instead of abutting

# ============================================================================
# PARAMETERS
# ============================================================================

# ---- iPod cavity and walls ------------------------------------------------
# The cavity is sized to the iPod and never moves relative to it; the outer
# footprint follows from the cavity plus the wall thicknesses.
CAVITY_W, CAVITY_H, CAVITY_R = 62.20, 104.20, 6.00
WALL_TOP    = 3.00
WALL_BOTTOM = 5.00
# (side walls: (OUTER_W - CAVITY_W) / 2 = 7.30 mm)

# ---- outer footprint, shared by all three parts ---------------------------
OUTER_W   = 76.80
OUTER_H   = CAVITY_H + WALL_TOP + WALL_BOTTOM
CORNER_R  = 7.50                   # plan-view corner radius
CAVITY_CX = OUTER_W / 2.0
CAVITY_CY = WALL_BOTTOM + CAVITY_H / 2.0

# ---- screws ---------------------------------------------------------------
SCREW_D = 3.15                     # M3 clearance hole
# The 4 corner screws keep their original position. The 2 new ones, at mid
# height on the side walls, sit 0.25 mm further in: the side wall is 7.299 mm
# and there is only 1.253 mm of budget to split between the counterbore
# clearing the edge chamfer and the wall left over to the iPod cavity.
# At x=4.75 that budget lands as 0.32 mm and 0.97 mm.
SCREW_EDGE_X = 5.00                # corner screws, from the side edges
SCREW_EDGE_Y = 4.50                # corner screws, from the top/bottom edges
SCREW_MID_X  = 4.75                # mid side-wall screws, from the side edges
# SCREW_EDGE_Y = 4.50 suits a 3.00 mm end wall: it is where the original top
# corners already sat, clearing the cavity corner by 1.87 mm and the outer
# corner by 2.02 mm. With WALL_BOTTOM = 3.00 the bottom corners mirror them.
SCREWS = [(SCREW_EDGE_X,           SCREW_EDGE_Y),
          (OUTER_W - SCREW_EDGE_X, SCREW_EDGE_Y),
          (SCREW_EDGE_X,           OUTER_H - SCREW_EDGE_Y),
          (OUTER_W - SCREW_EDGE_X, OUTER_H - SCREW_EDGE_Y),
          (SCREW_MID_X,            OUTER_H / 2.0),
          (OUTER_W - SCREW_MID_X,  OUTER_H / 2.0)]

# ---- FACE PLATE -----------------------------------------------------------
FACE_T             = 3.501         # same as the original
FACE_CHAMF_Z       = 1.679         # height where the edge chamfer starts
FACE_CHAMF_SETBACK = 1.471         # chamfer setback at the outer face
COUNTERBORE_D      = 6.00          # screw head recess
COUNTERBORE_DEPTH  = 2.501         # leaves exactly 1.000 mm under the head

SCREEN_W, SCREEN_H, SCREEN_R = 51.518, 39.922, 2.378
SCREEN_CX, SCREEN_CY         = 38.40, WALL_BOTTOM + 79.35   # from cavity floor
SCREEN_CHAMF_Z, SCREEN_CHAMF_OFF = 1.189, 1.4805

WHEEL_D, WHEEL_CX, WHEEL_CY = 37.99, 38.40, WALL_BOTTOM + 31.00   # from cavity floor
WHEEL_CHAMF_Z, WHEEL_D_OUT  = 0.884, 50.14

# ---- FRAME ----------------------------------------------------------------
FRAME_T = 14.00

JACK_D, JACK_X, JACK_Z = 10.00, 61.743, 7.29
DOCK_W, DOCK_H, DOCK_R = 28.83, 7.94, 2.00
DOCK_X, DOCK_Z         = 38.40, 7.70

# Wall openings flare from the cavity outwards with the SAME slope as the
# screen window chamfer. Each setback is the largest the surroundings allow
# while keeping 1.10 mm of material to the frame edge -- the jack is the
# limiter, because a 10 mm hole in a 14 mm frame leaves only 1.71 mm above it.
# Set any of them to 0 to go back to a straight bore.
CHAMFER_SLOPE = 0.6403
JACK_CHAMF, DOCK_CHAMF, HOLD_CHAMF = 0.60, 1.20, 1.20

# Hold switch window. Set HOLD = None to skip the cut.
#   w = window width            h = height (across the iPod thickness)
#   x = centre, measured from the same reference side as the jack hole
#   z = centre through the thickness        r = corner radius
# Measured off the reference iPod: switch 12.50 x 3.30, and a 31.50 mm gap
# between the switch edge and the jack hole edge. Assuming a 6.3 mm jack hole
# put the centre at x=20.84; a test print showed the window sat 1.0 mm too far
# from the jack, so it was moved to x=21.84. (The effective jack hole on the
# reference unit is therefore smaller than assumed.) The window is 14.0 x 5.0,
# leaving 0.75 mm each side so a fingernail can reach the switch at the bottom
# of the 3 mm wall.
HOLD = dict(w=14.0, h=5.0, x=21.84, z=7.29, r=1.5)

# ---- REAR PLATE -----------------------------------------------------------
REAR_T             = 5.000         # was 3.50; thickened so an M3x20 ends flush
REAR_CHAMF_RISE    = 1.599         # height of the edge chamfer
REAR_CHAMF_SETBACK = 1.141         # chamfer setback at the outer face
HEX_AF             = 5.846         # hex socket across flats (M3 nut = 5.5)
HEX_DEPTH          = 2.500         # nut pocket depth

# ============================================================================
# HELPERS
# ============================================================================

def rrect(w, h, r, cx=0.0, cy=0.0):
    """Rounded rectangle as a CrossSection."""
    cs = CrossSection.square((w - 2*r, h - 2*r), center=True).offset(r, JoinType.Round)
    return cs.translate((cx, cy))


def prism(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))


def taper(cs_low, z_low, cs_high, z_high, below=0.0, above=0.0):
    """Solid running from cs_low (at z_low) to cs_high (at z_high), with
    optional straight extensions below and above. Assumes cs_low fits inside
    cs_high, which holds for every flare in this design.

    The two extensions need opposite treatment:
      * the LARGE profile's extension goes into the hull. Because the profile
        does not change along it, it cannot widen the cone below z_high.
      * the SMALL profile's extension must stay out of the hull -- inside it,
        the cone would start opening from the far end of the extension -- so
        it is unioned on, overlapping the hull by OVERLAP.
    Neither side is left to meet the hull on a coincident plane. Abutting
    faces there can leave a zero-thickness membrane after the boolean, which
    once sealed the dock opening shut.
    """
    out = Manifold.batch_hull([prism(cs_low,  z_low - 1e-4, z_low),
                               prism(cs_high, z_high, z_high + max(above, 1e-4))])
    if below:
        out = out + prism(cs_low, z_low - below, z_low + OVERLAP)
    return out


def hexagon(af, cx=0.0, cy=0.0):
    """Hexagon with a vertex pointing at +Y, matching the original part."""
    rc = af / math.sqrt(3.0)                      # centre -> vertex
    pts = [(cx + rc*math.cos(math.radians(90 + 60*i)),
            cy + rc*math.sin(math.radians(90 + 60*i))) for i in range(6)]
    return CrossSection([pts])


def slab_y(cs, y0, y1):
    """CrossSection whose Y becomes Z, extruded along Y."""
    return Manifold.extrude(cs, y1 - y0).rotate((90, 0, 0)).translate((0, y1, 0))


def taper_y(cs_in, cs_out, y_in, y_out, margin=3.0):
    """Opening that grows from the inner face (y_in) to the outer one (y_out).

    Built along +z with the small profile at z=0 and the large one at
    z=length, then mapped onto y. Extensions follow the same rule as taper().
    """
    length = abs(y_out - y_in)
    body = Manifold.batch_hull([prism(cs_in,  -1e-4, 0.0),
                                prism(cs_out, length, length + margin)])
    body = body + prism(cs_in, -margin, OVERLAP)
    body = body.rotate((90, 0, 0))                # z -> -y, and cs y -> world z
    if y_out > y_in:
        body = body.mirror((0, 1, 0))             # z -> +y, keeping cs y -> z
    return body.translate((0, y_in, 0))


def wall_opening(cs, setback, y_in, y_out):
    """Wall opening with a flared mouth. `setback` is how much it grows per
    side at the outer face; the straight bore before the flare comes out of
    the remaining wall thickness."""
    if setback <= 0:
        return slab_y(cs, min(y_in, y_out) - 3.0, max(y_in, y_out) + 3.0)
    direction = 1.0 if y_out > y_in else -1.0
    depth = setback / CHAMFER_SLOPE               # depth of the flare
    straight = abs(y_out - y_in) - depth          # straight bore before it
    if straight < 0:
        raise ValueError('flare is deeper than the wall')
    return taper_y(cs, cs.offset(setback, JoinType.Round),
                   y_in + direction*straight, y_out, margin=straight + 3.0)

# ============================================================================
# PARTS
# ============================================================================

def face(grip=None):
    body = Manifold.batch_hull([
        prism(rrect(OUTER_W, OUTER_H, CORNER_R, OUTER_W/2, OUTER_H/2), 0, FACE_CHAMF_Z),
        prism(rrect(OUTER_W, OUTER_H, CORNER_R, OUTER_W/2, OUTER_H/2)
              .offset(-FACE_CHAMF_SETBACK, JoinType.Round), FACE_T - 1e-4, FACE_T),
    ])

    screen = taper(rrect(SCREEN_W, SCREEN_H, SCREEN_R, SCREEN_CX, SCREEN_CY),
                   SCREEN_CHAMF_Z,
                   rrect(SCREEN_W + 2*SCREEN_CHAMF_OFF, SCREEN_H + 2*SCREEN_CHAMF_OFF,
                         SCREEN_R + SCREEN_CHAMF_OFF, SCREEN_CX, SCREEN_CY), FACE_T,
                   below=SCREEN_CHAMF_Z + 2.0, above=2.0)

    wheel = taper(CrossSection.circle(WHEEL_D/2).translate((WHEEL_CX, WHEEL_CY)),
                  WHEEL_CHAMF_Z,
                  CrossSection.circle(WHEEL_D_OUT/2).translate((WHEEL_CX, WHEEL_CY)),
                  FACE_T, below=WHEEL_CHAMF_Z + 2.0, above=2.0)

    body = body - screen - wheel
    # The grip scallop is copied in from the original mesh, so it has to go in
    # BEFORE the screws are cut: its boxes overlap the bottom corner holes, and
    # cutting the screws first let the copy fill part of the pockets back in.
    if grip:
        body = grip(body)
    for (x, y) in SCREWS:
        body = body - Manifold.cylinder(FACE_T + 4, SCREW_D/2, SCREW_D/2, 0, False)\
                              .translate((x, y, -2))
        body = body - Manifold.cylinder(COUNTERBORE_DEPTH + 2, COUNTERBORE_D/2,
                                        COUNTERBORE_D/2, 0, False)\
                              .translate((x, y, FACE_T - COUNTERBORE_DEPTH))
    return body


def frame():
    body = prism(rrect(OUTER_W, OUTER_H, CORNER_R, OUTER_W/2, OUTER_H/2), 0, FRAME_T)
    body = body - prism(rrect(CAVITY_W, CAVITY_H, CAVITY_R, CAVITY_CX, CAVITY_CY),
                        -2, FRAME_T + 2)

    for (x, y) in SCREWS:
        body = body - Manifold.cylinder(FRAME_T + 4, SCREW_D/2, SCREW_D/2, 0, False)\
                              .translate((x, y, -2))

    y_top = CAVITY_CY + CAVITY_H/2.0     # inner face of the top wall
    y_bot = CAVITY_CY - CAVITY_H/2.0     # inner face of the bottom wall

    # headphone jack, through the top wall
    jack = CrossSection.circle(JACK_D/2.0).translate((JACK_X, JACK_Z))
    body = body - wall_opening(jack, JACK_CHAMF, y_top, OUTER_H)

    # dock connector, through the bottom wall
    dock = rrect(DOCK_W, DOCK_H, DOCK_R, DOCK_X, DOCK_Z)
    body = body - wall_opening(dock, DOCK_CHAMF, y_bot, 0.0)

    # Hold switch, through the top wall
    if HOLD:
        hold = rrect(HOLD['w'], HOLD['h'], HOLD['r'], HOLD['x'], HOLD['z'])
        body = body - wall_opening(hold, HOLD_CHAMF, y_top, OUTER_H)
    return body


def rear(grip=None):
    z_chamf = REAR_T - REAR_CHAMF_RISE
    body = Manifold.batch_hull([
        prism(rrect(OUTER_W, OUTER_H, CORNER_R, OUTER_W/2, OUTER_H/2), 0, z_chamf),
        prism(rrect(OUTER_W, OUTER_H, CORNER_R, OUTER_W/2, OUTER_H/2)
              .offset(-REAR_CHAMF_SETBACK, JoinType.Round), REAR_T - 1e-4, REAR_T),
    ])
    if grip:                                      # before the screws, see face()
        body = grip(body)
    for (x, y) in SCREWS:
        body = body - Manifold.cylinder(REAR_T + 4, SCREW_D/2, SCREW_D/2, 0, False)\
                              .translate((x, y, -2))
        body = body - Manifold.extrude(hexagon(HEX_AF, x, y), HEX_DEPTH + 2)\
                              .translate((0, 0, REAR_T - HEX_DEPTH))
    return body

# ============================================================================
# SIDE GRIP SCALLOPS
# ============================================================================
# Both plates carry a scallop along the side edges (y ~ 10..50) that forms a
# finger grip: a chamfer of slope 2.324 (the same as the click wheel) starting
# at z ~ 0.82 and running to the outer face. Its ends are not circular arcs, so
# instead of approximating the shape we transplant that region straight out of
# the original STL. The new part then matches the original exactly there.

def _stl_manifold(path):
    import numpy as np, struct
    from manifold3d import Mesh
    d = open(path, 'rb').read()
    n = struct.unpack('<I', d[80:84])[0]
    a = np.frombuffer(d[84:84+50*n], dtype=np.uint8).reshape(n, 50)
    tri = a[:, :48].copy().view('<f4').reshape(n, 4, 3)[:, 1:4, :].astype(np.float64)
    for i in range(3):
        tri[:, :, i] -= tri[:, :, i].min()
    u, inv = np.unique(np.round(tri.reshape(-1, 3), 4), axis=0, return_inverse=True)
    return Manifold(Mesh(vert_properties=u.astype(np.float32),
                         tri_verts=inv.reshape(-1, 3).astype(np.uint32)))


# boxes enclosing the two scallops, kept clear of the rounded corners
GRIP_BOXES = [(-1.0, 10.0, 7.0, 53.0), (OUTER_W - 10.0, OUTER_W + 1.0, 7.0, 53.0)]


def apply_grip_scallops(body, original_stl, dz, z_top):
    """Replace the two side regions with geometry from the original STL,
    shifted by dz in z."""
    import os
    if not os.path.exists(original_stl):
        print(f'  warning: {original_stl} missing - grip scallops not applied')
        return body
    orig = _stl_manifold(original_stl).translate((0, 0, dz))
    for (x0, x1, y0, y1) in GRIP_BOXES:
        box = Manifold.cube((x1 - x0, y1 - y0, z_top - dz + 1.0))\
                      .translate((x0, y0, dz))
        body = (body - box) + (orig ^ box)
    return body

# ============================================================================

def save_stl(man, path):
    import numpy as np, struct
    mesh = man.to_mesh()
    verts = np.asarray(mesh.vert_properties)[:, :3].astype('<f4')
    faces = np.asarray(mesh.tri_verts).astype(np.int64)
    tri = verts[faces]                                       # (n,3,3)
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(nrm, axis=1, keepdims=True)
    ln[ln == 0] = 1
    nrm = (nrm / ln).astype('<f4')
    buf = bytearray(b'\0' * 80 + struct.pack('<I', len(faces)))
    rec = np.zeros((len(faces), 50), dtype=np.uint8)
    rec[:, :12] = nrm.view(np.uint8).reshape(-1, 12)
    rec[:, 12:48] = tri.astype('<f4').view(np.uint8).reshape(-1, 36)
    buf += rec.tobytes()
    open(path, 'wb').write(bytes(buf))
    return len(faces)


if __name__ == '__main__':
    import sys, os
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, 'stl')

    parts = [
        ('face',        face,  'originals/simple-ipod-case-face.stl', FACE_T - 3.501, FACE_T),
        ('thick-frame', frame, None,                        0.0,            FRAME_T),
        ('rear',        rear,  'originals/simple-ipod-case-rear.stl', REAR_T - 3.500, REAR_T),
    ]
    for name, build, original, dz, z_top in parts:
        if original:
            src = os.path.join(base, original)
            man = build(grip=lambda b, src=src, dz=dz, z_top=z_top:
                        apply_grip_scallops(b, src, dz, z_top))
        else:
            man = build()
        path = os.path.join(out_dir, f'simple-ipod-case-{name}-v2.stl')
        ntri = save_stl(man, path)
        bb = man.bounding_box()
        print(f'{name:12s}  {ntri:6d} tri  vol={man.volume()/1000:7.3f} cm3  '
              f'genus={man.genus():3d}  status={man.status()}  '
              f'bbox=({bb[3]-bb[0]:.3f}, {bb[4]-bb[1]:.3f}, {bb[5]-bb[2]:.3f})')
