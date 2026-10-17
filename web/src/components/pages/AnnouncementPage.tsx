import Link from "next/link";
import { fill, FRESH } from "@/i18n/fresh";
import { asset, pathOf } from "@/lib/site";
import { wiki } from "@/lib/wiki";
import type { Lang } from "@/lib/wiki-types";


/** 74 → "1:14". */
function clock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

/**
 * Announcement: every film the studio has posted (data/announcements.json), newest first, each one
 * playable where it is and linked to the release notes it belongs to. The films are the very files
 * that went to the Discord servers, kept in assets/video/announcement/. A plain <video> element
 * with the browser's own controls: nothing loads until someone presses play (preload="none").
 */
export function AnnouncementPage({ lang }: { lang: Lang }) {
  const t = FRESH[lang].announcement;
  const names = new Intl.DateTimeFormat(lang === "pt-br" ? "pt-BR" : lang, { dateStyle: "long", timeZone: "UTC" });
  return (
    <section id="ac-announcement">
      <div className="ac-wrap ac-page-head">
        <h1 className="ac-h1">{t.title}</h1>
        <p className="ac-lead">{t.lede}</p>
      </div>
      <div className="ac-wrap">
        <ul className="ac-film-grid">
          {wiki().films.map((film) => {
            const notes =
              film.brand === "noctua"
                ? pathOf(lang, "noctua/")
                : `${pathOf(lang, "changelog/")}?model=${encodeURIComponent(film.brand)}`;
            return (
              <li key={film.id} className="ac-card ac-film">
                <video
                  className="ac-film-video"
                  controls
                  playsInline
                  preload="none"
                  poster={asset(`wiki/announcement/${film.poster}`)}
                  aria-label={film.title}
                >
                  <source src={asset(`wiki/announcement/${film.file}`)} type="video/mp4" />
                </video>
                <div className="ac-film-body">
                  <p className="ac-small ac-film-meta">
                    <span className="ac-tag">{t.kinds[film.kind]}</span>
                    <span className="ac-ltr">{clock(film.seconds)}</span>
                    <span>{fill(t.published, names.format(new Date(`${film.date}T00:00:00Z`)))}</span>
                  </p>
                  <h2 className="ac-film-title ac-ltr">{film.title}</h2>
                  <Link className="ac-link" href={notes}>
                    {t.notes}
                  </Link>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
