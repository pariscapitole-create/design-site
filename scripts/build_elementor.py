"""Build an Elementor template (JSON) from index.html.

The page lives in one HTML widget; the WPForms form (id 1389) sits in a
shortcode widget and is moved into the callback card at load time.
"""
import json, re, secrets, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
UP = "https://preparation-toeic.net/wp-content/uploads"
ASSETS = {
    "assets/logo-toeic-first.png": f"{UP}/2026/10/logo-toeic-first-transparent.png",
    "assets/pastille-cpf.png": f"{UP}/2026/10/pastille-cpf.png",
    "assets/centres-poster.jpg": f"{UP}/2026/10/toeic-first-paris-centres-poster.jpg",
    "assets/centres.mp4": f"{UP}/2026/10/toeic-first-paris-centres.mp4",
    "assets/scores/1-1.webp": f"{UP}/2024/11/1-1.webp",
    "assets/scores/2-1.webp": f"{UP}/2024/11/2-1.webp",
    **{f"assets/scores/{n}.webp": f"{UP}/2024/11/{n}.webp" for n in range(3, 9)},
}
FORM_ID = 1389
SCOPE = ".tf-lp"

FORM_CSS = """
#rappel .tf-form-slot{min-height:120px}
/* Paris is preselected and the message is optional: keep the hero card short */
#rappel #wpforms-1389-field_5-container,#rappel #wpforms-1389-field_9-container{display:none!important}
#rappel div.wpforms-container-full .wpforms-form button[type=submit]{text-transform:none!important;letter-spacing:0!important}
th,td,small,label,button{text-transform:none;letter-spacing:normal}
.skip{position:fixed!important;top:12px!important;transform:translateY(-200%);transition:transform .2s}
.skip:focus{transform:none}
/* The real form is taller than ours: tighten the hero so the offer strip still shows */
@media (min-width:961px){.hero-grid{padding-top:28px!important;padding-bottom:28px!important}.hero h1{margin-bottom:16px!important}}
#rappel .tf-form-fallback{color:var(--ink-soft);font-size:.95rem}
#rappel div.wpforms-container-full{margin:0!important;
  --wpforms-field-border-radius:10px;--wpforms-field-border-color:var(--navy-200);--wpforms-field-text-color:var(--ink);
  --wpforms-label-color:var(--ink);--wpforms-button-background-color:var(--orange-ink);--wpforms-button-border-radius:999px;
  --wpforms-field-size-input-height:46px;--wpforms-field-size-font-size:16px;--wpforms-label-size-font-size:14px;--wpforms-button-size-height:54px}
#rappel div.wpforms-container-full .wpforms-form .wpforms-field-container{display:grid;grid-template-columns:1fr 1fr;gap:0 12px}
#rappel div.wpforms-container-full .wpforms-form .wpforms-field{padding:0!important;margin:0 0 12px!important;grid-column:span 2}
#rappel div.wpforms-container-full .wpforms-form .wpforms-field-select,
#rappel div.wpforms-container-full .wpforms-form .wpforms-field-email,
#rappel div.wpforms-container-full .wpforms-form .wpforms-field-phone{grid-column:span 1}
#rappel div.wpforms-container-full .wpforms-form .wpforms-field-label{font:600 .88rem/1.3 var(--f-body)!important;color:var(--ink)!important;margin:0 0 5px!important}
#rappel div.wpforms-container-full .wpforms-form .wpforms-field-sublabel{font-size:.8rem!important;color:var(--ink-soft)!important}
#rappel div.wpforms-container-full .wpforms-form input:not([type=hidden]):not([type=checkbox]):not([type=radio]),
#rappel div.wpforms-container-full .wpforms-form select,
#rappel div.wpforms-container-full .wpforms-form textarea{width:100%!important;max-width:100%!important;height:46px;padding:0 14px!important;border:1.5px solid var(--navy-200)!important;border-radius:10px!important;background-color:#fff!important;font:400 1rem var(--f-body)!important;color:var(--ink)!important;box-shadow:none!important}
#rappel div.wpforms-container-full .wpforms-form input:focus,
#rappel div.wpforms-container-full .wpforms-form select:focus{border-color:var(--navy-900)!important;box-shadow:0 0 0 4px rgba(19,40,69,.12)!important;outline:none!important}
#rappel div.wpforms-container-full .wpforms-form .wpforms-field-row{max-width:none!important}
#rappel div.wpforms-container-full .wpforms-form .wpforms-error{color:#b42318!important;font-size:.85rem!important}
#rappel div.wpforms-container-full .wpforms-form .wpforms-submit-container{padding:4px 0 0!important;margin:0!important}
#rappel div.wpforms-container-full .wpforms-form button[type=submit]{width:100%!important;height:54px!important;border:0!important;border-radius:999px!important;background:var(--orange-ink)!important;color:#fff!important;font:600 1.05rem var(--f-body)!important;cursor:pointer;transition:background .2s}
#rappel div.wpforms-container-full .wpforms-form button[type=submit]:hover{background:var(--orange-ink-hover)!important}
@media (max-width:520px){#rappel div.wpforms-container-full .wpforms-form .wpforms-field{grid-column:span 2!important}}
"""


