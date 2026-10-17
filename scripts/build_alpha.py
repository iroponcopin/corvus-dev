#!/usr/bin/env python3
"""Builds alpha/index.html \u2014 the official notice that Alpha ended distribution, for every language.

Until 2026-09-28 this was Alpha's brand page. The owner retired Alpha and had it erased from the site
(「Alphaは公式に配信を終了したことを記載し、抹消」), so what stays at this URL is one page saying so: what
ended, what was withdrawn, what happens to worlds, and that OUKA, Cherry and Aureum continue. Everything
numeric is read from the site's own data at build time (data/versions.json, data/retirement.json).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from site_common import (  # noqa: E402
    ROOT, asset_root_prefix, available_langs, esc, page, write_page, alpha_retirement,
)

SECTION = "alpha/"

# The Alpha mark, cut from the owner's own logo photograph (the wordmark in
# that photograph is NOT used -- 「ロゴにはテキストが含まれていますがこれは一切
# 使用せずロゴだけを切り取り使用してください」). The gradient wordmark below it
# stays the page's h1: the mark is the picture of the name, the h1 IS the name,
# so the image is decorative and carries alt="" rather than repeating "Alpha"
# to a screen reader that is about to read the heading anyway.
#
# Intrinsic sizes are the real files on disk, measured, not guessed --
# mark-584.webp is 584x384 and mark-320.webp is 320x211. width/height are
# emitted so the hero reserves its box before the image arrives.
MARK = {"file": "mark-584.webp", "w": 584, "h": 384,
        "small": "mark-320.webp", "small_w": 320}


def facts() -> dict:
    """Version, module count and the retirement date \u2014 from the site's own data, not from here."""
    versions = json.loads((ROOT / "data" / "versions.json").read_text(encoding="utf-8"))
    mods = versions["mods"]
    distinct = sorted(set(mods.values()))
    if len(distinct) != 1:
        raise SystemExit(
            "ERROR: data/versions.json lists more than one version %s \u2014 the Alpha notice "
            "cannot state a single one." % distinct)
    block = alpha_retirement()
    if not block.get("retired") or block.get("retired_version") != distinct[0]:
        raise SystemExit(
            "ERROR: this page is the notice that Alpha ended, but data/retirement.json does not say the "
            "current release (%s) is the retirement release." % distinct[0])
    return {
        "version": distinct[0],
        "modules": len(mods),
        "mc": versions.get("mc_version", ""),
        "date": block.get("date", ""),
    }


