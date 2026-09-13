#!/usr/bin/env python3
"""
Geometric verification for the iPod Classic case.

Regenerates the three parts in memory (does not need the STLs on disk) and
checks the things a slicer or an assembly will not forgive:

  * each part is watertight, correctly wound, and has the expected topology
  * the waist's wall to the cavity is never thinner than WALL_SIDE
  * every corner screw keeps its known clearance to the cavity and the
    outer edge
  * the rear plate's hex/lightening pocket floors are at their design depth
  * face and rear follow the frame's outline: identical to it at the face
    that seats against the frame, and never sticking out past it
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
from manifold3d import CrossSection, Manifold

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
    base = gc.__file__.rsplit('/', 1)[0]
    face = gc.face(grip=lambda b, src=f'{base}/originals/simple-ipod-case-face.stl',
                   dz=gc.FACE_T - 3.501, z_top=gc.FACE_T:
                   gc.apply_grip_scallops(b, src, dz, z_top))
    frame = gc.frame()
    rear = gc.rear(grip=lambda b, src=f'{base}/originals/simple-ipod-case-rear.stl',
                   dz=gc.REAR_T - 3.500, z_top=gc.REAR_T:
                   gc.apply_grip_scallops(b, src, dz, z_top))
    return {'face': face, 'thick-frame': frame, 'rear': rear}


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

    print('\n=== 5) tampas acompanham o contorno do frame ===')
    # The frame is the reference. Comparing bounding boxes is not enough:
    # plates that overhung the frame by 4.3 mm along the grip band passed a
    # bbox check, because the corner pads already set the same extremes.
    # So full outlines are compared, three ways:
    #   a) at the face that seats on the frame, against the frame's own
    #      seating face (z = FRAME_T for the face plate, z = 0 for the rear)
    #   b) at several heights, outside GRIP_BOXES, the plate must still be
    #      exactly the frame's outline -- catches a notch or a bevel coming
    #      back anywhere else, which (a) and (c) cannot see
    #   c) no plate volume anywhere outside the frame's outline
    # Inside GRIP_BOXES the plates are allowed to recede (the scallop).
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

    TOL_AREA, TOL_VOL = 0.5, 0.5        # simplify() noise measures < 0.1
    grip_mask = None
    for (x0, x1, y0, y1) in gc.GRIP_BOXES:
        sq = CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))
        grip_mask = sq if grip_mask is None else grip_mask + sq

    seat = {'face': outer_outline(frame.slice(gc.FRAME_T - 0.05)),
            'rear': outer_outline(frame.slice(0.05))}
    frame_fp = outer_outline(frame.project())
    for name, t in (('face', gc.FACE_T), ('rear', gc.REAR_T)):
        plate = parts[name]
        x = xor_area(outer_outline(plate.slice(0.05)), seat[name])
        check(f'{name:12s} contorno na face de contato == frame', x < TOL_AREA,
              f'diferenca {x:.3f} mm2')
        for z in (0.05, t / 2.0, t - 0.05):
            x = xor_area(outer_outline(plate.slice(z)) - grip_mask, frame_fp - grip_mask)
            check(f'{name:12s} z={z:4.2f} contorno == frame fora do grip', x < TOL_AREA,
                  f'diferenca {x:.3f} mm2')
        outside = (plate - gc.prism(frame_fp, -1.0, t + 1.0)).volume()
        check(f'{name:12s} nada para fora do contorno do frame', outside < TOL_VOL,
              f'{outside:.3f} mm3 para fora')

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
