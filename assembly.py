#!/usr/bin/env python3
"""
Draw assembly.png: how the three v2 parts, the iPod and the hardware go
together.

    .venv/bin/python3 assembly.py

The parts come from generate_case.py, the same geometry as the STLs. The iPod,
the M3 x 20 button-head screws and the M3 nuts are simple stand-ins, sized
from the numbers in the README. Rendering is plain matplotlib: flat-shaded
triangles drawn back to front, with long triangles split first so the
drawing order holds up inside the pockets.

Requires matplotlib on top of generate_case.py's own requirements.
"""
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from manifold3d import Manifold, CrossSection

import generate_case as gc

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- stand-ins ---------------------------------------------------------------
IPOD_W, IPOD_H, IPOD_T, IPOD_R = 61.8, 103.5, 13.5, 5.0     # Classic 6th gen 160 GB
SCREW_L, HEAD_D, HEAD_H = 20.0, 5.7, 1.65                    # ISO 7380 M3 x 20
NUT_AF, NUT_T = 5.5, 2.4                                     # M3 hex nut

COLOURS = {
    'face':   (0.40, 0.55, 0.72),
    'frame':  (0.83, 0.67, 0.43),
    'rear':   (0.47, 0.63, 0.50),
    'ipod':   (0.86, 0.86, 0.88),
    'screen': (0.12, 0.13, 0.16),
    'wheel':  (0.97, 0.97, 0.97),
    'button': (0.78, 0.78, 0.80),
    'steel':  (0.60, 0.62, 0.66),
}
MAX_EDGE = 1.5          # mm; longer triangle edges are split before drawing


def ipod():
    """iPod body, screen, click wheel and centre button as side-by-side
    full-height columns, so each can take its own colour. (Thin tiles over the
    body would leave its top face just under them, which the back-to-front
    drawing order shows through.)"""
    z0, z1 = gc.FRAME_T - IPOD_T, gc.FRAME_T
    outline = gc.rrect(IPOD_W, IPOD_H, IPOD_R, gc.CAVITY_CX, gc.CAVITY_CY)
    screen = gc.rrect(gc.SCREEN_W - 2.0, gc.SCREEN_H - 2.0, 1.0, gc.SCREEN_CX, gc.SCREEN_CY)
    wheel = CrossSection.circle(18.25).translate((gc.WHEEL_CX, gc.WHEEL_CY))
    button = CrossSection.circle(6.75).translate((gc.WHEEL_CX, gc.WHEEL_CY))
    column = lambda cs: gc.prism(cs, z0, z1)
    return {'ipod': column(outline - screen - wheel), 'screen': column(screen),
            'wheel': column(wheel - button), 'button': column(button)}


def screw(x, y):
    """Button-head screw seated on the face counterbore floor, pointing down."""
    z_seat = gc.FRAME_T + gc.FACE_T - gc.COUNTERBORE_DEPTH
    head = Manifold.batch_hull([
        gc.prism(CrossSection.circle(HEAD_D / 2), z_seat, z_seat + 0.5),
        gc.prism(CrossSection.circle(HEAD_D / 2 - 1.0), z_seat + HEAD_H - 0.01, z_seat + HEAD_H)])
    head = head - gc.prism(gc.hexagon(2.0), z_seat + 0.6, z_seat + HEAD_H + 1)
    shank = gc.prism(CrossSection.circle(1.5), z_seat - SCREW_L, z_seat + 0.01)
    return (head + shank).translate((x, y, 0))


def nut(x, y):
    """Nut on its pocket's seat in the rear plate, which is mounted outer face
    down below the frame."""
    z_top = -(gc.REAR_T - gc.HEX_DEPTH)
    body = gc.prism(gc.hexagon(NUT_AF, x, y), z_top - NUT_T, z_top)
    return body - gc.prism(CrossSection.circle(1.5).translate((x, y)), z_top - NUT_T - 1, z_top + 1)


def assembled():
    """Every piece in its assembled place, as {name: [(Manifold, colour key)]}."""
    pieces = {
        'face':  [(gc.face().translate((0, 0, gc.FRAME_T)), 'face')],
        'frame': [(gc.frame(), 'frame')],
        'rear':  [(gc.rear().mirror((0, 0, 1)), 'rear')],
        'ipod':  [(m, key) for key, m in ipod().items()],
        'screws': [(screw(x, y), 'steel') for (x, y) in gc.SCREWS],
        'nuts':  [(nut(x, y), 'steel') for (x, y) in gc.SCREWS],
    }
    return pieces


# ---- rendering ---------------------------------------------------------------

