#!/usr/bin/env python3
"""Builds cherry-controls/index.html -- how to fly Cherry's aircraft and sail its ships, in every language.

Owner (2026-09-23, IROHA, verbatim):

    飛行機と戦闘機の操作方法と船の操作方法を教えてください
    Corvus Webに公開してください

--------------------------------------------------------------------------
Why a page of its own, and not a section of /cherry/
--------------------------------------------------------------------------
The brand page says two things and nothing else (build_cherry.py, by the owner's
2026-09-10 word: 「ブランドの強さを説明するだけで良いです」「書くならプレミア感がある
文章を添えるだけです」), and its docstring keeps play guides off it. So the controls live
here, in the Cherry colours, and the brand page carries one quiet link to them (outside its
release block, whose single link check_cherry_release.py counts).

It sits at the top level (cherry-controls/, like known-issues/), not at cherry/controls/:
check_lang_switcher.py discovers the sections it audits one directory deep, and a page it
cannot see is a page no gate can fail for.

--------------------------------------------------------------------------
Where every fact comes from -- the mod's code, not memory
--------------------------------------------------------------------------
Read from the Cherry source that built the release in downloads/ (CONTROLS_FOR), and
checked claim by claim against that code by two independent reviews before publishing:
  * aircraft keys: client/aircraft/AircraftInput.java (R flaps, Z afterburner/reverse, U gear,
    Y doors, K hook, M next target, N radar mode, J fire, Left Alt free look, the arrows); W/S
    throttle, A/D rudder and Space brakes are the game's own movement keys; the radar cone,
    range and dwell: common/weapon/RadarLock; leaving, doors, fuel, loading: AircraftEntity;
  * ship keys: client/naval/VesselHelmInput.java (, . = - ; '), VesselStationInput.java (H),
    VesselGunneryInput.java, VesselChartScreen.java; the door rule: LargeVesselEntity;
  * item names and the two key categories: the mod's lang files. It ships en_us and ja_jp
    only, so every other language shows them in English in game -- and they are printed in
    English here, marked lang="en";
  * the menu path, Space, Left Alt / Left Option, Sneak, Movement and the hotbar: vanilla
    26.3's own lang files, per language, so the page names them the way the game does. On a
    Mac the game names Left Alt "Left Option" (InputQuirks.keyboardTranslationKey), so both
    are given.
  * 26.3 binds keys by SDL scancode -- a place on the keyboard -- and names each one by the
    player's layout (InputConstants$Type: SDL_GetKeyName(SDL_GetKeyFromScancode(...))). The
    page names keys by their place on a US keyboard and says so. 1.1.2's page added the two JIS
    keys that differ ([=] is the ^ key, ['] the : key); 1.1.3 names neither (its keys are
    W A S D, Left Alt, H, Y and F5, which sit in the same places on a JIS keyboard).
  * 2026-09-23, 1.1.3 (the owner: make the controls very easy, no fixed view, anyone can fly
    and sail -- notes 14.79): the aircraft fly where you look (W/S throttle, left-click
    missiles, Left Alt to look around, everything else automatic) and the ships answer to
    W/A/S/D at the wheel (the stop detent, A/D with heading hold, Sneak or H to leave, Y for
    the ferry's doors, the warship's guns from the wheel). Every fact is read from 1.1.3's
    code and proven by a gate in the release suite (server GameTests and the FLIGHT, HELM
    and STATIONS client groups).

CONTROLS_FOR is the release whose code this was read from. A newer Cherry zip in downloads/
stops the build until the controls are read again against the new code and it is moved,
the way build_cherry.py's COPY_FOR guards the release line.

Markup inside the copy: [K] is a key cap (<kbd>). [SPACE], [LALT] and [LOPT] are the game's
own names for Space, Left Alt and Left Option in that language (KEYCAP). A pair of angle
brackets marks English text (lang="en"). Every language must carry exactly the English
shape, and the same keys in the same places (main() refuses anything else) -- so a
translation cannot move a key, drop one, or add one.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from site_common import (  # noqa: E402
    ROOT, asset_root_prefix, available_langs, esc, page, write_page,
)

SECTION = "cherry-controls/"
BRAND_SECTION = "cherry/"
# 1.1.4 changed no key (only the sound managers, their tests, the version and the README; 525d6f5..1.1.4): the copy stays true
# 1.2.0 changed no aircraft or ship key: FlightInput's one change is the rocket's launch key on the pad, which now unfolds the
# navigation console, and this page covers aircraft and ships only (1.1.4..1.2.0 on the Cherry branch)
# 1.2.1 changed no aircraft or ship key (AircraftInput, VesselHelmInput, VesselStationInput, VesselGunneryInput and VesselChartScreen are byte-identical
# between the V1.2.0 final fixes 4d0b3fc and 1.2.1; its new items are not aircraft or ships): the copy stays true
CONTROLS_FOR = "1.2.1"
RELEASE_RE = re.compile(r"^Cherry_MODs_v(?P<ver>\d+(?:\.\d+)*)\+mc(?P<mc>\d+(?:\.\d+)*)\.zip$")

# The game's own names for the keys whose names are translated (vanilla 26.3 lang files).
KEYCAP = {
    "en": {"SPACE": "Space", "LALT": "Left Alt", "LOPT": "Left Option"},
    "ja": {"SPACE": "Space", "LALT": "左Alt", "LOPT": "左Option"},
    "es": {"SPACE": "Espacio", "LALT": "Alt izdo.", "LOPT": "Opción izq."},
    "fr": {"SPACE": "Espace", "LALT": "Alt", "LOPT": "Option gauche"},
    "zh": {"SPACE": "空格", "LALT": "左Alt", "LOPT": "左Option"},
    "ko": {"SPACE": "Space", "LALT": "왼쪽 Alt", "LOPT": "왼쪽 Option"},
    "pt-br": {"SPACE": "Espaço", "LALT": "Alt", "LOPT": "Option esq."},
    "it": {"SPACE": "Spazio", "LALT": "Alt", "LOPT": "Opz sinistro"},
    "ar": {"SPACE": "Space", "LALT": "Alt الأيسر", "LOPT": "Left Option"},
    "ru": {"SPACE": "Пробел", "LALT": "Alt слева", "LOPT": "Option слева"},
    "id": {"SPACE": "Spasi", "LALT": "Alt Kiri", "LOPT": "Option Kiri"},
    "de": {"SPACE": "Leertaste", "LALT": "Alt", "LOPT": "Wahltaste links"},
    "tr": {"SPACE": "Boşluk", "LALT": "Sol Alt", "LOPT": "Sol Option"},
}
# Every key the page may name. Anything else inside [...] stops the build.
KNOWN_KEYS = {"A", "D", "F5", "H", "LALT", "LOPT", "S", "W", "Y"}
# The keys the game's "Movement" category holds and the mod's own mappings; the English copy
# must name every one of them (a binding missing from the page stops the build).
MOD_KEYS = {"H", "LALT", "Y"}
MOVEMENT_KEYS = {"A", "D", "S", "W"}

# The game's own name for its movement key category (key.category.minecraft.movement).
MOVEMENT = {
    "ja": "移動", "en": "Movement", "es": "Movimiento", "fr": "Mouvements", "zh": "移动",
    "ko": "이동", "pt-br": "Movimentos", "it": "Movimento", "ar": "حركة", "ru": "Движение",
    "id": "Pergerakan", "de": "Bewegung", "tr": "Hareket",
}

# The in-game way to the key bindings, and the two Cherry key categories, as each language shows them.
PATH = {
    "ja": ("設定", "操作設定", "キー割り当て"),
    "en": ("Options", "Controls", "Key Binds"),
    "es": ("Opciones", "Controles", "Teclas"),
    "fr": ("Options", "Contrôles", "Assignation des touches"),
    "zh": ("选项", "按键控制", "按键绑定"),
    "ko": ("설정", "조작", "키 지정"),
    "pt-br": ("Opções", "Controles", "Atalhos"),
    "it": ("Opzioni", "Comandi", "Assegnazione dei tasti"),
    "ar": ("الخيارات", "التحكم", "روابط المفاتيح"),
    "ru": ("Настройки", "Управление", "Назначение клавиш"),
    "id": ("Opsi", "Kendali", "Tombol Pintas"),
    "de": ("Optionen", "Steuerung", "Tastenbelegung"),
    "tr": ("Ayarlar", "Kontroller", "Tuş Atamaları"),
}
CATEGORIES = {"ja": ("Cherry の飛行", "Cherry 艦の持ち場")}
CATEGORIES_EN = ("⟨Cherry Flight⟩", "⟨Cherry Ship Stations⟩")

# Each language: the heading, then the two cards. A card is a title, facts, a key table (action, how)
# and titled lists. Every language must have exactly the English shape, with the same keys in the same
# places (main() refuses anything else). Where 1.1.2 does not do what a key's name says, the copy says
# what it does and names the version -- and main() refuses a version here other than CONTROLS_FOR, so a
# line about one release cannot survive onto the next one's page.
CONTROLS = {
    "en": {
        "heading": "Controls",
        "air": {
            "title": "Aircraft — the Stratos-900 airliner and the Aegis-X fighter",
            "facts": [
                "Place: use the item on the ground where she has room; she stands there facing the way you look.",
                "Board: right-click the middle of the aircraft. The first aboard flies her (the Stratos-900 seats 18). Leave with Sneak; you cannot leave in the air.",
                "Fuel: on the ground, use a Propellant Canister on her, one per use.",
                "Recover: stopped on the ground with nobody aboard, hold Sneak and right-click her with an empty hand.",
                "When you board, and whenever she is parked, a short guide to these keys shows above the middle of the screen.",
            ],
            "keys": [
                ["Steer", "Look where you want to go: she banks, turns, climbs and dives towards it by herself."],
                ["Throttle", "[W] more, [S] less; the lever stays where you leave it. Full throttle lights the Aegis-X afterburner. On the ground, [S] at zero holds her on the brakes."],
                ["Look around", "Hold [LALT] (on a Mac, [LOPT]): she keeps her course while you look about."],
                ["View", "Yours to choose: it never locks to first person or tilts with the aircraft. [F5] changes it at any time."],
                ["Missiles (Aegis-X)", "Left-click fires at the target the radar has locked."],
                ["By themselves", "Flaps, landing gear, wheel brakes, reverse thrust, afterburner, canopy and rear ramp, and the arresting hook."],
            ],
            "lists": [
                ["Take-off and landing", [
                    "Take-off: hold [W] to full throttle and look a little above the horizon. At take-off speed she raises her nose and lifts off, then raises her gear.",
                    "Landing: look at the runway a little below the horizon. She lowers her gear, holds her approach speed and flares just before touchdown. Once down, hold [S] to bring the throttle to zero: she brakes, and reverses if she can. To go around, look up and hold [W].",
                ]],
                ["Aegis-X weapons", [
                    "Load: use a Cherry Guided Missile on an Aegis-X on the ground, one per use. She carries two, and a new one comes loaded.",
                    "The radar picks the target by itself: it watches 30° around the nose out to 512 blocks, in the air and on the ground, and locks the contact nearest the nose once it has held it for about 1.5 seconds.",
                    "Left-click fires a missile at the locked target: in the air only, at most one a second.",
                ]],
            ],
        },
        "sea": {
            "title": "Ships — the Leviathan-Class ferry and the Dreadnought-Class destroyer",
            "facts": [
                "Place: look at the water from the shore or a boat and use the item. She floats with her stern just past the spot you look at and her bow the way you look, where the water is at least as deep as her draught along her whole length (3.5 m for the Leviathan-Class, 4 m for the Dreadnought-Class).",
                "Walk her decks and interiors. Standing at a station shows the key that takes it: [H]. Press [H] again to leave; at the wheel, Sneak leaves too. The chart table opens a screen instead: close it to leave.",
                "Recover: stopped, with nobody else aboard, stand amidships (on the Dreadnought-Class, in the CIC), hold Sneak and right-click at your feet with an empty hand.",
            ],
            "keys": [
                ["Engine", "[W] ahead, [S] back towards stop. Holding [S] from ahead stops at zero; press it again to go astern. The engine stays where you leave it."],
                ["Rudder", "Hold [A] for port (left), [D] for starboard (right). Let go and the wheel centres and she holds the heading she has."],
                ["At the wheel", "[W] [A] [S] [D] steer the ship instead of walking you. The instruments show above the hotbar, with a short guide to the keys when you take the wheel."],
            ],
            "lists": [
                ["Chart table", [
                    "At the chart table, [H] opens the chart. Left-click adds a waypoint; the mouse wheel zooms.",
                    "Its buttons switch the autopilot on or off and clear the route. A leg across land or shallow water is refused. The autopilot only steers: set the engine ahead at the wheel, and it stops the engine at the last waypoint.",
                ]],
                ["Doors (Leviathan-Class)", [
                    "Stopped (under 0.3 m/s, engine at 0) and at the wheel, [Y] opens and closes the bow visor and the ramps.",
                    "The engine gives no thrust until the doors are shut. The ramps can be walked on once fully down.",
                ]],
                ["Guns (Dreadnought-Class)", [
                    "At the wheel, with nobody at the gunnery console, the guns are yours: both triple turrets train on the point you look at. Left-click fires a salvo, every 10 seconds; right-click launches the VLS at the target the radar has locked, once its hatch is open.",
                    "A gunner who takes the gunnery console in the CIC takes the guns over; they come back to the wheel when the gunner leaves. Sonar: ships, boats, swimmers and submerged contacts on a sweeping scope.",
                ]],
            ],
        },
    },
    "ja": {
        "heading": "操作方法",
        "air": {
            "title": "飛行機 —— 旅客機 Stratos-900 と戦闘機 Aegis-X",
            "facts": [
                "置く: 周りに余地のある地面にアイテムを使うと、見ている向きに機首を向けて止まります。",
                "乗る: 機体の真ん中を右クリック。最初に乗った人が操縦します(Stratos-900 は 18 席)。降りるのはスニークで、空中では降りられません。",
                "燃料: 地上で機体に「推進剤キャニスター」を使います。1 回に 1 缶です。",
                "回収: 地上で止まっていて誰も乗っていないとき、スニークしながら素手で右クリックします。",
                "乗ったとき、また地上で止まっている間は、画面の中央の上に、ここのキーの短い案内が出ます。",
            ],
            "keys": [
                ["操縦", "行きたい方を見るだけです。機体はひとりでに傾いて、その方へ回り、上り、下ります。"],
                ["推力", "[W] で上げる、[S] で下げる。レバーは離した位置に留まります。推力いっぱいで Aegis-X のアフターバーナーが点きます。地上で推力 0 のまま [S] を押すと、ブレーキで止まります。"],
                ["見回す", "[LALT](Mac では [LOPT])を押している間。機体は向きを保ったまま、頭だけが回ります。"],
                ["視点", "自由です。一人称に固定されず、機体と一緒に傾きません。[F5] でいつでも切り替えられます。"],
                ["ミサイル(Aegis-X)", "左クリックで、レーダーがロックした目標へ撃ちます。"],
                ["自動", "フラップ、脚、車輪のブレーキ、逆推力、アフターバーナー、キャノピーと後部ランプ、着艦フック。"],
            ],
            "lists": [
                ["離陸と着陸", [
                    "離陸: [W] で推力いっぱいにして、地平線の少し上を見ます。離陸の速さになると機首を上げて浮き上がり、脚をしまいます。",
                    "着陸: 地平線の少し下に滑走路を見ます。脚を出し、進入の速さを保ち、接地の直前に機首を起こします。接地したら [S] を押し続けて推力を 0 にすると、ブレーキを掛け、逆推力のある機体は逆推力も使います。やり直すときは、上を見て [W] を押します。",
                ]],
                ["Aegis-X の兵装", [
                    "積む: 地上の Aegis-X に「Cherry 誘導ミサイル」を使うと、1 回に 1 発ずつ積めます。2 発まで積め、新しい機体は 2 発積んだ状態で出てきます。",
                    "目標はレーダーが自分で選びます。機首の前 30° 以内・512 ブロックまでを、空も地上も見て、機首にいちばん近い相手を約 1.5 秒捉え続けるとロックします。",
                    "左クリックで、ロックした目標へミサイルを撃ちます。空中でだけ、1 秒に 1 発までです。",
                ]],
            ],
        },
        "sea": {
            "title": "艦 —— Leviathan級フェリーと Dreadnought級駆逐艦",
            "facts": [
                "置く: 岸やボートから水面を見てアイテムを使います。見ている所のすぐ先に艦尾を置き、見ている向きに船首を向けて浮かびます。船体の長さにわたって喫水以上の深さ(Leviathan級 3.5 m、Dreadnought級 4 m)が要ります。",
                "甲板や艦内は歩けます。持ち場に立つと、就くキー [H] が画面に出ます。もう一度 [H] で離れます。舵輪ではスニークでも離れます。海図台は画面が開くので、閉じると離れます。",
                "回収: 止まっていて、ほかに誰も乗っていないとき、艦の真ん中(Dreadnought級は CIC の中)に立ち、スニークしながら素手で足もとを右クリックします。",
            ],
            "keys": [
                ["機関", "[W] で前進、[S] で停止の側へ。前進から [S] を押し続けると停止(0)で止まり、押し直すと後進に入ります。機関は離した位置に留まります。"],
                ["舵", "[A] を押している間は取舵(左)、[D] は面舵(右)。離すと舵は中央に戻り、そのときの方位を保ちます。"],
                ["舵輪", "[W] [A] [S] [D] は歩く代わりに艦を動かします。計器はホットバーの上に出て、舵輪に就いたときは短いキーの案内も出ます。"],
            ],
            "lists": [
                ["海図台", [
                    "海図台で [H] を押すと海図が開きます。左クリックで航路の点を足し、マウスホイールで縮尺を変えます。",
                    "ボタンで自動巡航の入/切と航路の消去。陸や浅瀬を横切る区間は断られます。自動巡航は舵を取るだけなので、機関は舵輪で前進にしておきます。最後の点で機関を止めます。",
                ]],
                ["扉(Leviathan級)", [
                    "止まっていて(0.3 m/s 未満、機関 0)舵輪に就いているとき、[Y] でバウバイザーとランプを開け閉めします。",
                    "扉が閉じきるまで機関は推力を出しません。ランプは下りきると歩けます。",
                ]],
                ["砲(Dreadnought級)", [
                    "砲術席に誰もいなければ、舵輪で砲を扱えます。3 連装砲塔 2 基が、見ている点へ向きます。左クリックで斉射(10 秒ごと)、右クリックで、レーダーがロックした目標へ VLS(ハッチが開ききってから)。",
                    "CIC の砲術席に砲術士が就くと、砲はその人へ移り、離れると舵輪へ戻ります。ソナー席: 周りの艦、ボート、泳いでいる者、水中の相手を、回る走査の画面に映します。",
                ]],
            ],
        },
    },
    "es": {
        "heading": "Controles",
        "air": {
            "title": "Aeronaves: el avión de pasajeros Stratos-900 y el caza Aegis-X",
            "facts": [
                "Colocar: usa el objeto en el suelo, donde tenga espacio; queda ahí mirando hacia donde miras.",
                "Subir: haz clic derecho en el centro de la aeronave. Quien sube primero la pilota (el Stratos-900 tiene 18 asientos). Para bajar, «Agacharse»; en el aire no se puede.",
                "Combustible: en tierra, usa un ⟨Propellant Canister⟩ sobre ella, uno por uso.",
                "Recuperar: detenida en tierra y sin nadie a bordo, mantén «Agacharse» y haz clic derecho con la mano vacía.",
                "Al subir, y siempre que esté detenida en tierra, aparece por encima del centro de la pantalla una breve guía de estas teclas.",
            ],
            "keys": [
                ["Dirigir", "Mira hacia donde quieres ir: la aeronave alabea, vira, sube y baja hacia allí por sí sola."],
                ["Potencia", "[W] más, [S] menos; la palanca de gases se queda donde la dejas. La potencia máxima enciende el posquemador del Aegis-X. En tierra, [S] con la potencia a cero la mantiene frenada."],
                ["Mirar alrededor", "Mantén [LALT] (en Mac, [LOPT]): la aeronave sigue su rumbo mientras miras a tu alrededor."],
                ["Vista", "Tú la eliges: nunca se bloquea en primera persona ni se inclina con la aeronave. [F5] la cambia en cualquier momento."],
                ["Misiles (Aegis-X)", "El clic izquierdo dispara al objetivo que el radar ha fijado."],
                ["Automáticos", "Flaps, tren de aterrizaje, frenos de las ruedas, inversión de empuje, posquemador, cubierta de la cabina y rampa trasera, y el gancho de apontaje."],
            ],
            "lists": [
                ["Despegue y aterrizaje", [
                    "Despegue: mantén [W] hasta la potencia máxima y mira un poco por encima del horizonte. Al alcanzar la velocidad de despegue, la aeronave levanta el morro y se eleva, y luego recoge el tren.",
                    "Aterrizaje: mira la pista un poco por debajo del horizonte. La aeronave baja el tren, mantiene la velocidad de aproximación y levanta el morro justo antes de tocar tierra. Ya en tierra, mantén [S] para llevar la potencia a cero: frena, e invierte el empuje si puede. Para abortar el aterrizaje, mira hacia arriba y mantén [W].",
                ]],
                ["Armamento del Aegis-X", [
                    "Cargar: usa un ⟨Cherry Guided Missile⟩ sobre un Aegis-X en tierra, uno por uso. Lleva dos, y uno nuevo llega cargado.",
                    "El radar elige el objetivo por sí solo: vigila 30° alrededor del morro hasta 512 bloques, en el aire y en tierra, y fija el contacto más cercano al morro tras mantenerlo unos 1,5 segundos.",
                    "El clic izquierdo dispara un misil al objetivo fijado: solo en el aire, como mucho uno por segundo.",
                ]],
            ],
        },
        "sea": {
            "title": "Buques: el transbordador clase Leviathan y el destructor clase Dreadnought",
            "facts": [
                "Colocar: desde la orilla o un bote, mira el agua y usa el objeto. El buque flota con la popa justo más allá del punto que miras y la proa hacia donde miras; el agua debe ser, a lo largo de toda su eslora, al menos tan profunda como su calado (3,5 m el clase Leviathan, 4 m el clase Dreadnought).",
                "Recorre sus cubiertas e interiores. Al ponerte en un puesto aparece la tecla para ocuparlo: [H]. Pulsa [H] otra vez para dejarlo; al timón, también puedes dejarlo con «Agacharse». La mesa de cartas abre una pantalla: ciérrala para dejarla.",
                "Recuperar: con el buque detenido y sin nadie más a bordo, ponte en medio del buque (en el clase Dreadnought, en el CIC), mantén «Agacharse» y haz clic derecho a tus pies con la mano vacía.",
            ],
            "keys": [
                ["Máquina", "[W] avante, [S] de vuelta hacia parada. Si mantienes [S] desde avante, la máquina se para en cero; vuelve a pulsarla para ir atrás. La máquina se queda donde la dejas."],
                ["Timón", "Mantén [A] para babor (izquierda) y [D] para estribor (derecha). Al soltar, la rueda se centra y el buque mantiene el rumbo que lleva."],
                ["Al timón", "[W] [A] [S] [D] gobiernan el buque en lugar de moverte a ti. Los instrumentos aparecen sobre la barra de acceso rápido, con una breve guía de las teclas al tomar el timón."],
            ],
            "lists": [
                ["Mesa de cartas", [
                    "En la mesa de cartas, [H] abre la carta. El clic izquierdo añade un punto de ruta; la rueda del ratón cambia la escala.",
                    "Sus botones conectan o desconectan el piloto automático y borran la ruta. Un tramo que cruza tierra o aguas someras se rechaza. El piloto automático solo gobierna: pon la máquina avante al timón; en el último punto la para.",
                ]],
                ["Puertas (clase Leviathan)", [
                    "Detenido (menos de 0,3 m/s, máquina en 0) y al timón, [Y] abre y cierra la visera de proa y las rampas.",
                    "La máquina no da empuje hasta que las puertas están cerradas. Las rampas se pueden pisar cuando han bajado del todo.",
                ]],
                ["Cañones (clase Dreadnought)", [
                    "Al timón, sin nadie en el puesto de artillería, los cañones son tuyos: las dos torres triples apuntan al punto que miras. El clic izquierdo dispara una salva, cada 10 segundos; el derecho lanza el VLS contra el objetivo fijado por el radar, una vez abierta su escotilla.",
                    "Un artillero que ocupe el puesto de artillería del CIC toma el mando de los cañones; vuelven al timón cuando se va. Sonar: buques, botes, nadadores y contactos sumergidos en una pantalla de barrido.",
                ]],
            ],
        },
    },
    "fr": {
        "heading": "Commandes",
        "air": {
            "title": "Avions : l’avion de ligne Stratos-900 et le chasseur Aegis-X",
            "facts": [
                "Poser : utilisez l’objet sur le sol, là où il a la place ; l’avion s’y pose face à la direction de votre regard.",
                "Monter : clic droit sur le milieu de l’avion. Le premier à monter pilote (le Stratos-900 a 18 places). Pour descendre, « S’accroupir » ; impossible en vol.",
                "Carburant : au sol, utilisez un ⟨Propellant Canister⟩ sur l’avion, un par utilisation.",
                "Récupérer : à l’arrêt au sol et sans personne à bord, maintenez « S’accroupir » et faites un clic droit à main nue.",
                "Quand vous montez à bord, et chaque fois que l’avion est à l’arrêt au sol, un court rappel de ces touches s’affiche au-dessus du centre de l’écran.",
            ],
            "keys": [
                ["Diriger", "Regardez là où vous voulez aller : l’avion s’incline, vire, monte et descend de lui-même dans cette direction."],
                ["Poussée", "[W] plus, [S] moins ; la manette reste où vous la laissez. La pleine poussée allume la postcombustion de l’Aegis-X. Au sol, [S] à zéro maintient l’avion sur ses freins."],
                ["Regarder autour", "Maintenez [LALT] (sur Mac, [LOPT]) : l’avion garde son cap pendant que vous regardez autour de vous."],
                ["Vue", "À vous de choisir : elle ne se bloque jamais en première personne et ne s’incline pas avec l’avion. [F5] la change à tout moment."],
                ["Missiles (Aegis-X)", "Le clic gauche tire sur la cible que le radar a verrouillée."],
                ["Automatiques", "Volets, train d’atterrissage, freins de roues, inversion de poussée, postcombustion, verrière et rampe arrière, et crosse d’appontage."],
            ],
            "lists": [
                ["Décollage et atterrissage", [
                    "Décollage : maintenez [W] jusqu’à la pleine poussée et regardez un peu au-dessus de l’horizon. À la vitesse de décollage, l’avion lève le nez et quitte le sol, puis rentre son train.",
                    "Atterrissage : regardez la piste un peu sous l’horizon. L’avion sort son train, tient sa vitesse d’approche et fait l’arrondi juste avant le toucher. Une fois au sol, maintenez [S] pour ramener la poussée à zéro : il freine, et inverse la poussée s’il le peut. Pour remettre les gaz, regardez vers le haut et maintenez [W].",
                ]],
                ["Armement de l’Aegis-X", [
                    "Charger : utilisez un ⟨Cherry Guided Missile⟩ sur un Aegis-X au sol, un par utilisation. Il en emporte deux, et un neuf arrive chargé.",
                    "Le radar choisit la cible de lui-même : il surveille 30° autour du nez jusqu’à 512 blocs, en l’air comme au sol, et verrouille le contact le plus proche du nez après l’avoir gardé environ 1,5 seconde.",
                    "Le clic gauche tire un missile sur la cible verrouillée : en vol seulement, au plus un par seconde.",
                ]],
            ],
        },
        "sea": {
            "title": "Navires : le transbordeur classe Leviathan et le destroyer classe Dreadnought",
            "facts": [
                "Poser : depuis le rivage ou un bateau, regardez l’eau et utilisez l’objet. Le navire flotte la poupe juste au-delà du point que vous regardez et l’étrave dans la direction de votre regard ; l’eau doit y être, sur toute sa longueur, au moins aussi profonde que son tirant d’eau (3,5 m pour la classe Leviathan, 4 m pour la classe Dreadnought).",
                "Parcourez ses ponts et ses intérieurs. À un poste, la touche pour le prendre s’affiche : [H]. Appuyez de nouveau sur [H] pour le quitter ; à la barre, « S’accroupir » permet aussi de la quitter. La table à cartes ouvre un écran : fermez-le pour la quitter.",
                "Récupérer : à l’arrêt et sans personne d’autre à bord, placez-vous au milieu du navire (sur la classe Dreadnought, dans le CIC), maintenez « S’accroupir » et faites un clic droit à vos pieds à main nue.",
            ],
            "keys": [
                ["Machine", "[W] en avant, [S] revient vers l’arrêt. Si vous maintenez [S] en marche avant, la machine s’arrête à zéro ; appuyez de nouveau pour passer en marche arrière. La manette reste où vous la laissez."],
                ["Barre", "Maintenez [A] pour bâbord (gauche), [D] pour tribord (droite). Relâchez : la roue revient au centre et le navire tient son cap actuel."],
                ["À la barre", "[W] [A] [S] [D] dirigent le navire au lieu de vous faire marcher. Les instruments s’affichent au-dessus de la barre d’action, avec un court rappel des touches quand vous prenez la barre."],
            ],
            "lists": [
                ["Table à cartes", [
                    "À la table à cartes, [H] ouvre la carte. Le clic gauche ajoute un point de route ; la molette change l’échelle.",
                    "Ses boutons engagent ou coupent le pilote automatique et effacent la route. Un tronçon qui traverse la terre ou des hauts-fonds est refusé. Le pilote automatique ne fait que barrer : mettez la machine en avant à la barre ; il l’arrête au dernier point.",
                ]],
                ["Portes (classe Leviathan)", [
                    "À l’arrêt (moins de 0,3 m/s, machine à 0) et à la barre, [Y] ouvre et ferme la visière d’étrave et les rampes.",
                    "La machine ne pousse pas tant que les portes ne sont pas fermées. On peut marcher sur les rampes une fois entièrement abaissées.",
                ]],
                ["Canons (classe Dreadnought)", [
                    "À la barre, sans personne au poste de tir, les canons sont à vous : les deux tourelles triples pointent vers l’endroit que vous regardez. Le clic gauche tire une salve, toutes les 10 secondes ; le clic droit lance le VLS sur la cible verrouillée par le radar, une fois sa trappe ouverte.",
                    "Un tireur qui prend le poste de tir du CIC reprend les canons ; ils reviennent à la barre quand il le quitte. Sonar : navires, embarcations, nageurs et contacts immergés sur un écran à balayage.",
                ]],
            ],
        },
    },
    "zh": {
        "heading": "操作方法",
        "air": {
            "title": "飞机：客机 Stratos-900 与战斗机 Aegis-X",
            "facts": [
                "放置：在有足够空间的地面上使用该物品，飞机会停在那里，机头朝向你注视的方向。",
                "登机：右键点击飞机中部。第一个登机的人驾驶（Stratos-900 有 18 个座位）。按“潜行”离机；在空中无法离机。",
                "燃料：在地面上对飞机使用 ⟨Propellant Canister⟩，每次一罐。",
                "回收：飞机停在地面且无人乘坐时，按住“潜行”并空手右键点击。",
                "登机时，以及飞机停在地面期间，屏幕中央上方会显示这些按键的简短说明。",
            ],
            "keys": [
                ["转向", "看向你想去的方向：飞机会自行倾斜、转弯、爬升或俯冲，飞向那里。"],
                ["推力", "[W] 增加，[S] 减少；油门杆停在你松开的位置。满油门时 Aegis-X 会点燃加力。在地面上，推力为零时按 [S] 会用刹车停住飞机。"],
                ["环顾四周", "按住 [LALT]（Mac 上为 [LOPT]）：飞机保持航向，你可以四处张望。"],
                ["视角", "由你选择：视角不会锁定为第一人称，也不会随飞机倾斜。[F5] 随时可以切换。"],
                ["导弹（Aegis-X）", "左键向雷达锁定的目标开火。"],
                ["自动", "襟翼、起落架、机轮刹车、反推、加力、座舱盖与尾部跳板，以及着舰钩。"],
            ],
            "lists": [
                ["起飞与降落", [
                    "起飞：按住 [W] 推满油门，并看向地平线稍上方。达到起飞速度后，飞机会抬起机头离地，随后收起起落架。",
                    "降落：看向地平线稍下方的跑道。飞机会放下起落架、保持进近速度，并在接地前拉平。接地后按住 [S] 把油门收到零：飞机会刹车，能反推的还会反推。要复飞，请抬头看并按住 [W]。",
                ]],
                ["Aegis-X 的武器", [
                    "装填：对地面上的 Aegis-X 使用 ⟨Cherry Guided Missile⟩，每次装一枚。最多两枚，新飞机自带两枚。",
                    "雷达会自行选择目标：它监视机头周围 30° 以内、512 格以内的空中与地面，持续捕捉离机头最近的目标约 1.5 秒后将其锁定。",
                    "左键向锁定的目标发射导弹：仅限空中，每秒最多一枚。",
                ]],
            ],
        },
        "sea": {
            "title": "舰船：Leviathan 级渡轮与 Dreadnought 级驱逐舰",
            "facts": [
                "放置：从岸边或船上看向水面并使用该物品。舰船会浮起，船尾刚好越过你注视的位置，船首朝向你注视的方向；整个船身长度上的水深都要不小于吃水（Leviathan 级 3.5 m，Dreadnought 级 4 m）。",
                "可以在甲板和舱内行走。站在岗位处，屏幕上会显示就位的按键：[H]。再按一次 [H] 离开；在舵轮处，按“潜行”也能离开。海图桌则会打开一个界面：关闭它即离开。",
                "回收：舰船停下且船上没有其他人时，站在船身中部（Dreadnought 级则在 CIC 内），按住“潜行”并空手右键点击脚下。",
            ],
            "keys": [
                ["主机", "[W] 前进，[S] 向停车方向回退。前进时按住 [S] 会停在零；再按一次进入后退。主机停在你松开的位置。"],
                ["舵", "按住 [A] 转向左舷（左），[D] 转向右舷（右）。松开后舵轮回中，舰船保持当前航向。"],
                ["在舵轮处", "[W] [A] [S] [D] 改为操纵舰船，而不是让你行走。仪表显示在快捷栏上方；在舵轮就位时，还会显示按键的简短说明。"],
            ],
            "lists": [
                ["海图桌", [
                    "在海图桌按 [H] 打开海图。左键添加航路点，鼠标滚轮缩放。",
                    "按钮可开关自动航行、清除航线。穿越陆地或浅水的航段会被拒绝。自动航行只负责操舵：请先在舵轮处把主机设为前进；到达最后一个航路点时它会停车。",
                ]],
                ["舱门（Leviathan 级）", [
                    "停船（低于 0.3 m/s、主机为 0）并在舵轮岗位时，按 [Y] 开关艏门和跳板。",
                    "舱门完全关闭前主机不会产生推力。跳板完全放下后可以在上面行走。",
                ]],
                ["火炮（Dreadnought 级）", [
                    "在舵轮处，若火炮岗位无人，火炮就归你操纵：两座三联装炮塔指向你注视的位置。左键齐射，每 10 秒一次；右键在舱盖打开后，向雷达锁定的目标发射垂直发射系统。",
                    "炮手在 CIC 的火炮岗位就位后会接管火炮；炮手离开后，火炮交还舵轮。声呐：在扫描屏上显示舰船、小船、游泳者和水下目标。",
                ]],
            ],
        },
    },
    "ko": {
        "heading": "조작 방법",
        "air": {
            "title": "항공기: 여객기 Stratos-900과 전투기 Aegis-X",
            "facts": [
                "놓기: 공간이 충분한 땅에 아이템을 사용하면 그 자리에 바라보는 방향으로 기수를 두고 섭니다.",
                "탑승: 기체의 한가운데를 오른쪽 클릭합니다. 먼저 탄 사람이 조종합니다(Stratos-900은 18석). 내릴 때는 ‘웅크리기’를 누르며, 공중에서는 내릴 수 없습니다.",
                "연료: 지상에서 기체에 ⟨Propellant Canister⟩를 사용합니다. 한 번에 하나씩입니다.",
                "회수: 지상에 멈춰 있고 아무도 타지 않았을 때, ‘웅크리기’를 누른 채 맨손으로 오른쪽 클릭합니다.",
                "탑승할 때와 지상에 멈춰 있는 동안에는 화면 가운데 위에 이 키들의 짧은 안내가 나옵니다.",
            ],
            "keys": [
                ["조종", "가고 싶은 쪽을 보세요. 기체가 저절로 기울고, 돌고, 오르고, 내려가며 그쪽으로 향합니다."],
                ["추력", "[W] 올림, [S] 내림. 레버는 놓은 자리에 머뭅니다. 추력을 최대로 하면 Aegis-X의 애프터버너가 켜집니다. 지상에서 추력 0일 때 [S]를 누르면 브레이크로 기체를 세워 둡니다."],
                ["둘러보기", "[LALT](Mac에서는 [LOPT])를 누르고 있는 동안, 기체는 방향을 유지하고 시선만 돌아갑니다."],
                ["시점", "원하는 대로 고릅니다. 1인칭으로 고정되지 않고, 기체와 함께 기울지도 않습니다. [F5]로 언제든 바꿀 수 있습니다."],
                ["미사일(Aegis-X)", "왼쪽 클릭으로 레이더가 고정한 목표에 발사합니다."],
                ["자동", "플랩, 착륙 장치, 바퀴 브레이크, 역추력, 애프터버너, 캐노피와 후방 램프, 착함 훅."],
            ],
            "lists": [
                ["이륙과 착륙", [
                    "이륙: [W]를 누르고 있어 추력을 최대로 하고, 지평선보다 조금 위를 봅니다. 이륙 속도가 되면 기수를 들어 떠오르고, 이어서 착륙 장치를 올립니다.",
                    "착륙: 지평선보다 조금 아래에 활주로를 봅니다. 착륙 장치를 내리고, 접근 속도를 유지하며, 접지 직전에 기수를 듭니다. 접지한 뒤 [S]를 누르고 있어 추력을 0으로 하면 브레이크를 걸고, 역추력이 있는 기체는 역추력도 씁니다. 복행하려면 위를 보고 [W]를 누르고 있습니다.",
                ]],
                ["Aegis-X 무장", [
                    "장전: 지상의 Aegis-X에 ⟨Cherry Guided Missile⟩을 사용하면 한 번에 한 발씩 실립니다. 두 발까지 실리며, 새 기체는 두 발을 실은 채 나옵니다.",
                    "목표는 레이더가 스스로 고릅니다. 기수 주위 30° 이내, 512블록까지를 공중과 지상 모두 살피고, 기수에 가장 가까운 상대를 약 1.5초 동안 잡아 두면 고정합니다.",
                    "왼쪽 클릭으로 고정한 목표에 미사일을 발사합니다. 공중에서만, 1초에 한 발까지입니다.",
                ]],
            ],
        },
        "sea": {
            "title": "함정: Leviathan급 카페리와 Dreadnought급 구축함",
            "facts": [
                "놓기: 물가나 보트에서 수면을 보고 아이템을 사용합니다. 바라보는 지점 바로 너머에 선미를 두고, 바라보는 방향으로 선수를 두고 뜹니다. 선체 길이 전체에 걸쳐 흘수 이상의 수심(Leviathan급 3.5 m, Dreadnought급 4 m)이 필요합니다.",
                "갑판과 선내를 걸어 다닐 수 있습니다. 근무 위치에 서면 그 자리를 맡는 키 [H]가 화면에 나옵니다. [H]를 다시 누르면 떠나고, 타륜에서는 ‘웅크리기’로도 떠납니다. 해도대는 대신 화면이 열리므로, 닫으면 떠납니다.",
                "회수: 멈춰 있고 다른 사람이 아무도 타지 않았을 때, 함정 한가운데(Dreadnought급은 CIC 안)에 서서 ‘웅크리기’를 누른 채 맨손으로 발밑을 오른쪽 클릭합니다.",
            ],
            "keys": [
                ["기관", "[W] 전진, [S] 정지 쪽으로 되돌림. 전진에서 [S]를 누르고 있으면 정지(0)에서 멈추고, 다시 누르면 후진합니다. 기관은 놓은 자리에 머뭅니다."],
                ["조타", "[A]를 누르고 있으면 좌현(왼쪽), [D]는 우현(오른쪽)으로 돕니다. 놓으면 타륜이 중앙으로 돌아오고, 그때의 침로를 유지합니다."],
                ["타륜에서", "[W] [A] [S] [D]는 걷는 대신 함정을 움직입니다. 계기는 단축 바 위에 나오고, 타륜을 맡을 때는 키의 짧은 안내도 나옵니다."],
            ],
            "lists": [
                ["해도대", [
                    "해도대에서 [H]를 누르면 해도가 열립니다. 왼쪽 클릭으로 항로점을 추가하고, 마우스 휠로 축척을 바꿉니다.",
                    "버튼으로 자동 항해를 켜고 끄며 항로를 지웁니다. 육지나 얕은 물을 가로지르는 구간은 거부됩니다. 자동 항해는 키만 잡으므로, 타륜에서 기관을 전진으로 해 두세요. 마지막 항로점에서 기관을 멈춥니다.",
                ]],
                ["문(Leviathan급)", [
                    "멈춰 있고(0.3 m/s 미만, 기관 0) 타륜을 맡았을 때 [Y]로 선수 바이저와 램프를 여닫습니다.",
                    "문이 완전히 닫힐 때까지 기관은 추력을 내지 않습니다. 램프는 완전히 내려가면 걸을 수 있습니다.",
                ]],
                ["함포(Dreadnought급)", [
                    "타륜에 있을 때 포술 위치에 아무도 없으면 함포를 직접 다룹니다. 3연장 포탑 2기가 바라보는 지점을 겨눕니다. 왼쪽 클릭으로 일제사격(10초마다), 오른쪽 클릭으로 해치가 열린 뒤 레이더가 고정한 목표에 VLS를 발사합니다.",
                    "CIC의 포술 위치에 포술사가 앉으면 함포는 그 사람에게 넘어가고, 포술사가 떠나면 타륜으로 돌아옵니다. 소나: 주변의 함정, 보트, 헤엄치는 사람과 수중 목표를 회전 탐색 화면에 표시합니다.",
                ]],
            ],
        },
    },
    "pt-br": {
        "heading": "Controles",
        "air": {
            "title": "Aeronaves: o avião de passageiros Stratos-900 e o caça Aegis-X",
            "facts": [
                "Posicionar: use o item no chão, onde houver espaço; a aeronave fica ali, virada para onde você olha.",
                "Embarcar: clique com o botão direito no meio da aeronave. Quem embarca primeiro pilota (o Stratos-900 tem 18 assentos). Para desembarcar, use “Agachar”; no ar não é possível.",
                "Combustível: no chão, use um ⟨Propellant Canister⟩ na aeronave, um por uso.",
                "Recolher: parada no chão e sem ninguém a bordo, segure “Agachar” e clique com o botão direito de mão vazia.",
                "Ao embarcar, e sempre que a aeronave estiver parada no chão, um guia curto destas teclas aparece acima do centro da tela.",
            ],
            "keys": [
                ["Direção", "Olhe para onde quer ir: a aeronave se inclina, faz a curva, sobe e desce rumo a esse ponto sozinha."],
                ["Potência", "[W] mais, [S] menos; a manete fica onde você deixar. A potência máxima acende o pós-combustor do Aegis-X. No chão, [S] com a potência em zero segura a aeronave nos freios."],
                ["Olhar ao redor", "Segure [LALT] (no Mac, [LOPT]): a aeronave mantém o rumo enquanto você olha em volta."],
                ["Visão", "Você escolhe: nunca fica presa em primeira pessoa nem se inclina com a aeronave. [F5] muda a visão a qualquer momento."],
                ["Mísseis (Aegis-X)", "O clique esquerdo dispara no alvo travado pelo radar."],
                ["Automáticos", "Flaps, trem de pouso, freios das rodas, reverso, pós-combustor, canopi e rampa traseira, e o gancho de pouso."],
            ],
            "lists": [
                ["Decolagem e pouso", [
                    "Decolagem: segure [W] até a potência máxima e olhe um pouco acima do horizonte. Na velocidade de decolagem, a aeronave levanta o nariz e sai do chão, depois recolhe o trem.",
                    "Pouso: olhe para a pista um pouco abaixo do horizonte. A aeronave baixa o trem, mantém a velocidade de aproximação e arredonda logo antes do toque. Já no chão, segure [S] para levar a potência a zero: ela freia, e usa o reverso se puder. Para arremeter, olhe para cima e segure [W].",
                ]],
                ["Armamento do Aegis-X", [
                    "Carregar: use um ⟨Cherry Guided Missile⟩ num Aegis-X no chão, um por uso. Ele leva dois, e um novo já vem carregado.",
                    "O radar escolhe o alvo sozinho: vigia 30° em torno do nariz até 512 blocos, no ar e no chão, e trava o contato mais próximo do nariz depois de mantê-lo por cerca de 1,5 segundo.",
                    "O clique esquerdo dispara um míssil no alvo travado: só no ar, no máximo um por segundo.",
                ]],
            ],
        },
        "sea": {
            "title": "Navios: o ferry classe Leviathan e o contratorpedeiro classe Dreadnought",
            "facts": [
                "Posicionar: da margem ou de um barco, olhe para a água e use o item. O navio flutua com a popa logo além do ponto que você olha e a proa virada para onde você olha; a água precisa ter, ao longo de todo o casco, pelo menos a profundidade do calado (3,5 m no classe Leviathan, 4 m no classe Dreadnought).",
                "Ande pelos conveses e interiores. Ao parar num posto, aparece a tecla para assumi-lo: [H]. Aperte [H] de novo para sair; no timão, “Agachar” também faz sair. A mesa de cartas abre uma tela: feche-a para sair.",
                "Recolher: parado e sem mais ninguém a bordo, fique no meio do navio (no classe Dreadnought, no CIC), segure “Agachar” e clique com o botão direito aos seus pés de mão vazia.",
            ],
            "keys": [
                ["Máquina", "[W] avante, [S] volta em direção a parar. Se você segurar [S] vindo de avante, a máquina para no zero; aperte de novo para dar ré. A máquina fica onde você deixar."],
                ["Leme", "Segure [A] para bombordo (esquerda), [D] para boreste (direita). Ao soltar, o timão se centraliza e o navio mantém o rumo que tem."],
                ["No timão", "[W] [A] [S] [D] governam o navio em vez de fazer você andar. Os instrumentos aparecem acima da barra rápida, com um guia curto das teclas quando você assume o timão."],
            ],
            "lists": [
                ["Mesa de cartas", [
                    "Na mesa de cartas, [H] abre a carta. O clique esquerdo adiciona um ponto de rota; a roda do mouse muda a escala.",
                    "Os botões ligam ou desligam o piloto automático e apagam a rota. Um trecho que cruza terra ou águas rasas é recusado. O piloto automático só governa o leme: ponha a máquina avante no timão; no último ponto ele para a máquina.",
                ]],
                ["Portas (classe Leviathan)", [
                    "Parado (abaixo de 0,3 m/s, máquina em 0) e no timão, [Y] abre e fecha a viseira de proa e as rampas.",
                    "A máquina não dá empuxo até as portas fecharem. Dá para andar nas rampas quando estão totalmente abaixadas.",
                ]],
                ["Canhões (classe Dreadnought)", [
                    "No timão, sem ninguém no posto de artilharia, os canhões são seus: as duas torres triplas apontam para o ponto que você olha. O clique esquerdo dispara uma salva, a cada 10 segundos; o direito lança o VLS contra o alvo travado pelo radar, depois que a escotilha abre.",
                    "Um artilheiro que assume o posto de artilharia no CIC toma os canhões para si; eles voltam ao timão quando o artilheiro sai. Sonar: navios, barcos, nadadores e contatos submersos numa tela de varredura.",
                ]],
            ],
        },
    },
    "it": {
        "heading": "Comandi",
        "air": {
            "title": "Velivoli: l’aereo di linea Stratos-900 e il caccia Aegis-X",
            "facts": [
                "Posizionare: usa l’oggetto a terra, dove c’è spazio; il velivolo resta lì, rivolto dove guardi.",
                "Salire: clic destro al centro del velivolo. Chi sale per primo pilota (lo Stratos-900 ha 18 posti). Per scendere usa «Accovacciati»; in volo non si può.",
                "Carburante: a terra, usa un ⟨Propellant Canister⟩ sul velivolo, uno per uso.",
                "Recuperare: fermo a terra e senza nessuno a bordo, tieni premuto «Accovacciati» e fai clic destro a mano vuota.",
                "Quando sali a bordo, e ogni volta che il velivolo è fermo a terra, sopra il centro dello schermo compare una breve guida a questi tasti.",
            ],
            "keys": [
                ["Direzione", "Guarda dove vuoi andare: il velivolo si inclina, vira, sale e scende verso quel punto da solo."],
                ["Manetta", "[W] più, [S] meno; la leva resta dove la lasci. La manetta al massimo accende il postbruciatore dell’Aegis-X. A terra, [S] a zero tiene il velivolo sui freni."],
                ["Guardarsi intorno", "Tieni premuto [LALT] (su Mac, [LOPT]): il velivolo mantiene la rotta mentre ti guardi intorno."],
                ["Visuale", "La scegli tu: non si blocca mai in prima persona e non si inclina con il velivolo. [F5] la cambia in qualsiasi momento."],
                ["Missili (Aegis-X)", "Il clic sinistro spara al bersaglio agganciato dal radar."],
                ["Automatici", "Flap, carrello, freni delle ruote, inversione di spinta, postbruciatore, tettuccio e rampa posteriore, e il gancio d’appontaggio."],
            ],
            "lists": [
                ["Decollo e atterraggio", [
                    "Decollo: tieni premuto [W] fino alla manetta al massimo e guarda poco sopra l’orizzonte. Alla velocità di decollo il velivolo alza il muso e si stacca da terra, poi ritrae il carrello.",
                    "Atterraggio: guarda la pista poco sotto l’orizzonte. Il velivolo estrae il carrello, mantiene la velocità di avvicinamento e richiama appena prima del contatto. Una volta a terra, tieni premuto [S] per portare la manetta a zero: frena, e inverte la spinta se può. Per riattaccare, guarda in alto e tieni premuto [W].",
                ]],
                ["Armamento dell’Aegis-X", [
                    "Caricare: usa un ⟨Cherry Guided Missile⟩ su un Aegis-X a terra, uno per uso. Ne porta due, e uno nuovo arriva carico.",
                    "Il radar sceglie il bersaglio da solo: sorveglia 30° attorno al muso fino a 512 blocchi, in aria e a terra, e aggancia il contatto più vicino al muso dopo averlo tenuto per circa 1,5 secondi.",
                    "Il clic sinistro lancia un missile sul bersaglio agganciato: solo in volo, al massimo uno al secondo.",
                ]],
            ],
        },
        "sea": {
            "title": "Navi: il traghetto classe Leviathan e il cacciatorpediniere classe Dreadnought",
            "facts": [
                "Posizionare: dalla riva o da una barca, guarda l’acqua e usa l’oggetto. La nave galleggia con la poppa appena oltre il punto che guardi e la prua rivolta dove guardi; l’acqua deve essere profonda almeno quanto il suo pescaggio per tutta la lunghezza (3,5 m la classe Leviathan, 4 m la classe Dreadnought).",
                "Cammina sui ponti e negli interni. Stando a una postazione compare il tasto per occuparla: [H]. Premi di nuovo [H] per lasciarla; al timone la lasci anche con «Accovacciati». Il tavolo delle carte apre invece una schermata: chiudila per lasciarlo.",
                "Recuperare: a nave ferma e senza nessun altro a bordo, mettiti a centro nave (sulla classe Dreadnought, nel CIC), tieni premuto «Accovacciati» e fai clic destro ai tuoi piedi a mano vuota.",
            ],
            "keys": [
                ["Macchina", "[W] avanti, [S] torna verso l’arresto. Tenendo premuto [S] mentre vai avanti, la macchina si ferma a zero; premilo di nuovo per andare indietro. La macchina resta dove la lasci."],
                ["Timone", "Tieni premuto [A] per virare a sinistra, [D] per virare a dritta (destra). Quando lasci, la ruota torna al centro e la nave mantiene la rotta che ha."],
                ["Al timone", "[W] [A] [S] [D] governano la nave invece di farti camminare. Gli strumenti compaiono sopra la barra di scelta rapida, con una breve guida ai tasti quando prendi il timone."],
            ],
            "lists": [
                ["Tavolo delle carte", [
                    "Al tavolo delle carte, [H] apre la carta. Il clic sinistro aggiunge un punto di rotta; la rotellina cambia la scala.",
                    "I suoi pulsanti inseriscono o disinseriscono il pilota automatico e cancellano la rotta. Un tratto che attraversa terra o acque basse viene rifiutato. Il pilota automatico governa solo il timone: metti la macchina avanti al timone; all’ultimo punto la ferma.",
                ]],
                ["Porte (classe Leviathan)", [
                    "Da ferma (sotto 0,3 m/s, macchina a 0) e al timone, [Y] apre e chiude il visore di prua e le rampe.",
                    "La macchina non dà spinta finché le porte non sono chiuse. Sulle rampe si cammina quando sono del tutto abbassate.",
                ]],
                ["Cannoni (classe Dreadnought)", [
                    "Al timone, se nessuno è alla postazione di tiro, i cannoni sono tuoi: le due torri trinate puntano dove guardi. Il clic sinistro spara una salva, ogni 10 secondi; il destro lancia il VLS sul bersaglio agganciato dal radar, una volta aperto il portello.",
                    "Un artigliere che occupa la postazione di tiro nel CIC prende il controllo dei cannoni; tornano al timone quando se ne va. Sonar: navi, barche, nuotatori e contatti sommersi su uno schermo a scansione.",
                ]],
            ],
        },
    },
    "ar": {
        "heading": "طريقة التحكم",
        "air": {
            "title": "الطائرات: طائرة الركاب Stratos-900 والمقاتلة Aegis-X",
            "facts": [
                "الوضع: استخدم العنصر على الأرض حيث يتسع لها المكان، فتقف هناك متجهةً إلى حيث تنظر.",
                "الصعود: انقر بالزر الأيمن على منتصف الطائرة. أول من يصعد هو الطيار (في Stratos-900 ثمانية عشر مقعدًا). للنزول استخدم «التسلل»، ولا يمكن النزول في الجو.",
                "الوقود: على الأرض، استخدم ⟨Propellant Canister⟩ على الطائرة، واحدًا في كل مرة.",
                "الاسترداد: والطائرة متوقفة على الأرض ولا أحد على متنها، اضغط «التسلل» مطوّلًا وانقر بالزر الأيمن بيد فارغة.",
                "عند الصعود، وكلما كانت الطائرة متوقفة على الأرض، يظهر فوق منتصف الشاشة دليل قصير لهذه المفاتيح.",
            ],
            "keys": [
                ["التوجيه", "انظر إلى حيث تريد أن تذهب: تميل الطائرة وتنعطف وتصعد وتهبط نحوه من تلقاء نفسها."],
                ["قوة الدفع", "[W] زيادة، [S] إنقاص؛ تبقى الذراع حيث تتركها. الدفع الكامل يُشعل الحارق اللاحق في Aegis-X. وعلى الأرض، حين يكون الدفع عند الصفر، يُبقي [S] الطائرة على المكابح."],
                ["النظر حولك", "اضغط [LALT] مطوّلًا (على Mac: [LOPT]): تحافظ الطائرة على مسارها بينما تنظر حولك."],
                ["زاوية الرؤية", "تختارها أنت: لا تُقفَل أبدًا على منظور الشخص الأول، ولا تميل مع الطائرة. يغيّرها [F5] في أي وقت."],
                ["الصواريخ (Aegis-X)", "النقر الأيسر يطلق النار على الهدف الذي أقفل عليه الرادار."],
                ["تلقائيًا", "القلابات، وعجلات الهبوط، ومكابح العجلات، وعكس الدفع، والحارق اللاحق، وغطاء قمرة القيادة والمنحدر الخلفي، وخطّاف الهبوط."],
            ],
            "lists": [
                ["الإقلاع والهبوط", [
                    "الإقلاع: اضغط [W] مطوّلًا حتى الدفع الكامل، وانظر إلى ما فوق الأفق بقليل. عند سرعة الإقلاع ترفع الطائرة مقدّمتها وتقلع، ثم تطوي عجلاتها.",
                    "الهبوط: انظر إلى المدرج أسفل الأفق بقليل. تُنزل الطائرة عجلاتها، وتحافظ على سرعة الاقتراب، وترفع مقدّمتها قليلًا قبيل ملامسة الأرض. وبعد الهبوط اضغط [S] مطوّلًا لإنزال الدفع إلى الصفر: فتفرمل، وتعكس الدفع إن استطاعت. ولإلغاء الهبوط، انظر إلى الأعلى واضغط [W] مطوّلًا.",
                ]],
                ["تسليح Aegis-X", [
                    "التحميل: استخدم ⟨Cherry Guided Missile⟩ على Aegis-X وهي على الأرض، صاروخًا في كل مرة. تحمل صاروخين، والطائرة الجديدة تأتي محمّلة.",
                    "يختار الرادار الهدف بنفسه: يراقب 30° حول المقدّمة حتى 512 كتلة، في الجو وعلى الأرض، ويقفل على أقرب هدف إلى المقدّمة بعد أن يبقيه نحو 1.5 ثانية.",
                    "النقر الأيسر يطلق صاروخًا على الهدف المقفل: في الجو فقط، وصاروخًا واحدًا في الثانية على الأكثر.",
                ]],
            ],
        },
        "sea": {
            "title": "السفن: العبّارة من فئة Leviathan والمدمّرة من فئة Dreadnought",
            "facts": [
                "الوضع: انظر إلى الماء من الشاطئ أو من قارب واستخدم العنصر. تطفو السفينة ومؤخرتها بعد الموضع الذي تنظر إليه مباشرةً ومقدّمتها متجهة إلى حيث تنظر، ويجب ألا يقل عمق الماء على طول بدنها كله عن غاطسها (3.5 م لفئة Leviathan و4 م لفئة Dreadnought).",
                "تجوّل على أسطحها وفي داخلها. حين تقف عند موقع عمل يظهر المفتاح الذي تتولاه به: [H]. اضغط [H] مجددًا لتتركه، وعند عجلة القيادة يمكنك تركها بـ«التسلل» أيضًا. أما طاولة الخرائط فتفتح شاشة: أغلقها لتتركها.",
                "الاسترداد: والسفينة متوقفة ولا أحد غيرك على متنها، قف في وسط السفينة (وفي فئة Dreadnought داخل مركز المعلومات القتالية)، واضغط «التسلل» مطوّلًا، وانقر بالزر الأيمن عند قدميك بيد فارغة.",
            ],
            "keys": [
                ["المحرّك", "[W] إلى الأمام، [S] رجوعًا نحو التوقف. إذا ضغطت [S] مطوّلًا والمحرّك إلى الأمام توقّف عند الصفر؛ واضغطه مجددًا للرجوع إلى الخلف. يبقى المحرّك حيث تتركه."],
                ["الدفّة", "اضغط [A] مطوّلًا للميسرة (اليسار)، و[D] للميمنة (اليمين). وحين تتركهما تعود عجلة القيادة إلى المنتصف وتحافظ السفينة على اتجاهها الحالي."],
                ["عند عجلة القيادة", "تحرّك [W] [A] [S] [D] السفينة بدلًا من أن تحرّكك أنت. وتظهر العدّادات فوق شريط المهام، مع دليل قصير للمفاتيح حين تتولى عجلة القيادة."],
            ],
            "lists": [
                ["طاولة الخرائط", [
                    "عند طاولة الخرائط يفتح [H] الخريطة. النقر الأيسر يضيف نقطة مسار، وعجلة الفأرة تغيّر المقياس.",
                    "أزرارها تشغّل الملاحة الآلية أو توقفها وتمسح المسار. يُرفض أي مقطع يعبر اليابسة أو المياه الضحلة. الملاحة الآلية تتولى الدفّة فقط: اجعل المحرّك إلى الأمام من عجلة القيادة، وهي توقفه عند آخر نقطة.",
                ]],
                ["الأبواب (فئة Leviathan)", [
                    "والسفينة متوقفة (أقل من 0.3 م/ث والمحرّك على 0) وأنت عند عجلة القيادة، يفتح [Y] واقي المقدّمة والمنحدرات ويغلقها.",
                    "لا يعطي المحرّك دفعًا حتى تُغلق الأبواب. ويمكن المشي على المنحدرات حين تنزل تمامًا.",
                ]],
                ["المدافع (فئة Dreadnought)", [
                    "عند عجلة القيادة، وموقع المدفعية خالٍ، تكون المدافع لك: يتجه البرجان الثلاثيان إلى النقطة التي تنظر إليها. النقر الأيسر يطلق رشقة كل 10 ثوانٍ، والنقر الأيمن يطلق منظومة الإطلاق العمودي على الهدف الذي أقفل عليه الرادار بعد انفتاح فتحتها.",
                    "إذا تولّى رامٍ موقع المدفعية في مركز المعلومات القتالية انتقلت إليه المدافع، وتعود إلى عجلة القيادة حين يغادر. السونار: السفن والقوارب والسبّاحون والأهداف المغمورة على شاشة مسح دوّارة.",
                ]],
            ],
        },
    },
    "ru": {
        "heading": "Управление",
        "air": {
            "title": "Самолёты: авиалайнер Stratos-900 и истребитель Aegis-X",
            "facts": [
                "Установка: используйте предмет на земле, где ему хватает места, — самолёт встанет там носом туда, куда вы смотрите.",
                "Посадка: правый клик по середине самолёта. Первый севший — пилот (в Stratos-900 18 мест). Выйти — «Красться»; в воздухе выйти нельзя.",
                "Топливо: на земле используйте на самолёте ⟨Propellant Canister⟩, по одной за раз.",
                "Возврат в предмет: когда самолёт стоит на земле и на борту никого нет, удерживайте «Красться» и сделайте правый клик пустой рукой.",
                "Когда вы садитесь в самолёт, а также всё время, пока он стоит на земле, над центром экрана показывается краткая подсказка по этим клавишам.",
            ],
            "keys": [
                ["Направление", "Смотрите туда, куда хотите лететь: самолёт сам накренится, повернёт, наберёт высоту или снизится в ту сторону."],
                ["Тяга", "[W] больше, [S] меньше; рычаг остаётся там, где вы его оставили. Полная тяга включает форсаж Aegis-X. На земле [S] при нулевой тяге держит самолёт на тормозах."],
                ["Осмотреться", "Удерживайте [LALT] (на Mac — [LOPT]): самолёт держит курс, пока вы смотрите по сторонам."],
                ["Вид", "Выбирайте сами: он никогда не фиксируется от первого лица и не наклоняется вместе с самолётом. [F5] переключает его в любой момент."],
                ["Ракеты (Aegis-X)", "Левый клик — пуск по цели, захваченной радаром."],
                ["Автоматически", "Закрылки, шасси, тормоза колёс, реверс, форсаж, фонарь и задняя рампа, а также посадочный гак."],
            ],
            "lists": [
                ["Взлёт и посадка", [
                    "Взлёт: удерживайте [W] до полной тяги и смотрите чуть выше горизонта. На скорости отрыва самолёт поднимет нос и оторвётся от земли, затем уберёт шасси.",
                    "Посадка: смотрите на полосу чуть ниже горизонта. Самолёт выпустит шасси, выдержит скорость захода и выполнит выравнивание перед самым касанием. После касания удерживайте [S], чтобы убрать тягу до нуля: самолёт затормозит и включит реверс, если он есть. Чтобы уйти на второй круг, посмотрите вверх и удерживайте [W].",
                ]],
                ["Вооружение Aegis-X", [
                    "Зарядка: используйте ⟨Cherry Guided Missile⟩ на Aegis-X, стоящем на земле, — по одной ракете. Он несёт две, и новый самолёт появляется заряженным.",
                    "Радар сам выбирает цель: он смотрит в пределах 30° вокруг носа до 512 блоков, в воздухе и на земле, и захватывает ближайшую к носу цель, удержанную около 1,5 секунды.",
                    "Левый клик пускает ракету по захваченной цели: только в воздухе, не чаще одной в секунду.",
                ]],
            ],
        },
        "sea": {
            "title": "Корабли: паром класса Leviathan и эсминец класса Dreadnought",
            "facts": [
                "Установка: посмотрите на воду с берега или из лодки и используйте предмет. Корабль всплывёт кормой сразу за точкой, на которую вы смотрите, и носом туда, куда вы смотрите; вода по всей его длине должна быть не мельче его осадки (3,5 м у класса Leviathan, 4 м у класса Dreadnought).",
                "По палубам и внутренним помещениям можно ходить. Когда вы стоите у поста, показывается клавиша, которой его можно занять: [H]. Нажмите [H] снова, чтобы уйти; у штурвала уйти можно и через «Красться». Штурманский стол вместо этого открывает экран: закройте его, чтобы уйти.",
                "Возврат в предмет: когда корабль стоит и на борту больше никого нет, встаньте посередине корабля (на классе Dreadnought — в БИЦ), удерживайте «Красться» и сделайте правый клик у себя под ногами пустой рукой.",
            ],
            "keys": [
                ["Машина", "[W] вперёд, [S] обратно к «стоп». Если удерживать [S] на ходу вперёд, машина остановится на нуле; нажмите ещё раз, чтобы дать задний ход. Машина остаётся там, где вы её оставили."],
                ["Руль", "Удерживайте [A] — на левый борт (влево), [D] — на правый борт (вправо). Отпустите — штурвал встанет прямо, и корабль будет держать текущий курс."],
                ["У штурвала", "[W] [A] [S] [D] управляют кораблём, а не вашим передвижением. Приборы показаны над панелью быстрого доступа, а когда вы встаёте к штурвалу, появляется краткая подсказка по клавишам."],
            ],
            "lists": [
                ["Штурманский стол", [
                    "У штурманского стола [H] открывает карту. Левый клик добавляет путевую точку, колесо мыши меняет масштаб.",
                    "Кнопки включают и выключают автопилот и стирают маршрут. Участок через сушу или мелководье отклоняется. Автопилот только рулит: дайте ход вперёд у штурвала; в последней точке он останавливает машину.",
                ]],
                ["Ворота (класс Leviathan)", [
                    "На стопе (меньше 0,3 м/с, машина на 0) и у штурвала [Y] открывает и закрывает носовой визор и рампы.",
                    "Пока ворота не закрыты, машина не даёт тяги. По рампам можно ходить, когда они опущены полностью.",
                ]],
                ["Орудия (класс Dreadnought)", [
                    "У штурвала, если пост артиллериста свободен, орудия ваши: обе трёхорудийные башни наводятся на точку, куда вы смотрите. Левый клик — залп, раз в 10 секунд; правый клик — пуск УВП по цели, захваченной радаром, после открытия крышки.",
                    "Артиллерист, занявший свой пост в БИЦ, забирает орудия себе; когда он уходит, они возвращаются к штурвалу. Сонар: корабли, лодки, пловцы и подводные контакты на экране кругового обзора.",
                ]],
            ],
        },
    },
    "id": {
        "heading": "Kontrol",
        "air": {
            "title": "Pesawat: pesawat penumpang Stratos-900 dan jet tempur Aegis-X",
            "facts": [
                "Menaruh: gunakan itemnya di tanah yang cukup lapang; pesawat berdiri di sana menghadap ke arah pandanganmu.",
                "Naik: klik kanan bagian tengah pesawat. Yang naik pertama menjadi pilot (Stratos-900 punya 18 kursi). Turun dengan “Jongkok”; tidak bisa turun di udara.",
                "Bahan bakar: di darat, gunakan ⟨Propellant Canister⟩ pada pesawat, satu per penggunaan.",
                "Mengambil kembali: saat diam di darat dan tak ada yang naik, tahan “Jongkok” lalu klik kanan dengan tangan kosong.",
                "Saat kamu naik, dan setiap kali pesawat diam di darat, panduan singkat untuk tombol-tombol ini muncul di atas bagian tengah layar.",
            ],
            "keys": [
                ["Mengarahkan", "Lihat ke arah yang ingin kamu tuju: pesawat akan miring, berbelok, menanjak, dan menukik ke sana dengan sendirinya."],
                ["Daya dorong", "[W] tambah, [S] kurangi; tuasnya tetap di posisi terakhir. Daya penuh menyalakan afterburner Aegis-X. Di darat, [S] saat daya nol menahan pesawat dengan rem."],
                ["Melihat sekitar", "Tahan [LALT] (di Mac, [LOPT]): pesawat tetap pada arahnya selagi kamu melihat-lihat."],
                ["Sudut pandang", "Kamu yang memilih: tidak pernah terkunci ke orang pertama dan tidak ikut miring bersama pesawat. [F5] menggantinya kapan saja."],
                ["Rudal (Aegis-X)", "Klik kiri menembak sasaran yang dikunci radar."],
                ["Otomatis", "Flap, roda pendarat, rem roda, dorong balik, afterburner, kanopi dan ramp belakang, serta kait pendaratan."],
            ],
            "lists": [
                ["Lepas landas dan mendarat", [
                    "Lepas landas: tahan [W] sampai daya penuh dan lihat sedikit di atas cakrawala. Pada kecepatan lepas landas, pesawat mengangkat hidung dan terangkat dari landasan, lalu melipat roda.",
                    "Mendarat: lihat landasan sedikit di bawah cakrawala. Pesawat menurunkan roda, menjaga kecepatan pendekatan, dan mengangkat hidung sesaat sebelum menyentuh landasan. Setelah mendarat, tahan [S] untuk menurunkan daya ke nol: pesawat mengerem, dan memakai dorong balik bila bisa. Untuk membatalkan pendaratan, lihat ke atas dan tahan [W].",
                ]],
                ["Persenjataan Aegis-X", [
                    "Mengisi: gunakan ⟨Cherry Guided Missile⟩ pada Aegis-X di darat, satu per penggunaan. Ia membawa dua, dan yang baru datang sudah terisi.",
                    "Radar memilih sasaran sendiri: ia mengawasi 30° di sekitar hidung sejauh 512 blok, di udara maupun di darat, dan mengunci kontak yang paling dekat dengan hidung setelah menahannya sekitar 1,5 detik.",
                    "Klik kiri menembakkan rudal ke sasaran yang terkunci: hanya di udara, paling banyak satu per detik.",
                ]],
            ],
        },
        "sea": {
            "title": "Kapal: feri kelas Leviathan dan kapal perusak kelas Dreadnought",
            "facts": [
                "Menaruh: dari pantai atau perahu, lihat ke air dan gunakan itemnya. Kapal mengapung dengan buritan tepat melewati titik yang kamu lihat dan haluan menghadap arah pandanganmu; airnya harus setidaknya sedalam sarat air kapal di sepanjang lambungnya (3,5 m untuk kelas Leviathan, 4 m untuk kelas Dreadnought).",
                "Jelajahi dek dan bagian dalamnya. Saat kamu berdiri di sebuah pos, tombol untuk mengambilnya ditampilkan: [H]. Tekan [H] lagi untuk pergi; di kemudi, “Jongkok” juga bisa dipakai untuk pergi. Meja peta justru membuka layar: tutup layarnya untuk pergi.",
                "Mengambil kembali: saat kapal diam dan tak ada orang lain di atasnya, berdirilah di tengah kapal (di kelas Dreadnought, di dalam CIC), tahan “Jongkok” lalu klik kanan di dekat kakimu dengan tangan kosong.",
            ],
            "keys": [
                ["Mesin", "[W] maju, [S] kembali ke arah berhenti. Jika kamu menahan [S] saat maju, mesin berhenti di nol; tekan lagi untuk mundur. Mesin tetap di posisi terakhir."],
                ["Kemudi", "Tahan [A] untuk ke kiri (port), [D] untuk ke kanan (starboard). Jika dilepas, roda kemudi kembali ke tengah dan kapal menahan haluannya saat itu."],
                ["Di kemudi", "[W] [A] [S] [D] mengemudikan kapal, bukan menggerakkan langkahmu. Instrumen tampil di atas bilah benda, disertai panduan singkat tombol saat kamu memegang kemudi."],
            ],
            "lists": [
                ["Meja peta", [
                    "Di meja peta, [H] membuka peta. Klik kiri menambah titik rute; roda mouse mengubah skala.",
                    "Tombolnya menyalakan atau mematikan autopilot dan menghapus rute. Ruas yang melintasi daratan atau perairan dangkal ditolak. Autopilot hanya mengemudi: majukan mesin di roda kemudi; di titik terakhir ia menghentikan mesin.",
                ]],
                ["Pintu (kelas Leviathan)", [
                    "Saat diam (di bawah 0,3 m/s, mesin 0) dan memegang kemudi, [Y] membuka dan menutup visor haluan dan ramp.",
                    "Mesin tidak memberi daya dorong sampai pintu tertutup. Ramp bisa diinjak setelah turun sepenuhnya.",
                ]],
                ["Meriam (kelas Dreadnought)", [
                    "Di kemudi, bila tak ada orang di pos penembak, meriam ada di tanganmu: kedua turet berlaras tiga membidik titik yang kamu lihat. Klik kiri menembakkan satu salvo, tiap 10 detik; klik kanan meluncurkan VLS ke sasaran yang dikunci radar, setelah palkanya terbuka.",
                    "Penembak yang mengambil pos penembak di CIC mengambil alih meriam; meriam kembali ke kemudi saat penembak itu pergi. Sonar: kapal, perahu, perenang, dan kontak di bawah air pada layar pindai berputar.",
                ]],
            ],
        },
    },
    "de": {
        "heading": "Steuerung",
        "air": {
            "title": "Flugzeuge: das Verkehrsflugzeug Stratos-900 und der Jäger Aegis-X",
            "facts": [
                "Aufstellen: Benutze den Gegenstand auf dem Boden, wo genug Platz ist; das Flugzeug steht dann dort, mit der Nase in Blickrichtung.",
                "Einsteigen: Rechtsklick auf die Mitte des Flugzeugs. Wer zuerst einsteigt, fliegt (die Stratos-900 hat 18 Sitze). Aussteigen mit „Schleichen“; in der Luft geht das nicht.",
                "Treibstoff: Benutze am Boden einen ⟨Propellant Canister⟩ am Flugzeug, einen pro Benutzung.",
                "Einsammeln: Steht es am Boden still und ist niemand an Bord, halte „Schleichen“ und mache mit leerer Hand einen Rechtsklick.",
                "Beim Einsteigen und immer, wenn das Flugzeug am Boden steht, erscheint über der Bildschirmmitte eine kurze Übersicht dieser Tasten.",
            ],
            "keys": [
                ["Lenken", "Schau dorthin, wo du hinwillst: Das Flugzeug neigt sich, kurvt, steigt und sinkt von selbst dorthin."],
                ["Schub", "[W] mehr, [S] weniger; der Hebel bleibt, wo du ihn lässt. Vollschub zündet den Nachbrenner der Aegis-X. Am Boden hält [S] bei Schub null das Flugzeug auf den Bremsen."],
                ["Umsehen", "[LALT] gedrückt halten (auf dem Mac [LOPT]): Das Flugzeug hält seinen Kurs, während du dich umsiehst."],
                ["Ansicht", "Du hast die Wahl: Sie rastet nie in der Ich-Perspektive ein und neigt sich nicht mit dem Flugzeug. [F5] wechselt sie jederzeit."],
                ["Raketen (Aegis-X)", "Linksklick feuert auf das vom Radar aufgeschaltete Ziel."],
                ["Automatisch", "Landeklappen, Fahrwerk, Radbremsen, Schubumkehr, Nachbrenner, Kabinenhaube und Heckrampe sowie der Fanghaken."],
            ],
            "lists": [
                ["Start und Landung", [
                    "Start: Halte [W] bis zum Vollschub und schau etwas über den Horizont. Bei Abhebegeschwindigkeit nimmt das Flugzeug die Nase hoch, hebt ab und fährt dann das Fahrwerk ein.",
                    "Landung: Schau auf die Landebahn etwas unter dem Horizont. Das Flugzeug fährt das Fahrwerk aus, hält die Anfluggeschwindigkeit und fängt kurz vor dem Aufsetzen ab. Halte nach dem Aufsetzen [S], um den Schub auf null zu nehmen: Es bremst und nutzt die Schubumkehr, sofern es eine hat. Zum Durchstarten schau nach oben und halte [W].",
                ]],
                ["Bewaffnung der Aegis-X", [
                    "Laden: Benutze eine ⟨Cherry Guided Missile⟩ an einer Aegis-X am Boden, eine pro Benutzung. Sie trägt zwei, und eine neue kommt geladen.",
                    "Das Radar wählt das Ziel selbst: Es überwacht 30° um die Nase bis 512 Blöcke, in der Luft und am Boden, und schaltet den Kontakt, der der Nase am nächsten ist, auf, nachdem es ihn etwa 1,5 Sekunden gehalten hat.",
                    "Linksklick feuert eine Rakete auf das aufgeschaltete Ziel: nur in der Luft, höchstens eine pro Sekunde.",
                ]],
            ],
        },
        "sea": {
            "title": "Schiffe: die Fähre der Leviathan-Klasse und der Zerstörer der Dreadnought-Klasse",
            "facts": [
                "Aufstellen: Schau vom Ufer oder aus einem Boot aufs Wasser und benutze den Gegenstand. Das Schiff schwimmt dann mit dem Heck knapp hinter der Stelle, auf die du schaust, und dem Bug in Blickrichtung; das Wasser muss dort über die ganze Länge mindestens so tief sein wie der Tiefgang (3,5 m bei der Leviathan-Klasse, 4 m bei der Dreadnought-Klasse).",
                "Du kannst über die Decks und durch die Innenräume gehen. Stehst du an einer Station, wird die Taste angezeigt, mit der du sie übernimmst: [H]. Drücke [H] erneut, um sie zu verlassen; am Ruder geht das auch mit „Schleichen“. Der Kartentisch öffnet stattdessen einen Bildschirm: Schließe ihn, um ihn zu verlassen.",
                "Einsammeln: Steht das Schiff still und ist sonst niemand an Bord, stell dich mittschiffs (auf der Dreadnought-Klasse in die Operationszentrale), halte „Schleichen“ und mache mit leerer Hand einen Rechtsklick vor deine Füße.",
            ],
            "keys": [
                ["Maschine", "[W] voraus, [S] zurück Richtung Stopp. Hältst du [S] aus der Vorausfahrt, bleibt die Maschine bei null stehen; drücke erneut für Rückwärtsfahrt. Der Hebel bleibt, wo du ihn lässt."],
                ["Ruder", "Halte [A] für Backbord (links), [D] für Steuerbord (rechts). Lässt du los, geht das Rad mittschiffs, und das Schiff hält seinen aktuellen Kurs."],
                ["Am Ruder", "[W] [A] [S] [D] steuern das Schiff, statt dich laufen zu lassen. Die Instrumente erscheinen über der Schnellzugriffsleiste, mit einer kurzen Übersicht der Tasten, wenn du das Ruder übernimmst."],
            ],
            "lists": [
                ["Kartentisch", [
                    "Am Kartentisch öffnet [H] die Seekarte. Linksklick fügt einen Wegpunkt hinzu; das Mausrad ändert den Maßstab.",
                    "Seine Knöpfe schalten den Autopiloten ein oder aus und löschen die Route. Ein Abschnitt über Land oder Flachwasser wird abgelehnt. Der Autopilot steuert nur: stelle die Maschine am Ruder auf voraus; am letzten Wegpunkt stoppt er sie.",
                ]],
                ["Tore (Leviathan-Klasse)", [
                    "Im Stillstand (unter 0,3 m/s, Maschine auf 0) und am Ruder öffnet und schließt [Y] das Bugvisier und die Rampen.",
                    "Die Maschine gibt keinen Schub, bis die Tore geschlossen sind. Die Rampen sind begehbar, sobald sie ganz unten sind.",
                ]],
                ["Geschütze (Dreadnought-Klasse)", [
                    "Am Ruder gehören dir die Geschütze, solange niemand an der Geschützstation ist: Beide Drillingstürme richten sich auf den Punkt, den du ansiehst. Linksklick feuert eine Salve, alle 10 Sekunden; Rechtsklick startet das VLS auf das vom Radar aufgeschaltete Ziel, sobald seine Klappe offen ist.",
                    "Wer die Geschützstation in der Operationszentrale übernimmt, übernimmt auch die Geschütze; sie gehen ans Ruder zurück, sobald er sie verlässt. Sonar: Schiffe, Boote, Schwimmer und getauchte Kontakte auf einem umlaufenden Suchschirm.",
                ]],
            ],
        },
    },
    "tr": {
        "heading": "Kontroller",
        "air": {
            "title": "Uçaklar: yolcu uçağı Stratos-900 ve savaş uçağı Aegis-X",
            "facts": [
                "Yerleştirme: eşyayı yeterince yer olan bir zeminde kullanın; uçak orada, baktığınız yöne burnunu çevirip durur.",
                "Binme: uçağın ortasına sağ tıklayın. İlk binen pilottur (Stratos-900’de 18 koltuk var). İnmek için “Eğilme”; havadayken inilemez.",
                "Yakıt: yerdeyken uçağa bir ⟨Propellant Canister⟩ kullanın; her kullanımda bir tane.",
                "Geri alma: uçak yerde dururken ve kimse binmemişken “Eğilme”yi basılı tutup boş elle sağ tıklayın.",
                "Bindiğinizde ve uçak yerde durduğu sürece, ekranın ortasının üstünde bu tuşlar için kısa bir rehber görünür.",
            ],
            "keys": [
                ["Yönlendirme", "Gitmek istediğiniz yere bakın: uçak kendiliğinden yatar, döner, tırmanır ve alçalarak oraya yönelir."],
                ["İtki", "[W] artır, [S] azalt; kol bıraktığınız yerde kalır. Tam itki, Aegis-X’in art yakıcısını yakar. Yerde, itki sıfırdayken [S] uçağı frende tutar."],
                ["Etrafa bakma", "[LALT] tuşunu basılı tutun (Mac’te [LOPT]): siz etrafa bakarken uçak rotasını korur."],
                ["Görünüm", "Seçim sizin: asla birinci şahıs görünümüne kilitlenmez ve uçakla birlikte yatmaz. [F5] onu istediğiniz an değiştirir."],
                ["Füzeler (Aegis-X)", "Sol tık, radarın kilitlendiği hedefe ateş eder."],
                ["Otomatik", "Flaplar, iniş takımı, tekerlek frenleri, ters itki, art yakıcı, kanopi ve arka rampa ile kuyruk kancası."],
            ],
            "lists": [
                ["Kalkış ve iniş", [
                    "Kalkış: tam itki için [W] tuşunu basılı tutun ve ufkun biraz üstüne bakın. Kalkış hızına gelince uçak burnunu kaldırıp yerden kesilir, ardından iniş takımını toplar.",
                    "İniş: ufkun biraz altındaki piste bakın. Uçak iniş takımını indirir, yaklaşma hızını korur ve teker koymadan hemen önce burnunu kaldırır. Teker koyduktan sonra itkiyi sıfıra indirmek için [S] tuşunu basılı tutun: uçak fren yapar, yapabiliyorsa ters itki de kullanır. Pas geçmek için yukarı bakın ve [W] tuşunu basılı tutun.",
                ]],
                ["Aegis-X silahları", [
                    "Yükleme: yerdeki bir Aegis-X’e ⟨Cherry Guided Missile⟩ kullanın; her kullanımda bir füze. İki füze taşır ve yeni uçak dolu gelir.",
                    "Radar hedefi kendisi seçer: burnun çevresindeki 30° içini, havada ve yerde, 512 bloğa kadar izler ve burna en yakın teması yaklaşık 1,5 saniye tuttuktan sonra kilitler.",
                    "Sol tık, kilitli hedefe füze ateşler: yalnızca havadayken, saniyede en fazla bir tane.",
                ]],
            ],
        },
        "sea": {
            "title": "Gemiler: Leviathan sınıfı feribot ve Dreadnought sınıfı muhrip",
            "facts": [
                "Yerleştirme: kıyıdan ya da bir tekneden suya bakıp eşyayı kullanın. Gemi, kıçı baktığınız noktanın hemen ötesinde ve pruvası baktığınız yöne dönük olarak yüzer; su, geminin boyu boyunca en az su çekimi kadar derin olmalıdır (Leviathan sınıfı 3,5 m, Dreadnought sınıfı 4 m).",
                "Güvertelerinde ve iç mekânlarında yürüyebilirsiniz. Bir görev yerinde durunca, orayı almanızı sağlayan tuş görünür: [H]. Ayrılmak için [H] tuşuna yeniden basın; dümende “Eğilme” ile de ayrılabilirsiniz. Harita masası ise bir ekran açar: ayrılmak için ekranı kapatın.",
                "Geri alma: gemi dururken ve başka kimse binmemişken geminin ortasında durun (Dreadnought sınıfında Muharebe Bilgi Merkezi’nde), “Eğilme”yi basılı tutup boş elle ayaklarınızın dibine sağ tıklayın.",
            ],
            "keys": [
                ["Makine", "[W] ileri, [S] durmaya doğru geri alır. İleri giderken [S] tuşunu basılı tutarsanız sıfırda durur; tornistan için yeniden basın. Makine bıraktığınız yerde kalır."],
                ["Dümen", "İskele (sol) için [A], sancak (sağ) için [D] tuşunu basılı tutun. Bıraktığınızda dümen dolabı ortalanır ve gemi o anki rotasını korur."],
                ["Dümende", "[W] [A] [S] [D] sizi yürütmek yerine gemiyi yönetir. Göstergeler araç çubuğunun üstünde görünür; dümene geçtiğinizde tuşlar için kısa bir rehber de çıkar."],
            ],
            "lists": [
                ["Harita masası", [
                    "Harita masasında [H] haritayı açar. Sol tık rota noktası ekler; fare tekerleği ölçeği değiştirir.",
                    "Düğmeleri otomatik seyri açar ya da kapatır ve rotayı siler. Karayı ya da sığ suyu geçen bir ayak reddedilir. Otomatik seyir yalnızca dümeni kullanır: makineyi dümende ileriye alın; son noktada makineyi durdurur.",
                ]],
                ["Kapılar (Leviathan sınıfı)", [
                    "Dururken (0,3 m/s altında, makine 0) ve dümendeyken [Y] pruva vizörünü ve rampaları açıp kapatır.",
                    "Kapılar kapanana kadar makine itki vermez. Rampalar tamamen indiğinde üzerlerinde yürünebilir.",
                ]],
                ["Toplar (Dreadnought sınıfı)", [
                    "Dümendeyken, topçu görev yerinde kimse yoksa toplar sizindir: iki üçlü top kulesi baktığınız noktaya döner. Sol tık 10 saniyede bir yaylım ateşi açar; sağ tık, kapağı açıldıktan sonra dikey atış sistemini radarın kilitlendiği hedefe ateşler.",
                    "Muharebe Bilgi Merkezi’ndeki topçu görev yerine geçen bir topçu, topları devralır; topçu ayrılınca toplar dümene geri döner. Sonar: gemiler, tekneler, yüzücüler ve su altındaki temaslar, dönen bir tarama ekranında.",
                ]],
            ],
        },
    },
}

# The page around the cards: its title, its description, and the two notes above the cards.
# {movement}, {flight}, {helm}, {path} and {keybinds} are filled per language (MOVEMENT,
# CATEGORIES, PATH); the Japanese note adds the two JIS keys that differ (see the docstring).
INTRO = {
    "en": {
        "title": "Cherry controls",
        "desc": "How to fly the Stratos-900 and the Aegis-X and sail the Leviathan-Class and the Dreadnought-Class: the default keys and what they do.",
        "note": "These are the default keys of {release}. [W] [A] [S] [D] and Sneak are the game’s own “{movement}” keys, and left- and right-click its attack and use; [LALT] is under “{flight}”, [H] and [Y] under “{helm}”. Change any of them in {path}.",
        "layout": "Keys are named by where they sit on a US keyboard. Yours may label the same key differently; {keybinds} shows each one by your keyboard’s name for it.",
    },
    "ja": {
        "title": "Cherry の操作方法",
        "desc": "Stratos-900 と Aegis-X の飛ばし方、Leviathan級と Dreadnought級の動かし方。既定のキーと、その働き。",
        "note": "{release} の既定のキーです。[W] [A] [S] [D] とスニークはゲーム本来の「{movement}」のキー、左クリックと右クリックはゲームの攻撃と使用です。[LALT] は「{flight}」、[H] と [Y] は「{helm}」にあります。どれも {path} で変えられます。",
        "layout": "キーは US 配列での位置で書いています。お使いのキーボードでは同じキーに別の名前が付いていることがあり、{keybinds}の画面にはその名前で出ます。",
    },
    "es": {
        "title": "Controles de Cherry",
        "desc": "Cómo pilotar el Stratos-900 y el Aegis-X y gobernar los buques clase Leviathan y Dreadnought: las teclas predeterminadas y lo que hacen.",
        "note": "Estas son las teclas predeterminadas de {release}. [W] [A] [S] [D] y «Agacharse» son las teclas de «{movement}» del propio juego, y el clic izquierdo y el derecho, sus acciones de atacar y usar; [LALT] está en «{flight}», y [H] y [Y], en «{helm}». Puedes cambiarlas todas en {path}.",
        "layout": "Las teclas se nombran por su posición en un teclado estadounidense. El tuyo puede rotular la misma tecla de otra forma; «{keybinds}» muestra cada una con el nombre que le da tu teclado.",
    },
    "fr": {
        "title": "Commandes de Cherry",
        "desc": "Piloter le Stratos-900 et l’Aegis-X, conduire les navires classe Leviathan et Dreadnought : les touches par défaut et leur rôle.",
        "note": "Ce sont les touches par défaut de {release}. [W] [A] [S] [D] et « S’accroupir » sont les touches « {movement} » du jeu lui-même, et les clics gauche et droit ses commandes attaquer et utiliser ; [LALT] se trouve sous « {flight} », [H] et [Y] sous « {helm} ». Toutes se modifient dans {path}.",
        "layout": "Les touches sont désignées par leur place sur un clavier américain (QWERTY) : sur un clavier AZERTY, par exemple, les touches appelées ici W, A, S et D sont Z, Q, S et D. « {keybinds} » affiche chaque touche sous le nom que lui donne votre clavier.",
    },
    "zh": {
        "title": "Cherry 操作方法",
        "desc": "驾驶 Stratos-900 与 Aegis-X，操纵 Leviathan 级与 Dreadnought 级舰船：默认按键及其作用。",
        "note": "以下为 {release} 的默认按键。[W] [A] [S] [D] 与“潜行”是游戏自身“{movement}”类的按键，左键和右键是游戏自身的攻击与使用；[LALT] 位于“{flight}”中，[H] 与 [Y] 位于“{helm}”中。均可在{path}中修改。",
        "layout": "按键以其在美式键盘上的位置命名。你的键盘可能给同一个键标注不同的名称；“{keybinds}”会以你的键盘所用的名称显示每个键。",
    },
    "ko": {
        "title": "Cherry 조작 방법",
        "desc": "Stratos-900과 Aegis-X를 조종하고 Leviathan급과 Dreadnought급을 운항하는 법: 기본 키와 그 기능.",
        "note": "{release}의 기본 키입니다. [W] [A] [S] [D]와 ‘웅크리기’는 게임 자체의 “{movement}” 키이고, 왼쪽 클릭과 오른쪽 클릭은 게임의 공격과 사용입니다. [LALT]는 “{flight}”에, [H]와 [Y]는 “{helm}”에 있습니다. 모두 {path}에서 바꿀 수 있습니다.",
        "layout": "키 이름은 미국식 키보드에서의 위치를 기준으로 적었습니다. 사용하는 키보드에서는 같은 키가 다르게 표시될 수 있으며, “{keybinds}” 화면에는 그 키보드에서의 이름으로 나옵니다.",
    },
    "pt-br": {
        "title": "Controles do Cherry",
        "desc": "Como pilotar o Stratos-900 e o Aegis-X e comandar os navios classe Leviathan e Dreadnought: as teclas padrão e o que fazem.",
        "note": "Estas são as teclas padrão do {release}. [W] [A] [S] [D] e “Agachar” são as teclas de “{movement}” do próprio jogo, e os cliques esquerdo e direito são o atacar e o usar do jogo; [LALT] fica em “{flight}”, e [H] e [Y], em “{helm}”. Todas podem ser alteradas em {path}.",
        "layout": "As teclas são indicadas pela posição num teclado americano. O seu pode marcar a mesma tecla de outro jeito; “{keybinds}” mostra cada uma com o nome que o seu teclado dá a ela.",
    },
    "it": {
        "title": "Comandi di Cherry",
        "desc": "Come pilotare lo Stratos-900 e l’Aegis-X e condurre le navi classe Leviathan e Dreadnought: i tasti predefiniti e cosa fanno.",
        "note": "Questi sono i tasti predefiniti di {release}. [W] [A] [S] [D] e «Accovacciati» sono i tasti «{movement}» del gioco stesso, e il clic sinistro e quello destro sono il suo attaccare e usare; [LALT] è sotto «{flight}», [H] e [Y] sotto «{helm}». Puoi cambiarli tutti in {path}.",
        "layout": "I tasti sono indicati in base alla loro posizione su una tastiera americana. La tua può etichettare lo stesso tasto in modo diverso; «{keybinds}» mostra ciascuno con il nome che gli dà la tua tastiera.",
    },
    "ar": {
        "title": "طريقة التحكم في Cherry",
        "desc": "كيف تقود Stratos-900 وAegis-X وتُبحر بسفن فئتي Leviathan وDreadnought: المفاتيح الافتراضية وما تفعله.",
        "note": "هذه هي المفاتيح الافتراضية في {release}. [W] [A] [S] [D] و«التسلل» هي مفاتيح «{movement}» في اللعبة نفسها، والنقر الأيسر والأيمن هما الهجوم والاستخدام فيها؛ [LALT] ضمن «{flight}»، و[H] و[Y] ضمن «{helm}». يمكنك تغييرها كلها من {path}.",
        "layout": "أسماء المفاتيح هنا بحسب مواضعها في لوحة المفاتيح الأمريكية. قد تحمل لوحتك المفتاح نفسه باسم آخر، وتعرض شاشة «{keybinds}» كل مفتاح بالاسم الذي تعطيه له لوحتك.",
    },
    "ru": {
        "title": "Управление в Cherry",
        "desc": "Как летать на Stratos-900 и Aegis-X и водить корабли классов Leviathan и Dreadnought: клавиши по умолчанию и что они делают.",
        "note": "Это клавиши {release} по умолчанию. [W] [A] [S] [D] и «Красться» — собственные клавиши игры из группы «{movement}», а левый и правый клик — её атака и использование; [LALT] — в группе «{flight}», [H] и [Y] — в группе «{helm}». Изменить любую можно в разделе {path}.",
        "layout": "Клавиши названы по их месту на американской клавиатуре. На вашей та же клавиша может быть подписана иначе; в разделе «{keybinds}» каждая показана так, как её называет ваша раскладка.",
    },
    "id": {
        "title": "Kontrol Cherry",
        "desc": "Cara menerbangkan Stratos-900 dan Aegis-X serta melayarkan kapal kelas Leviathan dan Dreadnought: tombol bawaan dan fungsinya.",
        "note": "Ini tombol bawaan {release}. [W] [A] [S] [D] dan “Jongkok” adalah tombol “{movement}” milik game itu sendiri, sedangkan klik kiri dan kanan adalah serang dan gunakan milik game; [LALT] ada di “{flight}”, [H] dan [Y] di “{helm}”. Semuanya bisa diubah di {path}.",
        "layout": "Tombol disebut menurut letaknya pada papan ketik AS. Papan ketikmu bisa menandai tombol yang sama secara berbeda; “{keybinds}” menampilkan setiap tombol dengan nama dari papan ketikmu.",
    },
    "de": {
        "title": "Cherry-Steuerung",
        "desc": "So fliegst du die Stratos-900 und die Aegis-X und fährst die Schiffe der Leviathan- und der Dreadnought-Klasse: die Standardtasten und was sie tun.",
        "note": "Das sind die Standardtasten von {release}. [W] [A] [S] [D] und „Schleichen“ sind die eigenen „{movement}“-Tasten des Spiels, Links- und Rechtsklick sein Angreifen und Benutzen; [LALT] steht unter „{flight}“, [H] und [Y] unter „{helm}“. Ändern kannst du alle unter {path}.",
        "layout": "Die Tasten sind nach ihrer Lage auf einer US-Tastatur benannt. Auf einer deutschen QWERTZ-Tastatur sind zum Beispiel Y und Z vertauscht: Die hier Y genannte Taste trägt dort die Aufschrift Z. „{keybinds}“ zeigt jede Taste unter dem Namen, den deine Tastatur ihr gibt.",
    },
    "tr": {
        "title": "Cherry kontrolleri",
        "desc": "Stratos-900 ve Aegis-X nasıl uçurulur, Leviathan ve Dreadnought sınıfı gemiler nasıl yönetilir: varsayılan tuşlar ve işlevleri.",
        "note": "Bunlar {release} sürümünün varsayılan tuşlarıdır. [W] [A] [S] [D] ve “Eğilme”, oyunun kendi “{movement}” tuşlarıdır; sol ve sağ tık da oyunun saldırı ve kullanma işlevleridir. [LALT] “{flight}” altında, [H] ve [Y] ise “{helm}” altındadır. Hepsini {path} içinde değiştirebilirsiniz.",
        "layout": "Tuşlar ABD klavyesindeki yerlerine göre adlandırılmıştır. Sizin klavyenizde aynı tuş başka bir adla işaretli olabilir; “{keybinds}” her tuşu klavyenizin verdiği adla gösterir.",
    },
}

TOKEN = re.compile(r"\[([^\]]+)\]|⟨([^⟩]+)⟩|\{(path|release)\}")
# Product names never break at their hyphen ("Stratos-" / "900" on a phone).
NO_BREAK = ("Stratos-900", "Aegis-X")
VERSION = re.compile(r"\b\d+\.\d+\.\d+\b")
ARABIC = re.compile(r"[؀-ۿ]")


def _keys(text: str) -> list[str]:
    """The keys a string names, in order ([...] only)."""
    return [m.group(1) for m in TOKEN.finditer(text) if m.group(1) is not None]


def _fill(text: str, lang: str) -> str:
    """Put the per-language names into a note; {path} stays for _inline, which renders it."""
    flight, helm = CATEGORIES.get(lang, CATEGORIES_EN)
    return (text.replace("{movement}", MOVEMENT[lang]).replace("{flight}", flight)
            .replace("{helm}", helm).replace("{keybinds}", PATH[lang][2]))


def _inline(text: str, lang: str) -> str:
    """Escape the text; [K] becomes a key cap, the angle brackets an English span, {path} the menu path."""
    out, at = [], 0
    for m in TOKEN.finditer(text):
        out.append(esc(text[at:m.start()]))
        if m.group(1) is not None:
            label = KEYCAP[lang].get(m.group(1), m.group(1))
            # Keys read left to right on every page, except a name written in Arabic, which
            # reads the way the Arabic game prints it ("Alt الأيسر").
            direction = "rtl" if ARABIC.search(label) else "ltr"
            out.append('<kbd class="cc-key" dir="%s">%s</kbd>' % (direction, esc(label)))
        elif m.group(2) is not None:
            out.append('<span lang="en" dir="ltr">%s</span>' % esc(m.group(2)))
        elif m.group(3) == "release":
            # One left-to-right unit, so the Arabic page prints "Cherry 1.1.2", not "1.1.2 Cherry".
            out.append('<span lang="en" dir="ltr">Cherry %s</span>' % esc(CONTROLS_FOR))
        else:
            out.append('<span class="cc-path">%s</span>' % " › ".join(
                '<span class="cc-step">%s</span>' % esc(step) for step in PATH[lang]))
        at = m.end()
    out.append(esc(text[at:]))
    html = "".join(out)
    for name in NO_BREAK:
        html = html.replace(esc(name), '<span class="cc-nb">%s</span>' % esc(name))
    return html


def _slots(lang: str) -> list[tuple[str, str]]:
    """Every structured string of one language's cards, with a stable name for where it sits."""
    c = CONTROLS[lang]
    slots = []
    for card in ("air", "sea"):
        part = c[card]
        slots.append(("%s.title" % card, part["title"]))
        slots += [("%s.facts[%d]" % (card, i), fact) for i, fact in enumerate(part["facts"])]
        for i, (action, how) in enumerate(part["keys"]):
            slots += [("%s.keys[%d].action" % (card, i), action), ("%s.keys[%d].how" % (card, i), how)]
        for i, (title, items) in enumerate(part["lists"]):
            slots.append(("%s.lists[%d].title" % (card, i), title))
            slots += [("%s.lists[%d][%d]" % (card, i, j), item) for j, item in enumerate(items)]
    return slots


