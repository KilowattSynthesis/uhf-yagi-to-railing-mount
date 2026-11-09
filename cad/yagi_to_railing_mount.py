import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal, assert_never

import build123d as bd
from build123d_ease import show
from loguru import logger


@dataclass(frozen=True)
class MetricBolt:
    """Nominal dimensions of a metric bolt and its hex nut.

    Precise values. Do not add clearance here.
    """

    name: str
    diameter: float
    nut_width_across_flats: float
    nut_thickness: float
    # Counterbore for the bolt head, with room for a socket/wrench.
    head_counterbore_diameter: float

    @property
    def nut_width_across_corners(self) -> float:
        """Width of the hex nut across its corners."""
        return self.nut_width_across_flats / math.cos(math.radians(30))


M3 = MetricBolt("M3", 3.0, 5.5, 2.4, 12.0)
M4 = MetricBolt("M4", 4.0, 7.0, 3.2, 15.0)
M5 = MetricBolt("M5", 5.0, 8.0, 4.0, 18.0)
M6 = MetricBolt("M6", 6.0, 10.0, 5.0, 20.0)

# Change these to switch bolt sizes.
ANTENNA_BOLT = M4  # Holds the antenna body to the plate.
CLAMP_BOLT = M5  # Clamps the top and bottom halves around the railing.


@dataclass
class Spec:
    """Specification for main_mount."""

    railing_width: float = 52
    railing_height: float = 26.5

    general_width: float = 35
    body_radius: float = 35

    antenna_elevation_angle_degrees: float = 40

    clamp_bolt: MetricBolt = CLAMP_BOLT
    antenna_bolt: MetricBolt = ANTENNA_BOLT

    # Diameter clearance for all bolt holes.
    bolt_hole_clearance: float = 0.5

    # Center-to-center distance between clamp bolt holes.
    bolt_separation: float = 75

    bolt_extra_length_into_bottom: float = 13.0

    # Clamp captive nut, pressed into the bottom of each clamp bolt boss.
    clamp_nut_clearance: float = 0.3
    clamp_bolt_boss_wall: float = 2.2  # Around the nut's corners.

    antenna_body_width: float = 15.0
    antenna_body_recess_depth: float = 2.0
    antenna_hole_sep: float = 46

    # Antenna bolts + nuts holding the antenna body to the plate.
    # Each hole is made as deep as possible, while keeping this much
    # material between it and any other feature or outer surface.
    antenna_bolt_hole_min_wall: float = 1.5
    antenna_nut_clearance: float = 0.4
    # From the recess floor to the center of the nut slot.
    antenna_nut_depth: float = 6.0

    # Round pad on top of the plate, so rotated hole patterns fit.
    antenna_pad_radius: float = 30.0
    # Raises the pad above the plate, for more material between the
    # rotated antenna bolt holes and the railing. Does not change the
    # clamp bolt length.
    antenna_pad_raise: float = 8.0
    # Total thickness of the pad, from its top surface.
    antenna_pad_thickness: float = 23.0

    # Rotation of the antenna about the plate normal, for each mounting
    # position. 0 is pointing straight out from the railing.
    antenna_azimuth_angles_degrees: tuple[float, ...] = field(
        default_factory=lambda: (-45.0, 0.0, 45.0)
    )

    # Through-holes parallel to the railing, for a safety rope.
    rope_hole_diameter: float = 7.0
    # (y, z) centers in the plate frame (before the elevation rotation).
    # Positioned for >=3 mm walls to the railing, bolts, and outer faces.
    rope_hole_positions: tuple[tuple[float, float], ...] = (
        (21.0, 18.0),  # Top half.
        (-28.0, 17.5),  # Top half. Tight: ~3 mm walls.
        (-18.0, -14.0),  # Bottom half.
        (0.0, -26.0),  # Bottom half.
    )

    make_type: Literal["full", "top", "bottom"] = "full"

    def __post_init__(self) -> None:
        """Post initialization checks."""
        # Antenna nut slot must fit within the pad.
        assert (
            self.antenna_body_recess_depth
            + self.antenna_nut_depth
            + self.antenna_bolt.nut_thickness
            < self.antenna_pad_thickness
        )
        # Leave material above the antenna nut slot.
        assert (
            self.antenna_nut_depth
            - (self.antenna_bolt.nut_thickness + self.antenna_nut_clearance)
            / 2
            >= 2  # noqa: PLR2004
        )
        assert self.antenna_hole_sep / 2 < self.antenna_pad_radius

    @property
    def clamp_bolt_boss_radius(self) -> float:
        """Radius of the boss around each clamp bolt."""
        nut_pocket_across_corners = (
            self.clamp_bolt.nut_width_across_flats + self.clamp_nut_clearance
        ) / math.cos(math.radians(30))
        return nut_pocket_across_corners / 2 + self.clamp_bolt_boss_wall

    @property
    def plate_top_z(self) -> float:
        """Top of the antenna plate (before recess), in plate frame."""
        return self.bolt_separation / 2

    @property
    def pad_top_z(self) -> float:
        """Top of the antenna pad (before recess), in plate frame."""
        return self.plate_top_z + self.antenna_pad_raise

    @property
    def recess_floor_z(self) -> float:
        """Floor of the antenna body recess, in plate frame."""
        return self.pad_top_z - self.antenna_body_recess_depth


