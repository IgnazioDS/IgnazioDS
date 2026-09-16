"""Assemble the full quest SVG document."""

from .. import layout
from . import actors, boss, hud, world
from .assets import AssetBook

PIXELATED = (
    "image-rendering:optimizeSpeed;image-rendering:-moz-crisp-edges;"
    "image-rendering:-webkit-optimize-contrast;image-rendering:crisp-edges;"
    "image-rendering:pixelated"
)


def render(script, roster):
    """QuestScript + Roster -> self-contained, infinitely looping SVG string."""
    book = AssetBook()
    gradients = {}
    scenery_back, scenery_front = world.chapters(script, book, gradients)
    world_layers = "".join([
        scenery_back,
        world.bonfires(script, book, gradients),
        boss.wyrm(script, book),
        actors.monster_actors(script, book),
        actors.knight_actor(script, book, boss.knight_dash(script)),
        actors.parry_sparks(script, book),
        actors.death_effects(script, book),
        boss.fire(script, book, gradients),
        boss.embers(script, book),
        scenery_front,
    ])
    overlay = "".join([
        actors.soul_wisps(script, book),
        boss.soul(script, book),
        hud.fade_overlay(script),
        hud.boss_intro(script, book),
        hud.health_bar(script),
        hud.souls_counter(script, roster, book),
        hud.date_labels(script, book),
        hud.boss_bar(script, book),
        hud.game_title(script, book),
        hud.chapter_titles(script, book),
        hud.victory_banner(script, book),
        hud.footer(book),
    ])
    w, h, s = layout.WIDTH, layout.HEIGHT, layout.SCALE
    style = f"<style>svg,image,use{{{PIXELATED}}}{world.css()}</style>"
    defs = book.defs().replace(
        "<defs>",
        f'<defs>{world.gradient_defs(gradients)}<clipPath id="frame"><rect width="{w}" height="{h}" rx="6"/></clipPath>',
        1,
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w * s} {h * s}" '
        f'width="{w * s}" height="{h * s}" image-rendering="optimizeSpeed" role="img" '
        f'aria-label="Self-playing dark fantasy quest over real GitHub contribution data">'
        f"<!-- self-playing dark fantasy quest · built by Ignazio De Santis · "
        f"github.com/IgnazioDS · eleventh.dev -->"
        f"<desc>Built by Ignazio De Santis (github.com/IgnazioDS, eleventh.dev). "
        f"A dark knight fights one monster per active day of real GitHub contributions; "
        f"the biggest day is the dragon. Regenerated daily.</desc>"
        f"{style}{defs}"
        f'<g transform="scale({s})"><g clip-path="url(#frame)">'
        f'<rect width="{w}" height="{h}" fill="#050308"/>'
        f"<g>{boss.shake(script)}{world_layers}</g>{overlay}</g>"
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="6" fill="none" stroke="#30363d"/>'
        "</g></svg>"
    )