def problems_in(langs: list[str]) -> list[str]:
    """Everything that would make a page wrong in a way nothing else would notice."""
    problems = []
    english = [(name, sorted(_keys(text))) for name, text in _slots("en")]
    named = {k for _name, text in _slots("en") for k in _keys(text)}
    for missing in sorted((MOD_KEYS | MOVEMENT_KEYS) - named):
        problems.append("en: the cards never name the key %r -- a binding the game has is missing from the page" % missing)
    for lang in langs:
        for table, where in ((CONTROLS, "CONTROLS"), (INTRO, "INTRO"), (PATH, "PATH"), (KEYCAP, "KEYCAP"),
                             (MOVEMENT, "MOVEMENT")):
            if lang not in table:
                problems.append("%s: no %s entry (no fallback by design)" % (lang, where))
        if any(lang not in table for table in (CONTROLS, INTRO, PATH, KEYCAP, MOVEMENT)):
            continue
        mine = [(name, sorted(_keys(text))) for name, text in _slots(lang)]
        if [name for name, _k in mine] != [name for name, _k in english]:
            problems.append("%s: the cards do not have the English shape" % lang)
            continue
        for (name, keys), (_n, want) in zip(mine, english):
            if keys != want:
                problems.append("%s %s: names the keys %s where English names %s" % (lang, name, keys, want))
        texts = [text for _name, text in _slots(lang)] + [INTRO[lang][k] for k in ("title", "desc", "note", "layout")]
        for text in texts:
            for key in _keys(text):
                if key not in KNOWN_KEYS:
                    problems.append("%s: [%s] is not a key this page knows (%r)" % (lang, key, text[:60]))
            # A line about one release ("In 1.1.2, astern gives no thrust") must not survive onto
            # the page of the next: every version the copy names is the one it was read from.
            for version in VERSION.findall(text):
                if version != CONTROLS_FOR:
                    problems.append("%s: the copy speaks of %s, but the controls were read from %s (%r)"
                                    % (lang, version, CONTROLS_FOR, text[:60]))
        if "{release}" not in INTRO[lang]["note"]:
            problems.append("%s: the note does not say which version the page describes" % lang)
        for key in ("title", "desc", "note", "layout"):
            if not INTRO[lang].get(key):
                problems.append("%s: INTRO has no %s" % (lang, key))
        if lang != "en" and INTRO[lang]["note"] == INTRO["en"]["note"]:
            problems.append("%s: the note is the English one" % lang)
    return problems


