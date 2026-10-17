"use client";

import { useEffect, useRef, useState } from "react";
import { attachMusic, setMusicPlaying } from "@/engine/audio";
import { asset } from "@/lib/site";
import { Icon } from "./Icon";

/**
 * OUKA's theme, "Silver and Petals": never autoplayed (preload none, loop), it plays on the
 * first press and pauses on the second; a refused play() resets the button. While it plays the
 * page's own drone steps back.
 */
export function ThemePlayer({ track, play, pause }: { track: string; play: string; pause: string }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    const el = audio.current;
    if (el === null) return;
    const onPause = (): void => {
      setPlaying(false);
      setMusicPlaying(false);
    };
    el.addEventListener("pause", onPause);
    el.addEventListener("ended", onPause);
    return () => {
      el.removeEventListener("pause", onPause);
      el.removeEventListener("ended", onPause);
      el.pause();
      setMusicPlaying(false);
    };
  }, []);

  const toggle = async (): Promise<void> => {
    const el = audio.current;
    if (el === null) return;
    if (!el.paused) {
      el.pause();
      return;
    }
    attachMusic(el);
    setPlaying(true);
    try {
      await el.play();
      setMusicPlaying(true);
    } catch {
      setPlaying(false);
      setMusicPlaying(false);
    }
  };

  return (
    <div className="ac-player">
      <button
        type="button"
        className="ac-btn ac-btn--ghost ac-btn--small"
        aria-pressed={playing}
        data-play={play}
        data-pause={pause}
        onClick={() => void toggle()}
      >
        <Icon name={playing ? "pause" : "play"} size={14} />
        {playing ? pause : play}
      </button>
      <span className="ac-small" lang="en" dir="ltr">
        {track}
      </span>
      <span className="ac-eq" aria-hidden="true" data-on={playing}>
        <i />
        <i />
        <i />
        <i />
      </span>
      <audio ref={audio} preload="none" loop>
        <source src={asset("wiki/audio/silver-and-petals.m4a")} type="audio/mp4" />
        <source src={asset("wiki/audio/silver-and-petals.mp3")} type="audio/mpeg" />
      </audio>
    </div>
  );
}