# 2026-09-28: Alpha ended distribution and was erased from the site (owner: 「公式に配信を終了したことを記載し、
# 抹消」). This is the one page that says so; it replaces the brand page. Every string is in all 13 languages,
# Japanese first, with no fallback. {modules} {version} {date} are read from the site's own data at build time.
NOTICE = {
    "ja": {
        "desc": "Alpha は公式に配信を終了しました。",
        "lede": "Alpha は公式に配信を終了しました。銃火器・鉄道・車両・建材・災害・異次元まで、{modules} のモジュールで出していたパックで、今後の版は出ません。最後の版 {version} が Alpha を止めます。",
        "h1": "終了したこと", "p1": "Alpha の配信は {date} に終了しました。{version} が最後の版で、{modules} の MOD を、ゲームに何も足さないプレースホルダーに置き換えます。",
        "h2": "取り下げたもの", "p2": "過去の版のダウンロード、Alpha のレシピ、導入手順・ゲート・機能紹介・ロードマップ・既知の不具合のページは、このサイトから消えました。更新履歴に残るのは、このお知らせだけです。",
        "h3": "ワールドについて", "p3": "更新の前にワールドのバックアップを取ってください。Alpha が足したブロックは空気になり、1 度保存されると戻りません。Y=319 より上に普通のブロックで建てたものは残ります。",
        "h4": "続くもの", "p4": "OUKA・Cherry・Aureum は別のブランドで、影響を受けません。Corvus が引き続き最新に保ちます。",
        "cta_dl": "廃止の更新", "cta_log": "変更履歴",
    },
    "en": {
        "desc": "Alpha has officially ended distribution.",
        "lede": "Alpha has officially ended distribution. It was a pack of {modules} modules \u2014 firearms, rail, vehicles, building, disasters and other dimensions \u2014 and no further version will be released. Its last release, {version}, switches it off.",
        "h1": "What has ended", "p1": "Distribution of Alpha ended on {date}. {version} is the last release: it replaces the {modules} mods with placeholders that add nothing to the game.",
        "h2": "What has been withdrawn", "p2": "Every earlier download, Alpha's recipes, and its install guide, gates, features, roadmap and known-issues pages are gone from this site. The changelog keeps only this notice.",
        "h3": "Your worlds", "p3": "Back up your worlds before you update. Blocks that Alpha added turn into empty air, and once a world has been saved that way they do not come back. What you built above Y=319 with ordinary blocks is kept.",
        "h4": "What continues", "p4": "OUKA, Cherry and Aureum are separate and are not affected. Corvus keeps updating them.",
        "cta_dl": "Retirement update", "cta_log": "Changelog",
    },
    "es": {
        "desc": "Alpha ha terminado oficialmente su distribución.",
        "lede": "Alpha ha terminado oficialmente su distribución. Era un pack de {modules} módulos \u2014armas de fuego, ferrocarril, vehículos, construcción, desastres y otras dimensiones\u2014 y no se publicará ninguna versión más. Su última versión, {version}, lo desactiva.",
        "h1": "Lo que ha terminado", "p1": "La distribución de Alpha terminó el {date}. {version} es la última versión: sustituye los {modules} mods por marcadores de posición que no añaden nada al juego.",
        "h2": "Lo que se ha retirado", "p2": "Todas las descargas anteriores, las recetas de Alpha y sus páginas de guía de instalación, portales, funciones, hoja de ruta y problemas conocidos han desaparecido de este sitio. El historial de cambios conserva solo este aviso.",
        "h3": "Tus mundos", "p3": "Haz una copia de seguridad de tus mundos antes de actualizar. Los bloques que Alpha añadió se convierten en aire vacío y, una vez guardado el mundo así, no vuelven. Lo que construiste por encima de Y=319 con bloques normales se conserva.",
        "h4": "Lo que continúa", "p4": "OUKA, Cherry y Aureum son independientes y no se ven afectados. Corvus sigue manteniéndolos al día.",
        "cta_dl": "Actualización de retirada", "cta_log": "Historial de cambios",
    },
    "fr": {
        "desc": "Alpha a officiellement cessé d'être distribué.",
        "lede": "Alpha a officiellement cessé d'être distribué. C'était un pack de {modules} modules \u2014 armes à feu, rail, véhicules, construction, catastrophes et autres dimensions \u2014 et aucune autre version ne sortira. Sa dernière version, la {version}, le désactive.",
        "h1": "Ce qui a pris fin", "p1": "La distribution d'Alpha a pris fin le {date}. La {version} est la dernière version : elle remplace les {modules} mods par des substituts qui n'ajoutent rien au jeu.",
        "h2": "Ce qui a été retiré", "p2": "Tous les téléchargements antérieurs, les recettes d'Alpha et ses pages de guide d'installation, portails, fonctionnalités, feuille de route et problèmes connus ont disparu de ce site. L'historique des mises à jour ne garde que cette annonce.",
        "h3": "Vos mondes", "p3": "Sauvegardez vos mondes avant de mettre à jour. Les blocs qu'Alpha avait ajoutés deviennent de l'air vide et, une fois le monde sauvegardé ainsi, ils ne reviennent pas. Ce que vous avez construit au-dessus de Y=319 avec des blocs ordinaires est conservé.",
        "h4": "Ce qui continue", "p4": "OUKA, Cherry et Aureum sont indépendants et ne sont pas touchés. Corvus continue de les tenir à jour.",
        "cta_dl": "Mise à jour de retrait", "cta_log": "Historique des mises à jour",
    },
    "zh": {
        "desc": "Alpha 已正式终止发布。",
        "lede": "Alpha 已正式终止发布。它是一个包含 {modules} 个模块的整合包\u2014\u2014枪械、铁路、载具、建筑、灾害与其他维度\u2014\u2014今后不会再发布新版本。最后一个版本 {version} 会将其停用。",
        "h1": "已经结束的", "p1": "Alpha 的发布于 {date} 结束。{version} 是最后一个版本：它把 {modules} 个模组替换为不给游戏添加任何内容的占位文件。",
        "h2": "已经撤下的", "p2": "所有旧版本的下载、Alpha 的配方，以及它的安装指南、传送门、功能、路线图和已知问题页面，均已从本站移除。更新记录只保留这份公告。",
        "h3": "你的世界", "p3": "更新前请先备份你的世界。Alpha 添加的方块会变成空气，世界以这种状态保存后就不会再回来。你在 Y=319 以上用普通方块建造的东西会保留。",
        "h4": "继续的", "p4": "OUKA、Cherry 和 Aureum 是独立的，不受影响。Corvus 会继续让它们保持最新。",
        "cta_dl": "退役更新", "cta_log": "更新记录",
    },
    "ko": {
        "desc": "Alpha는 공식적으로 배포를 종료했습니다.",
        "lede": "Alpha는 공식적으로 배포를 종료했습니다. 총기, 철도, 탈것, 건축, 재해, 다른 차원까지 {modules}개 모듈로 나왔던 팩이며, 앞으로 새 버전은 나오지 않습니다. 마지막 버전 {version}이 Alpha를 끕니다.",
        "h1": "끝난 것", "p1": "Alpha의 배포는 {date}에 끝났습니다. {version}이 마지막 버전이며, {modules}개 모드를 게임에 아무것도 더하지 않는 자리 표시용 파일로 바꿉니다.",
        "h2": "내린 것", "p2": "이전 버전의 다운로드, Alpha의 레시피, 설치 안내·게이트·기능 소개·로드맵·알려진 문제 페이지는 이 사이트에서 사라졌습니다. 업데이트 기록에는 이 공지만 남습니다.",
        "h3": "월드에 대해", "p3": "업데이트하기 전에 월드를 백업하세요. Alpha가 추가한 블록은 빈 공기로 바뀌고, 월드가 그 상태로 저장되면 다시 돌아오지 않습니다. Y=319보다 위에 일반 블록으로 지은 것은 남습니다.",
        "h4": "이어지는 것", "p4": "OUKA, Cherry, Aureum은 별개의 브랜드이며 영향을 받지 않습니다. Corvus가 계속 최신 상태로 유지합니다.",
        "cta_dl": "종료 업데이트", "cta_log": "업데이트 기록",
    },
    "pt-br": {
        "desc": "O Alpha encerrou oficialmente a distribuição.",
        "lede": "O Alpha encerrou oficialmente a distribuição. Era um pack de {modules} módulos \u2014 armas de fogo, ferrovia, veículos, construção, desastres e outras dimensões \u2014 e nenhuma outra versão será lançada. A última versão, {version}, o desativa.",
        "h1": "O que terminou", "p1": "A distribuição do Alpha terminou em {date}. A {version} é a última versão: ela substitui os {modules} mods por marcadores que não adicionam nada ao jogo.",
        "h2": "O que foi retirado", "p2": "Todos os downloads anteriores, as receitas do Alpha e suas páginas de guia de instalação, portais, recursos, roteiro e problemas conhecidos saíram deste site. O histórico de atualizações guarda apenas este aviso.",
        "h3": "Seus mundos", "p3": "Faça backup dos seus mundos antes de atualizar. Os blocos que o Alpha adicionou viram ar vazio e, depois que o mundo é salvo assim, não voltam. O que você construiu acima de Y=319 com blocos comuns é mantido.",
        "h4": "O que continua", "p4": "OUKA, Cherry e Aureum são independentes e não são afetados. O Corvus continua mantendo-os atualizados.",
        "cta_dl": "Atualização de encerramento", "cta_log": "Histórico de atualizações",
    },
    "it": {
        "desc": "Alpha ha concluso ufficialmente la distribuzione.",
        "lede": "Alpha ha concluso ufficialmente la distribuzione. Era un pacchetto di {modules} moduli \u2014 armi da fuoco, ferrovia, veicoli, costruzione, disastri e altre dimensioni \u2014 e non verrà rilasciata nessun'altra versione. L'ultima versione, {version}, lo disattiva.",
        "h1": "Cosa è finito", "p1": "La distribuzione di Alpha è terminata il {date}. La {version} è l'ultima versione: sostituisce i {modules} mod con segnaposto che non aggiungono nulla al gioco.",
        "h2": "Cosa è stato ritirato", "p2": "Tutti i download precedenti, le ricette di Alpha e le sue pagine di guida all'installazione, portali, funzioni, roadmap e problemi noti sono spariti da questo sito. La cronologia degli aggiornamenti conserva solo questo avviso.",
        "h3": "I tuoi mondi", "p3": "Fai una copia di sicurezza dei tuoi mondi prima di aggiornare. I blocchi che Alpha aveva aggiunto diventano aria vuota e, una volta salvato il mondo così, non tornano. Ciò che hai costruito sopra Y=319 con blocchi normali resta.",
        "h4": "Cosa continua", "p4": "OUKA, Cherry e Aureum sono indipendenti e non sono toccati. Corvus continua a mantenerli aggiornati.",
        "cta_dl": "Aggiornamento di ritiro", "cta_log": "Cronologia degli aggiornamenti",
    },
    "ar": {
        "desc": "أنهى Alpha توزيعه رسميًا.",
        "lede": "أنهى Alpha توزيعه رسميًا. كان حزمة من {modules} وحدة \u2014 أسلحة نارية وسكك حديدية ومركبات وبناء وكوارث وأبعاد أخرى \u2014 ولن يصدر أي إصدار آخر. وآخر إصدار له، {version}، يعطّله.",
        "h1": "ما انتهى", "p1": "انتهى توزيع Alpha في {date}. {version} هو الإصدار الأخير: يستبدل الإضافات الـ {modules} بعناصر نائبة لا تضيف شيئًا إلى اللعبة.",
        "h2": "ما سُحب", "p2": "أُزيلت من هذا الموقع كل التنزيلات السابقة ووصفات Alpha وصفحات دليل التثبيت والبوابات والميزات وخارطة الطريق والمشكلات المعروفة. ولا يحتفظ سجل التحديثات إلا بهذا الإعلان.",
        "h3": "عوالمك", "p3": "انسخ عوالمك احتياطيًا قبل التحديث. الكتل التي أضافها Alpha تتحول إلى هواء فارغ، وبعد حفظ العالم بهذه الحالة لا تعود. أما ما بنيته فوق Y=319 بكتل عادية فيبقى.",
        "h4": "ما يستمر", "p4": "OUKA وCherry وAureum مستقلة ولا تتأثر. ويواصل Corvus إبقاءها محدّثة.",
        "cta_dl": "تحديث الإيقاف", "cta_log": "سجل التحديثات",
    },
    "ru": {
        "desc": "Alpha официально прекратил распространение.",
        "lede": "Alpha официально прекратил распространение. Это была сборка из {modules} модулей \u2014 огнестрельное оружие, железная дорога, транспорт, строительство, катастрофы и другие измерения \u2014 и новых версий больше не будет. Его последняя версия, {version}, отключает его.",
        "h1": "Что закончилось", "p1": "Распространение Alpha закончилось {date}. {version} \u2014 последняя версия: она заменяет {modules} модов заглушками, которые ничего не добавляют в игру.",
        "h2": "Что снято", "p2": "Все прежние загрузки, рецепты Alpha и его страницы \u2014 руководство по установке, врата, возможности, дорожная карта и известные проблемы \u2014 удалены с этого сайта. В истории обновлений остаётся только это объявление.",
        "h3": "Ваши миры", "p3": "Сделайте резервную копию миров перед обновлением. Блоки, добавленные Alpha, превращаются в пустой воздух, и после сохранения мира в таком виде они не возвращаются. Всё, что вы построили выше Y=319 из обычных блоков, сохраняется.",
        "h4": "Что продолжается", "p4": "OUKA, Cherry и Aureum независимы и не затронуты. Corvus по-прежнему держит их актуальными.",
        "cta_dl": "Обновление о прекращении", "cta_log": "История обновлений",
    },
    "id": {
        "desc": "Alpha secara resmi mengakhiri distribusinya.",
        "lede": "Alpha secara resmi mengakhiri distribusinya. Ia adalah paket berisi {modules} modul \u2014 senjata api, kereta, kendaraan, bangunan, bencana, dan dimensi lain \u2014 dan tidak akan ada versi lagi. Rilis terakhirnya, {version}, mematikannya.",
        "h1": "Yang telah berakhir", "p1": "Distribusi Alpha berakhir pada {date}. {version} adalah rilis terakhir: ia mengganti {modules} mod dengan pengganti yang tidak menambahkan apa pun ke permainan.",
        "h2": "Yang ditarik", "p2": "Semua unduhan sebelumnya, resep Alpha, serta halaman panduan pemasangan, gerbang, fitur, peta jalan, dan masalah yang diketahui telah dihapus dari situs ini. Riwayat pembaruan hanya menyimpan pengumuman ini.",
        "h3": "Duniamu", "p3": "Cadangkan duniamu sebelum memperbarui. Blok yang ditambahkan Alpha menjadi udara kosong, dan setelah dunia disimpan seperti itu, blok tersebut tidak kembali. Apa yang kamu bangun di atas Y=319 dengan blok biasa tetap ada.",
        "h4": "Yang berlanjut", "p4": "OUKA, Cherry, dan Aureum terpisah dan tidak terpengaruh. Corvus terus menjaganya tetap mutakhir.",
        "cta_dl": "Pembaruan penghentian", "cta_log": "Riwayat pembaruan",
    },
    "de": {
        "desc": "Alpha hat den Vertrieb offiziell beendet.",
        "lede": "Alpha hat den Vertrieb offiziell beendet. Es war ein Paket aus {modules} Modulen \u2013 Schusswaffen, Eisenbahn, Fahrzeuge, Bauen, Katastrophen und andere Dimensionen \u2013, und es erscheint keine weitere Version. Die letzte Version, {version}, schaltet es ab.",
        "h1": "Was zu Ende ist", "p1": "Der Vertrieb von Alpha endete am {date}. {version} ist die letzte Version: Sie ersetzt die {modules} Mods durch Platzhalter, die dem Spiel nichts hinzufügen.",
        "h2": "Was zurückgezogen wurde", "p2": "Alle früheren Downloads, Alphas Rezepte sowie die Seiten zu Installationsanleitung, Portalen, Funktionen, Roadmap und bekannten Problemen sind von dieser Seite verschwunden. Der Änderungsverlauf behält nur diese Mitteilung.",
        "h3": "Deine Welten", "p3": "Sichere deine Welten, bevor du aktualisierst. Blöcke, die Alpha hinzugefügt hat, werden zu leerer Luft, und sobald eine Welt so gespeichert wurde, kommen sie nicht zurück. Was du oberhalb von Y=319 aus normalen Blöcken gebaut hast, bleibt erhalten.",
        "h4": "Was weitergeht", "p4": "OUKA, Cherry und Aureum sind eigenständig und nicht betroffen. Corvus hält sie weiter aktuell.",
        "cta_dl": "Abschluss-Update", "cta_log": "Änderungsverlauf",
    },
    "tr": {
        "desc": "Alpha dağıtımı resmen sonlandırdı.",
        "lede": "Alpha dağıtımı resmen sonlandırdı. {modules} modülden oluşan bir paketti \u2014 ateşli silahlar, demiryolu, araçlar, yapı, felaketler ve başka boyutlar \u2014 ve artık yeni sürüm çıkmayacak. Son sürümü {version}, onu kapatır.",
        "h1": "Sona eren", "p1": "Alpha'nın dağıtımı {date} tarihinde sona erdi. {version} son sürümdür: {modules} modu, oyuna hiçbir şey eklemeyen yer tutucularla değiştirir.",
        "h2": "Geri çekilen", "p2": "Önceki tüm indirmeler, Alpha'nın tarifleri ve kurulum kılavuzu, geçitler, özellikler, yol haritası ve bilinen sorunlar sayfaları bu siteden kaldırıldı. Güncelleme geçmişinde yalnızca bu duyuru kalır.",
        "h3": "Dünyalarınız", "p3": "Güncellemeden önce dünyalarınızı yedekleyin. Alpha'nın eklediği bloklar boş havaya dönüşür ve dünya böyle kaydedildikten sonra geri gelmez. Y=319'un üstünde sıradan bloklarla yaptığınız şeyler korunur.",
        "h4": "Devam eden", "p4": "OUKA, Cherry ve Aureum ayrıdır ve etkilenmez. Corvus onları güncel tutmaya devam eder.",
        "cta_dl": "Sonlandırma güncellemesi", "cta_log": "Güncelleme geçmişi",
    },
}

