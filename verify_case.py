#!/usr/bin/env python3
"""
Geometric verification for the iPod Classic case.

Regenerates the three parts in memory (does not need the STLs on disk) and
checks the things a slicer or an assembly will not forgive:

  * each part is watertight, correctly wound, and has the expected topology
  * the waist's wall to the cavity is never thinner than WALL_SIDE
  * every corner screw keeps its known clearance to the cavity and the
    outer edge
  * the rear plate's hex/lightening pocket floors are at their design depth,
    and the pocket has its rim and floor edges bevelled, clear of the nuts
  * face and rear follow the frame's outline: identical to it at the face
    that seats against the frame, and never sticking out past it
  * both plates bevel the whole of each side edge between the corner pads,
    at the designed size, and leave the pads' own edges untouched
  * the three parts do not interfere when assembled, and face/rear seat
    flush against the frame with no gap

This is the check the ad-hoc scratchpad scripts kept re-deriving over the
course of the design changes; it now lives with the generator instead, so
a change that regresses one of them fails loudly instead of needing a new
one-off script to notice.

    python3 verify_case.py

Exits 0 if everything passes, 1 otherwise. Requires manifold3d, numpy and
trimesh (trimesh only for the watertight check: manifold3d's own status()
can read Error.NoError on a boolean whose *exported* mesh is non-manifold,
which is exactly the failure mode this project hit more than once).
"""
import sys
import numpy as np
from manifold3d import CrossSection, JoinType, Manifold

import generate_case as gc

FAILURES = []


def check(label, ok, detail=''):
    mark = 'OK  ' if ok else 'FAIL'
    print(f'  [{mark}] {label}' + (f'  -- {detail}' if detail else ''))
    if not ok:
        FAILURES.append(label)
    return ok


def probe_volume(man, x0, x1, y0, y1, z0, z1):
    box = Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))
    return (man ^ box).volume()


def build_parts():
    return {'face': gc.face(), 'thick-frame': gc.frame(), 'rear': gc.rear()}


def watertight(man):
    import trimesh
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as f:
        path = f.name
    try:
        gc.save_stl(man, path)
        m = trimesh.load(path)
        return bool(m.is_watertight), bool(m.is_winding_consistent)
    finally:
        os.unlink(path)


