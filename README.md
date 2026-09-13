# iPod Classic case — v2

A reworked three-piece screw-together case for the iPod Classic. The three
parts sandwich the iPod: a face plate with the screen and click-wheel
openings, a thick middle frame that holds the device, and a plain rear plate.

Everything is generated from [`generate_case.py`](generate_case.py), so the
design is parametric — edit the numbers at the top and run it again.

## What changed from the original

| | original | v2 |
|---|---|---|
| screws | 4 | **6** |
| rear plate | 3.50 mm | **5.00 mm** |
| screw length | nothing standard fitted | **M3 × 20, flush** |
| Hold switch | no opening | **14.0 × 5.0 mm window** |
| jack / dock / Hold openings | straight bores | **flared outwards** |

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

### Six screws

The four corner screws keep their original positions. The two new ones sit at
mid height on the side walls, 4.75 mm from the edge rather than 5.00.

That 0.25 mm setback is forced. The side wall is 7.299 mm and there is only
**1.253 mm of budget** to split between two opposing needs: the Ø6 counterbore
must not break through the edge chamfer, and material must remain between the
hole and the iPod cavity. It is split as 0.32 mm and 0.97 mm.

**That 0.97 mm wall is the thinnest feature in the design.** It is the first
thing to check on a test print.

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

- 6 × M3 × 20 mm screws (cap or button head, Ø5.5 max)
- 6 × M3 hex nuts (5.5 mm across flats)

## Printing

| part | thickness | volume |
|---|---|---|
| face | 3.50 mm | 16.0 cm³ |
| frame | 14.00 mm | 27.3 cm³ |
| rear | 5.00 mm | 41.4 cm³ |

About 105 g in PLA if printed solid.

- **Both plates:** flat side down on the bed, **no supports**. The counterbores
  and hex pockets open upwards, so nothing overhangs.
- **Frame:** stands on the bed. It needs a 28.8 mm bridge over the dock cutout
  and a 14 mm one over the Hold window. No supports needed on most printers.
- The frame's port positions are not symmetric through the thickness (jack at
  7.29, dock at 7.70 of 14), so keep the STL's z=0 face towards the same plate
  every time.

## Regenerating

```bash
pip install manifold3d numpy
python3 generate_case.py            # writes into stl/
```

The generator reads the two original STLs from `originals/`. It needs them:
both plates carry a finger scallop along the side edges whose ends are not
circular arcs, so rather than approximating the shape the script transplants
that region straight out of the original mesh. Without those files the parts
still generate, but with plain side edges.

All three parts come out watertight, with consistent winding and the expected
topology (genus 8 / 10 / 6 — one handle per through-hole).

## Fusion model

[`fusion/ipod_case/`](fusion/ipod_case/) holds a script that rebuilds the same
three parts inside Autodesk Fusion as a parametric, editable model. In Fusion:
*Utilities → Add-Ins → Scripts and Add-Ins → Scripts → **+** →* point it at the
`fusion/ipod_case` folder and run it.

Thicknesses and depths are wired to User Parameters, so *Modify → Change
Parameters* rebuilds the model. Sketch profiles use explicit coordinates and
are not dimension-driven.

Two caveats: the script has **not been executed** — it only runs inside Fusion
— and it reproduces the side scallop as a loft with circular ends, up to
~0.6 mm off the original curve. The STLs are exact on that detail.
