# Legacy reference code

Kept for reference only — nothing here is imported by `kbrd_dev` or
deployed to the device (the Makefile's `deploy` target only rsyncs
`src/kbrd_dev/`).

## keyboard.py

The pre-Factory-grid `Keyboard` widget, superseded by
`kbrd_dev.ui.display.Display`. It rendered the *old* per-key geometry
model (`GET /api/layer/active`'s `layout.layout.keys[]`, computed via
KBRD-API's `layout_geometry()`/`geometry_layout.py` from a layout's
`geometry` field) and mounted each attached plugin's own live Kivy widget
on top of every key via `PluginRegistry`/`DisplayManager`.

KBRD-WEB's own `<Display>` no longer renders that way either — it builds
the grid straight from a layer's `factory_layout` (rows/cells/merges/
divisions — see `kbrd-web/src/utils/layout.ts`) instead, bypassing
`layout.layout` entirely. `kbrd_dev.ui.display` ports that same geometry
math (`kbrd_dev.layout_grid`) so the device matches what the web editor
actually shows. Full git history for this file is still available via
`git log -- src/kbrd_dev/ui/keyboard.py` in this repo; this copy just
keeps it easy to re-read without digging through history.
