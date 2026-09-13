#!/usr/bin/env python3
"""
Check that the Fusion script (fusion/ipod_case/ipod_case.py) builds the same
three parts as generate_case.py, without Fusion.

The Fusion script only runs inside Autodesk Fusion. This replays it against a
small stand-in for the Fusion API that turns every sketch and feature into a
real solid with manifold3d, then compares each resulting component with the
matching part from generate_case.py:

    .venv/bin/python3 fusion/verify_fusion.py
    .venv/bin/python3 fusion/verify_fusion.py --mutate nobevel   # must FAIL

A part matches when its topology (genus) is the same and nothing that differs
between the two is thicker than 0.1 mm -- Fusion keeps arcs and circles exact
where generate_case.py tessellates them, which leaves slivers thinner than
that. generate_case.py's mesh simplification (MESH_TOL) is switched off for
the reference for the same reason.

What the stand-in models, and only as far as the script uses it:
  * sketches: curves chained into closed loops; a profile is one loop, and a
    collection of profiles extrudes as the union of its loops
  * construction planes offset from XY (normal +z) and from XZ. The XZ plane
    is given normal -y and sketch y = +z on purpose, so code that guesses an
    orientation instead of asking the sketch shows up
  * extrude (one side with a start offset, or symmetric full length), loft
    between two convex sections (as their hull), combine cut
  * a cut that removes nothing raises, like Fusion's "no target body found"

What it cannot catch: a mistake in how the real Fusion API behaves. The first
run inside Fusion is still the real test.

--mutate plants a known defect in the Fusion script before replaying it, to
confirm the comparison still catches that kind of difference.
"""
import argparse, math, os, re, sys, types
import numpy as np
from manifold3d import Manifold, CrossSection

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

PARAMS = {}                                          # user parameters, in mm


def evaluate(expr):
    """Value of a Fusion expression such as 'rear_t - 0.8300 mm', in mm."""
    s = re.sub(r'\bmm\b', '', str(expr))
    return float(eval(s, {}, dict(PARAMS)))


# ============================================================================
# Fusion API stand-in
# ============================================================================

class Point3D:
    def __init__(self, x, y, z=0.0): self.x, self.y, self.z = x, y, z
    @staticmethod
    def create(x, y, z=0.0): return Point3D(x, y, z)


class ValueInput:
    def __init__(self, s): self.s = s
    @staticmethod
    def createByString(s): return ValueInput(s)


class ObjectCollection:
    def __init__(self): self.items = []
    @staticmethod
    def create(): return ObjectCollection()
    def add(self, x): self.items.append(x); return True
    @property
    def count(self): return len(self.items)
    def item(self, i): return self.items[i]


class Frame:
    """Plane frame in model mm: origin, sketch x and y axes, normal."""
    def __init__(self, o, xd, yd):
        self.o, self.xd, self.yd = (np.array(v, float) for v in (o, xd, yd))
        self.n = np.cross(self.xd, self.yd)
    def offset(self, d):
        return Frame(self.o + self.n * d, self.xd, self.yd)
    def matrix(self):                                # local (u, v, w) -> model
        return np.column_stack([self.xd, self.yd, self.n, self.o])


class ConstructionPlane:
    def __init__(self, frame, owner):
        self.frame, self._owner = frame, owner
        self.geometry = types.SimpleNamespace(origin=Point3D(*(frame.o * 0.1)))
    def deleteMe(self):
        self._owner.remove(self)


class ConstructionPlanes:
    def __init__(self): self.items = []
    def createInput(self):
        pi = types.SimpleNamespace()
        def set_by_offset(plane, v):
            pi.base, pi.offset = plane, evaluate(v.s)
        pi.setByOffset = set_by_offset
        return pi
    def add(self, pi):
        pl = ConstructionPlane(pi.base.frame.offset(pi.offset), self.items)
        self.items.append(pl)
        return pl


class Profile:
    def __init__(self, sketch, loop): self.sketch, self.loop = sketch, loop
    def cross_section(self):
        pts, n = self.loop, len(self.loop)
        area = sum(pts[i][0]*pts[(i+1) % n][1] - pts[(i+1) % n][0]*pts[i][1] for i in range(n))
        return CrossSection([pts if area > 0 else pts[::-1]])


