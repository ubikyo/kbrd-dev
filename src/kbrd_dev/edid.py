"""Physical screen size via the kernel's DRM/KMS sysfs tree.

KBRD-DEV drives its screen through SDL's `kmsdrm` video driver (see
`SDL_VIDEO_DRIVER` in `config.py`), which talks to the same Direct
Rendering Manager the kernel exposes under `/sys/class/drm/`. This is
also why `BR2_PACKAGE_LIBDRM_INSTALL_TESTS` is enabled on the image: it
ships `modetest`, the usual way to inspect connectors by hand over SSH.

For KBRD-DEV's own reporting, reading the sysfs tree directly is a
better fit than either linking libdrm or shelling out to `modetest`:
every connector already has a `status` file and, once connected, an
`edid` file holding the panel's raw EDID block — no ioctl bindings, no
subprocess, no parsing of a human-oriented text table that changes
shape across libdrm versions. This sysfs ABI has been stable since the
kernel introduced KMS.

The EDID base block encodes the panel's maximum image size in whole
centimetres at byte offsets 21 (width) and 22 (height) — see VESA's
"EDID release A2" section 3.6.4. A value of 0 in either byte means the
panel does not report a physical size (common on some projectors),
which is surfaced as `None` rather than a bogus 0mm.
"""

from pathlib import Path

DRM_ROOT = Path("/sys/class/drm")
_EDID_WIDTH_CM_OFFSET = 21
_EDID_HEIGHT_CM_OFFSET = 22


def read_physical_size_mm(drm_root: Path = DRM_ROOT) -> tuple[int, int] | None:
    """Return `(width_mm, height_mm)` for the first connected connector
    whose EDID reports a physical size, or `None` if there isn't one."""
    for connector in sorted(drm_root.glob("card*-*")):
        try:
            status = (connector / "status").read_text().strip()
        except OSError:
            continue
        if status != "connected":
            continue
        size = _parse_edid_size_mm(connector / "edid")
        if size is not None:
            return size
    return None


def _parse_edid_size_mm(edid_path: Path) -> tuple[int, int] | None:
    try:
        edid = edid_path.read_bytes()
    except OSError:
        return None
    if len(edid) <= _EDID_HEIGHT_CM_OFFSET:
        return None
    width_cm = edid[_EDID_WIDTH_CM_OFFSET]
    height_cm = edid[_EDID_HEIGHT_CM_OFFSET]
    if width_cm == 0 or height_cm == 0:
        return None
    return width_cm * 10, height_cm * 10
