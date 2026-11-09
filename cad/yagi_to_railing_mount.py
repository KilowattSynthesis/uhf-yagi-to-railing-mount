"""Mount for a UHF yagi antenna to a deck railing.

Three printed parts:
- `main_mount_bottom`: lower half of the railing clamp.
- `main_mount_top`: upper half of the railing clamp, with a level turntable
    base on top.
- `antenna_wedge`: sits on the turntable base. Its top face is tilted to the
    antenna elevation angle, and holds the antenna.

The wedge is held to the base by turntable bolts through arc slots, so it can
be turned to any azimuth in -90..+90 deg. Turning about the vertical axis
keeps the yagi elements level, and keeps the elevation constant.

Frames: X runs along the railing, Y points out from the railing (azimuth 0),
Z is up. The origin is the center of the railing. Positive azimuth is
counter-clockwise, viewed from above.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import build123d as bd
from build123d_ease import show
from loguru import logger


@dataclass(frozen=True)
class MetricBolt:
    """Nominal dimensions of a metric socket head bolt and its hex nut.

    Precise values. Do not add clearance here.
    """

    name: str
    diameter: float
    head_diameter: float
    nut_width_across_flats: float
    nut_thickness: float
    # Counterbore for the bolt head, with room for a socket/wrench.
    head_counterbore_diameter: float

    @property
    def nut_width_across_corners(self) -> float:
        """Width of the hex nut across its corners."""
        return self.nut_width_across_flats / math.cos(math.radians(30))


M3 = MetricBolt("M3", 3.0, 5.5, 5.5, 2.4, 12.0)
M4 = MetricBolt("M4", 4.0, 7.0, 7.0, 3.2, 15.0)
M5 = MetricBolt("M5", 5.0, 8.5, 8.0, 4.0, 18.0)
M6 = MetricBolt("M6", 6.0, 10.0, 10.0, 5.0, 20.0)

# Change these to switch bolt sizes.
ANTENNA_BOLT = M4  # Holds the antenna body to the wedge.
CLAMP_BOLT = M5  # Clamps the top and bottom halves around the railing.
TURNTABLE_BOLT = M4  # Holds the wedge to the turntable base.


@dataclass
class Spec:
    """Specification for the mount."""

    railing_width: float = 52
    railing_height: float = 26.5

    general_width: float = 35  # Along the railing.
    body_radius: float = 35

    antenna_elevation_angle_degrees: float = 40

    clamp_bolt: MetricBolt = CLAMP_BOLT
    antenna_bolt: MetricBolt = ANTENNA_BOLT
    turntable_bolt: MetricBolt = TURNTABLE_BOLT

    # Diameter clearance for all bolt holes.
    bolt_hole_clearance: float = 0.5
    # Clearance for nut pockets (on width across flats, and thickness).
    nut_clearance: float = 0.4

    # Blind bolt holes are made as deep as possible, while keeping this much
    # material between them and any other feature or outer surface.
    hole_min_wall: float = 1.5

    # Center-to-center distance between clamp bolt holes.
    bolt_separation: float = 75
    bolt_extra_length_into_bottom: float = 13.0

    # Clamp captive nut, pressed into the bottom of each clamp bolt boss.
    clamp_nut_clearance: float = 0.3
    clamp_bolt_boss_wall: float = 2.2  # Around the nut's corners.

    # Turntable: shared by the base (on the top clamp half) and the wedge.
    turntable_radius: float = 32.0
    turntable_base_thickness: float = 10.0
    # Radius of the turntable bolts, and of the arc slots in the wedge.
    turntable_bolt_radius: float = 18.0
    # Depth from the base's top face to the center of the nut slot.
    turntable_nut_depth: float = 6.0
    # Extra arc length on each end of the wedge slots.
    turntable_slot_extra_degrees: float = 1.0

    # Azimuths to mark with a notch on the turntable base's rim.
    azimuth_marks_degrees: tuple[float, ...] = field(
        default_factory=lambda: (-90.0, -60.0, -45.0, 0.0, 45.0, 60.0, 90.0)
    )
    mark_width: float = 1.2
    mark_depth: float = 1.0

    # Thickness of the wedge at its lowest point (the back).
    wedge_min_height: float = 10.0
    # Material under the turntable bolt heads, in the wedge.
    wedge_bolt_ledge_thickness: float = 6.0
    wedge_bolt_head_clearance: float = 1.0

    antenna_body_width: float = 15.0
    antenna_body_recess_depth: float = 2.0
    antenna_hole_sep: float = 46
    # Shifts the antenna back along its face (away from the boom's pointing
    # direction), so the front bolt hole has room inside the wedge.
    antenna_face_offset: float = 7.0
    # From the recess floor to the center of the antenna nut slot.
    antenna_nut_depth: float = 6.0
    # Thickness of the antenna's mounting bracket, under the bolt heads.
    # Only used for the hardware BOM. Measure yours.
    antenna_bracket_thickness: float = 3.0

    # How far a clamp bolt may stick out past its nut (below the clamp).
    clamp_bolt_max_protrusion: float = 10.0

    # Through-holes parallel to the railing, for a safety rope.
    rope_hole_diameter: float = 7.0

    # Safety rope holes through the wedge, along its X axis (parallel to
    # the yagi elements), in the tall front part. (y, z) centers in the
    # wedge frame (bottom at Z=0, antenna pointing +Y).
    wedge_rope_hole_positions: tuple[tuple[float, float], ...] = (
        (24.0, 8.0),
        (24.0, 18.5),
    )

    # Tapered registration pegs on the top clamp half's split face, which
    # fit into sockets in the bottom half. Tapered, so they self-center.
    registration_peg_base_radius: float = 3.0
    registration_peg_tip_radius: float = 1.5
    registration_peg_height: float = 3.0
    registration_clearance: float = 0.2  # On radius, and on depth.
    # (x, y) centers on the split face, beside the railing.
    registration_peg_positions: tuple[tuple[float, float], ...] = (
        (10.0, 30.5),
        (-10.0, 30.5),
        (10.0, -30.5),
        (-10.0, -30.5),
    )

    # Separate pin, between the turntable base and the wedge. Keeps the
    # wedge centered while it's turned.
    pivot_pin_diameter: float = 8.0
    pivot_pin_length: float = 8.0
    pivot_pin_clearance: float = 0.3  # On diameter.
    pivot_pin_chamfer: float = 0.6
    # (y, z) centers, relative to the railing center.
    rope_hole_positions: tuple[tuple[float, float], ...] = (
        (22.5, 21.5),  # Top half.
        (-22.5, 21.5),  # Top half.
        (12.0, -24.0),  # Bottom half.
        (-12.0, -24.0),  # Bottom half.
    )

    def __post_init__(self) -> None:
        """Post initialization checks."""
        # Leave material above the antenna nut slot.
        assert (
            self.antenna_nut_depth
            - (self.antenna_bolt.nut_thickness + self.nut_clearance) / 2
            >= 2  # noqa: PLR2004
        )
        # Turntable nut slot must fit within the base.
        assert (
            self.turntable_nut_depth + self.turntable_bolt.nut_thickness
            < self.turntable_base_thickness
        )
        # Turntable bolt heads must fit inside the wedge's rim.
        assert (
            self.turntable_bolt_radius + self.wedge_slot_head_width / 2
            < self.turntable_radius
        )
        # Wedge must be clear of the clamp bolt heads (hex key access).
        assert (
            self.turntable_radius
            < self.bolt_separation / 2 - self.clamp_bolt.head_diameter / 2 - 1
        )

    @property
    def clamp_bolt_boss_radius(self) -> float:
        """Radius of the boss around each clamp bolt."""
        nut_pocket_across_corners = (
            self.clamp_bolt.nut_width_across_flats + self.clamp_nut_clearance
        ) / math.cos(math.radians(30))
        return nut_pocket_across_corners / 2 + self.clamp_bolt_boss_wall

    @property
    def clamp_top_z(self) -> float:
        """Top face of the clamp (the turntable base's top face)."""
        return self.bolt_separation / 2

    @property
    def wedge_center_height(self) -> float:
        """Height of the wedge's antenna face, at the turntable axis."""
        return self.wedge_min_height + self.turntable_radius * math.tan(
            math.radians(self.antenna_elevation_angle_degrees)
        )

    @property
    def wedge_slot_head_width(self) -> float:
        """Width of the arc slot for the turntable bolt heads, in the wedge."""
        return (
            self.turntable_bolt.head_diameter + self.wedge_bolt_head_clearance
        )

    @property
    def antenna_floor_location(self) -> bd.Location:
        """Antenna recess floor, in the wedge frame.

        Local +Y is along the antenna boom (pointing forward and up), local +Z
        is out of the antenna face.
        """
        face = bd.Location(
            (0, 0, self.wedge_center_height),
            (self.antenna_elevation_angle_degrees, 0, 0),
        )
        return face * bd.Location(
            (0, -self.antenna_face_offset, -self.antenna_body_recess_depth)
        )


def hex_nut_pocket(
    width_across_flats: float, thickness: float
) -> bd.Part | bd.Compound:
    """Hex prism, flats parallel to the X axis, centered on Z=0."""
    across_corners = width_across_flats / math.cos(math.radians(30))
    return bd.extrude(
        bd.RegularPolygon(radius=across_corners / 2, side_count=6),
        amount=thickness / 2,
        both=True,
    )


_hole_depth_cache: dict[tuple[str, str], float] = {}


def max_hole_depth(  # noqa: PLR0913
    spec: Spec,
    *,
    name: str,
    body: bd.Part | bd.Compound,
    location: bd.Location,
    diameter: float,
    min_depth: float,
) -> float:
    """Find the deepest a blind hole can go, within `body`.

    Keeps `spec.hole_min_wall` of material around the hole. The hole starts
    at `location` and goes in its local -Z direction.

    Each result is cached by `spec` and `name`, and logged the first time
    it's computed.
    """
    cache_key = (repr(spec), name)
    if cache_key in _hole_depth_cache:
        return _hole_depth_cache[cache_key]

    wall = spec.hole_min_wall

    def fits(depth: float) -> bool:
        probe = bd.Cylinder(
            radius=diameter / 2 + wall,
            height=depth + wall,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        ).moved(location)
        outside = probe - body
        return outside.volume < 1e-3  # noqa: PLR2004

    # Binary search.
    low, high = min_depth, 100.0
    assert fits(low), f"No room for hole: {name}"
    while high - low > 0.1:  # noqa: PLR2004
        mid = (low + high) / 2
        if fits(mid):
            low = mid
        else:
            high = mid

    depth = math.floor(low * 2) / 2  # Round down to 0.5 mm.
    _hole_depth_cache[cache_key] = depth
    logger.info(f"{name}: {depth} mm deep")
    return depth


def cached_hole_depth(spec: Spec, name: str) -> float:
    """Get a hole depth found by `max_hole_depth`, after the part is built."""
    return _hole_depth_cache[(repr(spec), name)]


# Common ISO 4762 socket head bolt lengths.
STANDARD_BOLT_LENGTHS = (
    *(6, 8, 10, 12, 14, 16, 18, 20, 25, 30, 35, 40),
    *(45, 50, 55, 60, 65, 70, 75, 80, 90, 100),
)


def bolt_bom(spec: Spec) -> list[str]:
    """List the bolts needed, with the usable range of lengths.

    Call after building the parts, so the hole depths are known.
    """

    def bolt_line(
        count: int, bolt: MetricBolt, min_len: float, max_len: float, use: str
    ) -> str:
        fits = [
            length
            for length in STANDARD_BOLT_LENGTHS
            if min_len <= length <= max_len
        ]
        sizes = ", ".join(f"{bolt.name}x{length}" for length in fits)
        return (
            f"{count}x {sizes or 'NONE'} "
            f"({math.ceil(min_len)}-{math.floor(max_len)} mm, {use})"
        )

    # Shortest bolt engages the full nut; longest is limited by the blind
    # hole depth (or by protrusion, for the clamp bolts).
    clamp_nut_far_face = spec.bolt_extra_length_into_bottom - (
        spec.clamp_nut_clearance
    )
    clamp_min = spec.clamp_top_z + clamp_nut_far_face
    clamp_max = (
        spec.clamp_top_z
        + spec.bolt_extra_length_into_bottom
        + spec.clamp_bolt_max_protrusion
    )

    tt = spec.turntable_bolt
    tt_depth = min(
        cached_hole_depth(spec, f"Turntable base bolt hole at {angle} deg")
        for angle in (45, 135, 225, 315)
    )
    tt_min = (
        spec.wedge_bolt_ledge_thickness
        + spec.turntable_nut_depth
        + (tt.nut_thickness + spec.nut_clearance) / 2
    )
    tt_max = spec.wedge_bolt_ledge_thickness + tt_depth

    ant = spec.antenna_bolt
    ant_depth = min(
        cached_hole_depth(spec, f"Antenna bolt hole, {end}")
        for end in ("front", "back")
    )
    ant_min = (
        spec.antenna_bracket_thickness
        + spec.antenna_nut_depth
        + (ant.nut_thickness + spec.nut_clearance) / 2
    )
    ant_max = spec.antenna_bracket_thickness + ant_depth

    return [
        bolt_line(2, spec.clamp_bolt, clamp_min, clamp_max, "clamp"),
        bolt_line(2, tt, tt_min, tt_max, "turntable"),
        bolt_line(2, ant, ant_min, ant_max, "antenna"),
    ]


def clamp_body(spec: Spec) -> bd.Part | bd.Compound:
    """Both clamp halves joined, without the turntable base holes."""
    p = bd.Part(None)

    # Main body: round below the railing, square above it.
    p += bd.Cylinder(
        radius=spec.body_radius,
        height=spec.general_width,
    ).rotate(axis=bd.Axis.Y, angle=90)
    p += bd.Box(
        spec.general_width,
        spec.body_radius * 2,
        spec.clamp_top_z,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # Turntable base.
    p += bd.Cylinder(
        radius=spec.turntable_radius,
        height=spec.turntable_base_thickness,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
    ).translate((0, 0, spec.clamp_top_z))

    # Clamp bolt bosses, holes, and captive nuts. The bosses go up to the
    # top face, so the bolt heads sit level with it (no counterbore, so no
    # overhang when printing the top half upside down).
    for i in (-1, 1):
        y = i * spec.bolt_separation / 2

        p += bd.Cylinder(
            radius=spec.clamp_bolt_boss_radius,
            height=spec.clamp_top_z + spec.bolt_extra_length_into_bottom,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        ).translate((0, y, -spec.bolt_extra_length_into_bottom))

        # Main bolt hole.
        p -= bd.Cylinder(
            radius=(spec.clamp_bolt.diameter + spec.bolt_hole_clearance) / 2,
            height=spec.bolt_separation * 10,  # Arbitrary.
        ).translate((0, y, 0))

        # Captive nut, pressed in from the bottom of the boss.
        nut_thick = spec.clamp_bolt.nut_thickness + spec.clamp_nut_clearance
        p -= hex_nut_pocket(
            spec.clamp_bolt.nut_width_across_flats + spec.clamp_nut_clearance,
            # Extra length so it cleanly opens out the bottom.
            nut_thick + 2,
        ).translate(
            (0, y, -spec.bolt_extra_length_into_bottom + nut_thick / 2 - 1)
        )

    # Remove the railing.
    p -= bd.Box(
        spec.general_width * 2,  # Arbitrary.
        spec.railing_width,
        spec.railing_height,
    )

    # Safety rope holes, through the full width.
    for rope_y, rope_z in spec.rope_hole_positions:
        p -= (
            bd.Cylinder(
                radius=spec.rope_hole_diameter / 2,
                height=spec.general_width * 2,  # Arbitrary.
            )
            .rotate(axis=bd.Axis.Y, angle=90)
            .translate((0, rope_y, rope_z))
        )

    return p


def turntable_base_cutouts(
    spec: Spec, top_body: bd.Part | bd.Compound
) -> bd.Part | bd.Compound:
    """Turntable bolt holes, captive nut slots, and azimuth marks.

    `top_body` is the top clamp half, used to find the bolt hole depths.
    """
    bolt = spec.turntable_bolt
    nut_af = bolt.nut_width_across_flats + spec.nut_clearance
    nut_thick = bolt.nut_thickness + spec.nut_clearance
    hole_diameter = bolt.diameter + spec.bolt_hole_clearance

    p = bd.Part(None)

    # Four bolts, 90 deg apart. With the wedge's two 90 deg arc slots, each
    # opposite pair covers half of the -90..+90 deg azimuth range.
    for angle in (45, 135, 225, 315):
        # Build along +X, then rotate into place.
        depth = max_hole_depth(
            spec,
            name=f"Turntable base bolt hole at {angle} deg",
            body=top_body,
            location=bd.Location(
                bd.Vector(spec.turntable_bolt_radius, 0, spec.clamp_top_z)
                .rotate(bd.Axis.Z, angle)
                .to_tuple()
            ),
            diameter=hole_diameter,
            min_depth=spec.turntable_nut_depth + bolt.nut_thickness,
        )
        feature = bd.Part(None)
        feature += bd.Cylinder(
            radius=hole_diameter / 2,
            height=depth + 1,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        ).translate((spec.turntable_bolt_radius, 0, spec.clamp_top_z + 1))

        # Nut pocket, with a slot to slide the nut in from the rim.
        nut_z = spec.clamp_top_z - spec.turntable_nut_depth
        feature += hex_nut_pocket(nut_af, nut_thick).translate(
            (spec.turntable_bolt_radius, 0, nut_z)
        )
        feature += bd.Box(
            spec.turntable_radius,
            nut_af,
            nut_thick,
            align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER),
        ).translate((spec.turntable_bolt_radius, 0, nut_z))

        p += feature.rotate(bd.Axis.Z, angle)

    # Hole for the pivot pin.
    p += pivot_pin_hole(spec).translate((0, 0, spec.clamp_top_z))

    # Azimuth marks on the rim. The 0 deg mark is wider.
    for azimuth in spec.azimuth_marks_degrees:
        p += (
            bd.Box(
                spec.mark_width * (2 if azimuth == 0 else 1),
                spec.mark_depth * 2,
                spec.turntable_base_thickness * 2,
            )
            .translate((0, spec.turntable_radius, spec.clamp_top_z))
            .rotate(bd.Axis.Z, azimuth)
        )

    return p


def clamp_half(
    spec: Spec,
    half: Literal["top", "bottom"],
    *,
    rotate_for_printing: bool = True,
) -> bd.Part | bd.Compound:
    """Create one half of the railing clamp.

    With `rotate_for_printing=False`, the part stays in its assembled
    position.
    """
    body = clamp_body(spec)
    big = spec.bolt_separation * 5
    p = body & bd.Box(
        big,
        big,
        big,
        align=(
            bd.Align.CENTER,
            bd.Align.CENTER,
            bd.Align.MIN if half == "top" else bd.Align.MAX,
        ),
    )

    if half == "top":
        p -= turntable_base_cutouts(spec, p)

    # Registration pegs on the top half (pointing down), and sockets in the
    # bottom half.
    for peg_x, peg_y in spec.registration_peg_positions:
        if half == "top":
            p += bd.Cone(
                bottom_radius=spec.registration_peg_tip_radius,
                top_radius=spec.registration_peg_base_radius,
                height=spec.registration_peg_height,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
            ).translate((peg_x, peg_y, 0))
        else:
            # Same taper, offset outward by the clearance.
            clearance = spec.registration_clearance
            p -= bd.Cone(
                bottom_radius=spec.registration_peg_tip_radius + clearance,
                top_radius=spec.registration_peg_base_radius + clearance,
                height=spec.registration_peg_height + clearance,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
            ).translate((peg_x, peg_y, 0))

    # Both halves print with their large flat face (the turntable base, or
    # the split face) on the bed.
    if rotate_for_printing:
        p = p.rotate(axis=bd.Axis.X, angle=180)

    return p


def antenna_cutouts(
    spec: Spec, wedge_body: bd.Part | bd.Compound
) -> bd.Part | bd.Compound:
    """Recess channel, bolt holes, and side-entry nut slots for the antenna.

    Built with the antenna recess floor at Z=0 and the antenna along Y, then
    moved onto the wedge's antenna face. `wedge_body` is used to find the
    bolt hole depths.
    """
    bolt = spec.antenna_bolt
    nut_af = bolt.nut_width_across_flats + spec.nut_clearance
    nut_thick = bolt.nut_thickness + spec.nut_clearance
    hole_diameter = bolt.diameter + spec.bolt_hole_clearance

    p = bd.Part(None)

    # Channel for the antenna body.
    p += bd.Box(
        spec.antenna_body_width,
        500,
        20,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    for i in (-1, 1):
        y = i * spec.antenna_hole_sep / 2

        # Bolt hole, as deep as it can go.
        depth = max_hole_depth(
            spec,
            name=f"Antenna bolt hole, {'front' if i > 0 else 'back'}",
            body=wedge_body,
            location=spec.antenna_floor_location * bd.Location((0, y, 0)),
            diameter=hole_diameter,
            min_depth=spec.antenna_nut_depth + bolt.nut_thickness,
        )
        p += bd.Cylinder(
            radius=hole_diameter / 2,
            height=depth + 1,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        ).translate((0, y, 1))

        # Hex nut pocket, rotated so flats are parallel to the slot.
        p += (
            hex_nut_pocket(nut_af, nut_thick)
            .rotate(bd.Axis.Z, 90)
            .translate((0, y, -spec.antenna_nut_depth))
        )

        # Slot to slide the nut in from the outside of the wedge.
        p += bd.Box(
            nut_af,
            spec.turntable_radius * 2,
            nut_thick,
            align=(
                bd.Align.CENTER,
                bd.Align.MIN if i > 0 else bd.Align.MAX,
                bd.Align.CENTER,
            ),
        ).translate((0, y, -spec.antenna_nut_depth))

    return p.moved(spec.antenna_floor_location)


def antenna_wedge(spec: Spec) -> bd.Part | bd.Compound:
    """Create the wedge that holds the antenna at its elevation angle.

    Built bottom-down at Z=0, which is also its print orientation. Azimuth 0
    (the antenna pointing direction) is +Y.
    """
    # Cylinder, cut off by the tilted antenna face.
    p = bd.Cylinder(
        radius=spec.turntable_radius,
        height=200,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    ) & bd.Box(
        300,
        300,
        300,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
    ).moved(
        bd.Location(
            (0, 0, spec.wedge_center_height),
            (spec.antenna_elevation_angle_degrees, 0, 0),
        )
    )

    # Safety rope holes, through the full width.
    for rope_y, rope_z in spec.wedge_rope_hole_positions:
        p -= (
            bd.Cylinder(
                radius=spec.rope_hole_diameter / 2,
                height=spec.turntable_radius * 3,  # Arbitrary.
            )
            .rotate(axis=bd.Axis.Y, angle=90)
            .translate((0, rope_y, rope_z))
        )

    # Arc slots for the turntable bolts, centered on the +/-X axis (away from
    # the antenna boom), each spanning 90 deg.
    slot_extra = spec.turntable_slot_extra_degrees
    for start in (-45 - slot_extra, 135 - slot_extra):
        arc = bd.CenterArc(
            (0, 0), spec.turntable_bolt_radius, start, 90 + 2 * slot_extra
        )
        p -= bd.extrude(
            bd.SlotArc(
                arc,
                spec.turntable_bolt.diameter + spec.bolt_hole_clearance,
            ),
            amount=200,
        )
        p -= bd.extrude(
            bd.SlotArc(arc, spec.wedge_slot_head_width),
            amount=200,
        ).translate((0, 0, spec.wedge_bolt_ledge_thickness))

    # Pointer mark on the front, to line up with the base's azimuth marks.
    p -= bd.Box(
        spec.mark_width,
        spec.mark_depth * 2,
        200,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    ).translate((0, spec.turntable_radius, 0))

    p -= pivot_pin_hole(spec)

    p -= antenna_cutouts(spec, p)

    return p


def pivot_pin_hole(spec: Spec) -> bd.Part | bd.Compound:
    """Hole for half of the pivot pin, going down from Z=0 (and up)."""
    return bd.Cylinder(
        radius=(spec.pivot_pin_diameter + spec.pivot_pin_clearance) / 2,
        # Extra depth so the pin never bottoms out.
        height=(spec.pivot_pin_length / 2 + 0.5) * 2,
    )


def pivot_pin(spec: Spec) -> bd.Part | bd.Compound:
    """Pin between the turntable base and the wedge, centered at Z=0.

    Prints standing upright.
    """
    p = bd.Part() + bd.Cylinder(
        radius=spec.pivot_pin_diameter / 2,
        height=spec.pivot_pin_length,
    )
    return bd.chamfer(
        p.edges().filter_by(bd.GeomType.CIRCLE), spec.pivot_pin_chamfer
    )


def main_mount_assembly(spec: Spec, azimuth_deg: float) -> bd.Compound:
    """Create the assembled mount, as named parts."""
    top = clamp_half(spec, "top", rotate_for_printing=False)
    top.label = "main_mount_top"
    top.color = bd.Color("navyblue")

    bottom = clamp_half(spec, "bottom", rotate_for_printing=False)
    bottom.label = "main_mount_bottom"
    bottom.color = bd.Color("purple")

    # Compound -> Solid, so the color is kept in the STEP export.
    wedge_solid = antenna_wedge(spec).solid()
    assert wedge_solid is not None
    wedge = wedge_solid.rotate(bd.Axis.Z, azimuth_deg).translate(
        (0, 0, spec.clamp_top_z)
    )
    wedge.label = "antenna_wedge"
    wedge.color = bd.Color("lightblue")

    pin_solid = pivot_pin(spec).solid()
    assert pin_solid is not None
    pin = pin_solid.translate((0, 0, spec.clamp_top_z))
    pin.label = "turntable_pivot_pin"
    pin.color = bd.Color("orange")

    return bd.Compound(
        label="main_mount_assembly", children=[top, bottom, wedge, pin]
    )


if __name__ == "__main__":
    # Azimuth of the wedge in the assembly preview.
    SHOW_AZIMUTH_DEGREES = 45.0

    parts: dict[str, bd.Part | bd.Compound] = {
        "main_mount_top": clamp_half(Spec(), "top"),
        "main_mount_bottom": clamp_half(Spec(), "bottom"),
        "antenna_wedge": antenna_wedge(Spec()),
        "turntable_pivot_pin": pivot_pin(Spec()).translate(
            (0, 0, Spec().pivot_pin_length / 2)
        ),
        "preview_main_mount_assembly": main_mount_assembly(
            Spec(), SHOW_AZIMUTH_DEGREES
        ),
    }

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(
        exist_ok=True
    )
    for name, part in parts.items():
        assert isinstance(part, bd.Part | bd.Solid | bd.Compound), (
            f"{name} is not an expected type ({type(part)})"
        )
        if not part.is_manifold:
            logger.warning(f'Part "{name}" is not manifold')

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    logger.info(
        "Bolts:\n" + "\n".join(f"  {line}" for line in bolt_bom(Spec()))
    )

    logger.info(f"Showing assembly (azimuth {SHOW_AZIMUTH_DEGREES} deg)")
    show(parts["preview_main_mount_assembly"])
