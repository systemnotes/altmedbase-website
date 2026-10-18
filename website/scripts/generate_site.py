#!/usr/bin/env python3
"""
Static site generator for the Natural Remedies Directory.
Reads JSON files from data/canonical/json/ and outputs HTML files to dist/.
"""

import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import shutil

BASE_DIR = Path(__file__).parent.parent
CANONICAL_JSON_DIR = BASE_DIR.parent.parent / "altmedbase" / "data" / "canonical" / "json"
TEMPLATES_DIR = BASE_DIR / "templates"
DIST_DIR = BASE_DIR / "dist"
CSS_DIR = DIST_DIR / "css"
CONFIG_FILE = BASE_DIR / "site_config.json"

env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

# Collection type to singular page prefix used in filenames.
COLLECTION_TO_PREFIX = {
    "remedies": "remedy",
    "ailments": "ailment",
    "protocols": "protocol",
    "therapies": "therapy",
    "practitioners": "practitioner",
    "products": "product",
    "education": "education",
    "suppliers": "supplier",
    "testimonials": "testimonial",
    "references": "reference",
}

# Reverse: singular prefix -> plural collection name
PREFIX_TO_COLLECTION = {v: k for k, v in COLLECTION_TO_PREFIX.items()}


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_data():
    """Load all JSON data files from canonical store."""
    data = {}
    for file in CANONICAL_JSON_DIR.glob("*.json"):
        with open(file) as f:
            data[file.stem] = json.load(f)
    return data


def render_page(template_name, output_name, context):
    print(f"DEBUG: render_page called with output_name={output_name!r}")
    template = env.get_template(template_name)
    html = template.render(**context)
    output_path = DIST_DIR / output_name
    print(f"DEBUG: output_path={output_path!r}, exists={output_path.exists()}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Generated: {output_path}")


def get_prefix_for_item(item_id: str) -> str:
    """Get the singular prefix for an item ID like 'remedy_001'."""
    parts = item_id.split("_")
    return parts[0] if parts else ""


def get_url_for_item(item_id: str) -> str:
    """Get the HTML filename for an item ID like 'remedy_001'."""
    return f"{item_id}.html"


def resolve_id(item, field, lookup, collection_prefix):
    """Resolve a list of related IDs into (id, title, summary) tuples."""
    result = []
    for ref_id in item.get(field, []):
        ref = lookup.get(ref_id)
        if ref:
            title = ref.get("title", "")
            summary = ref.get("summary", "")
            result.append((ref_id, title, summary))
    return result


def build_reverse_relationships(item, data):
    """Find every item across all collections that references this one."""
    reverse = {}
    for coll_name, coll_items in data.items():
        for ref_item in coll_items:
            for related_field in ["related_remedies", "related_ailments",
                                   "related_protocols", "related_therapies",
                                   "related_practitioners", "related_products",
                                   "related_educations", "related_suppliers",
                                   "related_testimonials", "protocols",
                                   "common_treatments", "products_supplied"]:
                if item["id"] in ref_item.get(related_field, []):
                    reverse.setdefault(related_field, []).append(
                        (ref_item["id"], ref_item.get("title", ""), ref_item.get("summary", ""))
                    )
    return reverse


def build_index(config, data):
    """Build the home page."""
    # data is already a dict of collections: {collection_name: [items, ...]}
    # The template accesses data.ailments, data.remedies etc., so we need to
    # make sure these are accessible. data already has this structure.
    stats = {k: len(v) for k, v in data.items()}
    # Build lookup dict that templates expect
    lookup = {}
    for coll_name, items in data.items():
        for item in items:
            lookup[item["id"]] = item
    # Convert data dict to object-like structure for template access
    class DataAccessor:
        def __init__(self, data_dict):
            # Store the dict and create attributes for each collection
            self._data = data_dict
            # Set attributes for each collection that exists in the data
            for key in data_dict:
                # Store as both attribute and accessible via getattr
                setattr(self, key, data_dict[key])
        
        def items(self):
            return self._data.items()
    
    data_accessor = DataAccessor(data)
    render_page("index.html", "index.html", {
        "config": config,
        "title": "Home",
        "data": data_accessor,
        "stats": stats,
        "collection_prefixes": COLLECTION_TO_PREFIX,
        "PREFIX_TO_COLLECTION": PREFIX_TO_COLLECTION,
        "get_url_for_item": get_url_for_item,
        "lookup": lookup,
    })


