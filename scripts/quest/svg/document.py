"""Assemble the full quest SVG document."""

from .. import layout
from . import actors, boss, cards, cinema, fx, hud, world
from .assets import AssetBook

PIXELATED = (
    "image-rendering:optimizeSpeed;image-rendering:-moz-crisp-edges;"
    "image-rendering:-webkit-optimize-contrast;image-rendering:crisp-edges;"
    "image-rendering:pixelated"
)


def render(script, roster):
    """QuestScript + Roster -> self-contained, infinitely looping SVG string."""
    book = AssetBook()
    gradients, styles = {}, {}
    world_layers = _world(script, book, gradients, styles)
    overlay = _overlay(script, roster, book)
    return _frame(script, book, gradients, styles, world_layers, overlay)


def _world(script, book, gradients, styles):
    """Everything that shakes with the ground: scenery, fires, the wyrm, monsters, the knight, blows."""
    back, front = world.scene_layers(script, book, gradients, styles, sky={0: cinema.flyby(script, book)})
    return "".join([
        back,
        world.bonfires(script, book, gradients),
        cinema.ignition(script, book, gradients),
        boss.wyrm(script, book),
        actors.monster_actors(script, book),
        actors.knight_actor(script, book),
        boss.marks(script, book),
        fx.hit_marks(script, book),
        fx.parry_sparks(script, book),
        fx.death_effects(script, book),
        boss.fire(script, book, gradients),
        boss.embers(script, book),
        front,
    ])


def _overlay(script, roster, book):
    """Everything that stays still over the world: souls in flight, fades, the HUD and the cards."""
    hud_layer = "".join([
        hud.health_bar(script, book),
        hud.souls_counter(script, roster, book),
        hud.quest_strip(script, roster, book),
    ])
    return "".join([
        fx.soul_wisps(script, book),
        boss.soul(script, book),
        boss.flash(script),
        hud.fade_overlay(script),
        cards.boss_intro(script, book),
        f'<g opacity="0">{hud.visibility(script)}{hud_layer}</g>',
        hud.nameplates(script, book),
        hud.boss_bar(script, book),
        cards.game_title(script, roster, book),
        cards.chapter_titles(script, book),
        cards.victory_banner(script, book),
        cards.quest_complete(script, roster, book),
        hud.footer(book),
    ])


def _frame(script, book, gradients, styles, world_layers, overlay):
    w, h, s = layout.WIDTH, layout.HEIGHT, layout.SCALE
    style = f"<style>svg,image,use{{{PIXELATED}}}{world.css()}{''.join(styles[name] for name in sorted(styles))}</style>"
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