# ★ NOT a format string, for the reason build_cherry.py gives: __ROOT__ is replaced with
#   str.replace(), and main() refuses a page that still holds it.
HEAD = """<link rel="stylesheet" href="__ROOT__assets/css/cherry-tokens.css">
<style>
.cc-wrap{background:var(--ch-bg);color:var(--ch-text);padding:3.5rem 1rem 5rem;
  margin:0 calc(50% - 50vw);width:100vw}
.cc-inner{max-width:48rem;margin:0 auto}
.cc-eyebrow{margin:0 0 .6rem;font-size:.8rem;letter-spacing:.16em;text-transform:uppercase}
.cc-eyebrow a{color:var(--ch-petal-deep);text-decoration:none;display:inline-flex;
  align-items:center;min-height:var(--tap,44px)}
.cc-eyebrow a:hover,.cc-eyebrow a:focus-visible{color:var(--ch-petal);text-decoration:underline;
  text-underline-offset:.3em}
.cc-eyebrow a:focus-visible{outline:2px solid var(--ch-petal);outline-offset:3px}
.cc-title{font-size:clamp(2.2rem,6vw,3.3rem);line-height:1.1;margin:0 0 1.2rem;
  letter-spacing:-.01em;color:var(--ch-petal)}
.cc-note{margin:0 0 .75rem;font-size:.98rem;line-height:1.8;color:var(--ch-text)}
.cc-note.cc-layout{color:var(--ch-text-muted);font-size:.92rem}
.cc-path{white-space:normal}
.cc-nb{white-space:nowrap}
.cc-step{font-weight:600;color:var(--ch-petal)}
.cc-card{margin:2.25rem 0 0;padding:clamp(1.25rem,4vw,2rem);border-radius:18px;
  background:var(--ch-bg-lift);border:1px solid var(--ch-line)}
.cc-h2{margin:0 0 1rem;padding:0;border:0;font-size:clamp(1.2rem,3.4vw,1.45rem);
  line-height:1.4;color:var(--ch-petal)}
/* style.css marks every h2 with the site's glow-green bar; these pages are in the Cherry colours */
.cc-h2::before{content:none}
.cc-h3{margin:1.75rem 0 .6rem;padding:0;border:0;font-size:1rem;line-height:1.5;
  color:var(--ch-petal-deep)}
.cc-list{margin:0;padding-inline-start:1.2rem;line-height:1.8}
.cc-list li{margin:.35rem 0;color:var(--ch-text)}
.cc-list li::marker{color:var(--ch-blush)}
.cc-keys{width:100%;margin:1.25rem 0 0;border-collapse:collapse;font-size:.95rem;
  line-height:1.7}
/* style.css sets every th in small muted capitals (and uppercase Turkish would print a
   dotted capital I); these are action names, read as sentences, in the page's own case */
.cc-keys th,.cc-keys td{padding:.7rem 0;border-top:1px solid var(--ch-line);border-bottom:0;
  vertical-align:top;text-align:start;background:none}
.cc-keys th{width:34%;padding-inline-end:1rem;font-weight:600;color:var(--ch-text);
  font-size:inherit;text-transform:none;letter-spacing:normal}
.cc-keys td{color:var(--ch-text)}
.cc-key{display:inline-block;min-width:1.9em;margin:0 .1em;padding:0 .45em;
  border:1px solid rgba(__HALO_RGB__,.5);border-bottom-width:2px;border-radius:6px;
  background:rgba(__HALO_RGB__,.08);color:var(--ch-petal);text-align:center;
  font:600 .86em/1.65 ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  white-space:nowrap;box-shadow:none}
@media (max-width:34rem){
  .cc-keys th,.cc-keys td{display:block;width:auto;padding-inline-end:0}
  .cc-keys th{padding-bottom:.1rem}
  .cc-keys td{border-top:0;padding-top:0}
}
</style>"""
HALO_RGB = "232,180,198"