def build_collection_page(config, data, collection_name, filename):
    """Build a collection listing page."""
    items = sorted(data.get(collection_name, []), key=lambda x: x.get("title", "").lower())
    prefix = COLLECTION_TO_PREFIX.get(collection_name, collection_name)
    render_page("collection.html", filename, {
        "config": config,
        "title": collection_name.capitalize(),
        "collection": collection_name,
        "collection_prefix": prefix,
        "items": items,
        "data": data,
        "collection_prefixes": COLLECTION_TO_PREFIX,
        "PREFIX_TO_COLLECTION": PREFIX_TO_COLLECTION,
        "get_url_for_item": get_url_for_item,
    })


def build_item_page(config, data, item, collection_name, template_name, output_name=None):
    """Build an individual item page (remedy, ailment, protocol, etc.)."""
    if not output_name:
        # Determine the subdirectory based on collection name
        # Use plural collection name for directory (e.g., "ailments", "remedies")
        output_name = f"{collection_name}/{item['id']}.html"

    # Build lookup dict for cross-referencing (ID -> item).
    lookup = {}
    for coll_name, coll_items in data.items():
        for coll_item in coll_items:
            lookup[coll_item["id"]] = coll_item

    # Pre-compute forward cross-references with URLs
    related_with_info = {}

    # Maps from item fields to collection types
    field_to_collection = {
        "related_remedies": "remedies",
        "related_ailments": "ailments",
        "related_protocols": "protocols",
        "related_therapies": "therapies",
        "related_practitioners": "practitioners",
        "related_products": "products",
        "related_educations": "education",
        "related_suppliers": "suppliers",
        "related_testimonials": "testimonials",
        "protocols": "protocols",
        "common_treatments": "remedies",
        "products_supplied": "products",
    }

    for field, coll in field_to_collection.items():
        info = resolve_id(item, field, lookup, COLLECTION_TO_PREFIX.get(collection_name, ""))
        if info:
            related_with_info[field] = info

    # Get reverse relationships with collections
    reverse = build_reverse_relationships(item, data)

    render_page(template_name, output_name, {
        "config": config,
        "title": item["title"],
        "item": item,
        "collection": collection_name,
        "data": data,
        "lookup": lookup,
        "related_with_info": related_with_info,
        "reverse_relationships": reverse,
        "collection_prefixes": COLLECTION_TO_PREFIX,
        "PREFIX_TO_COLLECTION": PREFIX_TO_COLLECTION,
        "get_url_for_item": get_url_for_item,
    })


def build_remedy_pages(config, data):
    """Generate individual remedy pages."""
    for remedy in data.get("remedies", []):
        build_item_page(config, data, remedy, "remedies", "remedy.html")


def build_ailment_pages(config, data):
    """Generate individual ailment pages."""
    for ailment in data.get("ailments", []):
        build_item_page(config, data, ailment, "ailments", "ailment.html")


def build_protocol_pages(config, data):
    """Generate individual protocol pages."""
    for proto in data.get("protocols", []):
        build_item_page(config, data, proto, "protocols", "protocol.html")


def build_therapy_pages(config, data):
    """Generate individual therapy pages."""
    for therapy in data.get("therapies", []):
        build_item_page(config, data, therapy, "therapies", "therapy.html")


def build_practitioner_pages(config, data):
    """Generate individual practitioner pages."""
    for prac in data.get("practitioners", []):
        build_item_page(config, data, prac, "practitioners", "practitioner.html")


def build_product_pages(config, data):
    """Generate individual product pages."""
    for prod in data.get("products", []):
        build_item_page(config, data, prod, "products", "product.html")


def build_supplier_pages(config, data):
    """Generate individual supplier pages."""
    for sup in data.get("suppliers", []):
        build_item_page(config, data, sup, "suppliers", "supplier.html")


def build_testimonial_pages(config, data):
    """Generate individual testimonial pages."""
    for test in data.get("testimonials", []):
        build_item_page(config, data, test, "testimonials", "testimonial.html")


def build_reference_pages(config, data):
    """Generate individual reference pages."""
    for ref in data.get("references", []):
        build_item_page(config, data, ref, "references", "reference.html")


def build_education_pages(config, data):
    """Generate individual education pages."""
    for edu in data.get("education", []):
        build_item_page(config, data, edu, "education", "education.html")