HEAD = """<style>
/* ★ この HEAD は .format() を通さない。二重波括弧はそのまま CSS に出て
   規則を丸ごと無効にする(実際に一度そうなり、カードが素の見出しになった)。 */
.al-wrap{padding:3.5rem 0 1rem}
.al-hero{max-width:52rem}
/* The mark sits above the name at hero scale. It is capped in rem AND in vw so
   it cannot outgrow a phone; height:auto keeps the measured 584x384 ratio. */
.al-mark{display:block;width:min(19rem,58vw);height:auto;margin:0 0 1.15rem}
/* One entrance, once. The mark is not an animated logo (that is Cherry's and
   OUKA's job) -- it rises into place and then holds. */
@media (prefers-reduced-motion:no-preference){
  .al-mark{animation:al-mark-in 900ms cubic-bezier(.16,.84,.28,1) both}
}
@keyframes al-mark-in{from{opacity:0;transform:translateY(14px) scale(.985)}
  to{opacity:1;transform:none}}
.al-name{font-size:clamp(2.6rem,7vw,4.2rem);line-height:1.02;margin:0 0 .8rem;
  letter-spacing:-.02em;
  background:linear-gradient(100deg,var(--text) 18%,var(--accent-strong) 62%,var(--glow-green) 96%);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.al-lede{font-size:1.14rem;line-height:1.78;color:var(--text);margin:0 0 1.6rem}
.al-cta{display:flex;gap:.7rem;flex-wrap:wrap;margin-bottom:2.6rem}
.al-grid{display:grid;gap:1.25rem;
  grid-template-columns:repeat(auto-fit,minmax(15rem,1fr))}
.al-card{background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:14px;
  padding:1.4rem 1.3rem;box-shadow:var(--glass-highlight)}
.al-card h2{font-size:1.06rem;margin:0 0 .5rem;color:var(--accent-strong)}
.al-card p{margin:0;color:var(--text-muted);line-height:1.7;font-size:.97rem}
</style>"""


