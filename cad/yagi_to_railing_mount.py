from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never

import build123d as bd
from build123d_ease import show
from loguru import logger


@dataclass
class Spec:
    """Specification for main_mount."""

    railing_width: float = 52
    railing_height: float = 26.5

    general_width: float = 35

    antenna_elevation_angle_degrees: float = 40

    # Precise bolt diameter. Do not add clearance.
    bolt_diameter: float = 5.0
    # Center-to-center distance between bolt holes.
    bolt_separation: float = 75

    bolt_diameter_clearance: float = 0.5  # Clearance for bolt holes.

    bolt_extra_length_into_bottom: float = 13.0

    antenna_body_width: float = 15.0
    antenna_body_recess_depth: float = 2.0
    antenna_hole_sep: float = 46
    antenna_hole_peg_diameter: float = 5.0

    zip_tie_slot_width: float = 8.0
    zip_tie_slot_height: float = 4.0

    make_type: Literal["full", "top", "bottom"] = "full"

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert True


def main_mount_joined(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of part."""
    p = bd.Part(None)

    # Create the main body.
    p += bd.Cylinder(
        radius=(spec.bolt_separation / 2 - spec.bolt_diameter / 2),
        height=spec.general_width,
    ).rotate(axis=bd.Axis.Y, angle=90)

    # Add the rotated mount plate for the antenna.
    plate_mount = (
        bd.Part()
        + bd.Box(
            spec.general_width,
            spec.bolt_separation - spec.bolt_diameter,
            spec.bolt_separation / 2,
            align=(
                bd.Align.CENTER,
                bd.Align.CENTER,
                bd.Align.MIN,
            ),
        )
        - bd.Box(
            spec.antenna_body_width,
            500,
            20,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        ).translate(
            (0, 0, spec.bolt_separation / 2 - spec.antenna_body_recess_depth)
        )
    )
    # Add channel for antenna body, and pegs to mate with antenna body holes.
    for i in (-1, 1):
        plate_mount += (
            bd.Cylinder(
                radius=spec.antenna_hole_peg_diameter / 2,
                height=2,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        ).translate(
            (
                0,
                i * spec.antenna_hole_sep / 2,
                spec.bolt_separation / 2 - spec.antenna_body_recess_depth,
            )
        )

    # Add slots for zip ties to hold the antenna body in place.
    for i in (-1, 1):
        plate_mount -= (
            bd.Box(
                spec.antenna_body_width * 5,  # Arbitrary.
                spec.zip_tie_slot_width,
                spec.zip_tie_slot_height,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
            )
        ).translate(
            (
                0,
                i * spec.antenna_hole_sep * 0.5,
                spec.bolt_separation / 2 - spec.antenna_body_recess_depth - 5,
            )
        )

    # Add bolt holes part.
    for i in (-1, 1):
        plate_mount += bd.Cylinder(
            radius=spec.bolt_diameter / 2 + 3,
            height=(spec.bolt_separation / 2),
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

        # Main bolt hole.
        plate_mount -= bd.Cylinder(
            radius=spec.bolt_diameter / 2 + spec.bolt_diameter_clearance / 2,
            height=spec.bolt_separation * 10,  # Arbitrary.
        ).translate((0, i * spec.bolt_separation / 2, 0))

        # Bolt head.
        plate_mount -= bd.Cylinder(
            radius=9,
            height=100,
            align=(
                bd.Align.CENTER,
                bd.Align.CENTER,
                bd.Align.MIN,
            ),
        ).translate(
            (
                0,
                i * spec.bolt_separation / 2,
                (spec.bolt_separation / 2)
                - spec.bolt_extra_length_into_bottom,
            )
        )

    p += plate_mount.rotate(
        axis=bd.Axis.X, angle=spec.antenna_elevation_angle_degrees
    )

    # Remove the railing.
    p -= bd.Box(
        spec.general_width * 2,  # Arbitrary.
        spec.railing_width,
        spec.railing_height,
        align=bd.Align.CENTER,
    )

    # Apply the make type.
    if spec.make_type == "full":
        pass
    elif spec.make_type in ("top", "bottom"):
        p -= bd.Box(
            spec.general_width * 2,
            spec.bolt_separation * 5,
            spec.bolt_separation * 5,
            align=(
                bd.Align.CENTER,
                bd.Align.CENTER,
                {"bottom": bd.Align.MIN, "top": bd.Align.MAX}[spec.make_type],
            ),
        ).rotate(axis=bd.Axis.X, angle=spec.antenna_elevation_angle_degrees)

    else:
        assert_never(spec.make_type)

    # Rotate for easy printing.
    if spec.make_type == "top":
        p = p.rotate(
            axis=bd.Axis.X, angle=180 - spec.antenna_elevation_angle_degrees
        )

    return p


if __name__ == "__main__":
    parts = {
        "main_mount_top": show(main_mount_joined(Spec(make_type="top"))),
        "main_mount_bottom": show(main_mount_joined(Spec(make_type="bottom"))),
        "preview_main_mount_joined": show(main_mount_joined(Spec())),
    }

    logger.info("Showing CAD model(s)")

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
