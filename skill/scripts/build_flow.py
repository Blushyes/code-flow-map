#!/usr/bin/env python3
"""Render a FLOW_DATA spec into a single self-contained interactive HTML.

Usage:
    # single flow
    python build_flow.py <spec.json> <output.html> [--no-open]
    # refactor compare (old vs new, side by side with cross-mapping)
    python build_flow.py --old <old.json> --new <new.json> <output.html> [--no-open]

Inlines the vendored dagre + rough.js and the spec into assets/flow-template.html,
so the output opens offline / over file://. Validates that every edge and every
io from/to points at a node that exists — a wrong link silently breaks the
data-flow navigation, so we fail loud instead. In compare mode it additionally
checks that every new-node `maps_from` and every `removed.old_id` points at a
real old node — the two specs stay physically separate (old never references
new), the only link is new -> old.
"""
import json, sys, subprocess, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
TEMPLATE = ASSETS / "flow-template.html"
VENDOR = ASSETS / "vendor"


def validate(spec):
    errs = []
    nodes = spec.get("nodes", [])
    ids = [n.get("id") for n in nodes]
    node_ids = set(ids)
    for i in ids:
        if ids.count(i) > 1:
            errs.append(f"duplicate node id: {i}")
    cl_ids = {c.get("id") for c in spec.get("clusters", [])}
    for n in nodes:
        if n.get("cluster") and n["cluster"] not in cl_ids:
            errs.append(f"node {n.get('id')} references missing cluster {n['cluster']}")
        for io_key in ("inputs", "outputs"):
            for it in n.get(io_key, []):
                for link_key in ("from", "to"):
                    tgt = it.get(link_key)
                    for t in (tgt if isinstance(tgt, list) else ([tgt] if tgt else [])):
                        if t not in node_ids:
                            errs.append(f"node {n.get('id')} {io_key} '{it.get('name')}' "
                                        f"{link_key} -> unknown node '{t}'")
    for e in spec.get("edges", []):
        for k in ("from", "to"):
            if e.get(k) not in node_ids:
                errs.append(f"edge {e.get('from')}->{e.get('to')}: {k} is unknown node")
    return set(errs)  # dedup


def validate_mapping(old, new):
    errs = []
    old_ids = {n.get("id") for n in old.get("nodes", [])}
    for n in new.get("nodes", []):
        for o in n.get("maps_from", []) or []:
            if o not in old_ids:
                errs.append(f"new node {n.get('id')} maps_from -> unknown old node '{o}'")
    for r in new.get("removed", []) or []:
        if r.get("old_id") not in old_ids:
            errs.append(f"removed.old_id '{r.get('old_id')}' is not an old node")
    return set(errs)


def fail_if(errs):
    if errs:
        print("SPEC ERRORS:", file=sys.stderr)
        for e in sorted(errs):
            print("  - " + e, file=sys.stderr)
        sys.exit(1)


def main():
    argv = sys.argv[1:]
    no_open = "--no-open" in argv
    old_path = new_path = None
    if "--old" in argv:
        old_path = pathlib.Path(argv[argv.index("--old") + 1])
    if "--new" in argv:
        new_path = pathlib.Path(argv[argv.index("--new") + 1])
    # positionals = anything that isn't a flag or a flag's value
    skip = {"--no-open"}
    flagval_idx = set()
    for fl in ("--old", "--new"):
        if fl in argv:
            flagval_idx.add(argv.index(fl)); flagval_idx.add(argv.index(fl) + 1)
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and i not in flagval_idx and a not in skip]

    compare = bool(old_path and new_path)
    if compare:
        if not pos:
            sys.exit("usage: build_flow.py --old <old.json> --new <new.json> <output.html>")
        out_path = pathlib.Path(pos[0])
        old = json.loads(old_path.read_text(encoding="utf-8"))
        new = json.loads(new_path.read_text(encoding="utf-8"))
        fail_if(validate(old) | validate(new) | validate_mapping(old, new))
        flow_data = {"old": old, "new": new}
        title = (new.get("title") or old.get("title") or "refactor") + " · 重构对比"
        n_count = len(old.get("nodes", [])) + len(new.get("nodes", []))
    else:
        if len(pos) < 2:
            sys.exit("usage: build_flow.py <spec.json> <output.html> [--no-open]")
        spec = json.loads(pathlib.Path(pos[0]).read_text(encoding="utf-8"))
        out_path = pathlib.Path(pos[1])
        fail_if(validate(spec))
        flow_data = spec
        title = spec.get("title", "code flow")
        n_count = len(spec.get("nodes", []))

    html = TEMPLATE.read_text(encoding="utf-8")
    dagre_js = (VENDOR / "dagre.min.js").read_text(encoding="utf-8")
    rough_js = (VENDOR / "roughjs.min.js").read_text(encoding="utf-8")

    html = html.replace("__TITLE__", title)
    html = html.replace("/*__DAGRE_JS__*/", dagre_js)
    html = html.replace("/*__ROUGH_JS__*/", rough_js)
    data = json.dumps(flow_data, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace("/*__FLOW_DATA__*/ null", data)

    out_path.write_text(html, encoding="utf-8")
    mode = "compare" if compare else "single"
    print(f"wrote {out_path}  ({len(html)//1024} KB, {mode}, {n_count} nodes)")

    if not no_open:
        opener = {"darwin": "open"}.get(sys.platform, "xdg-open")
        try:
            subprocess.run([opener, str(out_path)], check=False)
        except FileNotFoundError:
            print(f"open it manually: {out_path.resolve()}")


if __name__ == "__main__":
    main()
