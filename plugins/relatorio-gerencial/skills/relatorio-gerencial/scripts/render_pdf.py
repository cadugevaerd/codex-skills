#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = SCRIPT_DIR / "assets" / "report-template.html"


def badge_class(urgency: str) -> str:
    return {
        "critica": "danger",
        "alta": "danger",
        "media": "warn",
        "baixa": "calm",
    }.get(urgency, "warn")


def item_meta(item: dict[str, Any]) -> str:
    parts: list[str] = [
        f"Status: {item.get('status', 'aberto')}",
        f"Prioridade: {str(item.get('priority', 'media')).upper()}",
        f"Tipo: {item.get('type', 'item')}",
    ]
    if item.get("agent"):
        parts.append(f"Agente: {item.get('agent')}")
    if item.get("repo"):
        parts.append(f"Escopo: {item.get('repo')}")
    return " · ".join(parts)


def render_html(data: dict[str, Any], template_path: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    groups = data.get("groups", [])[:5]
    current_tasks = data.get("current_tasks", [])[:4]
    stats = data.get("stats", {})

    current_html = "".join(f"<li>{html.escape(str(task))}</li>" for task in current_tasks) or "<li>Sem tarefas atuais informadas.</li>"

    groups_html = []
    details_html = []
    for group in groups:
        repos = ", ".join(group.get("repos", [])[:3]) or "portfolio"
        examples = "".join(f"<li>{html.escape(str(example))}</li>" for example in group.get("examples", [])[:2])
        if not examples:
            examples = "<li>Sem resumo executivo rápido disponível.</li>"

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

        items = group.get("detailed_items", []) or []
        item_rows = []
        for item in items:
            item_rows.append(
                f"""
                <article class="detail-item">
                  <div class="detail-item-head">
                    <span class="detail-item-id">{html.escape(str(item.get('id', 'SEM-ID')))} · {html.escape(str(item.get('repo', 'trabalho-atual')))}</span>
                    <span class="badge {badge_class(str(item.get('priority', 'media')))}">{html.escape(str(item.get('priority', 'media')).upper())}</span>
                  </div>
                  <div class="detail-item-title">{html.escape(str(item.get('title', 'Item sem titulo')))}</div>
                  <div class="detail-item-meta">{html.escape(item_meta(item))}</div>
                  <div class="detail-item-desc">{html.escape(str(item.get('description', 'Sem detalhe registrado.')))}</div>
                  <div class="detail-item-source">Fonte: {html.escape(str(item.get('source', 'Sem fonte informada.')))}</div>
                </article>
                """
            )

        if not item_rows:
            item_rows = ["<div class='detail-item'>Sem itens detalhados nesta iniciativa.</div>"]

        details_html.append(
            f"""
            <section class="detail-section">
              <div class="detail-section-head">
                <span class="emoji">{html.escape(str(group.get('emoji', '📌')))}</span>
                <h2>{html.escape(str(group.get('title', 'Iniciativa')))}</h2>
                <span class="badge {badge_class(str(group.get('urgency', 'media')))}">{html.escape(str(group.get('urgency', 'media')).upper())}</span>
              </div>
              <p>{html.escape(str(group.get('summary', 'Detalhamento dos itens da iniciativa.')))}</p>
              <div class="detail-items">
                {"\n".join(item_rows)}
              </div>
            </section>
            """
        )

    if not details_html:
        details_html.append(
            """
            <section class="detail-section">
              <div class="detail-section-head"><h2>Detalhamento</h2></div>
              <p>Nenhum item de backlog foi agrupado para detalhamento.</p>
            </section>
            """
        )

    return (
        template.replace("{{DATE}}", html.escape(str(data.get("date", ""))))
        .replace("{{TITLE}}", html.escape(str(data.get("title", "Relatorio gerencial"))))
        .replace("{{CURRENT_TASKS}}", current_html)
        .replace("{{GROUPS}}", "\n".join(groups_html))
        .replace("{{DETAILED_GROUPS}}", "\n".join(details_html))
        .replace("{{MANUAL_COUNT}}", str(stats.get("manual_tasks", 0)))
        .replace("{{BACKLOG_COUNT}}", str(stats.get("backlog_items", 0)))
        .replace("{{REPO_COUNT}}", str(len(stats.get("repos", []))))
        .replace("{{DETAIL_COUNT}}", str(int(stats.get("detailed_items", 0))))
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
        page.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True, margin={"top": "10mm", "right": "8mm", "bottom": "10mm", "left": "8mm"})
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


def draw_wrapped(draw: Any, xy: tuple[int, int], text: str, font: Any, fill: str, width: int, line_height: int, max_lines: int | None = None) -> int:
    chars = max(20, width // max(7, max(1, int(font.size * 0.5))))
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

    scale = 3
    width, height = 1240, 1754
    def new_page() -> tuple[Any, Any]:
        page = Image.new("RGB", (width * scale, height * scale), "#f7fafc")
        page_draw = ImageDraw.Draw(page)
        for bg_y in range(height):
            ratio = bg_y / height
            r = int(250 - 10 * ratio)
            g = int(252 - 9 * ratio)
            b = int(255 - 24 * ratio)
            y1 = bg_y * scale
            page_draw.line([(0, y1), (width * scale, y1)], fill=(r, g, b))
        return page, page_draw

    image, draw = new_page()

    fp = font_path()
    font = lambda size: ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
    title_font = font(42 * scale)
    h2_font = font(24 * scale)
    h3_font = font(20 * scale)
    body_font = font(17 * scale)
    small_font = font(14 * scale)
    tiny_font = font(12 * scale)

    sx = lambda v: int(v * scale)
    margin = sx(86)
    chart_left = sx(86)
    draw.rounded_rectangle((margin, sx(70), sx(width) - margin, sx(185)), radius=18 * scale, fill="#ffffff", outline="#d8e0ea", width=2 * scale)
    draw.text((sx(114), sx(92)), str(data.get("title", "Relatorio gerencial")), font=title_font, fill="#172033")
    draw.text((sx(width - 210 - 86), sx(98)), f"📅 {data.get('date', '')}", font=body_font, fill="#536173")
    draw.text((sx(114), sx(147)), "Resumo executivo para acompanhamento de prioridade, risco e proxima acao.", font=body_font, fill="#536173")

    stats = data.get("stats", {})
    metrics = [
        ("🎯", stats.get("manual_tasks", 0), "tarefas atuais"),
        ("📌", stats.get("backlog_items", 0), "itens em backlog"),
        ("🗂", len(stats.get("repos", [])), "repositorios"),
        ("📚", stats.get("detailed_items", 0), "itens detalhados"),
    ]
    card_w = (width - 2 * 86 - 24) // 4
    for i, (emoji, value, label) in enumerate(metrics):
        x = sx(86) + i * sx(card_w + 12)
        draw.rounded_rectangle((x, sx(210), x + sx(card_w), sx(306)), radius=16 * scale, fill="#ffffff", outline="#d8e0ea", width=2 * scale)
        draw.text((x + sx(22), sx(232)), f"{emoji} {value}", font=h2_font, fill="#172033")
        draw.text((x + sx(22), sx(270)), str(label).upper(), font=tiny_font, fill="#536173")

    left_x, left_y, left_w = 86, 335, 390
    right_x, right_y, right_w = left_x + left_w + 24, 335, width - 2 * left_x - left_w - 24
    draw.rounded_rectangle((sx(left_x), sx(left_y), sx(left_x + left_w), sx(1020)), radius=16 * scale, fill="#ffffff", outline="#d8e0ea", width=2 * scale)
    draw.text((sx(left_x + 22), sx(left_y + 22)), "🎯 Foco Atual", font=h2_font, fill="#172033")
    y = sx(left_y + 66)
    current_tasks = data.get("current_tasks", [])[:5] or ["Sem tarefas atuais informadas."]
    for task in current_tasks:
        y = draw_wrapped(draw, (sx(left_x + 28), y), f"• {task}", body_font, "#253047", sx(left_w - 56), sx(25), max_lines=3) + sx(8)

    draw.rounded_rectangle((sx(left_x), sx(1044), sx(left_x + left_w), sx(1455)), radius=16 * scale, fill="#ffffff", outline="#d8e0ea", width=2 * scale)
    draw.text((sx(left_x + 22), sx(1066)), "⚠️ Riscos", font=h2_font, fill="#172033")
    risk = "Itens de alta urgencia podem afetar prazo, confiabilidade ou previsibilidade se ficarem sem decisao."
    y = draw_wrapped(draw, (sx(left_x + 24), sx(1110)), risk, body_font, "#253047", sx(left_w - 48), sx(25), max_lines=5)
    draw.text((sx(left_x + 22), y + sx(28)), "✅ Decisoes", font=h2_font, fill="#172033")
    draw_wrapped(draw, (sx(left_x + 24), y + sx(72)), "Confirmar prioridade dos blocos marcados como ALTA/CRITICA na proxima conversa.", body_font, "#253047", sx(left_w - 48), sx(25), max_lines=5)

    draw.rounded_rectangle((sx(right_x), sx(right_y), sx(right_x + right_w), sx(1455)), radius=16 * scale, fill="#ffffff", outline="#d8e0ea", width=2 * scale)
    draw.text((sx(right_x + 22), sx(right_y + 22)), "🚧 Proximos Blocos de Trabalho", font=h2_font, fill="#172033")
    y = sx(right_y + 68)
    colors = {"critica": "#b42318", "alta": "#c2412d", "media": "#b7791f", "baixa": "#2f7d64"}
    for group in data.get("groups", [])[:5]:
        if y > sx(1360):
            break
        urgency = str(group.get("urgency", "media")).lower()
        draw.rounded_rectangle((sx(right_x + 20), y, sx(right_x + right_w - 20), y + sx(166)), radius=14 * scale, fill="#f8fafc", outline="#e2e8f0", width=1 * scale)
        draw.text((sx(right_x + 38), y + sx(18)), f"{group.get('emoji', '📌')} {group.get('title', 'Iniciativa')}", font=h3_font, fill="#172033")
        badge = urgency.upper()
        badge_w = 16 + len(badge) * 9
        draw.rounded_rectangle((sx(right_x + right_w - 42 - badge_w), y + sx(16), sx(right_x + right_w - 34), y + sx(42)), radius=13 * scale, fill=colors.get(urgency, "#b7791f"))
        draw.text((sx(right_x + right_w - 34 - badge_w), y + sx(21)), badge, font=tiny_font, fill="#ffffff")
        draw_wrapped(draw, (sx(right_x + 42), y + sx(54)), str(group.get("summary", "")), body_font, "#253047", sx(right_w - 84), sx(23), max_lines=2)
        repos = ", ".join(group.get("repos", [])[:3]) or "portfolio"
        draw.text((sx(right_x + 42), y + sx(104)), f"Repos: {repos} · {group.get('microtasks_count', 0)} itens agrupados", font=small_font, fill="#536173")
        draw_wrapped(draw, (sx(right_x + 42), y + sx(126)), f"Proxima acao: {group.get('next_action', 'Definir prioridade.')}", small_font, "#253047", sx(right_w - 84), sx(20), max_lines=2)
        y += sx(178)

    draw.text((sx(86), sx(1508)), "📌 Este report agrupa microtarefas por resultado esperado, sem exposição de jargão técnico.", font=body_font, fill="#39475a")

    pages = [image]
    detail_groups = [group for group in data.get("groups", [])[:5] if group.get("detailed_items")]
    if detail_groups:
        detail_page, detail_draw = new_page()
        pages.append(detail_page)
        detail_draw.text((sx(86), sx(72)), "Detalhamento dos itens", font=title_font, fill="#172033")
        detail_draw.text((sx(86), sx(132)), "Backlog e tarefas atuais agrupados por iniciativa.", font=body_font, fill="#536173")
        y = sx(195)

        def ensure_space(required_height: int = 210) -> None:
            nonlocal detail_page, detail_draw, y
            if y + sx(required_height) <= sx(1580):
                return
            detail_page, detail_draw = new_page()
            pages.append(detail_page)
            detail_draw.text((sx(86), sx(72)), "Detalhamento dos itens", font=title_font, fill="#172033")
            y = sx(145)

        for group in detail_groups:
            ensure_space(180)
            urgency = str(group.get("urgency", "media")).upper()
            detail_draw.rounded_rectangle((sx(86), y, sx(width - 86), y + sx(92)), radius=16 * scale, fill="#ffffff", outline="#d8e0ea", width=2 * scale)
            detail_draw.text((sx(112), y + sx(22)), f"{group.get('emoji', '📌')} {group.get('title', 'Iniciativa')}", font=h2_font, fill="#172033")
            detail_draw.text((sx(width - 225), y + sx(28)), urgency, font=small_font, fill="#536173")
            y = draw_wrapped(detail_draw, (sx(112), y + sx(58)), str(group.get("summary", "")), small_font, "#536173", sx(width - 224), sx(20), max_lines=2) + sx(20)

            for item in group.get("detailed_items", []):
                ensure_space(190)
                top = y
                detail_draw.rounded_rectangle((sx(104), top, sx(width - 104), top + sx(150)), radius=12 * scale, fill="#ffffff", outline="#e2e8f0", width=1 * scale)
                detail_draw.text((sx(128), top + sx(18)), f"{item.get('id', 'SEM-ID')} · {item.get('repo', 'trabalho-atual')}", font=tiny_font, fill="#536173")
                detail_draw.text((sx(width - 225), top + sx(18)), str(item.get("priority", "media")).upper(), font=tiny_font, fill="#b42318")
                title_y = draw_wrapped(detail_draw, (sx(128), top + sx(42)), str(item.get("title", "Item sem titulo")), h3_font, "#172033", sx(width - 276), sx(25), max_lines=2)
                meta = item_meta(item)
                meta_y = draw_wrapped(detail_draw, (sx(128), title_y + sx(4)), meta, tiny_font, "#536173", sx(width - 276), sx(17), max_lines=2)
                draw_wrapped(detail_draw, (sx(128), meta_y + sx(6)), str(item.get("description", "Sem detalhe registrado.")), small_font, "#253047", sx(width - 276), sx(20), max_lines=3)
                y = top + sx(166)

    # Anti-puxar suavemente para saída mais nítida.
    try:
        antialias = Image.Resampling.LANCZOS
    except AttributeError:  # compatibilidade com PIL antigo
        antialias = Image.ANTIALIAS

    resized_pages = [page.resize((width, height), antialias) for page in pages]
    resized_pages[0].save(pdf_path, "PDF", resolution=300.0, save_all=True, append_images=resized_pages[1:])
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Renderiza relatorio executivo em PDF do estado de andamento")
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
