# UI format helper

This repository bundles 010 Editor templates and archive samples for Metal Gear Solid V's UI formats.  The `ui_tool` package implements a small CLI that can decompile binary `.uilb` layout files into JSON (and assemble JSON back into binary) so you can inspect and edit the data without using 010 Editor.

## Usage

```bash
python -m ui_tool decompile path/to/layout.uilb layout.json
python -m ui_tool compile layout.json rebuilt.uilb
python -m ui_tool convert 'uilb/PC GZ/UI_gz_title_logo.uilb' converted.uilb
```

The JSON contains all numeric fields from the template, so you can tweak values and round-trip the file.  Currently only the UILB layout container is implemented; the command dispatch is structured so adding UIF, UIGB, or UIA decoders only requires plugging new modules into the CLI.

The `convert` command upgrades PC Ground Zeroes `.uilb` archives to the TPP layout format so that you can reuse older resources in the newer engine.  The repository ships with a hash map that covers the resource paths contained in `ui format examples.zip`; if you want to convert files that reference new assets you can pass `--path-map` to point at a custom JSON file that maps path strings to their TPP hash values.