class Profiles:
    def __init__(self, sk): self.sk = sk
    @property
    def count(self): return len(self.sk.loops())
    def item(self, i): return Profile(self.sk, self.sk.loops()[i])


class Sketch:
    TOL = 1e-4                                       # mm, to join curve ends

    def __init__(self, plane):
        self.frame = plane.frame
        self.chains, self.rings = [], []
        self.sketchCurves = types.SimpleNamespace(
            sketchLines=types.SimpleNamespace(addByTwoPoints=self.add_line),
            sketchArcs=types.SimpleNamespace(addByCenterStartSweep=self.add_arc),
            sketchCircles=types.SimpleNamespace(addByCenterRadius=self.add_circle))
        self.profiles = Profiles(self)

    def _uv(self, p):                                # sketch-space cm -> mm
        if abs(p.z) > 1e-9:
            raise ValueError('sketch point off the sketch plane (z=%g)' % p.z)
        return (p.x * 10.0, p.y * 10.0)

    def add_line(self, a, b):
        self.chains.append([self._uv(a), self._uv(b)])

    def add_arc(self, c, s, sweep):
        (cx, cy), (sx, sy) = self._uv(c), self._uv(s)
        r, a0 = math.hypot(sx - cx, sy - cy), math.atan2(sy - cy, sx - cx)
        n = max(2, int(math.ceil(abs(sweep) / math.radians(0.5))))
        self.chains.append([(cx + r*math.cos(a0 + sweep*k/n), cy + r*math.sin(a0 + sweep*k/n))
                            for k in range(n + 1)])

    def add_circle(self, c, r_cm):
        (cx, cy), r = self._uv(c), r_cm * 10.0
        self.rings.append([(cx + r*math.cos(2*math.pi*k/720), cy + r*math.sin(2*math.pi*k/720))
                           for k in range(720)])

    def modelToSketchSpace(self, p):
        d = np.array([p.x, p.y, p.z]) * 10.0 - self.frame.o
        return Point3D(d @ self.frame.xd * 0.1, d @ self.frame.yd * 0.1, d @ self.frame.n * 0.1)

    def loops(self):
        near = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1]) < self.TOL
        pool, loops = [list(c) for c in self.chains], [list(r) for r in self.rings]
        while pool:
            cur = pool.pop(0)
            while not near(cur[-1], cur[0]):
                for i, seg in enumerate(pool):
                    if near(seg[0], cur[-1]):
                        cur += seg[1:]; pool.pop(i); break
                    if near(seg[-1], cur[-1]):
                        cur += seg[::-1][1:]; pool.pop(i); break
                else:
                    raise ValueError('sketch has an open chain ending at (%.4f, %.4f)' % cur[-1])
            loops.append(cur[:-1])
        return loops


class Body:
    def __init__(self, man): self.man = man


def profile_union(profile):
    profs = profile.items if isinstance(profile, ObjectCollection) else [profile]
    if len({id(p.sketch.frame) for p in profs}) != 1:
        raise ValueError('profiles from different sketches in one feature')
    cs = CrossSection()
    for p in profs:
        cs = cs + p.cross_section()
    return profs[0].sketch.frame, cs


def apply(comp, op, tool, participants, what):
    if op == 'new':
        body = Body(tool)
        comp.bodies.append(body)
        return [body]
    targets = participants if participants is not None else list(comp.bodies)
    removed = 0.0
    for b in targets:
        if b not in comp.bodies:
            raise ValueError('%s: participant body no longer exists' % what)
        before = b.man.volume()
        b.man = b.man - tool
        removed += before - b.man.volume()
    if removed < 1e-6:
        raise RuntimeError('%s: no target body found to cut' % what)
    return []


def feature_result(bodies):
    coll = ObjectCollection()
    for b in bodies:
        coll.add(b)
    return types.SimpleNamespace(bodies=coll)


class ExtrudeInput:
    def __init__(self, profile, op):
        self.profile, self.op = profile, op
        self.startExtent = self.participantBodies = self.extent = None
    def setOneSideExtent(self, d, direction):
        self.extent = ('one', evaluate(d.s))
    def setDistanceExtent(self, symmetric, v):
        raise AssertionError('fell back to the old setDistanceExtent API')
    def setSymmetricExtent(self, v, full_length):
        assert full_length is True
        self.extent = ('sym', evaluate(v.s))


