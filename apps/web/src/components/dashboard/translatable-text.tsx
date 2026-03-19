"use client";

import { Languages, LoaderCircle } from "lucide-react";
import { createElement, type ElementType, type MouseEvent, useMemo, useState } from "react";
import { translateProjectText } from "@/lib/api";

const translationCache = new Map<string, string>();

function hasEnglishContent(text: string) {
  return /[A-Za-z]{3,}/.test(text);
}

type TranslatableTextProps = {
  projectId?: string;
  text: string;
  as?: ElementType;
  className?: string;
  translationClassName?: string;
};

export function TranslatableText({
  projectId,
  text,
  as = "p",
  className,
  translationClassName,
}: TranslatableTextProps) {
  const [translated, setTranslated] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const canTranslate = useMemo(() => Boolean(projectId && hasEnglishContent(text)), [projectId, text]);

  async function handleTranslate(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();

    if (!projectId || !canTranslate) return;
    if (translated) {
      setTranslated(null);
      return;
    }

    const cacheKey = `${projectId}:${text}`;
    const cached = translationCache.get(cacheKey);
    if (cached) {
      setTranslated(cached);
      return;
    }

    try {
      setLoading(true);
      const result = await translateProjectText(projectId, text);
      translationCache.set(cacheKey, result.translated_text);
      setTranslated(result.translated_text);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="translatable-block">
      <div className="translatable-row">
        {createElement(as, { className }, text)}
        {canTranslate ? (
          <button className="translate-chip" onClick={handleTranslate} type="button">
            {loading ? <LoaderCircle className="spin" size={12} /> : <Languages size={12} />}
            {translated ? "收起翻译" : "翻译"}
          </button>
        ) : null}
      </div>
      {translated ? <div className={translationClassName ?? "translation-box"}>{translated}</div> : null}
    </div>
  );
}
