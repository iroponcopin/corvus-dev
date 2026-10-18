import type { Lang } from "@/lib/wiki-types";

/**
 * Copy for the home page's V2 sections (the closing line of Act III, the Bento grid, The Lineup,
 * the telemetry drawer), in all 13 languages. Typed as a record over Lang, so a missing language
 * is a compile error. Never use the word for "brand" here: the copy says "model".
 */
export interface HomeV2 {
  /** The line at the end of Act III. */
  closing: string;
  bento: { title: string; lede: string; open: string; close: string; modal: string; pill: string };
  lineup: { title: string; lede: string; scrub: string; open: string; power: string; blade: string };
  telemetry: { inspect: string; payload: string; bytes: string; modified: string; truncated: string; drawer: string };
}

export const HOME_V2: Record<Lang, HomeV2> = {
  ja: {
    closing: "Corvus — すべてのリリースが還る場所",
    bento: { title: "最新リリース", lede: "稼働中の各モデルの最新版です。版数は公開中のフィードから読みます。", open: "変更点を読む", close: "閉じる", modal: "変更履歴", pill: "最新" },
    lineup: { title: "ラインナップ", lede: "ホバーかスクロールで、各モデルの色がページを染めます。", scrub: "横にスクロール", open: "開く", power: "電力グリッド", blade: "刃のコンボ" },
    telemetry: { inspect: "ペイロードを見る", payload: "ペイロード", bytes: "バイト", modified: "最終更新", truncated: "先頭 4 KB を表示", drawer: "閉じる" },
  },
  en: {
    closing: "Corvus — Where Every Release Returns",
    bento: { title: "Latest releases", lede: "The newest version of each live model. Version pills read the published feed.", open: "Read the notes", close: "Close", modal: "Changelog entry", pill: "Latest" },
    lineup: { title: "The Lineup", lede: "Hover or scroll, and each model tints the page with its own colour.", scrub: "Scroll sideways", open: "Open", power: "Power grid", blade: "Blade combo" },
    telemetry: { inspect: "Inspect payload", payload: "Payload", bytes: "Bytes", modified: "Last-modified", truncated: "First 4 KB shown", drawer: "Close" },
  },
  es: {
    closing: "Corvus — Donde cada versión regresa",
    bento: { title: "Últimas versiones", lede: "La versión más reciente de cada modelo activo. Las etiquetas leen el feed publicado.", open: "Leer las notas", close: "Cerrar", modal: "Entrada del registro de cambios", pill: "Última" },
    lineup: { title: "La alineación", lede: "Pasa el cursor o desplázate y cada modelo tiñe la página con su color.", scrub: "Desplázate en horizontal", open: "Abrir", power: "Red de energía", blade: "Combo de hoja" },
    telemetry: { inspect: "Inspeccionar carga", payload: "Carga", bytes: "Bytes", modified: "Última modificación", truncated: "Se muestran los primeros 4 KB", drawer: "Cerrar" },
  },
  fr: {
    closing: "Corvus — Là où chaque version revient",
    bento: { title: "Dernières versions", lede: "La version la plus récente de chaque modèle actif. Les pastilles lisent le flux publié.", open: "Lire les notes", close: "Fermer", modal: "Entrée du journal des modifications", pill: "Dernière" },
    lineup: { title: "La gamme", lede: "Survolez ou faites défiler : chaque modèle teinte la page de sa couleur.", scrub: "Défilez à l'horizontale", open: "Ouvrir", power: "Grille d'énergie", blade: "Combo de lame" },
    telemetry: { inspect: "Inspecter la charge", payload: "Charge", bytes: "Octets", modified: "Dernière modification", truncated: "4 Ko affichés", drawer: "Fermer" },
  },
  zh: {
    closing: "Corvus — 每一次发布都回归之处",
    bento: { title: "最新版本", lede: "每个在营模型的最新版本。版本标签读取已发布的数据源。", open: "阅读更新说明", close: "关闭", modal: "更新日志条目", pill: "最新" },
    lineup: { title: "阵容", lede: "悬停或滚动，每个模型都会以自己的颜色染亮页面。", scrub: "横向滚动", open: "打开", power: "能量网格", blade: "刀刃连击" },
    telemetry: { inspect: "查看负载", payload: "负载", bytes: "字节", modified: "最后修改", truncated: "仅显示前 4 KB", drawer: "关闭" },
  },
  ko: {
    closing: "Corvus — 모든 릴리스가 돌아오는 곳",
    bento: { title: "최신 릴리스", lede: "운영 중인 각 모델의 최신 버전입니다. 버전 표시는 게시된 피드에서 읽습니다.", open: "변경 내용 보기", close: "닫기", modal: "변경 기록 항목", pill: "최신" },
    lineup: { title: "라인업", lede: "마우스를 올리거나 스크롤하면 각 모델의 색이 페이지를 물들입니다.", scrub: "가로로 스크롤", open: "열기", power: "전력 그리드", blade: "블레이드 콤보" },
    telemetry: { inspect: "페이로드 보기", payload: "페이로드", bytes: "바이트", modified: "최종 수정", truncated: "처음 4KB만 표시", drawer: "닫기" },
  },
  "pt-br": {
    closing: "Corvus — Onde cada lançamento retorna",
    bento: { title: "Últimos lançamentos", lede: "A versão mais recente de cada modelo ativo. Os selos leem o feed publicado.", open: "Ler as notas", close: "Fechar", modal: "Entrada do registro de alterações", pill: "Última" },
    lineup: { title: "A linha de produtos", lede: "Passe o cursor ou role: cada modelo tinge a página com a sua cor.", scrub: "Role na horizontal", open: "Abrir", power: "Grade de energia", blade: "Combo de lâmina" },
    telemetry: { inspect: "Inspecionar carga", payload: "Carga", bytes: "Bytes", modified: "Última modificação", truncated: "Mostrando os primeiros 4 KB", drawer: "Fechar" },
  },
  it: {
    closing: "Corvus — Dove ogni versione ritorna",
    bento: { title: "Ultime versioni", lede: "La versione più recente di ogni modello attivo. Le etichette leggono il feed pubblicato.", open: "Leggi le note", close: "Chiudi", modal: "Voce del registro modifiche", pill: "Ultima" },
    lineup: { title: "La gamma", lede: "Passa il mouse o scorri: ogni modello tinge la pagina con il suo colore.", scrub: "Scorri in orizzontale", open: "Apri", power: "Griglia di potenza", blade: "Combo della lama" },
    telemetry: { inspect: "Ispeziona payload", payload: "Payload", bytes: "Byte", modified: "Ultima modifica", truncated: "Mostrati i primi 4 KB", drawer: "Chiudi" },
  },
  ar: {
    closing: "Corvus — حيث يعود كل إصدار",
    bento: { title: "أحدث الإصدارات", lede: "أحدث نسخة من كل نموذج نشط. تقرأ الشارات الإصدار من الموجز المنشور.", open: "اقرأ الملاحظات", close: "إغلاق", modal: "مدخل سجل التغييرات", pill: "الأحدث" },
    lineup: { title: "التشكيلة", lede: "مرّر المؤشر أو تصفّح، فيلوّن كل نموذج الصفحة بلونه.", scrub: "تصفّح أفقياً", open: "فتح", power: "شبكة الطاقة", blade: "تركيبة النصل" },
    telemetry: { inspect: "فحص الحمولة", payload: "الحمولة", bytes: "بايت", modified: "آخر تعديل", truncated: "عرض أول 4 كيلوبايت", drawer: "إغلاق" },
  },
  ru: {
    closing: "Corvus — Куда возвращается каждый релиз",
    bento: { title: "Последние релизы", lede: "Самая свежая версия каждой действующей линейки. Метки версий берутся из опубликованной ленты.", open: "Читать заметки", close: "Закрыть", modal: "Запись журнала изменений", pill: "Последняя" },
    lineup: { title: "Линейка", lede: "Наведите курсор или прокрутите: каждая модель окрашивает страницу своим цветом.", scrub: "Прокрутите вбок", open: "Открыть", power: "Энергосеть", blade: "Комбо клинка" },
    telemetry: { inspect: "Полезная нагрузка", payload: "Полезная нагрузка", bytes: "Байты", modified: "Изменён", truncated: "Показаны первые 4 КБ", drawer: "Закрыть" },
  },
  id: {
    closing: "Corvus — Tempat setiap rilis pulang",
    bento: { title: "Rilis terbaru", lede: "Versi terbaru tiap model yang aktif. Label versi membaca umpan yang terbit.", open: "Baca catatannya", close: "Tutup", modal: "Entri catatan perubahan", pill: "Terbaru" },
    lineup: { title: "Lini produk", lede: "Arahkan kursor atau gulir, dan tiap model mewarnai halaman dengan warnanya.", scrub: "Gulir ke samping", open: "Buka", power: "Jaringan daya", blade: "Kombo bilah" },
    telemetry: { inspect: "Periksa payload", payload: "Payload", bytes: "Byte", modified: "Terakhir diubah", truncated: "4 KB pertama ditampilkan", drawer: "Tutup" },
  },
  de: {
    closing: "Corvus — Wo jede Veröffentlichung heimkehrt",
    bento: { title: "Neueste Versionen", lede: "Die jeweils neueste Version jedes aktiven Modells. Die Versionsmarken lesen den veröffentlichten Feed.", open: "Hinweise lesen", close: "Schließen", modal: "Eintrag im Änderungsprotokoll", pill: "Neueste" },
    lineup: { title: "Das Lineup", lede: "Mit Zeiger oder Scrollen färbt jedes Modell die Seite in seiner Farbe.", scrub: "Seitlich scrollen", open: "Öffnen", power: "Energienetz", blade: "Klingen-Kombo" },
    telemetry: { inspect: "Payload prüfen", payload: "Payload", bytes: "Bytes", modified: "Zuletzt geändert", truncated: "Erste 4 KB angezeigt", drawer: "Schließen" },
  },
  tr: {
    closing: "Corvus — Her sürümün geri döndüğü yer",
    bento: { title: "Son sürümler", lede: "Her etkin modelin en yeni sürümü. Sürüm etiketleri yayımlanan beslemeden okunur.", open: "Notları oku", close: "Kapat", modal: "Değişiklik günlüğü kaydı", pill: "Son" },
    lineup: { title: "Ürün dizisi", lede: "Üzerine gelin ya da kaydırın; her model sayfayı kendi rengiyle boyar.", scrub: "Yatay kaydırın", open: "Aç", power: "Güç ağı", blade: "Bıçak kombosu" },
    telemetry: { inspect: "Yükü incele", payload: "Yük", bytes: "Bayt", modified: "Son değişiklik", truncated: "İlk 4 KB gösteriliyor", drawer: "Kapat" },
  },
};