def true_pointing_degrees(
    elevation_deg: float, plate_rotation_deg: float
) -> tuple[float, float]:
    """Get the real (azimuth, elevation) for a rotation about plate normal.

    Rotating on the tilted plate trades away some elevation.
    """
    el = math.radians(elevation_deg)
    rot = math.radians(plate_rotation_deg)
    # Boom direction in world frame (Y=out from railing, Z=up).
    x = math.sin(rot)
    y = math.cos(rot) * math.cos(el)
    z = math.cos(rot) * math.sin(el)
    return (
        math.degrees(math.atan2(x, y)),
        math.degrees(math.asin(z)),
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


_antenna_hole_depth_cache: dict[tuple[str, float, float], float] = {}


def antenna_hole_depth(
    spec: Spec, body: bd.Part | bd.Compound, angle_deg: float, y: float
) -> float:
    """Find the deepest antenna bolt hole (below the recess floor).

    Keeps `antenna_bolt_hole_min_wall` of material around the hole, within
    `body` (world frame, no antenna cutouts). The hole is at `y` along the
    antenna, which is rotated by `angle_deg` about the plate normal.

    Each result is cached and logged the first time it's computed.
    """
    cache_key = (
        # The body doesn't depend on the make type or antenna angles.
        repr(
            replace(spec, make_type="full", antenna_azimuth_angles_degrees=())
        ),
        round(angle_deg, 3),
        round(y, 3),
    )
    if cache_key in _antenna_hole_depth_cache:
        return _antenna_hole_depth_cache[cache_key]

    hole = bd.Vector(0, y, 0).rotate(bd.Axis.Z, angle_deg)
    x, y = hole.X, hole.Y

    wall = spec.antenna_bolt_hole_min_wall
    probe_radius = (
        spec.antenna_bolt.diameter + spec.bolt_hole_clearance
    ) / 2 + wall

    def fits(depth: float) -> bool:
        probe = (
            bd.Cylinder(
                radius=probe_radius,
                height=depth + wall,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
            )
            .translate((x, y, spec.recess_floor_z))
            .rotate(axis=bd.Axis.X, angle=spec.antenna_elevation_angle_degrees)
        )
        outside = probe - body
        return outside.volume < 1e-3  # noqa: PLR2004

    # Binary search. The nut slot sets the minimum.
    low = spec.antenna_nut_depth + spec.antenna_bolt.nut_thickness
    high = spec.recess_floor_z
    assert fits(low), f"No room for antenna bolt hole at ({x:.1f}, {y:.1f})"
    while high - low > 0.1:  # noqa: PLR2004
        mid = (low + high) / 2
        if fits(mid):
            low = mid
        else:
            high = mid

    depth = math.floor(low * 2) / 2  # Round down to 0.5 mm.
    _antenna_hole_depth_cache[cache_key] = depth
    logger.info(
        f"Antenna bolt hole at {angle_deg:+.0f} deg, "
        f"{'front' if cache_key[2] > 0 else 'back'}: "
        f"{depth} mm deep below recess floor"
    )
    return depth


def antenna_bolt_cutouts(
    spec: Spec, angle_deg: float, body: bd.Part | bd.Compound
) -> bd.Part | bd.Compound:
    """Recess channel, bolt holes, and side-entry nut slots at one angle.

    Built in the plate frame with the antenna along Y, then rotated about
    the plate normal (Z). `body` is used to find the bolt hole depths.
    """
    p = bd.Part(None)

    # Channel for the antenna body.
    p += bd.Box(
        spec.antenna_body_width,
        500,
        20,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    ).translate((0, 0, spec.recess_floor_z))

    bolt = spec.antenna_bolt
    nut_af = bolt.nut_width_across_flats + spec.antenna_nut_clearance
    nut_thick = bolt.nut_thickness + spec.antenna_nut_clearance
    nut_z = spec.recess_floor_z - spec.antenna_nut_depth

    for i in (-1, 1):
        y = i * spec.antenna_hole_sep / 2

        # Bolt hole, as deep as it can go.
        depth = antenna_hole_depth(spec, body, angle_deg, y)
        p += bd.Cylinder(
            radius=(bolt.diameter + spec.bolt_hole_clearance) / 2,
            height=depth + 1,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        ).translate((0, y, spec.recess_floor_z + 1))

        # Hex nut pocket, rotated so flats are parallel to the slot.
        p += (
            hex_nut_pocket(nut_af, nut_thick)
            .rotate(bd.Axis.Z, 90)
            .translate((0, y, nut_z))
        )

        # Slot to slide the nut in from the outside edge of the pad.
        p += bd.Box(
            nut_af,
            spec.antenna_pad_radius + 8 - spec.antenna_hole_sep / 2,
            nut_thick,
            align=(
                bd.Align.CENTER,
                bd.Align.MIN if i > 0 else bd.Align.MAX,
                bd.Align.CENTER,
            ),
        ).translate((0, y, nut_z))

    return p.rotate(bd.Axis.Z, angle_deg)


def _split_cutter(
    spec: Spec, keep: Literal["top", "bottom"]
) -> bd.Part | bd.Compound:
    """Solid to subtract, to keep only the `keep` half (world frame)."""
    return bd.Box(
        spec.antenna_pad_radius * 4,
        spec.bolt_separation * 5,
        spec.bolt_separation * 5,
        align=(
            bd.Align.CENTER,
            bd.Align.CENTER,
            {"bottom": bd.Align.MIN, "top": bd.Align.MAX}[keep],
        ),
    ).rotate(axis=bd.Axis.X, angle=spec.antenna_elevation_angle_degrees)


def main_mount_joined(
    spec: Spec, *, rotate_for_printing: bool = True
) -> bd.Part | bd.Compound:
    """Create a CAD model of part.

    With `rotate_for_printing=False`, the part stays in its assembled
    position.
    """
    p = bd.Part(None)

    # Create the main body.
    p += bd.Cylinder(
        radius=spec.body_radius,
        height=spec.general_width,
    ).rotate(axis=bd.Axis.Y, angle=90)

    # Add the rotated mount plate for the antenna.
    plate_mount = bd.Part() + bd.Box(
        spec.general_width,
        spec.body_radius * 2,
        spec.plate_top_z,
        align=(
            bd.Align.CENTER,
            bd.Align.CENTER,
            bd.Align.MIN,
        ),
    )

    # Round pad, wide enough for the rotated antenna hole patterns.
    plate_mount += bd.Cylinder(
        radius=spec.antenna_pad_radius,
        height=spec.antenna_pad_thickness,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
    ).translate((0, 0, spec.pad_top_z))

    # Add clamp bolt bosses.
    for i in (-1, 1):
        plate_mount += bd.Cylinder(
            radius=spec.clamp_bolt_boss_radius,
            height=spec.plate_top_z,
            align=(
                bd.Align.CENTER,
                bd.Align.CENTER,
                bd.Align.MIN,
            ),
        ).translate(
            (
                0,
                i * spec.bolt_separation / 2,
                -spec.bolt_extra_length_into_bottom,
            )
        )

    # Clamp bolt holes, heads, and captive nuts.
    for i in (-1, 1):
        y = i * spec.bolt_separation / 2

        # Main bolt hole.
        plate_mount -= bd.Cylinder(
            radius=(spec.clamp_bolt.diameter + spec.bolt_hole_clearance) / 2,
            height=spec.bolt_separation * 10,  # Arbitrary.
        ).translate((0, y, 0))

        # Bolt head.
        plate_mount -= bd.Cylinder(
            radius=spec.clamp_bolt.head_counterbore_diameter / 2,
            height=100,
            align=(
                bd.Align.CENTER,
                bd.Align.CENTER,
                bd.Align.MIN,
            ),
        ).translate(
            (
                0,
                y,
                spec.plate_top_z - spec.bolt_extra_length_into_bottom,
            )
        )

        # Captive nut, pressed in from the bottom of the boss.
        nut_thick = spec.clamp_bolt.nut_thickness + spec.clamp_nut_clearance
        plate_mount -= hex_nut_pocket(
            spec.clamp_bolt.nut_width_across_flats + spec.clamp_nut_clearance,
            # Extra length so it cleanly opens out the bottom.
            nut_thick + 2,
        ).translate(
            (0, y, -spec.bolt_extra_length_into_bottom + nut_thick / 2 - 1)
        )

    p += plate_mount.rotate(
        axis=bd.Axis.X, angle=spec.antenna_elevation_angle_degrees
    )

    # Remove the railing.
    p -= bd.Box(
        spec.antenna_pad_radius * 4,  # Arbitrary.
        spec.railing_width,
        spec.railing_height,
        align=bd.Align.CENTER,
    )

    # Safety rope holes, through the full width.
    for rope_y, rope_z in spec.rope_hole_positions:
        p -= (
            bd.Cylinder(
                radius=spec.rope_hole_diameter / 2,
                height=spec.antenna_pad_radius * 4,  # Arbitrary.
            )
            .rotate(axis=bd.Axis.Y, angle=90)
            .translate((0, rope_y, rope_z))
            .rotate(axis=bd.Axis.X, angle=spec.antenna_elevation_angle_degrees)
        )

    # Antenna mounting cutouts (bolts + nuts), at each angle. Not needed
    # for the bottom half.
    if spec.make_type != "bottom":
        # Top half, without the antenna cutouts. Used to size the holes.
        top_body = p - _split_cutter(spec, "top")
        for angle in spec.antenna_azimuth_angles_degrees:
            p -= antenna_bolt_cutouts(spec, angle, top_body).rotate(
                axis=bd.Axis.X, angle=spec.antenna_elevation_angle_degrees
            )

    # Apply the make type.
    if spec.make_type == "full":
        pass
    elif spec.make_type in ("top", "bottom"):
        p -= _split_cutter(spec, spec.make_type)

    else:
        assert_never(spec.make_type)

    # Rotate for easy printing.
    if rotate_for_printing and spec.make_type == "top":
        p = p.rotate(
            axis=bd.Axis.X, angle=180 - spec.antenna_elevation_angle_degrees
        )

    return p


def main_mount_assembly(spec: Spec) -> bd.Compound:
    """Create the assembled top and bottom halves, as named parts."""
    top = main_mount_joined(
        replace(spec, make_type="top"), rotate_for_printing=False
    )
    top.label = "main_mount_top"
    top.color = bd.Color("navyblue")

    bottom = main_mount_joined(
        replace(spec, make_type="bottom"), rotate_for_printing=False
    )
    bottom.label = "main_mount_bottom"
    bottom.color = bd.Color("magenta")

    return bd.Compound(label="main_mount_assembly", children=[top, bottom])


if __name__ == "__main__":
    angle_variants: dict[str, tuple[float, ...]] = {
        # 90 deg also covers -90 deg (same holes, antenna flipped).
        "az45": (-45.0, 0.0, 45.0, 90.0),
        "az60": (-60.0, 0.0, 60.0),
    }
    # Which variant's assembly to show in the viewer.
    SHOW_VARIANT = "az60"
    assert SHOW_VARIANT in angle_variants

    for variant_name, angles in angle_variants.items():
        for angle in angles:
            az, el = true_pointing_degrees(
                Spec.antenna_elevation_angle_degrees, angle
            )
            logger.info(
                f"{variant_name}: plate rotation {angle:+.0f} deg -> "
                f"true azimuth {az:+.1f} deg, elevation {el:.1f} deg"
            )

    parts: dict[str, bd.Part | bd.Compound] = {
        "main_mount_bottom": main_mount_joined(Spec(make_type="bottom"))
    }
    for variant_name, angles in angle_variants.items():
        parts[f"main_mount_top_{variant_name}"] = main_mount_joined(
            Spec(make_type="top", antenna_azimuth_angles_degrees=angles)
        )
        parts[f"preview_main_mount_assembly_{variant_name}"] = (
            main_mount_assembly(Spec(antenna_azimuth_angles_degrees=angles))
        )

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

    logger.info(f"Showing assembly ({SHOW_VARIANT})")
    show(parts[f"preview_main_mount_assembly_{SHOW_VARIANT}"])
