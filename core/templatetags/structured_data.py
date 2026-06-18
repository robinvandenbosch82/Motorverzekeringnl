"""
Structured-data for imported content pages (ContentPagina).

The contentfabriek import may or may not supply a hand-authored `schema_jsonld`.
This tag bridges the gap so EVERY content page ships a valid, @id-linked graph:

  * If `schema_jsonld` is present AND parses as JSON, it is trusted verbatim
    (admin/CSV is the source of truth) — but only after a validity gate so one
    malformed feed value can never break the page's structured data.
  * Otherwise we synthesise an Article (+ FAQPage when the page has FAQ HTML)
    from the model fields, wired into the site graph by @id reference.

Used by templates/pages/content_rich.html and content_pagina.html.
"""
import json
import re

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# <h3>question</h3> ... <p>answer</p>  (the cp-faq markup shape)
_FAQ_RE = re.compile(r"<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>", re.S | re.I)


def _text(html):
    return _WS_RE.sub(" ", _TAG_RE.sub("", html or "")).strip()


def _abs_image(pagina, origin):
    src = pagina.get_image_source()
    if not src:
        return ""
    if src.startswith(("http://", "https://")):
        return src
    media = settings.MEDIA_URL.strip("/")
    return f"{origin}/{media}/{src.lstrip('/')}"


def _faq_node(pagina, canonical):
    pairs = _FAQ_RE.findall(pagina.faq_html or "")
    questions = []
    for q, a in pairs:
        q, a = _text(q), _text(a)
        if q and a:
            questions.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            })
    if not questions:
        return None
    return {"@type": "FAQPage", "@id": f"{canonical}#faq", "mainEntity": questions}


def _article_node(pagina, origin, canonical):
    node = {
        "@type": "Article",
        "@id": f"{canonical}#article",
        "headline": pagina.titel,
        "inLanguage": "nl-NL",
        "mainEntityOfPage": {"@id": f"{canonical}#webpage"},
        "isPartOf": {"@id": f"{origin}/#website"},
        "publisher": {"@id": f"{origin}/#organization"},
        # Imported pages carry no per-article author; the brand is the author.
        "author": {"@id": f"{origin}/#organization"},
    }
    if pagina.meta_description:
        node["description"] = pagina.meta_description
    img = _abs_image(pagina, origin)
    if img:
        node["image"] = img
    # imported_at is auto_now → a reliable "last modified" signal.
    if getattr(pagina, "imported_at", None):
        node["dateModified"] = pagina.imported_at.date().isoformat()
    return node


@register.simple_tag
def content_structured_data(pagina):
    """Render the <script type=application/ld+json> for a ContentPagina."""
    origin = settings.SITE_ORIGIN
    canonical = origin + pagina.get_absolute_url()

    # 1) Trust a valid hand-authored graph verbatim.
    raw = (pagina.schema_jsonld or "").strip()
    if raw:
        try:
            json.loads(raw)
            return mark_safe(f'<script type="application/ld+json">{raw}</script>')
        except (ValueError, TypeError):
            pass  # malformed → fall through to the generated graph

    # 2) Synthesise Article (+ FAQ) from the model fields.
    graph = [_article_node(pagina, origin, canonical)]
    faq = _faq_node(pagina, canonical)
    if faq:
        graph.append(faq)

    payload = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         ensure_ascii=False)
    return mark_safe(f'<script type="application/ld+json">{payload}</script>')
