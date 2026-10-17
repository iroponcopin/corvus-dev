#!/usr/bin/env python3
"""Builds /discord/ in every language: how to use the Corvus Discord bot.

Two sources, deliberately split
-------------------------------
* STRUCTURE comes from data/discord_commands.json, which is exported straight
  from the bot's real command tree by discord-release-bot/export_commands.py.
  Which commands exist, what parameters they take, which need Manage Server --
  none of that is typed here, so a renamed subcommand cannot leave the page
  describing something that no longer exists. The bot's own test suite fails
  if that export goes stale (discord-release-bot/tests/test_export.py).
* MEANING comes from data/discord_bot.json, which is written by hand in all
  thirteen languages. Discord's own command descriptions are English (Discord
  resolves them from each READER's client locale, not from the server), so
  reprinting them would leave twelve languages reading an English table.

The two are checked against each other at build time: every command in the
export must have a gloss in every language, and every gloss must correspond to
a real command. Either kind of drift stops the build rather than rendering a
page with blank rows or documenting a command nobody can run.

The invite link is NOT rebuilt here -- it comes from build_download.py's
_discord_invite(), the same function the Download page uses, so the two pages
cannot offer different links. The permission number in data/discord.json is
checked against the one the bot actually asks for.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import (  # noqa: E402
    ROOT, esc, page, write_page, available_langs,
)
from build_download import _discord_invite  # noqa: E402

PROSE_PATH = ROOT / "data" / "discord_bot.json"
COMMANDS_PATH = ROOT / "data" / "discord_commands.json"
INVITE_CONFIG_PATH = ROOT / "data" / "discord.json"

#: Chrome keys every language block must carry. Listed rather than derived
#: from English so that deleting a key from English cannot silently delete it
#: from the page for all thirteen.
REQUIRED = (
    "title", "nav", "description", "lede", "invite", "invite_note",
    "setup_title", "s1_h", "s1_p", "s2_h", "s2_p", "s3_h", "s3_p", "s4_h", "s4_p",
    "cmds_title", "th_cmd", "th_what", "th_who", "who_all", "who_admin",
    "posts_title", "posts_p", "post_update", "post_upcoming", "post_intake",
    "lang_title", "lang_p", "lang_note",
    "privacy_title", "privacy_p", "rate_note",
)


def _command_keys(commands):
    """'bug', 'bug new', ... in the order they should be printed."""
    keys = []
    for group in commands["groups"]:
        keys.append(group["name"])
        for sub in group["subcommands"]:
            keys.append(f"{group['name']} {sub['name']}")
    return keys


def _load():
    prose = json.loads(PROSE_PATH.read_text(encoding="utf-8"))
    commands = json.loads(COMMANDS_PATH.read_text(encoding="utf-8"))
    keys = _command_keys(commands)
    if not keys:
        raise SystemExit(
            "discord: data/discord_commands.json lists no commands. The page would render "
            "an empty table under a 'Every command' heading. Re-run "
            "discord-release-bot/export_commands.py and copy the result here."
        )

    invite_cfg = json.loads(INVITE_CONFIG_PATH.read_text(encoding="utf-8"))
    declared = str(invite_cfg.get("permissions", ""))
    actual = str(commands.get("invite_permissions", ""))
    if actual and declared != actual:
        raise SystemExit(
            f"discord: data/discord.json says the invite asks for permissions {declared}, "
            f"but the bot actually asks for {actual}. One of the two is wrong, and the "
            f"page would tell people the wrong thing about what they are granting. "
            f"Update data/discord.json to match bot/config.py's PERMISSIONS."
        )
    return prose, commands, keys


def _check_language(lang, block, keys):
    missing = [k for k in REQUIRED if not block.get(k)]
    if missing:
        raise SystemExit(
            f"discord: '{lang}' is missing {missing}. Those sections would render as empty "
            f"headings, which reads as a broken page rather than an untranslated one."
        )
    glosses = block.get("cmd") or {}
    absent = [k for k in keys if not glosses.get(k)]
    if absent:
        raise SystemExit(
            f"discord: '{lang}' has no description for {absent}. Those commands would appear "
            f"in the table with a blank 'what it does' column."
        )
    extra = [k for k in glosses if k not in keys]
    if extra:
        raise SystemExit(
            f"discord: '{lang}' describes {extra}, which the bot does not have. Either the "
            f"command was renamed (re-export data/discord_commands.json) or the page is "
            f"documenting something nobody can run."
        )


def _params_html(cmd):
    if not cmd["parameters"]:
        return ""
    bits = []
    for p in cmd["parameters"]:
        name = esc(p["name"])
        bits.append(f'<span class="dc-arg">&lt;{name}&gt;</span>')
    return " " + " ".join(bits)


def _rows(lang, block, commands):
    glosses = block["cmd"]
    out = []
    for group in commands["groups"]:
        gname = group["name"]
        out.append(
            f'<tr class="dc-group-row"><th colspan="3" scope="colgroup">'
            f'<code>/{esc(gname)}</code> — {esc(glosses[gname])}</th></tr>'
        )
        for sub in _ordered(group["subcommands"]):
            key = f"{gname} {sub['name']}"
            who = block["who_admin"] if sub["admin"] else block["who_all"]
            who_cls = "dc-who dc-who--admin" if sub["admin"] else "dc-who"
            out.append(
                f'<tr><td><code>/{esc(gname)} {esc(sub["name"])}</code>'
                f'{_params_html(sub)}</td>'
                f'<td>{esc(glosses[key])}</td>'
                f'<td><span class="{who_cls}">{esc(who)}</span></td></tr>'
            )
    return "\n".join(out)


def _kind_values(commands):
    """The literal values you type after <kind>, from the export.

    Worth printing even though step 4 names the four categories in prose:
    the prose says "advance notices", the command takes `upcoming`. Rendered
    inside that sentence rather than under the card, where a bare row of code
    chips with no lead-in reads as leftover debris.
    """
    kinds = commands.get("route_kinds") or []
    return " ".join(f"<code>{esc(k)}</code>" for k in kinds)


#: The order subcommands are printed in. data/discord_commands.json is sorted
#: alphabetically so its diffs stay readable, but alphabetical puts `new`
#: third -- behind `close` and `list` -- and `new` is the one a reader came
#: for. Anything not named here keeps its alphabetical position at the end,
#: so a subcommand added later still appears.
SUBCOMMAND_ORDER = (
    "new", "list", "close", "reopen",              # /bug, /request
    "set", "show", "clear",                        # /channels, /language
    "channel", "status", "latest", "enable", "disable", "launcher",
    "upcoming", "test",                            # /release
)


def _ordered(subcommands):
    def key(sub):
        try:
            return (0, SUBCOMMAND_ORDER.index(sub["name"]), "")
        except ValueError:
            return (1, 0, sub["name"])
    out = sorted(subcommands, key=key)
    assert len(out) == len(subcommands)
    return out


def build_lang(lang, block, commands, invite_url):
    langs = commands.get("languages") or []
    names = commands.get("language_names") or {}
    chips = "".join(
        f'<li class="dc-lang"><span class="dc-lang-name">{esc(names.get(code, code))}</span>'
        f'<code>{esc(code)}</code></li>' for code in langs)

    cta = ""
    if invite_url:
        cta = (
            f'<p class="dc-cta"><a class="btn btn-primary" href="{esc(invite_url)}" '
            f'target="_blank" rel="noopener noreferrer">{esc(block["invite"])}</a></p>'
            f'<p class="dc-note">{esc(block["invite_note"])}</p>'
        )

    kinds = _kind_values(commands)
    steps_src = (("s1_h", "s1_p"), ("s2_h", "s2_p"), ("s3_h", "s3_p"), ("s4_h", "s4_p"))
    steps = "".join(
        f'<li><h3>{esc(block[h])}</h3><p>{block[p]}'
        + (f' <span class="dc-kinds">{kinds}</span>' if h == "s4_h" and kinds else "")
        + '</p></li>'
        for h, p in steps_src
    )

    body = f"""
