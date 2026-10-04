"""Build the portfolio: content.yaml + templates/ + images/source/ + fonts/ -> site/.

Run locally with:  uv run python build.py
GitHub Actions runs the same command on every push and publishes site/.
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from PIL import Image, ImageOps

ROOT = Path(__file__).parent
SOURCE_IMAGES = ROOT / "images" / "source"
FONTS = ROOT / "fonts"
SITE = ROOT / "site"
IMAGES_OUT = SITE / "img"

FEATURE_WIDTH = 1520  # main projects, shown at up to 760 px wide, twice that for sharp screens
THUMB_WIDTH = 720     # research figures
PHOTO_SIZE = 312      # shown at 104 px, three times that for sharp screens
OG_SIZE = 1200        # link preview image for LinkedIn and others
LOCAL_TZ = ZoneInfo("Europe/Copenhagen")

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#1B5E8C"/>
<text x="32" y="42" font-family="system-ui, sans-serif" font-size="26" font-weight="700"
 fill="#FFFFFF" text-anchor="middle">JK</text></svg>"""


def svg_size(path: Path) -> tuple[int, int]:
    """Width and height from the SVG's viewBox."""
    match = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', path.read_text())
    return (round(float(match.group(1))), round(float(match.group(2)))) if match else (1200, 675)


def prepare_image(name: str, width: int, out_name: str | None = None, square: bool = False,
                  fmt: str = "WEBP") -> dict:
    """Resize and compress one source image into site/img/. SVGs are copied unchanged."""
    source = SOURCE_IMAGES / name
    if source.suffix.lower() == ".svg":
        shutil.copy(source, IMAGES_OUT / source.name)
        w, h = svg_size(source)
        return {"src": f"img/{source.name}", "width": w, "height": h}

    image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    if square:
        image = ImageOps.fit(image, (width, width), Image.LANCZOS)
    elif image.width > width:
        image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)

    suffix = ".webp" if fmt == "WEBP" else ".jpg"
    target = IMAGES_OUT / (out_name or f"{source.stem}{suffix}")
    if fmt == "WEBP":
        image.save(target, "WEBP", quality=82, method=6)
    else:
        image.save(target, "JPEG", quality=85, optimize=True, progressive=True)
    return {"src": f"img/{target.name}", "width": image.width, "height": image.height}


def json_ld(c: dict, photo_url: str) -> str:
    """Structured data that tells search engines this page is a person's profile."""
    person = c["person"]
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": person["name"],
        "jobTitle": person["role"],
        "url": c["site"]["url"],
        "image": photo_url,
        "address": {"@type": "PostalAddress", "addressLocality": "Copenhagen", "addressCountry": "DK"},
        "sameAs": [l["url"] for l in person["links"] if l["url"].startswith("https://")],
        "knowsAbout": ["Machine learning", "MLOps", "AI agents", "Retrieval-augmented generation",
                       "Large language models", "Data science", "Time series forecasting",
                       "Deep learning", "Air quality modelling", "Environmental acoustics"],
    }
    return json.dumps(data, ensure_ascii=False)


def main() -> None:
    c = yaml.safe_load((ROOT / "content.yaml").read_text(encoding="utf-8"))

    if SITE.exists():
        shutil.rmtree(SITE)
    IMAGES_OUT.mkdir(parents=True)
    shutil.copytree(FONTS, SITE / "fonts")  # self-hosted font, no request to Google Fonts

    photo = prepare_image(c["person"]["photo"], PHOTO_SIZE, "photo.webp", square=True)
    og = prepare_image(c["person"]["photo"], OG_SIZE, "og.jpg", square=True, fmt="JPEG")

    images = {}
    for item in c["projects"]:
        images[item["image"]] = prepare_image(item["image"], FEATURE_WIDTH)
    for item in c["research"]:
        images[item["image"]] = prepare_image(item["image"], THUMB_WIDTH)

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
        undefined=StrictUndefined,  # a missing value stops the build instead of leaving a gap
        trim_blocks=True,
        lstrip_blocks=True,
    )
    now = datetime.now(LOCAL_TZ)
    html = env.get_template("index.html.j2").render(
        c=c, photo=photo, og=og, images=images, year=now.year,
        json_ld=json_ld(c, c["site"]["url"] + og["src"]),
    )
    (SITE / "index.html").write_text(html, encoding="utf-8")

    url = c["site"]["url"]
    (SITE / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {url}sitemap.xml\n")
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{url}</loc><lastmod>{now.date().isoformat()}</lastmod></url>\n"
        "</urlset>\n"
    )
    (SITE / ".nojekyll").write_text("")  # serve files as they are, without GitHub's Jekyll step

    total = sum(f.stat().st_size for f in SITE.rglob("*") if f.is_file())
    print(f"Built {SITE}/ ({total / 1024:.0f} KB in total)")
    for f in sorted(IMAGES_OUT.iterdir()):
        print(f"  img/{f.name:22} {f.stat().st_size / 1024:6.0f} KB")


if __name__ == "__main__":
    main()