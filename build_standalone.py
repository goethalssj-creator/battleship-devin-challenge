"""Builds atlantis_standalone.html: index.html with every image in assets/ embedded, so the single file works on its own."""
import base64, pathlib, re
root = pathlib.Path(__file__).parent
html = (root / "index.html").read_text()
uri = lambda p: "data:image/webp;base64," + base64.b64encode((root / p).read_bytes()).decode()
html = html.replace("url(assets/bg.webp)", f"url({uri('assets/bg.webp')})")
sprites = {p.stem: uri(f"assets/{p.name}") for p in sorted((root / "assets").glob("*_[hv].webp"))}
old_r = 'const ruinURL = (name, horiz) => `assets/ruin_${KIND[name]}_${horiz?"h":"v"}.webp`;'
assert old_r in html
html = html.replace(old_r, 'const ruinURL = (name, horiz) => SPRITE_DATA[`ruin_${KIND[name]}_${horiz?"h":"v"}`];')
table = "const SPRITE_DATA = {" + ",".join(f'"{k}":"{v}"' for k, v in sprites.items()) + "};\n"
old = 'const spriteURL = (name, horiz) => `assets/${KIND[name]}_${horiz?"h":"v"}.webp`;'
assert old in html
html = html.replace(old, table + 'const spriteURL = (name, horiz) => SPRITE_DATA[`${KIND[name]}_${horiz?"h":"v"}`];')
html = html.replace("i.src='assets/bg.webp'", "i.src=''")
assert "assets/" not in re.sub(r"data:image/webp;base64,[A-Za-z0-9+/=]+", "", html)
(root / "atlantis_standalone.html").write_text(html)
print("wrote atlantis_standalone.html", len(html) // 1024, "KB")