def build_lunr_index(data):
    """Build Lunr.js search index for frontend."""
    all_items = []
    for collection_name, items in data.items():
        for item in items:
            item_with_type = dict(item)
            item_with_type["collection"] = collection_name
            all_items.append(item_with_type)

    search_docs = []
    for item in all_items:
        evidence = item.get("evidence", {})
        evidence_grade = evidence.get("grade", "") if evidence else ""
        evidence_source = evidence.get("source", "") if evidence else ""

        # Get the singular prefix for URL generation
        item_id = item.get("id", "")
        singular_prefix = get_prefix_for_item(item_id)
        page_url = f"{item_id}.html"

        doc = {
            "id": item_id,
            "title": item.get("title", ""),
            "category": item.get("category", ""),
            "collection": item.get("collection", ""),
            "page_url": page_url,
            "summary": item.get("summary", ""),
            "tags": " ".join(item.get("tags", [])),
            "indications": " ".join(item.get("indications", [])),
            "contraindications": " ".join(item.get("contraindications", [])),
            "preparations": " ".join(item.get("preparations", [])),
            "body_systems": " ".join(item.get("body_systems_affected", item.get("body_systems", []))),
            "evidence_type": item.get("evidence_type", ""),
            "evidence_grade": evidence_grade,
            "evidence_source": evidence_source,
            "botanical_name": item.get("botanical_name", ""),
            "family": item.get("family", ""),
            "common_names": " ".join(item.get("common_names", [])),
            "parts_used": " ".join(item.get("parts_used", [])),
            "safety_profile": json.dumps(item.get("safety_profile", {})),
            "tcm_properties": json.dumps(item.get("tcm_properties", {})),
            "ayurvedic_energetics": json.dumps(item.get("ayurvedic_energetics", {})),
            "constituents": json.dumps([str(c) for c in item.get("constituents", [])]),
            "related_remedies": " ".join(item.get("related_remedies", [])),
            "related_ailments": " ".join(item.get("related_ailments", [])),
        }
        search_docs.append(doc)

    # Also add evidence field as object for better search
    for doc in search_docs:
        doc["evidence"] = item.get("evidence", {})

    output_path = DIST_DIR / "search_index.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(search_docs, f, indent=2)
    print(f"Generated: {output_path}")


def copy_assets():
    """Copy CSS and other assets to dist."""
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    src_css = TEMPLATES_DIR / "css" / "style.css"
    dst_css = CSS_DIR / "style.css"
    if src_css.exists():
        shutil.copy(src_css, dst_css)
        print(f"Copied: {dst_css}")
    else:
        # Fallback: write embedded CSS if source file doesn't exist
        dst_css.write_text(EMBEDDED_CSS)
        print(f"Generated embedded CSS: {dst_css}")


EMBEDDED_CSS = """
/* Fallback CSS - templates/css/style.css should be used instead */
body { font-family: sans-serif; margin: 0; padding: 0; line-height: 1.6; }
header nav { background: #333; padding: 1rem; }
header .logo { color: #fff; font-weight: bold; text-decoration: none; }
main { padding: 2rem; max-width: 800px; margin: auto; }
footer { text-align: center; padding: 1rem; background: #eee; }
.tags { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0; }
.tag { background: #e0e0e0; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.85rem; }
"""


def main():
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    CSS_DIR.mkdir(parents=True, exist_ok=True)

    # Copy base.html if it exists in templates
    src_base = TEMPLATES_DIR / "base.html"
    dst_base = DIST_DIR / "base.html"
    if src_base.exists():
        shutil.copy(src_base, dst_base)
        print(f"Copied: {dst_base}")

    config = load_config()
    data = load_data()

    # Build the home page
    build_index(config, data)

    # Build About page
    render_page("about.html", "about.html", {
        "config": config,
        "title": "About",
        "data": data,
        "stats": {k: len(v) for k, v in data.items()},
        "collection_prefixes": COLLECTION_TO_PREFIX,
        "get_url_for_item": get_url_for_item,
    })

    # Dynamically discover all collections
    collections = {}
    for collection_name, items in data.items():
        collections[collection_name] = items

    # Build dynamic collection listing pages
    for collection_name, items in collections.items():
        filename = f"{collection_name}.html"
        build_collection_page(config, data, collection_name, filename)

    # Map collection names to their templates
    TEMPLATE_MAP = {
        "remedies": "remedy.html",
        "ailments": "ailment.html",
        "protocols": "protocol.html",
        "therapies": "therapy.html",
        "testimonials": "testimonial.html",
        "references": "reference.html",
        "suppliers": "supplier.html",
        "products": "product.html",
        "education": "education.html",
        "practitioners": "practitioner.html",
    }

    # Build individual item pages for each collection
    for collection_name, items in collections.items():
        template_name = TEMPLATE_MAP.get(collection_name, "generic.html")
        for item in items:
            output_name = f"{item['id']}.html"
            build_item_page(config, data, item, collection_name, template_name, output_name)

    # Build search index
    build_lunr_index(data)

    # Copy assets last
    copy_assets()

    print("Site generation complete.")


if __name__ == "__main__":
    main()