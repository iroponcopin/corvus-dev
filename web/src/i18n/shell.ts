import type { Lang } from "@/lib/wiki-types";

/**
 * The site shell's own copy (V2 overhaul, pass 1): the loading screen shown once per session and the
 * Cmd/Ctrl+K palette. Thirteen languages, written for this release; a native speaker has not yet read them.
 * The word for a model is "model" throughout; "brand" never appears in any language.
 */
export interface Shell {
  loader: {
    /** Top-left wordmark line, top-right muted line, centre eyebrow, centre title, bottom-left line. */
    top: string;
    muted: string;
    eyebrow: string;
    title: string;
    bottom: string;
  };
  palette: {
    open: string;
    placeholder: string;
    label: string;
    empty: string;
    hint: string;
    close: string;
    models: string;
    changelog: string;
    recipes: string;
    results: string;
  };
}

export const SHELL: Record<Lang, Shell> = {
  ja: {
    loader: { top: "CORVUS", muted: "すべてのリリースが戻る場所", eyebrow: "部屋を準備しています", title: "すべてのリリースが、ここに戻る。", bottom: "体験を読み込んでいます" },
    palette: { open: "検索", placeholder: "モデル・更新履歴・レシピを検索", label: "検索", empty: "一致する項目はありません", hint: "↑↓ で移動 · Enter で開く · Esc で閉じる", close: "閉じる", models: "モデル", changelog: "更新履歴", recipes: "レシピ", results: "検索結果" },
  },
  en: {
    loader: { top: "CORVUS", muted: "Where every release returns", eyebrow: "PREPARING THE ROOM", title: "Where every release returns.", bottom: "LOADING EXPERIENCE" },
    palette: { open: "Search", placeholder: "Search models, changelogs and recipes", label: "Search", empty: "No matches", hint: "↑↓ to move · Enter to open · Esc to close", close: "Close", models: "Models", changelog: "Changelog", recipes: "Recipes", results: "Results" },
  },
  es: {
    loader: { top: "CORVUS", muted: "Donde vuelve cada versión", eyebrow: "PREPARANDO LA SALA", title: "Donde vuelve cada versión.", bottom: "CARGANDO LA EXPERIENCIA" },
    palette: { open: "Buscar", placeholder: "Busca modelos, cambios y recetas", label: "Buscar", empty: "Sin coincidencias", hint: "↑↓ para moverte · Intro para abrir · Esc para cerrar", close: "Cerrar", models: "Modelos", changelog: "Historial", recipes: "Recetas", results: "Resultados" },
  },
  fr: {
    loader: { top: "CORVUS", muted: "Là où chaque version revient", eyebrow: "PRÉPARATION DE LA SALLE", title: "Là où chaque version revient.", bottom: "CHARGEMENT DE L’EXPÉRIENCE" },
    palette: { open: "Rechercher", placeholder: "Rechercher modèles, mises à jour et recettes", label: "Rechercher", empty: "Aucun résultat", hint: "↑↓ pour naviguer · Entrée pour ouvrir · Échap pour fermer", close: "Fermer", models: "Modèles", changelog: "Mises à jour", recipes: "Recettes", results: "Résultats" },
  },
  zh: {
    loader: { top: "CORVUS", muted: "每一次发布都会回归", eyebrow: "正在准备场景", title: "每一次发布都会回归。", bottom: "正在加载体验" },
    palette: { open: "搜索", placeholder: "搜索模型、更新日志和配方", label: "搜索", empty: "没有匹配项", hint: "↑↓ 移动 · Enter 打开 · Esc 关闭", close: "关闭", models: "模型", changelog: "更新日志", recipes: "配方", results: "结果" },
  },
  ko: {
    loader: { top: "CORVUS", muted: "모든 릴리스가 돌아오는 곳", eyebrow: "공간을 준비하는 중", title: "모든 릴리스가 돌아옵니다.", bottom: "경험을 불러오는 중" },
    palette: { open: "검색", placeholder: "모델, 업데이트 기록, 레시피 검색", label: "검색", empty: "일치하는 항목이 없습니다", hint: "↑↓ 이동 · Enter 열기 · Esc 닫기", close: "닫기", models: "모델", changelog: "업데이트 기록", recipes: "레시피", results: "결과" },
  },
  "pt-br": {
    loader: { top: "CORVUS", muted: "Onde cada versão retorna", eyebrow: "PREPARANDO A SALA", title: "Onde cada versão retorna.", bottom: "CARREGANDO A EXPERIÊNCIA" },
    palette: { open: "Buscar", placeholder: "Buscar modelos, atualizações e receitas", label: "Buscar", empty: "Nenhum resultado", hint: "↑↓ para mover · Enter para abrir · Esc para fechar", close: "Fechar", models: "Modelos", changelog: "Atualizações", recipes: "Receitas", results: "Resultados" },
  },
  it: {
    loader: { top: "CORVUS", muted: "Dove ogni versione ritorna", eyebrow: "PREPARAZIONE DELLA SALA", title: "Dove ogni versione ritorna.", bottom: "CARICAMENTO DELL’ESPERIENZA" },
    palette: { open: "Cerca", placeholder: "Cerca modelli, aggiornamenti e ricette", label: "Cerca", empty: "Nessun risultato", hint: "↑↓ per muoversi · Invio per aprire · Esc per chiudere", close: "Chiudi", models: "Modelli", changelog: "Aggiornamenti", recipes: "Ricette", results: "Risultati" },
  },
  ar: {
    loader: { top: "CORVUS", muted: "حيث تعود كل إصدارة", eyebrow: "تجهيز الغرفة", title: "حيث تعود كل إصدارة.", bottom: "جارٍ تحميل التجربة" },
    palette: { open: "بحث", placeholder: "ابحث في النماذج وسجل التحديثات والوصفات", label: "بحث", empty: "لا توجد نتائج", hint: "↑↓ للتنقل · Enter للفتح · Esc للإغلاق", close: "إغلاق", models: "النماذج", changelog: "سجل التحديثات", recipes: "الوصفات", results: "النتائج" },
  },
  ru: {
    loader: { top: "CORVUS", muted: "Здесь возвращается каждый релиз", eyebrow: "ПОДГОТОВКА ЗАЛА", title: "Здесь возвращается каждый релиз.", bottom: "ЗАГРУЗКА" },
    palette: { open: "Поиск", placeholder: "Поиск по моделям, журналу изменений и рецептам", label: "Поиск", empty: "Ничего не найдено", hint: "↑↓ — перемещение · Enter — открыть · Esc — закрыть", close: "Закрыть", models: "Модели", changelog: "Журнал изменений", recipes: "Рецепты", results: "Результаты" },
  },
  id: {
    loader: { top: "CORVUS", muted: "Tempat setiap rilis kembali", eyebrow: "MENYIAPKAN RUANGAN", title: "Tempat setiap rilis kembali.", bottom: "MEMUAT PENGALAMAN" },
    palette: { open: "Cari", placeholder: "Cari model, riwayat pembaruan, dan resep", label: "Cari", empty: "Tidak ada hasil", hint: "↑↓ untuk bergerak · Enter untuk membuka · Esc untuk menutup", close: "Tutup", models: "Model", changelog: "Riwayat pembaruan", recipes: "Resep", results: "Hasil" },
  },
  de: {
    loader: { top: "CORVUS", muted: "Wo jede Version zurückkehrt", eyebrow: "DER RAUM WIRD VORBEREITET", title: "Wo jede Version zurückkehrt.", bottom: "ERLEBNIS WIRD GELADEN" },
    palette: { open: "Suche", placeholder: "Modelle, Changelogs und Rezepte durchsuchen", label: "Suche", empty: "Keine Treffer", hint: "↑↓ bewegen · Enter öffnen · Esc schließen", close: "Schließen", models: "Modelle", changelog: "Changelog", recipes: "Rezepte", results: "Ergebnisse" },
  },
  tr: {
    loader: { top: "CORVUS", muted: "Her sürümün döndüğü yer", eyebrow: "ODA HAZIRLANIYOR", title: "Her sürümün döndüğü yer.", bottom: "DENEYİM YÜKLENİYOR" },
    palette: { open: "Ara", placeholder: "Modelleri, güncelleme geçmişini ve tarifleri ara", label: "Ara", empty: "Eşleşme yok", hint: "↑↓ taşı · Enter aç · Esc kapat", close: "Kapat", models: "Modeller", changelog: "Güncelleme geçmişi", recipes: "Tarifler", results: "Sonuçlar" },
  },
};
