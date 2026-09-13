# iPod Classic case — v2

A reworked three-piece screw-together case for the iPod Classic. The three
parts sandwich the iPod: a face plate with the screen and click-wheel
openings, a thick middle frame that holds the device, and a plain rear plate.

Everything is generated from [`generate_case.py`](generate_case.py), so the
design is parametric — edit the numbers at the top and run it again.

## What changed from the original

| | original | v2 |
|---|---|---|
| rear plate | 3.50 mm | **5.00 mm** |
| screw length | nothing standard fitted | **M3 × 20, flush** |
| Hold switch | no opening | **14.0 × 5.0 mm window** |
| jack / dock / Hold openings | straight bores | **flared outwards** |
| bottom wall | 5.00 mm | **3.00 mm**, same as the top |
| outer size | 76.80 × 112.20 mm | **76.80 × 110.20 mm** |
| frame/face/rear side walls | solid, 7.30 mm all round | **thin waist, thick only at the screws** |
| face/rear edge chamfer | decorative bevel (from the original) | **removed — follows the frame's outline instead** |

### Screw length

On the original the path from the counterbore floor to the outer face of the
rear plate measured **18.54 mm**, so an M3 × 20 stood 1.46 mm proud. M3 × 16
could never work: the frame alone is 14 mm, which leaves 2 mm to cross both
plates *and* engage the nut — less than the 2.40 mm thickness of the nut.

The fix was to thicken the rear plate, not the face plate. The rear is a plain
slab, so thickness costs nothing there; thickening the face would sink the
screen and click wheel to the bottom of deeper wells.

| | |
|---|---|
| material under the screw head | 1.000 mm |
| frame | 14.000 mm |
| rear web to the nut | 2.500 mm |
| nut pocket | 2.500 mm |
| **total** | **20.000 mm** |

An M3 × 20 now ends flush with the outer face, with 2.50 mm of thread engaged
in a 2.40 mm nut. Assembled height went from 21.00 to 22.50 mm.

### Weight reduction

An earlier revision added two extra screws at mid height on the side walls,
for six in total. They never had much clamping to offer — the four corners
already hold the plates flat — and they were the design's weakest point: only
0.97 mm of wall between the hole and the iPod cavity, the thinnest feature in
the whole case.

