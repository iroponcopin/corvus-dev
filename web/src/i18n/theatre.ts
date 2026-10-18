import type { Lang } from "@/lib/wiki-types";

/**
 * The home theatre's own copy (the template's scroll-scrubbed hero, with Corvus content): the hero block, the chapter
 * line above each model, the model link, and the closing Store block. Thirteen languages, no English fallback.
 */
export interface Theatre {
  /** The hero title, two lines (the template's "YOUR CINEMA. / BUILT AT HOME."). */
  title: [string, string];
  lede: string;
  /** The hero CTA: the Store download. */
  cta: string;
  /** "Chapter" before the chapter number. */
  chapter: string;
  /** The link under each model. */
  open: string;
  /** The closing block: title, lede and its CTA reuse `cta`. */
  endTitle: [string, string];
  endLede: string;
  /** The hero's accessible name. */
  label: string;
}

export const THEATRE: Record<Lang, Theatre> = {
  ja: {
    title: ["すべてのリリースが、", "ここに戻る。"],
    lede: "Halia、OUKA、Cherry、Tsubomi。Corvus Store ひとつで、すべてのモデルを入れて、更新して、遊べます。",
    cta: "Corvus Store をダウンロード",
    chapter: "章",
    open: "詳しく見る",
    endTitle: ["ひとつのストア。", "すべてのモデル。"],
    endLede: "Corvus Store が Minecraft とモデルの導入から更新までを引き受けます。macOS と Windows に対応。",
    label: "Corvus の紹介",
  },
  en: {
    title: ["Every release.", "Returns here."],
    lede: "Halia, OUKA, Cherry, Tsubomi. One Corvus Store installs, updates and launches every model.",
    cta: "Download Corvus Store",
    chapter: "Chapter",
    open: "Explore",
    endTitle: ["One store.", "Every model."],
    endLede: "Corvus Store handles Minecraft and every model, from the first install to each update. For macOS and Windows.",
    label: "Corvus introduction",
  },
  es: {
    title: ["Cada versión.", "Vuelve aquí."],
    lede: "Halia, OUKA, Cherry, Tsubomi. Una sola Corvus Store instala, actualiza y abre cada modelo.",
    cta: "Descargar Corvus Store",
    chapter: "Capítulo",
    open: "Explorar",
    endTitle: ["Una tienda.", "Todos los modelos."],
    endLede: "Corvus Store se ocupa de Minecraft y de cada modelo, desde la primera instalación hasta cada actualización. Para macOS y Windows.",
    label: "Presentación de Corvus",
  },
  fr: {
    title: ["Chaque version.", "Revient ici."],
    lede: "Halia, OUKA, Cherry, Tsubomi. Un seul Corvus Store installe, met à jour et lance chaque modèle.",
    cta: "Télécharger Corvus Store",
    chapter: "Chapitre",
    open: "Découvrir",
    endTitle: ["Une boutique.", "Tous les modèles."],
    endLede: "Corvus Store prend en charge Minecraft et chaque modèle, de la première installation à chaque mise à jour. Pour macOS et Windows.",
    label: "Présentation de Corvus",
  },
  zh: {
    title: ["每一次发布，", "都回到这里。"],
    lede: "Halia、OUKA、Cherry、Tsubomi。一个 Corvus Store 即可安装、更新并启动所有模型。",
    cta: "下载 Corvus Store",
    chapter: "章节",
    open: "了解更多",
    endTitle: ["一个商店。", "所有模型。"],
    endLede: "Corvus Store 负责 Minecraft 与每个模型，从首次安装到每次更新。支持 macOS 和 Windows。",
    label: "Corvus 简介",
  },
  ko: {
    title: ["모든 릴리스가", "이곳으로 돌아옵니다."],
    lede: "Halia, OUKA, Cherry, Tsubomi. Corvus Store 하나로 모든 모델을 설치하고, 업데이트하고, 실행합니다.",
    cta: "Corvus Store 다운로드",
    chapter: "챕터",
    open: "자세히 보기",
    endTitle: ["하나의 스토어.", "모든 모델."],
    endLede: "Corvus Store가 Minecraft와 모든 모델을 첫 설치부터 매 업데이트까지 맡습니다. macOS와 Windows 지원.",
    label: "Corvus 소개",
  },
  "pt-br": {
    title: ["Cada versão.", "Volta para cá."],
    lede: "Halia, OUKA, Cherry, Tsubomi. Uma só Corvus Store instala, atualiza e abre cada modelo.",
    cta: "Baixar a Corvus Store",
    chapter: "Capítulo",
    open: "Explorar",
    endTitle: ["Uma loja.", "Todos os modelos."],
    endLede: "A Corvus Store cuida do Minecraft e de cada modelo, da primeira instalação a cada atualização. Para macOS e Windows.",
    label: "Apresentação da Corvus",
  },
  it: {
    title: ["Ogni versione.", "Torna qui."],
    lede: "Halia, OUKA, Cherry, Tsubomi. Un solo Corvus Store installa, aggiorna e avvia ogni modello.",
    cta: "Scarica Corvus Store",
    chapter: "Capitolo",
    open: "Scopri",
    endTitle: ["Un solo store.", "Tutti i modelli."],
    endLede: "Corvus Store gestisce Minecraft e ogni modello, dalla prima installazione a ogni aggiornamento. Per macOS e Windows.",
    label: "Presentazione di Corvus",
  },
  ar: {
    title: ["كل إصدارة", "تعود إلى هنا."],
    lede: "Halia وOUKA وCherry وTsubomi. متجر Corvus Store واحد يثبّت كل نموذج ويحدّثه ويشغّله.",
    cta: "تنزيل Corvus Store",
    chapter: "الفصل",
    open: "استكشف",
    endTitle: ["متجر واحد.", "كل النماذج."],
    endLede: "يتولى Corvus Store أمر Minecraft وكل نموذج، من التثبيت الأول حتى كل تحديث. لنظامي macOS وWindows.",
    label: "تعريف بـ Corvus",
  },
  ru: {
    title: ["Каждый релиз", "возвращается сюда."],
    lede: "Halia, OUKA, Cherry, Tsubomi. Один Corvus Store устанавливает, обновляет и запускает каждую модель.",
    cta: "Скачать Corvus Store",
    chapter: "Глава",
    open: "Подробнее",
    endTitle: ["Один магазин.", "Все модели."],
    endLede: "Corvus Store берёт на себя Minecraft и каждую модель — от первой установки до каждого обновления. Для macOS и Windows.",
    label: "Знакомство с Corvus",
  },
  id: {
    title: ["Setiap rilis.", "Kembali ke sini."],
    lede: "Halia, OUKA, Cherry, Tsubomi. Satu Corvus Store memasang, memperbarui, dan menjalankan setiap model.",
    cta: "Unduh Corvus Store",
    chapter: "Bab",
    open: "Jelajahi",
    endTitle: ["Satu toko.", "Semua model."],
    endLede: "Corvus Store mengurus Minecraft dan setiap model, dari pemasangan pertama hingga setiap pembaruan. Untuk macOS dan Windows.",
    label: "Perkenalan Corvus",
  },
  de: {
    title: ["Jede Version.", "Kehrt hierher zurück."],
    lede: "Halia, OUKA, Cherry, Tsubomi. Ein einziger Corvus Store installiert, aktualisiert und startet jedes Modell.",
    cta: "Corvus Store herunterladen",
    chapter: "Kapitel",
    open: "Entdecken",
    endTitle: ["Ein Store.", "Jedes Modell."],
    endLede: "Corvus Store übernimmt Minecraft und jedes Modell, von der ersten Installation bis zu jedem Update. Für macOS und Windows.",
    label: "Corvus vorgestellt",
  },
  tr: {
    title: ["Her sürüm", "buraya döner."],
    lede: "Halia, OUKA, Cherry, Tsubomi. Tek bir Corvus Store her modeli kurar, günceller ve başlatır.",
    cta: "Corvus Store'u indir",
    chapter: "Bölüm",
    open: "Keşfet",
    endTitle: ["Tek mağaza.", "Tüm modeller."],
    endLede: "Corvus Store, Minecraft'ı ve her modeli ilk kurulumdan her güncellemeye kadar yönetir. macOS ve Windows için.",
    label: "Corvus tanıtımı",
  },
};