def triangles(man, dz=0.0):
    mesh = man.translate((0, 0, dz)).to_mesh()
    T = np.asarray(mesh.vert_properties)[:, :3][np.asarray(mesh.tri_verts)]
    for _ in range(12):
        e = np.stack([np.linalg.norm(T[:, (i + 1) % 3] - T[:, i], axis=1) for i in range(3)], axis=1)
        longest = e.argmax(axis=1)
        split = e.max(axis=1) > MAX_EDGE
        if not split.any():
            break
        keep, S = T[~split], T[split]
        k = longest[split]
        idx = np.arange(len(S))
        a, b, c = S[idx, k], S[idx, (k + 1) % 3], S[idx, (k + 2) % 3]
        m = (a + b) / 2.0
        T = np.concatenate([keep, np.stack([a, m, c], 1), np.stack([m, b, c], 1)])
    N = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    return T, N


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def render(ax, items, view, title, up=(0, 1, 0), focus=None, labels=()):
    """items: [(T, N, rgb)]. view points from the scene towards the camera.
    focus: (3D point, half-width in mm) to crop to. labels: [(text, T)]."""
    d = unit(view)
    rx = unit(np.cross(up, d))
    ry = np.cross(d, rx)
    light = unit(-0.45 * rx + 0.60 * ry + 0.65 * d)
    polys, colours = [], []
    for T, N, rgb in items:
        vis = N @ d > 1e-3
        t, n = T[vis], N[vis]
        shade = 0.42 + 0.72 * np.clip(n @ light, 0, 1)
        polys.append(t)
        colours.append(np.clip(np.asarray(rgb)[None, :] * shade[:, None], 0, 1))
    t, c = np.concatenate(polys), np.concatenate(colours)
    order = np.argsort(t.mean(axis=1) @ d)
    t, c = t[order], c[order]
    xy = np.stack([t @ rx, t @ ry], axis=-1)
    if focus is not None:
        p, half = focus
        cx, cy = np.asarray(p) @ rx, np.asarray(p) @ ry
        near = (np.abs(xy[..., 0].mean(1) - cx) < half * 4) & (np.abs(xy[..., 1].mean(1) - cy) < half * 4)
        xy, c = xy[near], c[near]
        ax.set_xlim(cx - half, cx + half)
        ax.set_ylim(cy - half, cy + half)
    else:
        ax.set_xlim(xy[..., 0].min() - 3, xy[..., 0].max() + 3)
        ax.set_ylim(xy[..., 1].min() - 3, xy[..., 1].max() + 3)
    # edges in the face colour, wide enough to close the anti-aliasing seams
    # between neighbouring triangles
    ax.add_collection(PolyCollection(xy, facecolors=c, edgecolors=c, linewidths=0.6))
    if labels:
        column = xy[..., 0].max() + 12
        for text, T in labels:
            px, py = T.reshape(-1, 3) @ rx, T.reshape(-1, 3) @ ry
            y = 0.5 * (py.min() + py.max())
            ax.annotate(text, xy=(px.max() + 1, y), xytext=(column, y),
                        fontsize=15, color='#222', va='center',
                        arrowprops=dict(arrowstyle='-', color='#888', lw=0.8))
        lo, hi = ax.get_xlim()
        ax.set_xlim(lo, column + 92)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=15, color='#333')


def main():
    pieces = assembled()

    def tris(names, offsets=None):
        out = {}
        for name in names:
            dz = (offsets or {}).get(name, 0.0)
            out[name] = [triangles(m, dz) + (COLOURS[key],) for (m, key) in pieces[name]]
        return out

    everything = ('face', 'frame', 'rear', 'ipod', 'screws', 'nuts')
    together = tris(everything)
    flat = lambda group: [item for name in group for item in together[name]]

    # exploded along z, in assembly order from the bottom up
    lift = {'nuts': -150.0, 'rear': -62.0, 'frame': 0.0, 'ipod': 62.0, 'face': 120.0, 'screws': 165.0}
    apart = tris(everything, lift)
    label_of = {'screws': '4 × M3 × 20 screws',
                'face': 'face plate',
                'ipod': 'iPod, screen up',
                'frame': 'frame, printed top up',
                'rear': 'rear plate, pockets down',
                'nuts': '4 × M3 nuts'}
    labels = [(label_of[n], np.concatenate([T for (T, N, rgb) in apart[n]])) for n in
              ('screws', 'face', 'ipod', 'frame', 'rear', 'nuts')]

    fig = plt.figure(figsize=(18, 13), facecolor='white')
    grid = fig.add_gridspec(2, 3, width_ratios=[1.7, 1, 1])
    front, back = (0.55, -0.75, 1.0), (0.55, -0.75, -1.0)

    # z up, the case's length across the picture, seen from above its right side
    render(fig.add_subplot(grid[:, 0]), [i for n in everything for i in apart[n]],
           (1.0, 0.3, 0.85), 'exploded — assembly order', up=(0, 0, 1), labels=labels)
    render(fig.add_subplot(grid[0, 1]), flat(everything), front, 'assembled — front')
    render(fig.add_subplot(grid[1, 1]), flat(everything), back, 'assembled — back')

    sx, sy = gc.SCREWS[2]                          # top-left corner
    render(fig.add_subplot(grid[0, 2]), flat(everything), (0.3, -0.45, 1.0),
           'screw head in a face counterbore',
           focus=((sx + 5, sy - 5, gc.FRAME_T + gc.FACE_T), 14.0))
    render(fig.add_subplot(grid[1, 2]), flat(everything), (-0.3, -0.45, -1.0),
           'nut in a rear hex pocket',
           focus=((sx + 5, sy - 5, -gc.REAR_T), 14.0))

    fig.tight_layout()
    out = os.path.join(HERE, 'assembly.png')
    fig.savefig(out, dpi=90, facecolor='white')
    print('->', out)


if __name__ == '__main__':
    main()
