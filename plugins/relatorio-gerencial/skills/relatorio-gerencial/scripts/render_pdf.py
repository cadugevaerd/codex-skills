#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = SCRIPT_DIR.parent / "assets" / "report-template.html"


def badge_class(urgency: str) -> str:
    return {
        "critica": "danger",
        "alta": "danger",
        "media": "warn",
        "baixa": "calm",
    }.get(urgency, "warn")


def render_html(data: dict[str, Any], template_path: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    groups = data.get("groups", [])[:5]
    current_tasks = data.get("current_tasks", [])[:4]
    stats = data.get("stats", {})

    current_html = "".join(f"<li>{html.escape(str(task))}</li>" for task in current_tasks) or "<li>Sem tarefas atuais informadas.</li>"
    groups_html = []
    for group in groups:
        repos = ", ".join(group.get("repos", [])[:3]) or "portfolio"
        examples = "".join(f"<li>{html.escape(str(example))}</li>" for example in group.get("examples", [])[:2])
        groups_html.append(
            f"""
            <article class="initiative">
              <div class="initiative-head">
                <span class="emoji">{html.escape(str(group.get('emoji', '📌')))}</span>
                <h3>{html.escape(str(group.get('title', 'Iniciativa')))}</h3>
                <span class="badge {badge_class(str(group.get('urgency', 'media')))}">{html.escape(str(group.get('urgency', 'media')).upper())}</span>
              </div>
              <p>{html.escape(str(group.get('summary', '')))}</p>
              <div class="meta">Repos: {html.escape(repos)} · {int(group.get('microtasks_count', 0))} itens agrupados</div>
              <ul class="examples">{examples}</ul>
              <div class="next">Proxima acao: {html.escape(str(group.get('next_action', 'Definir prioridade.')))}</div>
            </article>
            """
        )

    return (
        template.replace("{{DATE}}", html.escape(str(data.get("date", ""))))
        .replace("{{TITLE}}", html.escape(str(data.get("title", "Relatorio gerencial"))))
        .replace("{{CURRENT_TASKS}}", current_html)
        .replace("{{GROUPS}}", "\n".join(groups_html))
        .replace("{{MANUAL_COUNT}}", str(stats.get("manual_tasks", 0)))
        .replace("{{BACKLOG_COUNT}}", str(stats.get("backlog_items", 0)))
        .replace("{{REPO_COUNT}}", str(len(stats.get("repos", []))))
    )


def render_with_playwright(html_path: Path, pdf_path: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        return False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 1754}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.pdf(path=str(pdf_path), format="A4", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        browser.close()
    return True


def render_with_weasyprint(html_path: Path, pdf_path: Path) -> bool:
    try:
        from weasyprint import HTML  # type: ignore
    except Exception:
        return False
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    return True


def render_with_chromium(html_path: Path, pdf_path: Path) -> bool:
    browser = next((cmd for cmd in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable") if shutil.which(cmd)), None)
    if not browser:
        return False
    subprocess.run(
        [browser, "--headless", "--disable-gpu", "--no-sandbox", f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def font_path() -> str | None:
    try:
        completed = subprocess.run(
            ["fc-match", "-f", "%{file}", "DejaVu Sans"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return completed.stdout.strip() or None
    except Exception:
        return None


def draw_wrapped(draw: Any, xy: tuple[int, int], text: str, font: Any, fill: str, width: int, line_height: int, max_lines: int | None = None) -> int:
    chars = max(18, width // max(7, int(font.size * 0.48)))
    lines: list[str] = []
    for paragraph in str(text).splitlines() or [""]:
        lines.extend(textwrap.wrap(paragraph, width=chars) or [""])
    if max_lines is not None:
        lines = lines[:max_lines]
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def render_with_pillow(data: dict[str, Any], pdf_path: Path) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return False

    scale = 2
    width, height = 1240, 1754
    image = Image.new("RGB", (width, height), "#f7fafc")
    draw = ImageDraw.Draw(image)

    fp = font_path()
    font = lambda size: ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
    title_font = font(42)
    h2_font = font(24)
    h3_font = font(20)
    body_font = font(17)
    small_font = font(14)
    tiny_font = font(12)

    # Soft executive background.
    for y in range(height):
        ratio = y / height
        r = int(250 - 10 * ratio)
        g = int(252 - 9 * ratio)
        b = int(255 - 24 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    margin = 86
    draw.rounded_rectangle((margin, 70, width - margin, 185), radius=18, fill="#ffffff", outline="#d8e0ea", width=2)
    draw.text((margin + 28, 92), str(data.get("title", "Relatorio gerencial")), font=title_font, fill="#172033")
    draw.text((width - margin - 210, 98), f"📅 {data.get('date', '')}", font=body_font, fill="#536173")
    draw.text((margin + 28, 147), "Resumo executivo para acompanhamento de prioridade, risco e proxima acao.", font=body_font, fill="#536173")

    stats = data.get("stats", {})
    metrics = [
        ("🎯", stats.get("manual_tasks", 0), "tarefas atuais"),
        ("📌", stats.get("backlog_items", 0), "itens em backlog"),
        ("🗂", len(stats.get("repos", [])), "repositorios"),
    ]
    card_w = (width - 2 * margin - 24) // 3
    for i, (emoji, value, label) in enumerate(metrics):
        x = margin + i * (card_w + 12)
        draw.rounded_rectangle((x, 210, x + card_w, 306), radius=16, fill="#ffffff", outline="#d8e0ea", width=2)
        draw.text((x + 22, 232), f"{emoji} {value}", font=h2_font, fill="#172033")
        draw.text((x + 22, 270), str(label).upper(), font=tiny_font, fill="#536173")

    left_x, left_y, left_w = margin, 335, 390
    right_x, right_y, right_w = margin + left_w + 24, 335, width - 2 * margin - left_w - 24
    draw.rounded_rectangle((left_x, left_y, left_x + left_w, 1020), radius=16, fill="#ffffff", outline="#d8e0ea", width=2)
    draw.text((left_x + 22, left_y + 22), "🎯 Foco Atual", font=h2_font, fill="#172033")
    y = left_y + 66
    current_tasks = data.get("current_tasks", [])[:5] or ["Sem tarefas atuais informadas."]
    for task in current_tasks:
        y = draw_wrapped(draw, (left_x + 28, y), f"• {task}", body_font, "#253047", left_w - 56, 25, max_lines=3) + 8

    draw.rounded_rectangle((left_x, 1044, left_x + left_w, 1455), radius=16, fill="#ffffff", outline="#d8e0ea", width=2)
    draw.text((left_x + 22, 1066), "⚠️ Riscos", font=h2_font, fill="#172033")
    risk = "Itens de alta urgencia podem afetar prazo, confiabilidade ou previsibilidade se ficarem sem decisao."
    y = draw_wrapped(draw, (left_x + 24, 1110), risk, body_font, "#253047", left_w - 48, 25, max_lines=5)
    draw.text((left_x + 22, y + 28), "✅ Decisoes", font=h2_font, fill="#172033")
    draw_wrapped(draw, (left_x + 24, y + 72), "Confirmar prioridade dos blocos marcados como ALTA/CRITICA na proxima conversa.", body_font, "#253047", left_w - 48, 25, max_lines=5)

    draw.rounded_rectangle((right_x, right_y, right_x + right_w, 1455), radius=16, fill="#ffffff", outline="#d8e0ea", width=2)
    draw.text((right_x + 22, right_y + 22), "🚧 Proximos Blocos de Trabalho", font=h2_font, fill="#172033")
    y = right_y + 68
    colors = {"critica": "#b42318", "alta": "#c2412d", "media": "#b7791f", "baixa": "#2f7d64"}
    for group in data.get("groups", [])[:5]:
        if y > 1360:
            break
        urgency = str(group.get("urgency", "media")).lower()
        draw.rounded_rectangle((right_x + 20, y, right_x + right_w - 20, y + 166), radius=14, fill="#f8fafc", outline="#e2e8f0", width=1)
        draw.text((right_x + 38, y + 18), f"{group.get('emoji', '📌')} {group.get('title', 'Iniciativa')}", font=h3_font, fill="#172033")
        badge = urgency.upper()
        badge_w = 16 + len(badge) * 9
        draw.rounded_rectangle((right_x + right_w - 42 - badge_w, y + 16, right_x + right_w - 34, y + 42), radius=13, fill=colors.get(urgency, "#b7791f"))
        draw.text((right_x + right_w - 34 - badge_w, y + 21), badge, font=tiny_font, fill="#ffffff")
        draw_wrapped(draw, (right_x + 42, y + 54), str(group.get("summary", "")), body_font, "#253047", right_w - 84, 23, max_lines=2)
        repos = ", ".join(group.get("repos", [])[:3]) or "portfolio"
        draw.text((right_x + 42, y + 104), f"Repos: {repos} · {group.get('microtasks_count', 0)} itens agrupados", font=small_font, fill="#536173")
        draw_wrapped(draw, (right_x + 42, y + 126), f"Proxima acao: {group.get('next_action', 'Definir prioridade.')}", small_font, "#253047", right_w - 84, 20, max_lines=2)
        y += 178

    draw.text((margin, 1508), "📌 Este report agrupa microtarefas por resultado esperado, nao por detalhe tecnico.", font=body_font, fill="#39475a")

    image = image.resize((width // scale, height // scale))
    image.save(pdf_path, "PDF", resolution=150.0)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Renderiza relatorio gerencial HTML/PDF de uma pagina")
    parser.add_argument("--input", required=True, help="JSON gerado por agrupar_tasks.py")
    parser.add_argument("--out", required=True, help="Caminho do PDF final")
    parser.add_argument("--html-out", help="Opcional: salvar HTML intermediario")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    args = parser.parse_args()

    data = json.loads(Path(args.input).expanduser().read_text(encoding="utf-8"))
    html_text = render_html(data, Path(args.template).expanduser())
    pdf_path = Path(args.out).expanduser()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as tmp:
        html_path = Path(args.html_out).expanduser() if args.html_out else Path(tmp) / "relatorio-gerencial.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_text, encoding="utf-8")
        rendered = (
            render_with_playwright(html_path, pdf_path)
            or render_with_weasyprint(html_path, pdf_path)
            or render_with_chromium(html_path, pdf_path)
            or render_with_pillow(data, pdf_path)
        )
        if not rendered:
            fallback = pdf_path.with_suffix(".html")
            fallback.write_text(html_text, encoding="utf-8")
            raise SystemExit(
                "Nao encontrei Playwright, WeasyPrint ou Chromium para gerar PDF. "
                f"HTML salvo em {fallback}. Instale um renderizador e rode novamente."
            )
    print(f"PDF gerado: {pdf_path}")


if __name__ == "__main__":
    main()
