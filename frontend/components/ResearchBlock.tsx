import type { ResearchBlock as ResearchBlockType } from "@/lib/types";

interface ResearchBlockProps {
  block: ResearchBlockType;
}

export function ResearchBlock({ block }: ResearchBlockProps) {
  return (
    <article
      className="rounded-card border border-border bg-workspace p-5 shadow-subtle"
      data-block-id={block.id}
      data-block-type={block.type}
    >
      <header className="mb-3 flex items-center gap-2">
        <h3 className="font-sans text-base font-semibold text-charcoal">{block.title}</h3>
        {block.cached && (
          <span className="rounded-chip border border-border bg-sand px-2 py-0.5 font-sans text-[11px] text-secondary">
            Cached
          </span>
        )}
      </header>
      <div className="font-sans text-[14px] leading-relaxed text-charcoal whitespace-pre-wrap">
        {block.content}
      </div>
      {block.sources && block.sources.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {block.sources.map((url, i) => (
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-sans text-[12px] text-terracotta underline hover:no-underline"
            >
              Source {i + 1}
            </a>
          ))}
        </div>
      )}
    </article>
  );
}