class ExtrudeFeatures:
    def __init__(self, comp): self.comp = comp
    def createInput(self, profile, op): return ExtrudeInput(profile, op)
    def add(self, ei):
        frame, cs = profile_union(ei.profile)
        kind, d = ei.extent
        if kind == 'one':
            w0 = evaluate(ei.startExtent.s) if ei.startExtent is not None else 0.0
            w1 = w0 + d
        else:
            w0, w1 = -d / 2.0, d / 2.0
        if w1 <= w0:
            raise ValueError('extrude of non-positive length')
        tool = Manifold.extrude(cs, w1 - w0).translate((0, 0, w0)).transform(frame.matrix())
        return feature_result(apply(self.comp, ei.op, tool, ei.participantBodies, 'extrude'))


class LoftFeatures:
    def __init__(self, comp): self.comp = comp
    def createInput(self, op):
        return types.SimpleNamespace(op=op, participantBodies=None, isSolid=False,
                                     loftSections=ObjectCollection())
    def add(self, li):
        assert li.isSolid and li.loftSections.count == 2
        ends = []
        for p in li.loftSections.items:
            frame, cs = profile_union(p)
            if abs(CrossSection.hull(cs).area() - cs.area()) > 1e-3 * cs.area():
                raise ValueError('loft section is not convex; its hull would not stand in for the loft')
            ends.append(Manifold.extrude(cs, 1e-5).transform(frame.matrix()))
        tool = Manifold.batch_hull(ends)
        return feature_result(apply(self.comp, li.op, tool, li.participantBodies, 'loft'))


class CombineFeatures:
    def __init__(self, comp): self.comp = comp
    def createInput(self, target, tools):
        return types.SimpleNamespace(target=target, tools=tools, operation=None,
                                     isKeepToolBodies=True)
    def add(self, ci):
        assert ci.operation == 'cut'
        tool = Manifold()
        for b in ci.tools.items:
            tool = tool + b.man
        apply(self.comp, 'cut', tool, [ci.target], 'combine')
        if not ci.isKeepToolBodies:
            for b in ci.tools.items:
                self.comp.bodies.remove(b)
        return types.SimpleNamespace()


class Component:
    def __init__(self):
        self.name, self.bodies = None, []
        self.constructionPlanes = ConstructionPlanes()
        self.xYConstructionPlane = ConstructionPlane(Frame((0, 0, 0), (1, 0, 0), (0, 1, 0)), [])
        self.xZConstructionPlane = ConstructionPlane(Frame((0, 0, 0), (1, 0, 0), (0, 0, 1)), [])
        self.sketches = types.SimpleNamespace(add=Sketch)
        self.features = types.SimpleNamespace(extrudeFeatures=ExtrudeFeatures(self),
                                              loftFeatures=LoftFeatures(self),
                                              combineFeatures=CombineFeatures(self))


def install_stand_in():
    """Register fake adsk, adsk.core and adsk.fusion modules. Returns the list
    that collects components and the one that collects message boxes."""
    components, messages = [], []

    def add_component(matrix):
        comp = Component()
        components.append(comp)
        return types.SimpleNamespace(component=comp)

    user_parameters = types.SimpleNamespace(
        itemByName=PARAMS.get,
        add=lambda name, v, units, comment: PARAMS.__setitem__(name, evaluate(v.s)))
    design = types.SimpleNamespace(
        designType=None, unitsManager=types.SimpleNamespace(), userParameters=user_parameters,
        rootComponent=types.SimpleNamespace(
            occurrences=types.SimpleNamespace(addNewComponent=add_component)))
    app = types.SimpleNamespace(
        userInterface=types.SimpleNamespace(messageBox=messages.append),
        documents=types.SimpleNamespace(add=lambda doc_type: None),
        activeProduct=design)

    adsk = types.ModuleType('adsk')
    core = types.ModuleType('adsk.core')
    fusion = types.ModuleType('adsk.fusion')
    core.ValueInput, core.Point3D, core.ObjectCollection = ValueInput, Point3D, ObjectCollection
    core.Matrix3D = types.SimpleNamespace(create=lambda: None)
    core.Application = types.SimpleNamespace(get=lambda: app)
    core.DocumentTypes = types.SimpleNamespace(FusionDesignDocumentType='design')
    fusion.FeatureOperations = types.SimpleNamespace(NewBodyFeatureOperation='new',
                                                     CutFeatureOperation='cut')
    fusion.DistanceExtentDefinition = types.SimpleNamespace(create=lambda v: v)
    fusion.ExtentDirections = types.SimpleNamespace(PositiveExtentDirection='positive')
    fusion.OffsetStartDefinition = types.SimpleNamespace(create=lambda v: v)
    fusion.Design = types.SimpleNamespace(cast=lambda x: x)
    fusion.DesignTypes = types.SimpleNamespace(ParametricDesignType='parametric')
    adsk.core, adsk.fusion = core, fusion
    sys.modules.update({'adsk': adsk, 'adsk.core': core, 'adsk.fusion': fusion})
    return components, messages