def build_body(c: dict, f: dict, lang_prefix: str, asset_prefix: str) -> str:
    lede = c["lede"].format(**f)
    mark = (
        '<img class="al-mark" src="%sassets/img/alpha/%s" '
        'srcset="%sassets/img/alpha/%s %dw, %sassets/img/alpha/%s %dw" '
        'sizes="min(19rem,58vw)" width="%d" height="%d" alt="" '
        'decoding="async" fetchpriority="high" loading="eager">'
        % (asset_prefix, MARK["file"],
           asset_prefix, MARK["small"], MARK["small_w"],
           asset_prefix, MARK["file"], MARK["w"],
           MARK["w"], MARK["h"])
    )
    cards = []
    for h, p in (("h1", "p1"), ("h2", "p2"), ("h3", "p3"), ("h4", "p4")):
        cards.append('<div class="al-card"><h2>%s</h2><p>%s</p></div>'
                     % (esc(c[h]), esc(c[p].format(**f))))
    return (
        '<div class="al-wrap"><div class="al-hero">'
        '%s'
        '<h1 class="al-name">Alpha</h1><p class="al-lede">%s</p>'
        '<div class="al-cta">'
        '<a class="btn btn--action" href="%sdownload/">%s</a>'
        '<a class="btn" href="%schangelog/">%s</a>'
        '</div></div>'
        '<div class="al-grid">%s</div></div>'
        % (mark, esc(lede), lang_prefix, esc(c["cta_dl"]),
           lang_prefix, esc(c["cta_log"]), "".join(cards))
    )