def head_css(root: str) -> str:
    return HEAD.replace("__ROOT__", root).replace("__HALO_RGB__", HALO_RGB)


def _card(lang: str, key: str) -> str:
    part = CONTROLS[lang][key]
    anchor = "cc-" + key
    facts = "".join("<li>%s</li>" % _inline(fact, lang) for fact in part["facts"])
    rows = "".join('<tr><th scope="row">%s</th><td>%s</td></tr>' % (_inline(action, lang), _inline(how, lang))
                   for action, how in part["keys"])
    lists = "".join('<h3 class="cc-h3">%s</h3><ul class="cc-list">%s</ul>'
                    % (_inline(title, lang), "".join("<li>%s</li>" % _inline(item, lang) for item in items))
                    for title, items in part["lists"])
    return ('<section class="cc-card" aria-labelledby="%s"><h2 class="cc-h2" id="%s">%s</h2>'
            '<ul class="cc-list">%s</ul><table class="cc-keys"><tbody>%s</tbody></table>%s</section>'
            % (anchor, anchor, _inline(part["title"], lang), facts, rows, lists))


def build_body(lang: str) -> str:
    intro = INTRO[lang]
    return ('<div class="cc-wrap"><div class="cc-inner">'
            '<p class="cc-eyebrow"><a href="../%s" lang="en" dir="ltr">Cherry</a></p>'
            '<h1 class="cc-title">%s</h1>'
            '<p class="cc-note">%s</p><p class="cc-note cc-layout">%s</p>'
            '%s%s</div></div>'
            % (BRAND_SECTION, esc(CONTROLS[lang]["heading"]), _inline(_fill(intro["note"], lang), lang),
               _inline(_fill(intro["layout"], lang), lang), _card(lang, "air"), _card(lang, "sea")))