def main():
    parts = build_parts()
    expected_genus = {'face': 6, 'thick-frame': 8, 'rear': 4}

    print('=== 0) minimos de seguranca absolutos (independentes dos parametros atuais) ===')
    # These do not read back a parameter and check it equals itself -- they
    # are a floor the design must not go under, whatever a future change
    # sets WALL_SIDE, REAR_POCKET_KEEP etc. to. 2.5 mm/2.0 mm are the
    # thinnest walls this project has ever printed and trusted; below that
    # is unproven territory, not a hard physical limit.
    check('WALL_TOP >= 2.5 mm', gc.WALL_TOP >= 2.5, f'{gc.WALL_TOP:.2f} mm')
    check('WALL_BOTTOM >= 2.5 mm', gc.WALL_BOTTOM >= 2.5, f'{gc.WALL_BOTTOM:.2f} mm')
    check('WALL_SIDE >= 2.5 mm', gc.WALL_SIDE >= 2.5, f'{gc.WALL_SIDE:.2f} mm')
    check('REAR_POCKET_KEEP >= 2.0 mm', gc.REAR_POCKET_KEEP >= 2.0, f'{gc.REAR_POCKET_KEEP:.2f} mm')
    check('rear hex floor (REAR_T - HEX_DEPTH) >= 2.0 mm',
          gc.REAR_T - gc.HEX_DEPTH >= 2.0, f'{gc.REAR_T - gc.HEX_DEPTH:.2f} mm')
    check('face counterbore leaves >= 0.8 mm under the screw head',
          gc.FACE_T - gc.COUNTERBORE_DEPTH >= 0.8, f'{gc.FACE_T - gc.COUNTERBORE_DEPTH:.2f} mm')
    check('screw hole clearance (SCREW_D) is a real M3 clearance fit',
          3.1 <= gc.SCREW_D <= 3.4, f'{gc.SCREW_D:.2f} mm')
    # The owner asked for these edges to be softened; a bevel shrunk to
    # nothing would still pass every shape check below, since those follow
    # the parameters.
    check('side bevel is a real edge break (SIDE_BEVEL_H >= 0.5 mm)',
          gc.SIDE_BEVEL_H >= 0.5, f'{gc.SIDE_BEVEL_H:.2f} mm')
    check('rear pocket bevels are real edge breaks (REAR_POCKET_BEVEL_H >= 0.5 mm)',
          gc.REAR_POCKET_BEVEL_H >= 0.5, f'{gc.REAR_POCKET_BEVEL_H:.2f} mm')

    print('\n=== 1) estanqueidade, winding e topologia ===')
    for name, man in parts.items():
        wt, wind = watertight(man)
        check(f'{name:12s} watertight', wt)
        check(f'{name:12s} winding consistente', wind)
        check(f'{name:12s} genus == {expected_genus[name]}',
              man.genus() == expected_genus[name], f'genus={man.genus()}')
        check(f'{name:12s} status Manifold', str(man.status()) == 'Error.NoError',
              str(man.status()))

    print('\n=== 2) parede da cintura fina ate a cavidade (frame) ===')
    frame = parts['thick-frame']
    # comfortably past PAD_R from each corner, so no pad contributes here
    y0 = gc.SCREW_EDGE_Y + gc.SCREW_D/2.0 + gc.PAD_R + 3.0
    y1 = gc.OUTER_H - y0
    for y in np.linspace(y0, y1, 5):
        keep = gc.WALL_SIDE
        wall = probe_volume(frame, gc.CAVITY_CX - gc.CAVITY_W/2 - keep,
                             gc.CAVITY_CX - gc.CAVITY_W/2, y, y + 0.5, 4.0, 10.0)
        beyond = probe_volume(frame, 0.0, gc.CAVITY_CX - gc.CAVITY_W/2 - keep,
                               y, y + 0.5, 4.0, 10.0)
        expected = keep * 0.5 * 6.0
        check(f'y={y:6.2f}  parede == {keep:.2f} mm', abs(wall - expected) < 1e-3,
              f'{wall:.3f} mm3 (esperado {expected:.3f})')
        check(f'y={y:6.2f}  nada alem da parede', beyond < 1e-6, f'{beyond:.4f} mm3')

    print('\n=== 3) folga dos parafusos de canto ===')
    # Measured on the solid, not calculated along one axis: a formula that
    # only looks at the flat wall misses the cavity's own rounded corner,
    # which is closer in some directions and further in others. A ring at
    # MARGIN beyond the hole must be fully covered by material -- if it
    # is not, `missing` says exactly how much and where the shortfall is.
    MARGIN = 1.5
    for (x, y) in gc.SCREWS:
        ring = CrossSection.circle(gc.SCREW_D/2.0 + MARGIN).translate((x, y)) \
             - CrossSection.circle(gc.SCREW_D/2.0).translate((x, y))
        tool = Manifold.extrude(ring, gc.FRAME_T)
        missing = (tool - frame).volume()
        check(f'parafuso ({x:.2f},{y:.2f}) anel de +{MARGIN:.1f} mm coberto',
              missing < 1e-3, f'{missing:.4f} mm3 faltando')

    print('\n=== 4) piso do bolsao da traseira e dos encaixes de porca ===')
    rear = parts['rear']
    rx0 = gc.SCREW_EDGE_X + gc.HEX_AF/np.sqrt(3.0) + gc.REAR_POCKET_CLEAR
    ry0 = gc.SCREW_EDGE_Y + gc.HEX_AF/np.sqrt(3.0) + gc.REAR_POCKET_CLEAR
    cx, cy = (rx0 + (gc.OUTER_W - rx0))/2.0, (ry0 + (gc.OUTER_H - ry0))/2.0
    floor = probe_volume(rear, cx - 0.25, cx + 0.25, cy - 0.25, cy + 0.25, 0.0, gc.REAR_T + 1)
    expected_floor = 0.5 * 0.5 * gc.REAR_POCKET_KEEP
    check('piso do bolsao central == REAR_POCKET_KEEP', abs(floor - expected_floor) < 1e-3,
          f'{floor:.4f} mm3 (esperado {expected_floor:.4f})')
    hex_rc = gc.HEX_AF / np.sqrt(3.0)
    for (x, y) in gc.SCREWS:
        # offset from the screw's own axis (empty for the shaft) but still
        # inside the hex boss, to measure the floor around it
        px = x + hex_rc * (-1 if x > gc.OUTER_W/2 else 1) * 0.6
        hex_floor = probe_volume(rear, px - 0.25, px + 0.25, y - 0.25, y + 0.25,
                                  0.0, gc.REAR_T - gc.HEX_DEPTH)
        expected_hex_floor = 0.5 * 0.5 * (gc.REAR_T - gc.HEX_DEPTH)
        check(f'piso do encaixe de porca ({x:.2f},{y:.2f})',
              abs(hex_floor - expected_hex_floor) < 1e-3,
              f'{hex_floor:.4f} mm3 (esperado {expected_hex_floor:.4f})')

    print('\n=== 4b) bolsao da traseira com as duas arestas chanfradas ===')
    # Same approach as 5b: the rear plate built without its pocket, minus the
    # real one, must be exactly a pocket built here from the parameters --
    # rim bevel out to the mouth, straight wall, floor bevel in to the floor,
    # floor at REAR_POCKET_KEEP. Then the webs it leaves at the outer face.
    def rr(w_, h_, r_, cx_, cy_):
        return CrossSection.square((w_ - 2*r_, h_ - 2*r_), center=True) \
            .offset(r_, JoinType.Round).translate((cx_, cy_))

    def ext(cs, z0, z1):
        return Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))

    ph = gc.REAR_POCKET_BEVEL_H
    pw = gc.REAR_POCKET_BEVEL_SLOPE * ph
    rx1, ry1 = gc.OUTER_W - rx0, gc.OUTER_H - ry0
    nominal = rr(rx1 - rx0, ry1 - ry0, gc.REAR_POCKET_R, cx, cy)
    zf, za, zb, zt = gc.REAR_POCKET_KEEP, gc.REAR_POCKET_KEEP + ph, gc.REAR_T - ph, gc.REAR_T
    pocket = (Manifold.batch_hull([ext(nominal.offset(-pw, JoinType.Round), zf, zf + 1e-4),
                                   ext(nominal, za, za + 1e-4)])
              + ext(nominal, za - 1e-3, zb + 1e-3)
              + Manifold.batch_hull([ext(nominal, zb - 1e-4, zb),
                                     ext(nominal.offset(pw, JoinType.Round), zt, zt + 1.0)]))
    saved_pocket = gc.rear_pocket
    gc.rear_pocket = lambda: Manifold()
    try:
        no_pocket = gc.rear()
    finally:
        gc.rear_pocket = saved_pocket
    removed = no_pocket - rear
    extra = (removed - pocket).volume()
    missing = ((no_pocket ^ pocket) - removed).volume()
    added = (rear - no_pocket).volume()
    check('bolsao nao acrescenta material', added < 0.05, f'{added:.4f} mm3')
    check('nada removido fora do bolsao teorico (chanfros, parede, piso)', extra < 0.05,
          f'{max(extra, 0.0):.4f} mm3')
    check('bolsao teorico removido por inteiro', missing < 0.05,
          f'{missing:.4f} mm3 faltando de {(no_pocket ^ pocket).volume():.1f}')

    top = rear.slice(gc.REAR_T - 1e-4)        # any lower and the rim bevel reads wider webs
    polys = top.to_polygons()
    def signed(p_):
        n_ = len(p_)
        return 0.5 * sum(p_[i][0]*p_[(i+1) % n_][1] - p_[(i+1) % n_][0]*p_[i][1] for i in range(n_))
    holes = sorted([q for q in polys if signed(q) < 0], key=signed)   # biggest first
    mouth = CrossSection([[tuple(v) for v in reversed(holes[0])]])
    others = None
    for q in holes[1:]:
        c_ = CrossSection([[tuple(v) for v in reversed(q)]])
        others = c_ if others is None else others + c_
    outline = CrossSection([[tuple(v) for v in q] for q in polys if signed(q) > 0])
    lo, hi = 0.0, 10.0
    for _ in range(25):                          # largest clear offset of the mouth
        g = (lo + hi) / 2.0
        grown = mouth.offset(g, JoinType.Round)
        if (grown ^ others).area() < 1e-6 and (grown - outline).area() < 1e-6:
            lo = g
        else:
            hi = g
    check('parede entre a boca do bolsao e sextavados/borda >= 2.0 mm', lo >= 2.0,
          f'{lo:.2f} mm na face externa')

    print('\n=== 5) tampas acompanham o contorno do frame ===')
    # The frame is the reference. Comparing bounding boxes is not enough:
    # plates that overhung the frame by 4.3 mm along the side passed a bbox
    # check, because the corner pads already set the same extremes. So full
    # outlines are compared, three ways:
    #   a) at the face that seats on the frame, against the frame's own
    #      seating face (z = FRAME_T for the face plate, z = 0 for the rear)
    #   b) at several heights, everywhere except the side bevel band, the
    #      plate must be exactly the frame's outline (the bevel itself, and
    #      that it spares the pads, is checked in 3D in 5b)
    #   c) no plate volume anywhere outside the frame's outline
    def outer_outline(cs):
        """Outer boundaries only (counter-clockwise contours), holes dropped."""
        keep = []
        for p in cs.to_polygons():
            n = len(p)
            area2 = sum(p[i][0]*p[(i+1) % n][1] - p[(i+1) % n][0]*p[i][1] for i in range(n))
            if area2 > 0:
                keep.append([tuple(v) for v in p])
        return CrossSection(keep)

    def xor_area(a, b):
        return (a - b).area() + (b - a).area()

    # The bevel band, derived here rather than read from the generator: the
    # straight waist edge x_w, and the y where each pad's arc reaches it.
    x_w = (gc.OUTER_W - gc.OUTER_W_THIN) / 2.0
    dy = np.sqrt(gc.PAD_R**2 - (gc.CORNER_R - x_w)**2)
    span0, span1 = gc.CORNER_R + dy, gc.OUTER_H - gc.CORNER_R - dy
    bevel_w = gc.SIDE_BEVEL_SLOPE * gc.SIDE_BEVEL_H
    strip_w = x_w + bevel_w + 0.5
    band = CrossSection.square((strip_w + 1.0, span1 - span0)).translate((-1.0, span0)) \
         + CrossSection.square((strip_w + 1.0, span1 - span0)).translate((gc.OUTER_W - strip_w, span0))

    TOL_AREA, TOL_VOL = 0.5, 0.5        # simplify() noise measures < 0.1
    seat = {'face': outer_outline(frame.slice(gc.FRAME_T - 0.05)),
            'rear': outer_outline(frame.slice(0.05))}
    frame_fp = outer_outline(frame.project())
    for name, t in (('face', gc.FACE_T), ('rear', gc.REAR_T)):
        plate = parts[name]
        x = xor_area(outer_outline(plate.slice(0.05)), seat[name])
        check(f'{name:12s} contorno na face de contato == frame', x < TOL_AREA,
              f'diferenca {x:.3f} mm2')
        for z in (0.05, t / 2.0, t - 0.05):
            x = xor_area(outer_outline(plate.slice(z)) - band, frame_fp - band)
            check(f'{name:12s} z={z:4.2f} ressaltos e topo/base == frame', x < TOL_AREA,
                  f'diferenca {x:.3f} mm2')
        outside = (plate - gc.prism(frame_fp, -1.0, t + 1.0)).volume()
        check(f'{name:12s} nada para fora do contorno do frame', outside < TOL_VOL,
              f'{outside:.3f} mm3 para fora')

    print('\n=== 5b) chanfro lateral das tampas, so entre os ressaltos ===')
    # Sampling edges at a handful of points let a 10 mm gap in the bevel, a
    # notch inside a pad and a cut that ignored the pad arc all pass. So each
    # plate is compared in 3D against the same plate built with no bevel, and
    # what was removed must be exactly the theoretical bevel -- built here
    # from the parameters, not by calling the generator's own cutter:
    #   * nothing added
    #   * nothing removed outside the theoretical bevel (slot, extra depth)
    #   * nothing of the theoretical bevel left in place (gap, short end)
    #   * nothing removed inside any pad disc
    corners = [(gc.CORNER_R, gc.CORNER_R), (gc.OUTER_W - gc.CORNER_R, gc.CORNER_R),
               (gc.CORNER_R, gc.OUTER_H - gc.CORNER_R),
               (gc.OUTER_W - gc.CORNER_R, gc.OUTER_H - gc.CORNER_R)]
    discs = None
    for (cx_, cy_) in corners:
        d = CrossSection.circle(gc.PAD_R).translate((cx_, cy_))
        discs = d if discs is None else discs + d

    def theoretical_bevel(t):
        sl, h = gc.SIDE_BEVEL_SLOPE, gc.SIDE_BEVEL_H
        tri = CrossSection([[(x_w - 1.0, t - h - 1.0 / sl),
                             (x_w + sl * h + sl, t + 1.0),
                             (x_w - 1.0, t + 1.0)]])
        # extrude along +z, then turn so the extrusion runs along +y and the
        # triangle's second coordinate becomes world z
        left = Manifold.extrude(tri, span1 - span0).rotate((90, 0, 0)).translate((0, span1, 0))
        both = left + left.mirror((1, 0, 0)).translate((gc.OUTER_W, 0, 0))
        return both - Manifold.extrude(discs, t + 4.0).translate((0, 0, -1.0))

    saved = gc.side_bevels
    gc.side_bevels = lambda t: Manifold()
    try:
        plain = {'face': gc.face(), 'rear': gc.rear()}
    finally:
        gc.side_bevels = saved

    TOL = 0.05                                   # mm3; tessellation noise < 0.01
    for name, t in (('face', gc.FACE_T), ('rear', gc.REAR_T)):
        plate, ref = parts[name], plain[name]
        wedge = theoretical_bevel(t)
        bb = wedge.bounding_box()
        z_lo = t - gc.SIDE_BEVEL_H - 1.0 / gc.SIDE_BEVEL_SLOPE
        if not (abs(bb[2] - z_lo) < 0.01 and abs(bb[5] - (t + 1.0)) < 0.01
                and abs(bb[1] - span0) < 0.01 and abs(bb[4] - span1) < 0.01):
            check(f'{name:12s} chanfro teorico mal posicionado', False, str(bb))
            continue
        removed = ref - plate
        added = (plate - ref).volume()
        extra = (removed - wedge).volume()
        missing = ((ref ^ wedge) - removed).volume()
        in_pads = (removed ^ Manifold.extrude(discs, t + 4.0).translate((0, 0, -1.0))).volume()
        check(f'{name:12s} chanfro nao acrescenta material', added < TOL, f'{added:.4f} mm3')
        check(f'{name:12s} nada removido fora do chanfro teorico', extra < TOL, f'{extra:.4f} mm3')
        check(f'{name:12s} chanfro completo nas 2 laterais, de ressalto a ressalto',
              missing < TOL, f'{missing:.4f} mm3 faltando de {(ref ^ wedge).volume():.3f}')
        check(f'{name:12s} nada removido dos ressaltos', in_pads < TOL / 5, f'{in_pads:.5f} mm3')

    print('\n=== 6) interferencia e encaixe na montagem ===')
    face_mounted = parts['face'].translate((0, 0, gc.FRAME_T))
    rear_mounted = parts['rear'].mirror((0, 0, 1))
    fi = (frame ^ face_mounted).volume()
    ri = (frame ^ rear_mounted).volume()
    check('frame x face sem interferencia', fi < 1e-6, f'{fi:.6f} mm3')
    check('frame x rear sem interferencia', ri < 1e-6, f'{ri:.6f} mm3')
    # zero interference alone would also pass a plate floating 1 mm away:
    # pushed 0.05 mm into the frame, each plate must start to overlap it
    fc = (frame ^ face_mounted.translate((0, 0, -0.05))).volume()
    rc = (frame ^ rear_mounted.translate((0, 0, 0.05))).volume()
    check('face encosta no frame (sem folga)', fc > 1.0, f'{fc:.2f} mm3 a 0.05 mm')
    check('rear encosta no frame (sem folga)', rc > 1.0, f'{rc:.2f} mm3 a 0.05 mm')

    print('\n=== 7) resumo dimensional ===')
    total = sum(m.volume() for m in parts.values()) / 1000.0
    print(f'  volume total: {total:.3f} cm3  (~{total*1.191:.1f} g em PLA)')
    print(f'  contorno externo: {gc.OUTER_W:.2f} x {gc.OUTER_H:.2f} mm, '
          f'cavidade {gc.CAVITY_W:.2f} x {gc.CAVITY_H:.2f} x {gc.FRAME_T:.2f} mm')

    print()
    if FAILURES:
        print(f'{len(FAILURES)} verificacao(oes) falharam:')
        for f in FAILURES:
            print(f'  - {f}')
        return 1
    print('Todas as verificacoes passaram.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
