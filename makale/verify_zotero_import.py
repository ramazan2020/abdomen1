from pathlib import Path
import re


ris = Path("zotero_import/234_makale_zotero_import.ris").read_text(encoding="utf-8")
bib = Path("zotero_import/234_makale_zotero_import.bib").read_text(encoding="utf-8")
markers = ["GÃ", "Ä±", "ÅŸ", "Ã¼", "Ã‡", "Ĺ", "â€“", "Â©", "Î™"]

print("ris_TY", ris.count("TY  - "))
print("ris_ER", ris.count("ER  -"))
print("bib_entries", len(re.findall(r"^@", bib, re.M)))
print("replacement_ris", "\ufffd" in ris)
print("replacement_bib", "\ufffd" in bib)
marker_result = {m: (m in ris or m in bib) for m in markers}
print("markers", repr(marker_result).encode("unicode_escape").decode())

for needle in ["2010", "Güneri", "Theodorakopoulos"]:
    i = ris.find(needle)
    if i >= 0:
        print(needle, ris[i:i + 140].encode("unicode_escape").decode())