def link_label(lang: str) -> str:
    """The brand page's link to this one says what this page's heading says (build_cherry.py)."""
    return CONTROLS[lang]["heading"]


def _newest_release() -> str | None:
    found = [RELEASE_RE.match(p.name) for p in (ROOT / "downloads").glob("Cherry_MODs_v*.zip")]
    versions = [m.group("ver") for m in found if m]
    return max(versions, key=lambda v: tuple(int(x) for x in v.split(".")), default=None)


def main() -> int:
    langs = available_langs()
    newest = _newest_release()
    if newest != CONTROLS_FOR:
        raise SystemExit(
            "ERROR: build_cherry_controls: the controls were read from Cherry %s's code, but the newest "
            "Cherry zip in downloads/ is %s. Read the keys and rules again against that version's code, "
            "correct the copy, then move CONTROLS_FOR." % (CONTROLS_FOR, newest))
    problems = problems_in(langs)
    if problems:
        raise SystemExit("ERROR: build_cherry_controls:\n  " + "\n  ".join(problems))
    for lang in langs:
        root = asset_root_prefix(1, lang)
        body = build_body(lang)
        # Nothing of the markup may survive into what a reader sees, and nothing may fall back.
        text_only = re.sub(r"<[^>]+>", "", body)
        for leftover in ("[", "]", "⟨", "⟩", "{", "}", "__"):
            if leftover in text_only:
                raise SystemExit("ERROR: build_cherry_controls: %s shows %r to the reader." % (lang, leftover))
        html = page(
            lang=lang,
            section=SECTION,
            title=INTRO[lang]["title"],
            description=INTRO[lang]["desc"],
            active="cherry",
            body=body,
            depth=1,
            extra_head=head_css(root),
        )
        if "__ROOT__" in html or "__HALO_RGB__" in html or "{{" in html:
            raise SystemExit("ERROR: build_cherry_controls: %s still holds a substitution token." % lang)
        target = ROOT / ("" if lang == "ja" else lang) / SECTION / "index.html"
        for rel in (root + "assets/css/cherry-tokens.css", "../" + BRAND_SECTION + "index.html"):
            if not (target.parent / rel).resolve().is_file():
                raise SystemExit("ERROR: build_cherry_controls: %s links %s, which is not there." % (lang, rel))
        # 1.1.3's page names 29 keys in every language (the note 7, the cards 22: counted from the English copy; every
        # language carries the same keys, problems_in). A page that renders fewer than 25 lost part of a card; 1.1.2's
        # floor of 40 was for its larger key set.
        if html.count('<kbd class="cc-key"') < 25:
            raise SystemExit("ERROR: build_cherry_controls: %s has fewer than 25 key caps -- the cards "
                             "did not render." % lang)
        write_page(lang, SECTION, html)
    # The brand page's one way here must arrive here, in every language (build_cherry.py
    # writes it before this runs; a link to a page that is not there is a quiet 404).
    for lang in langs:
        brand = ROOT / ("" if lang == "ja" else lang) / BRAND_SECTION / "index.html"
        link = '<a class="ch-more-link" href="../%s">%s</a>' % (SECTION, esc(link_label(lang)))
        if link not in brand.read_text(encoding="utf-8"):
            raise SystemExit("ERROR: build_cherry_controls: %s has no link %r." % (brand.relative_to(ROOT), link))
        here = (brand.parent / ("../" + SECTION) / "index.html").resolve()
        if here != (ROOT / ("" if lang == "ja" else lang) / SECTION / "index.html").resolve() or not here.is_file():
            raise SystemExit("ERROR: build_cherry_controls: %s's link resolves to %s." % (lang, here))
    print("build_cherry_controls: %d language(s), controls read from Cherry %s"
          % (len(langs), CONTROLS_FOR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
