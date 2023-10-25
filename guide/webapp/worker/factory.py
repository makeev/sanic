from pathlib import Path

from sanic import Request, Sanic, html, redirect

from webapp.display.layouts.models import MenuItem
from webapp.display.page import Page, PageRenderer
from webapp.endpoint.view import bp
from webapp.worker.config import load_config, load_menu
from webapp.worker.reload import setup_livereload
from webapp.worker.style import setup_style


def _compile_sidebar_order(items: list[MenuItem]) -> list[str]:
    order = []
    for item in items:
        if item.path:
            order.append(item.path.removesuffix(".html") + ".md")
        if item.items:
            order.extend(_compile_sidebar_order(item.items))
    return order


def create_app(root: Path) -> Sanic:
    app = Sanic("Documentation")
    app.config.PUBLIC_DIR = root / "public"
    app.config.CONTENT_DIR = root / "content"
    app.config.CONFIG_DIR = root / "config"
    app.config.STYLE_DIR = root / "style"
    app.config.NODE_MODULES_DIR = root / "node_modules"
    app.config.LANGUAGES = ["en"]
    app.config.SIDEBAR = load_menu(app.config.CONFIG_DIR / "en" / "sidebar.yaml")
    app.config.NAVBAR = load_menu(app.config.CONFIG_DIR / "en" / "navbar.yaml")
    app.config.GENERAL = load_config(app.config.CONFIG_DIR / "en" / "general.yaml")

    setup_livereload(app)
    setup_style(app)
    app.blueprint(bp)

    app.static("/assets/", app.config.PUBLIC_DIR / "assets")

    @app.before_server_start
    async def setup(app: Sanic):
        app.ext.dependency(PageRenderer(base_title="TestApp"))
        page_order = _compile_sidebar_order(app.config.SIDEBAR)
        app.ctx.pages = Page.load_pages(app.config.CONTENT_DIR, page_order)
        app.ctx.get_page = Page.get

    @app.get("/", name="root")
    @app.get("/index.html", name="index")
    async def index(request: Request):
        return redirect(request.app.url_for("page", language="en", path=""))

    @app.get("/<language:str>", name="page-without-path")
    @app.get("/<language:str>/<path:path>")
    async def page(
        request: Request,
        page_renderer: PageRenderer,
        language: str,
        path: str = "",
    ):
        return html(page_renderer.render(request, language, path))

    @app.on_request
    async def set_language(request: Request):
        request.ctx.language = request.match_info.get("language", Page.DEFAULT_LANGUAGE)

    return app
