from __future__ import annotations

from marketcore.presentation.dashboard.navigation import navigation_items


def render_shell(content: str, lang: str = "ru", timezone: str = "Europe/Moscow") -> str:
    nav = navigation_items()
    nav_html = "".join(
        f'<a class="nav-item" href="{item["path"]}">{item["key"].upper()}</a>'
        for item in nav
    )

    return f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Finam_Core Dashboard</title>
  <style>
    body {{ margin:0; font-family: Arial, sans-serif; background:#f6f7f9; color:#1f2937; }}
    header {{ height:56px; display:flex; align-items:center; justify-content:space-between; padding:0 16px; background:#111827; color:white; }}
    .app {{ display:flex; min-height:calc(100vh - 56px); }}
    nav {{ width:220px; background:#ffffff; border-right:1px solid #e5e7eb; padding:12px; }}
    .nav-item {{ display:block; padding:10px 12px; text-decoration:none; color:#111827; border-radius:8px; }}
    .nav-item:hover {{ background:#f3f4f6; }}
    main {{ flex:1; padding:20px; }}
    .card {{ background:white; border:1px solid #e5e7eb; border-radius:12px; padding:16px; margin-bottom:12px; }}
    footer {{ padding:12px 16px; background:#ffffff; border-top:1px solid #e5e7eb; }}
    .mobile-bottom {{ display:none; }}
    @media (max-width: 767px) {{
      .app {{ display:block; }}
      nav {{ display:none; }}
      main {{ padding:12px; padding-bottom:72px; }}
      .mobile-bottom {{ display:flex; position:fixed; bottom:0; left:0; right:0; height:56px; background:white; border-top:1px solid #e5e7eb; justify-content:space-around; align-items:center; }}
      .mobile-bottom a {{ color:#111827; text-decoration:none; font-size:12px; }}
    }}
  </style>
</head>
<body>
<header>
  <strong>Finam_Core Dashboard</strong>
  <div>{lang.upper()} | {timezone}</div>
</header>
<div class="app">
  <nav>{nav_html}</nav>
  <main>{content}</main>
</div>
<div class="mobile-bottom">
  <a href="/">HOME</a>
  <a href="/market">MARKET</a>
  <a href="/research">RESEARCH</a>
  <a href="/risk">RISK</a>
  <a href="/system">SYSTEM</a>
</div>
<footer>Dashboard Framework V1</footer>
</body>
</html>"""
