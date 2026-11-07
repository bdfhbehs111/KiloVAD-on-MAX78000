import fitz, sys, pathlib
src = pathlib.Path(sys.argv[1]); out = src.with_suffix(".txt")
doc = fitz.open(src)
out.write_text("".join(f"\n===== PAGE {i} =====\n" + p.get_text() for i, p in enumerate(doc, 1)), encoding="utf-8")
print(f"{src.name}: pages={doc.page_count} -> {out}")