Back to four corner screws, the entire span between them on each side wall is
free — nothing needs to be routed through it any more. Rather than keep the
full 7.30 mm side wall and hollow it out from inside, the outer silhouette
itself now only carries that thickness where a screw actually needs it —
the same idea as the [iPhone 13 rugged case](https://github.com/zmacario/iphone13-rugged-case)'s
frame, which thickens only around its own screws instead of a uniform wall:

- **Side walls (all three parts)** thin down to 3.00 mm — the same thickness
  already proven by the top/bottom walls — everywhere except within reach of
  a corner screw. There, a local pad restores the original 7.30 mm, blending
  into the thin waist smoothly enough that it needed no explicit fillet.
- **Rear plate** additionally keeps its own pocket across the flat outer
  face, clear of the four screw/nut bosses and the grip scallops, leaving
  2.50 mm to the inner face (the same floor thickness already proven by the
  hex nut pockets).

Face and rear share the exact same outline as the frame, at every height —
which also meant dropping the decorative edge chamfer the original design
had on both plates: the waist isn't convex, so it fought the usual
hull-based taper that built that bevel (see
[Regenerating](#regenerating)). Face and rear are now a plain extrusion of
the same waisted outline as the frame, so all three meet flush at every
edge, with no bevel where they meet.

The grip scallop on the sides is transplanted from the original mesh (see
[Regenerating](#regenerating)) and keeps its original, unthinned thickness —
a deliberately thicker band for the fingers to grip, not an oversight. All
**three** parts need that transplant, the frame included: its waist runs
right through the same span, and without it the frame's edge sat up to
3.8 mm inside the plates' there -- an early version of this change shipped
with only the plates transplanted, which is exactly that bug. `verify_case.py`
now checks the grip band's edge position against the frame specifically, so
it cannot silently come back.

| part | original | pockets only | thin waist + pads |
|---|---|---|---|
| face | 15.99 cm³ | 15.61 cm³ | 14.70 cm³ |
| frame | 27.43 cm³ | 18.42 cm³ | 20.74 cm³ |
| rear | 41.39 cm³ | 28.89 cm³ | 26.83 cm³ |
| **total** | **84.81 cm³** | **62.92 cm³** | **62.28 cm³** |

Still meaningfully lighter than the original, though the frame's own grip
transplant gives some of the pocket-based savings back — that material was
never optional, it is what keeps the frame flush with the plates. All three
parts are verified watertight, with the waist's wall measured at exactly
3.00 mm to the cavity outside the grip band, and the corner screws keeping
their original margins (1.87 mm to the cavity, 2.02 mm to the outer edge).

### Flared openings

The jack, dock and Hold openings widen from the cavity towards the outer face
with the same slope as the screen window chamfer (0.6403). Each setback is the
largest the surroundings allow while keeping 1.10 mm of material to the frame
edge:

| opening | inner | outer | setback/side |
|---|---|---|---|
| headphone jack | Ø10.00 | Ø11.20 | 0.60 |
| Hold switch | 14.00 × 5.00 | 16.40 × 7.40 | 1.20 |
| dock connector | 28.83 × 7.94 | 31.23 × 10.34 | 1.20 |

The jack gets half the setback of the others because a Ø10 hole in a 14 mm
frame leaves only 1.71 mm of material above it.

### Bottom wall

The original frame had a 5.00 mm bottom wall and a 3.00 mm top wall. Both
are now 3.00 mm. That works because the top corner screws already sat
against a 3.00 mm wall, clearing the cavity by 1.87 mm and the outer corner
by 2.02 mm; the bottom corners now mirror them exactly.

The iPod cavity does not change, so **the whole case is 2.0 mm shorter**, and
all three parts change with it. Everything positioned against the iPod — the
cavity, the screen window, the click wheel, the jack and the Hold window — is
measured from the cavity floor and stays exactly where it was relative to the
device, and the side grip scallop keeps its distance from the bottom edge.

The dock flare still fits, with 1.13 mm of straight bore ahead of it. The one
trade-off is the material bridging the dock cutout: it is now 3 mm deep
instead of 5 mm.

## Fit

The cavity is **62.20 × 104.20 × 14.00 mm**. Width and height suit any
full-size iPod (61.8 × 103.5 mm); the 14 mm depth is what picks the model:

- **iPod 5th gen 60/80 GB** — 14.0 mm, exact, no slack
- **iPod Classic 6th gen 160 GB (2007)** — 13.5 mm, 0.5 mm slack (tested)
- **Classic 6th/7th gen 10.5 mm models** — 3.5 mm of slack, the device rattles

The Hold window was first placed from caliper measurements, then **corrected
by 1.0 mm after a test print of the frame** on a Classic 6th gen 160 GB. That
unit's switch is what it matches; if yours does not line up, adjust
`HOLD['x']` and regenerate.

## Hardware

- 4 × M3 × 20 mm screws (cap or button head, Ø5.5 max)
- 4 × M3 hex nuts (5.5 mm across flats)

## Printing

| part | thickness | volume |
|---|---|---|
| face | 3.50 mm | 14.70 cm³ |
| frame | 14.00 mm | 20.74 cm³ |
| rear | 5.00 mm | 26.83 cm³ |

About 74 g in PLA if printed solid (was ~101 g before the weight reduction).

- **Both plates:** flat side down on the bed, **no supports**. The counterbores
  and hex pockets open upwards, and the waist's thin sections need no support
  either — they are just a thinner wall, not an enclosed cavity.
- **Frame:** stands on the bed. It needs a 28.8 mm bridge over the dock cutout
  and a 14 mm one over the Hold window. No supports needed on most printers.
- The frame's port positions are not symmetric through the thickness (jack at
  7.29, dock at 7.70 of 14), so keep the STL's z=0 face towards the same plate
  every time.

## Regenerating

```bash
python3 -m venv .venv && .venv/bin/pip install manifold3d numpy trimesh
.venv/bin/python3 generate_case.py            # writes into stl/
.venv/bin/python3 verify_case.py              # checks the result
```

[`verify_case.py`](verify_case.py) rebuilds the three parts in memory and
checks watertightness/topology, the waist's wall thickness, every corner
screw's clearance, the rear pocket and hex floors, that face/frame/rear
share the same outer silhouette (including the grip band's exact edge
position, not just the overall bounding box -- a mismatch confined to one
local region does not necessarily move the box), and that the assembled
parts do not interfere. It replaces the one-off scratchpad scripts this
project used to re-derive these checks after every change. A Claude Code
subagent (`.claude/agents/ipod-case-reviewer.md`) runs it automatically,
plus a judgment pass on whether the design still keeps the iPod secure and
easy to handle, after any change made through Claude.

The generator reads all three original STLs from `originals/`. It needs
them: every part carries a finger scallop along the side edges whose ends
are not circular arcs, so rather than approximating the shape the script
transplants that region straight out of the matching original mesh (the
frame's own original, not just the two plates' -- see "Weight reduction"
above for what skipping it did). Without those files the parts still
generate, but with plain side edges, and the frame's would then be flush
with the plates only outside the grip band.

All three parts come out watertight, with consistent winding and the expected
topology (genus 6 / 8 / 4 — one handle per through-hole; the rear plate's
lightening pocket is blind, so it adds none).

The waisted outline is not convex, which is why `outer_profile()` builds it
as a 2D union rather than a hull (`Manifold.batch_hull` always returns
something convex, which would fill the waist back in). A few `.simplify()`
calls (`MESH_TOL`) clean up near-duplicate vertices from the waist's arcs,
ahead of the jack/Hold cuts and the grip scallop transplant, so those
booleans stay manifold.

## Fusion model

[`fusion/ipod_case/`](fusion/ipod_case/) holds a script that rebuilds the same
three parts inside Autodesk Fusion as a parametric, editable model. In Fusion:
*Utilities → Add-Ins → Scripts and Add-Ins → Scripts → **+** →* point it at the
`fusion/ipod_case` folder and run it.

Thicknesses and depths are wired to User Parameters, so *Modify → Change
Parameters* rebuilds the model. Sketch profiles use explicit coordinates and
are not dimension-driven.

Caveats: the script has **not been executed** — it only runs inside Fusion —
and it reproduces the side scallop as a loft with circular ends, up to
~0.6 mm off the original curve, where the STLs are exact.

It also does **not yet have the thin waist**: it is 4 screws (matching
`generate_case.py`) with the frame lightened by a blind side-wall pocket,
which is what the STLs did *before* this pass replaced it with the waist.
The rear plate's own pocket is unaffected and still matches. Modelling the
waist's non-convex outline in Fusion's sketch/loft API is a materially
bigger job than the change was in `generate_case.py`, and was left out of
this pass — ask if you want it done. The decorative edge chamfer on the
face and rear plates was dropped from both, so `plate()` here is now also
a plain extrusion.