def scope_selector(sel):
    sel = sel.strip()
    if sel in (":root", "body"):
        return SCOPE
    if sel.startswith("html"):
        return sel
    if sel.startswith(".js "):
        return f".js {SCOPE} " + sel[4:]
    return f"{SCOPE} {sel}"


def scope_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j == -1:
            out.append(css[i:]); break
        head = css[i:j].strip()
        # find matching brace
        depth, k = 1, j + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0); k += 1
        body = css[j + 1:k - 1]
        if head.startswith("@media") or head.startswith("@supports"):
            out.append(f"{head}{{{scope_css(body)}}}")
        elif head.startswith("@"):
            out.append(f"{head}{{{body}}}")
        else:
            out.append(",".join(scope_selector(s) for s in head.split(",")) + f"{{{body}}}")
        i = k
    return "\n".join(out)


def eid():
    return secrets.token_hex(4)[:7]


def main():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    for local, url in ASSETS.items():
        html = html.replace(local, url)

    css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    fonts = "\n".join(re.findall(r'<link[^>]+(?:fonts\.googleapis|fonts\.gstatic)[^>]*>', html))
    body = re.search(r"<body>(.*?)</body>", html, re.S).group(1)

    # Callback card: keep heading and note, swap our form for a slot that receives WPForms
    form = re.search(r'<!-- À brancher.*?-->\s*<form class="callback".*?</form>', body, re.S).group(0)
    h2 = re.search(r'<h2 id="rappel-title">.*?</h2>', form).group(0)
    sub = re.search(r'<p class="sub">.*?</p>', form).group(0)
    card = (f'<div class="callback" id="rappel" role="region" aria-labelledby="rappel-title">\n      {h2}\n      {sub}\n'
            f'      <div class="tf-form-slot" id="tf-form-slot"><p class="tf-form-fallback">Le formulaire se charge… '
            f'Vous pouvez aussi <a href="https://preparation-toeic.net/contact/#wpforms-form-{FORM_ID}">nous écrire depuis la page contact</a>.</p></div>\n'
            f'    </div>')
    body = body.replace(form, card)

    # Script: drop our form validation, guard the formula preselect, move WPForms into the card
    body = body.replace("  document.documentElement.classList.add('js');\n", "")
    body = re.sub(r"\n  // Callback form validation.*?\n  \}\);\n", "\n", body, flags=re.S)
    body = body.replace("    document.getElementById('f-formule').value = a.dataset.formule;\n", "")
    body = body.replace("document.getElementById('f-name').focus({preventScroll:true})",
                        "(document.querySelector('#rappel input:not([type=hidden])') || {focus(){}}).focus({preventScroll:true})")
    # The HTML widget renders before the shortcode widget, so wait for the DOM
    body = body.replace("(() => {\n", "document.addEventListener('DOMContentLoaded', () => {\n  const src = document.getElementById('tf-wpforms-src');\n"
                        "  const wpf = src && src.querySelector('.wpforms-container');\n"
                        "  if (wpf) { document.getElementById('tf-form-slot').replaceChildren(wpf); src.hidden = true;\n"
                        "    const sb = wpf.querySelector('button[type=submit]');\n"
                        "    if (sb) { sb.textContent = 'Être rappelé'; sb.dataset.submitText = 'Être rappelé'; } }\n", 1)
    body = body.replace("})();\n</script>", "});\n</script>")
    assert "f-name" not in body.split("<script>")[-1].replace("f-name-err", ""), "stale form reference"

    page = (f"<script>document.documentElement.classList.add('js')</script>\n{fonts}\n"
            f"<style>\n{scope_css(css)}\n{scope_css(FORM_CSS)}\n"
            f".elementor-widget-html:has(.tf-lp){{margin:0!important}}\n"
            # OceanWP sets html{font-size:62.5%} and colours every heading: undo both on this page
            f"html{{font-size:16px!important}}\n"
            f"{SCOPE} h1,{SCOPE} h2,{SCOPE} h3,{SCOPE} h4{{color:inherit}}\n</style>\n"
            f'<div class="tf-lp">\n{body.strip()}\n</div>')

    zero = {"unit": "px", "top": "0", "right": "0", "bottom": "0", "left": "0", "isLinked": True}
    widget_common = {"_margin": zero, "_padding": zero}
    tpl = {
        "version": "0.4",
        "title": "TOEIC First Paris - landing",
        "type": "page",
        "page_settings": {"template": "elementor_canvas", "hide_title": "yes"},
        "content": [{
            "id": eid(), "elType": "container", "isInner": False,
            "settings": {"content_width": "full", "flex_gap": {"unit": "px", "size": 0, "column": "0", "row": "0"},
                         "padding": zero, "margin": zero},
            "elements": [
                {"id": eid(), "elType": "widget", "widgetType": "html", "elements": [],
                 "settings": {"html": page, **widget_common}},
                {"id": eid(), "elType": "widget", "widgetType": "shortcode", "elements": [],
                 "settings": {"shortcode": f'[wpforms id="{FORM_ID}"]', "_element_id": "tf-wpforms-src", **widget_common}},
            ],
        }],
    }
    out = ROOT / "elementor" / "toeic-first-paris.json"
    out.write_text(json.dumps(tpl, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "elementor" / "preview-widget.html").write_text(page, encoding="utf-8")
    print(out, len(page))


if __name__ == "__main__":
    sys.exit(main())
