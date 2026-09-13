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
| face/rear edges | bevel all round, plus a finger-grip scallop on the lower half of each side | **frame's outline, with a bevel along each whole side between the corner pads** |

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

This is what the tested build uses. An M3 × 18 would have allowed a thinner
rear plate, but it could not be found in shops, so the rear stays at 5.00 mm to
suit the M3 × 20.

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
  face, clear of the four screw/nut bosses, leaving 2.50 mm to the inner face
  (the same floor thickness already proven by the hex nut pockets). Neither of
  its edges is sharp: the rim on the outer face and the corner where the wall
  meets the floor both carry the same bevel as the plates' side edges (0.83 mm
  high, 1.93 mm wide), so the wall runs in from the floor, straight for
  0.84 mm, then out to the mouth. At the outer face the mouth comes within
  3.22 mm of the side bevels (5.15 mm before it was bevelled) and 5.52 mm of
  the hex nut pockets.

Face and rear start from the same waisted outline as the frame, so all three
meet flush at every edge; the only thing cut into that outline afterwards is
the side bevel below, on the plates' outer faces. That also meant dropping the
decorative edge chamfer the original design had all round both plates: the
waist isn't convex, so it fought the usual hull-based taper that built that
bevel (see [Regenerating](#regenerating)).

### Side bevel

Each plate bevels the outer-face edge of both sides, along the **whole** side
between the bottom and top corner pads, so no side edge is a sharp corner.
The pads keep their full square edge: the bevel stops exactly where each
pad's arc meets the straight side (y = 16.44 and 93.76 mm) and follows that
arc, so no pad loses material. The frame has no bevel.

| | |
|---|---|
| slope | 2.324 mm in per mm down (same as the click wheel chamfer) |
| down the side | 0.83 mm |
| in across the outer face | 1.93 mm |

That is the profile the original design's finger-grip scallop already left on
the thin waist; `SIDE_BEVEL_SLOPE` and `SIDE_BEVEL_H` in `generate_case.py`
change it.

It replaces that scallop, which was transplanted from the original mesh and
had three problems here: it only existed on the lower half of each side, it
cut a 6.2 × 2.7 mm recess into the bottom pads, and it brought a short stretch
of the original's decorative chamfer with it. Transplanted unclipped, it had
also left both plates overhanging the frame by up to 4.3 mm; `verify_case.py`
now compares full outlines, so neither that nor a bevel reaching into a pad can
pass again.

| part | original | pockets only | thin waist + pads |
|---|---|---|---|
| face | 15.99 cm³ | 15.61 cm³ | 14.06 cm³ |
| frame | 27.43 cm³ | 18.42 cm³ | 16.19 cm³ |
| rear | 41.39 cm³ | 28.89 cm³ | 26.18 cm³ |
| **total** | **84.81 cm³** | **62.92 cm³** | **56.43 cm³** |

A third less material than the original design. All three parts are
verified watertight, with the waist's wall measured at exactly 3.00 mm to
the cavity along its whole length and the corner screws keeping their
original margins (1.87 mm to the cavity, 2.02 mm to the outer edge).

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
device.

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
after test prints of the frame** on a Classic 6th gen 160 GB: 1.0 mm towards
the headphone jack, and later 1.0 mm towards the face plate (centre z=8.29 of
14, away from the rear plate). That unit's switch is what it matches; if yours
does not line up, adjust `HOLD['x']` / `HOLD['z']` and regenerate.

## Hardware

- 4 × M3 × 20 mm button-head screws (ISO 7380: Ø5.7 head, 1.65 mm tall, sits below the
  face in the 2.5 mm deep Ø6.0 counterbore). A socket-cap head (ISO 4762, 3.0 mm tall)
  also fits but stands about 0.5 mm proud.
- 4 × M3 hex nuts (5.5 mm across flats)

### Corner screw pockets

The corner screws sit so close to the rounded corners that the pockets around
them used to leave walls to the outside thinner than an extrusion line: **0.33
mm** at each hex nut pocket in the rear plate, and **0.59 mm** at each
screw-head counterbore in the face plate — right where the nut or head bears
when the screw is tightened. Thickening them would take squarer corners or
screws moved towards the cavity, and both change the frame.

So wherever such a wall would be thinner than **1.30 mm** (`CORNER_WEB_MIN`:
three 0.4 mm lines plus margin), it is cut away down to the pocket's own floor:
each pocket opens to its corner through an entrance that is flat — not a
slope, the same vertical cut from the floor to the outer face — with sides that
meet the outline square on.

| | rear nut pocket | face counterbore |
|---|---|---|
| floor of the entrance | nut seat, 2.5 mm above the inner face | counterbore floor, 1.0 mm above the inner face |
| wall before | 0.33 mm | 0.59 mm |
| walls left | ~1.3 mm | ~1.3 mm |

A nut still cannot turn (4 of the hex's 6 corners stay walled) or slide out (the
entrance's throat, 4.7 mm, is narrower than the nut's 5.5 mm), and still goes
in from above as before. A screw head still bears on the whole counterbore
floor, which the entrance does not touch.

## Printing

| part | thickness | volume |
|---|---|---|
| face | 3.50 mm | 14.06 cm³ |
| frame | 14.00 mm | 16.19 cm³ |
| rear | 5.00 mm | 26.18 cm³ |

About 67 g in PLA if printed solid (was ~101 g before the weight reduction).

- **Both plates:** flat side down on the bed, **no supports**. The counterbores
  and hex pockets (both with their corner entrances) and the rear pocket open
  upwards, and
  every bevel (sides, pocket rim, pocket floor) narrows as it rises, so none of
  them overhangs. The waist's thin sections need no support either — they are
  just a thinner wall, not an enclosed cavity.
- **Frame:** stands on the bed. It needs a 28.8 mm bridge over the dock cutout
  and a 14 mm one over the Hold window. No supports needed on most printers.
- The frame's port positions are not symmetric through the thickness (jack at
  7.29, dock at 7.70, Hold at 8.29 of 14, measured from the rear plate), so the
  STL's z=0 face — the one on the bed — always goes against the rear plate.

## Regenerating

```bash
python3 -m venv .venv && .venv/bin/pip install manifold3d numpy trimesh
.venv/bin/python3 generate_case.py            # writes into stl/
.venv/bin/python3 verify_case.py              # checks the result
```

[`verify_case.py`](verify_case.py) rebuilds the three parts in memory and
checks watertightness/topology, the waist's wall thickness, every corner
screw's clearance, the rear pocket and hex floors, the corner entrances of the
nut pockets and counterbores (flat from their floor, walls left >= 1.2 mm, 4 hex
corners still walled), the rear pocket's exact
bevelled shape and the web it leaves to the nuts, that face and rear
match the frame's full outline at the face that seats against it and never
stick out past it (a full-outline comparison, not a bounding box -- the
bounding box missed a 4.3 mm overhang once), that the side bevel runs every
side between the pads at its designed size while the pads stay untouched, and
that the assembled parts touch without interfering. It replaces the one-off scratchpad scripts this project used to
re-derive these checks after every change. For bigger changes, a Claude
Code subagent (`.claude/agents/ipod-case-reviewer.md`) also gives an
independent review, including a judgment pass on whether the design still
keeps the iPod secure and easy to handle.

The generator no longer reads anything from `originals/`: everything,
including the side bevel, is built from the parameters. The original STLs stay
there for reference.

All three parts come out watertight, with consistent winding and the expected
topology (genus 6 / 8 / 4 — one handle per through-hole; the rear plate's
lightening pocket is blind, so it adds none).

The waisted outline is not convex, which is why `outer_profile()` builds it
as a 2D union rather than a hull (`Manifold.batch_hull` always returns
something convex, which would fill the waist back in). A few `.simplify()`
calls (`MESH_TOL`) clean up near-duplicate vertices from the waist's arcs,
ahead of the jack/Hold cuts, so those booleans stay manifold. The side
bevel's cutter stops 0.001 mm (`OVERLAP`) short of each pad's arc for the same
reason: ending exactly on it left a non-manifold edge at every junction.

## Fusion model

[`fusion/ipod_case/`](fusion/ipod_case/) holds a script that rebuilds the same
three parts inside Autodesk Fusion as an editable model. In Fusion:
*Utilities → Add-Ins → Scripts and Add-Ins → Scripts → **+** →* point it at the
`fusion/ipod_case` folder and run it.

It builds the same model as the STLs: the thin waist, the side bevels, the rear
pocket with both edges bevelled, the corner entrances at the nut pockets and
counterbores, and the Hold window where the test prints put it. Fusion keeps
arcs and circles exact where the STLs are tessellated; otherwise the two should
not differ, so a change to `generate_case.py` needs the same change there.

The plate and frame thicknesses and the pocket depths are wired to User
Parameters, so *Modify → Change Parameters* rebuilds those features. The
outline, the bevels and the corner entrances are computed from the constants at
the top of the script when it runs: edit those and run it again. Sketch
profiles use explicit coordinates and are not dimension-driven.

Caveat: the script has **not been executed in Fusion** — it only runs there. It
was checked by replaying it against a stand-in for the Fusion API that builds
each feature's solid, and all three parts matched `generate_case.py`'s to within
tessellation (nothing thicker than 0.1 mm apart). The stand-in cannot catch a
mistake in how the real API behaves, so the first run inside Fusion is the real
test; if it stops with an error, the message names the part it was building.