<div class="hero dc-hero">
  <h1>{esc(block['title'])}</h1>
  <p class="dc-lede">{esc(block['lede'])}</p>
  {cta}
</div>

<section class="card dc-setup">
  <h2>{esc(block['setup_title'])}</h2>
  <ol class="dc-steps">{steps}</ol>
</section>

<section class="card dc-posts">
  <h2>{esc(block['posts_title'])}</h2>
  <p>{esc(block['posts_p'])}</p>
  <ul class="dc-posts-list">
    <li>{esc(block['post_update'])}</li>
    <li>{esc(block['post_upcoming'])}</li>
    <li>{esc(block['post_intake'])}</li>
  </ul>
</section>

<section class="card dc-commands">
  <h2>{esc(block['cmds_title'])}</h2>
  <div class="dc-table-wrap">
    <table class="dc-table">
      <thead><tr>
        <th scope="col">{esc(block['th_cmd'])}</th>
        <th scope="col">{esc(block['th_what'])}</th>
        <th scope="col">{esc(block['th_who'])}</th>
      </tr></thead>
      <tbody>
{_rows(lang, block, commands)}
      </tbody>
    </table>
  </div>
  <p class="dc-note">{esc(block['rate_note'])}</p>
</section>

<section class="card dc-langs">
  <h2>{esc(block['lang_title'])}</h2>
  <p>{esc(block['lang_p'])}</p>
  <ul class="dc-lang-list">{chips}</ul>
  <p class="dc-note">{esc(block['lang_note'])}</p>
</section>

<section class="card dc-privacy">
  <h2>{esc(block['privacy_title'])}</h2>
  <p>{esc(block['privacy_p'])}</p>
</section>"""

    return page(
        lang=lang, section="discord/", title=block["title"],
        description=block["description"], active="discord",
        body=body, depth=1,
    )


def main():
    prose, commands, keys = _load()
    invite_url, configured = _discord_invite()
    if not configured:
        print("discord: WARNING - data/discord.json has no real client_id, so the page "
              "will build WITHOUT an invite button.")
    langs = available_langs()
    built = 0
    for lang in langs:
        if lang not in prose:
            raise SystemExit(
                f"discord: data/discord_bot.json has no block for '{lang}'. Falling back to "
                f"English on a page whose whole subject is a bot that speaks thirteen "
                f"languages would contradict the page itself."
            )
        _check_language(lang, prose[lang], keys)
        write_page(lang, "discord/", build_lang(lang, prose[lang], commands, invite_url))
        built += 1
    if built == 0:
        raise SystemExit("discord: built ZERO pages; available_langs() returned nothing.")
    print(f"discord: {built} languages, {len(keys)} commands documented")


if __name__ == "__main__":
    main()