# ============================================================================
# Comparison
# ============================================================================

MUTATIONS = {
    'noentrance':    'no corner entrances at the nut pockets and counterbores',
    'nobevel':       'no side bevels on the plates',
    'nopocketbevel': 'rear pocket without its rim and floor bevels',
    'waist':         'side walls 0.5 mm thicker at the waist',
    'hold':          'Hold window back at z = 7.29',
}


def mutate(fc, name):
    if name == 'noentrance':
        fc.corner_entrance = lambda *args: None
    elif name == 'nobevel':
        fc.side_bevels = lambda *args: None
    elif name == 'nopocketbevel':
        fc.REAR_POCKET_BEVEL_SLOPE = 1e-3
    elif name == 'waist':
        fc.W_THIN -= 1.0
    elif name == 'hold':
        fc.HOLD = dict(fc.HOLD, z=7.29)


def thicker_than(piece, t):
    """True if any part of the piece is thicker than t, probed on slices
    across all three axes (a skin thin in z is wide in x and y)."""
    for rot in ((0, 0, 0), (90, 0, 0), (0, 90, 0)):
        q = piece.rotate(rot)
        b = q.bounding_box()
        for k in range(1, 12):
            if q.slice(b[2] + (b[5] - b[2]) * k / 12).offset(-t / 2.0).area() > 1e-4:
                return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--mutate', choices=sorted(MUTATIONS),
                    help='plant a known defect in the Fusion script first; the check must then fail')
    args = ap.parse_args()

    components, messages = install_stand_in()
    sys.path.insert(0, REPO)
    sys.path.insert(0, os.path.join(HERE, 'ipod_case'))
    import generate_case as gc
    import ipod_case as fc
    gc.MESH_TOL = 0.0
    if args.mutate:
        print('mutation: %s' % MUTATIONS[args.mutate])
        mutate(fc, args.mutate)

    fc.run(None)
    failed = [m for m in messages if m.startswith('Failed')]
    if failed:
        print(failed[0])
        return 1

    ok = len(components) == 3
    for comp, ref_build in zip(components, (gc.face, gc.frame, gc.rear)):
        ref = ref_build()
        if len(comp.bodies) != 1:
            print('[FAIL] %-5s  %d bodies, expected 1' % (comp.name, len(comp.bodies)))
            ok = False
            continue
        man = comp.bodies[0].man
        diff = (man - ref) + (ref - man)
        bad = [p for p in diff.decompose() if p.volume() > 0.01 and thicker_than(p, 0.1)]
        same_genus = man.genus() == ref.genus()
        status = 'OK  ' if same_genus and not bad else 'FAIL'
        ok = ok and status == 'OK  '
        print('[%s] %-5s  fusion %.3f cm3, generate_case %.3f cm3, genus %d/%d, '
              'differences thicker than 0.1 mm: %s'
              % (status, comp.name, man.volume() / 1000, ref.volume() / 1000,
                 man.genus(), ref.genus(),
                 ', '.join('%.2f mm3 around (%.1f, %.1f, %.1f)'
                           % ((p.volume(),) + tuple((p.bounding_box()[i] + p.bounding_box()[i + 3]) / 2
                                                    for i in range(3)))
                           for p in bad) or 'none'))
    print('The Fusion script matches generate_case.py.' if ok else
          'The Fusion script does NOT match generate_case.py.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
