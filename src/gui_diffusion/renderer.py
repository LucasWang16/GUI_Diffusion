from __future__ import annotations

from html import escape
from pathlib import Path

from .models import StateGraph


def render_html(graph: StateGraph, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    screens = {screen.id: screen for screen in graph.screens}
    screens_js = _screens_js(graph)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(graph.app_name)}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #e9edf2;
      color: #17202a;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, #e7edf3 0%, #f7f9fb 55%, #edf3eb 100%);
    }}
    #app {{
      position: relative;
      width: 390px;
      height: 720px;
      background: #fbfcfd;
      border: 1px solid #c8d0d8;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 18px 60px rgba(15, 23, 42, 0.16);
    }}
    .topbar {{
      height: 82px;
      padding: 24px;
      box-sizing: border-box;
      background: #263238;
      color: white;
    }}
    .screen-title {{
      font-size: 20px;
      font-weight: 700;
      line-height: 1.2;
    }}
    [data-gui-id] {{
      position: absolute;
      box-sizing: border-box;
      border-radius: 8px;
      font-size: 15px;
      letter-spacing: 0;
    }}
    button, .listitem {{
      border: 1px solid #8ca0a8;
      background: #ffffff;
      color: #1b2a32;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 650;
    }}
    button.primary {{
      background: #2f6f73;
      color: #ffffff;
      border-color: #2f6f73;
    }}
    input {{
      border: 1px solid #9aa9b4;
      background: #ffffff;
      padding: 0 14px;
      color: #17202a;
    }}
    .card, .status {{
      border: 1px solid #d2dbe2;
      background: #ffffff;
      padding: 16px;
      display: flex;
      align-items: center;
      line-height: 1.35;
    }}
    .heading {{
      font-size: 16px;
      font-weight: 750;
      display: flex;
      align-items: center;
      color: #263238;
    }}
    .status {{
      background: #eef7f1;
      border-color: #9fc8ad;
      color: #245033;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <main id="app" data-current-screen="{escape(graph.initial_screen)}"></main>
  <script>
    const SCREENS = {screens_js};
    let currentScreen = "{escape(graph.initial_screen)}";
    function render(screenId) {{
      currentScreen = screenId;
      const screen = SCREENS[screenId];
      const app = document.getElementById("app");
      app.dataset.currentScreen = screenId;
      app.innerHTML = `<div class="topbar"><div class="screen-title">${{screen.title}}</div></div>`;
      for (const component of screen.components) {{
        const [x1, y1, x2, y2] = component.bbox;
        let el;
        if (component.role === "textbox") {{
          el = document.createElement("input");
          el.placeholder = component.label;
          el.setAttribute("aria-label", component.label);
        }} else if (component.role === "button") {{
          el = document.createElement("button");
          el.textContent = component.label;
          if (component.id.startsWith("save") || component.id.startsWith("add") || component.id === "done") {{
            el.className = "primary";
          }}
        }} else {{
          el = document.createElement("div");
          el.className = component.role;
          el.textContent = component.label;
          if (component.role === "listitem") el.setAttribute("role", "button");
        }}
        el.dataset.guiId = component.id;
        el.dataset.role = component.role;
        if (component.target_screen) {{
          el.dataset.targetScreen = component.target_screen;
          el.addEventListener("click", () => render(component.target_screen));
        }}
        el.style.left = `${{x1}}px`;
        el.style.top = `${{y1}}px`;
        el.style.width = `${{x2 - x1}}px`;
        el.style.height = `${{y2 - y1}}px`;
        app.appendChild(el);
      }}
    }}
    window.__guiDiffusion = {{
      getCurrentScreen: () => currentScreen,
      getScreens: () => SCREENS,
      render
    }};
    render(currentScreen);
  </script>
</body>
</html>
"""
    if graph.initial_screen not in screens:
        raise ValueError(f"initial screen {graph.initial_screen!r} is not in graph")
    out_path.write_text(html, encoding="utf-8")


def _screens_js(graph: StateGraph) -> str:
    parts = []
    for screen in graph.screens:
        components = []
        for component in screen.components:
            target = "null" if component.target_screen is None else f'"{escape(component.target_screen)}"'
            components.append(
                "{"
                f'"id":"{escape(component.id)}",'
                f'"role":"{escape(component.role)}",'
                f'"label":"{escape(component.label)}",'
                f'"bbox":[{",".join(str(v) for v in component.bbox)}],'
                f'"target_screen":{target}'
                "}"
            )
        parts.append(
            "{"
            f'"id":"{escape(screen.id)}",'
            f'"title":"{escape(screen.title)}",'
            f'"purpose":"{escape(screen.purpose)}",'
            f'"components":[{",".join(components)}]'
            "}"
        )
    return "{" + ",".join(f'"{escape(screen.id)}":{part}' for screen, part in zip(graph.screens, parts)) + "}"