def main() -> int:
    f = facts()
    langs = available_langs()
    for lang in langs:
        c = NOTICE[lang]
        lang_prefix = "../"
        # NOT the same string as lang_prefix: /de/alpha/ is two levels below
        # the site root but one below its language root. Hardcoding "../" here
        # is the 404 that site_common.asset_root_prefix() exists to prevent.
        asset_prefix = asset_root_prefix(1, lang)
        html = page(
            lang=lang,
            section=SECTION,
            title="Alpha",
            description=c["desc"],
            active="",
            body=build_body(c, f, lang_prefix, asset_prefix),
            depth=1,
            extra_head=HEAD,
        )
        # The mark is the one thing on this page that can fail silently: a
        # wrong prefix or a dropped <img> still renders a perfectly good text
        # hero, and nothing goes red. Assert it is there, with a path that
        # resolves from THIS page's depth, before the file is written.
        want = '%sassets/img/alpha/%s' % (asset_prefix, MARK["file"])
        if want not in html:
            raise SystemExit(
                "ERROR: build_alpha: the hero mark (%s) is not in the rendered "
                "%s page." % (want, lang))
        target = ROOT / ("" if lang == "ja" else lang) / SECTION / "index.html"
        probe = (target.parent / want).resolve()
        if not probe.is_file():
            raise SystemExit(
                "ERROR: build_alpha: %s references %s, which resolves to %s -- "
                "no such file. The hero mark would 404." % (lang, want, probe))
        write_page(lang, SECTION, html)
    print("build_alpha: %d language(s), notice for %s (%s), %d modules, hero mark %s"
          % (len(langs), f["version"], f["date"], f["modules"], MARK["file"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
