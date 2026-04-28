from pathlib import Path
import re
import html
from datetime import datetime


ROOT = Path(".")
CONTENT_DIR = ROOT / "content" / "insights"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "insights"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError("File must start with frontmatter.")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError("Frontmatter is not closed properly.")
    frontmatter_block = parts[1]
    body = parts[2].strip()

    data = {}
    for line in frontmatter_block.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"Invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()

    required = [
        "title",
        "slug",
        "description",
        "published",
        "updated",
        "author",
        "category",
        "summary",
    ]
    for key in required:
        if key not in data or not data[key]:
            raise ValueError(f"Missing frontmatter field: {key}")

    return data, body


def format_human_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.day} {dt.strftime('%B %Y')}"


def markdown_to_html(text: str) -> str:
    lines = text.splitlines()
    blocks = []
    paragraph_lines = []

    def flush_paragraph():
        nonlocal paragraph_lines
        if paragraph_lines:
            paragraph_text = " ".join(line.strip() for line in paragraph_lines).strip()
            if paragraph_text:
                blocks.append(f"<p>{html.escape(paragraph_text)}</p>")
            paragraph_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            blocks.append(f"<h3>{html.escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            flush_paragraph()
            blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            flush_paragraph()
            blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        else:
            paragraph_lines.append(stripped)

    flush_paragraph()
    return "\n".join(blocks)


def render_template(template: str, replacements: dict) -> str:
    output = template
    for key, value in replacements.items():
        output = output.replace(f"{{{{{key}}}}}", value)
    return output


def build_articles():
    article_template = read_text(TEMPLATES_DIR / "article.html")
    insights_template = read_text(TEMPLATES_DIR / "insights_index.html")

    article_summaries = []
    sitemap_urls = [
        "  <url>",
        "    <loc>https://sheafcoherence.com/</loc>",
        "  </url>",
        "  <url>",
        "    <loc>https://sheafcoherence.com/insights/</loc>",
        "  </url>",
    ]

    markdown_files = sorted(CONTENT_DIR.glob("*.md"), reverse=True)

    for md_file in markdown_files:
        raw = read_text(md_file)
        meta, body = parse_frontmatter(raw)

        content_html = markdown_to_html(body)
        published_human = format_human_date(meta["published"])
        updated_human = format_human_date(meta["updated"])

        article_html = render_template(
            article_template,
            {
                "TITLE": html.escape(meta["title"]),
                "DESCRIPTION": html.escape(meta["description"]),
                "SLUG": html.escape(meta["slug"]),
                "AUTHOR": html.escape(meta["author"]),
                "PUBLISHED": html.escape(meta["published"]),
                "UPDATED": html.escape(meta["updated"]),
                "PUBLISHED_HUMAN": html.escape(published_human),
                "UPDATED_HUMAN": html.escape(updated_human),
                "CATEGORY": html.escape(meta["category"]),
                "SUMMARY": html.escape(meta["summary"]),
                "CONTENT": content_html,
            },
        )

        article_path = OUTPUT_DIR / meta["slug"] / "index.html"
        write_text(article_path, article_html)

        article_summaries.append(
            "\n".join(
                [
                    '<article class="insight-item">',
                    f'  <p class="eyebrow"><time datetime="{html.escape(meta["published"])}">{html.escape(published_human)}</time></p>',
                    f'  <h2><a href="/insights/{html.escape(meta["slug"])}/">{html.escape(meta["title"])}</a></h2>',
                    f'  <p>{html.escape(meta["summary"])}</p>',
                    "</article>",
                ]
            )
        )

        sitemap_urls.extend(
            [
                "  <url>",
                f"    <loc>https://sheafcoherence.com/insights/{html.escape(meta['slug'])}/</loc>",
                f"    <lastmod>{html.escape(meta['updated'])}</lastmod>",
                "  </url>",
            ]
        )

    insights_html = render_template(
        insights_template,
        {"ARTICLES_LIST": "\n\n".join(article_summaries)},
    )
    write_text(OUTPUT_DIR / "index.html", insights_html)

    robots_txt = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            "User-agent: OAI-SearchBot",
            "Allow: /",
            "",
            "User-agent: GPTBot",
            "Allow: /",
            "",
            "Sitemap: https://sheafcoherence.com/sitemap.xml",
            "",
        ]
    )
    write_text(ROOT / "robots.txt", robots_txt)

    sitemap_xml = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *sitemap_urls,
            "</urlset>",
            "",
        ]
    )
    write_text(ROOT / "sitemap.xml", sitemap_xml)


if __name__ == "__main__":
    build_articles()
    print("Build complete.")

