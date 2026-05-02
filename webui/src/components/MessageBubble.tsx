import { useCallback, useMemo, useState } from "react";
import { ChevronRight, Copy, Download, FileIcon, FileText, ImageIcon, PlaySquare, Wrench } from "lucide-react";
import { useTranslation } from "react-i18next";

import { ImageLightbox } from "@/components/ImageLightbox";
import { MarkdownText } from "@/components/MarkdownText";
import { cn } from "@/lib/utils";
import type { UIImage, UIMediaAttachment, UIMessage } from "@/lib/types";

interface ParsedDocument {
  name: string;
  content: string;
}

function parseDocuments(text: string): { documents: ParsedDocument[]; cleanText: string } {
  const documents: ParsedDocument[] = [];
  const regex = /---DOCUMENT:([^\n]+)---\n([\s\S]*?)---END_DOCUMENT---/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    documents.push({ name: match[1].trim(), content: match[2].trim() });
  }
  const cleanText = text.replace(regex, "").trim();
  return { documents, cleanText };
}

function downloadDocument(name: string, content: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

interface MessageBubbleProps {
  message: UIMessage;
}

/**
 * Render a single message. Following agent-chat-ui: user turns are a rounded
 * "pill" right-aligned with a muted fill; assistant turns render as bare
 * markdown so prose/code read like a document rather than a chat bubble.
 * Each turn fades+slides in for a touch of motion polish.
 *
 * Trace rows (tool-call hints, progress breadcrumbs) render as a subdued
 * collapsible group so intermediate steps never masquerade as replies.
 */
export function MessageBubble({ message }: MessageBubbleProps) {
  const baseAnim = "animate-in fade-in-0 slide-in-from-bottom-1 duration-300";

  if (message.kind === "trace") {
    return <TraceGroup message={message} />;
  }

  if (message.role === "user") {
    const images = message.images ?? [];
    const media = message.media ?? [];
    const hasImages = images.length > 0;
    const hasMedia = media.length > 0;
    const hasText = message.content.trim().length > 0;
    return (
      <div
        className={cn(
          "group ml-auto flex max-w-[min(85%,36rem)] flex-col items-end gap-1.5",
          baseAnim,
        )}
      >
        {hasImages ? <UserImages images={images} align="right" /> : null}
        {!hasImages && hasMedia ? (
          <MessageMedia media={media} align="right" />
        ) : null}
        {hasText ? (
          <p
            className={cn(
              "ml-auto w-fit rounded-[18px] bg-secondary/70 px-4 py-2",
              "text-left text-[18px]/[1.8] whitespace-pre-wrap break-words",
            )}
          >
            {message.content}
          </p>
        ) : null}
      </div>
    );
  }

  const empty = message.content.trim().length === 0;
  const media = message.media ?? [];

  const { documents, cleanText } = useMemo(() => {
    if (message.role !== "assistant") return { documents: [], cleanText: message.content };
    return parseDocuments(message.content);
  }, [message.content, message.role]);

  return (
    <div className={cn("w-full text-sm", baseAnim)} style={{ lineHeight: "var(--cjk-line-height)" }}>
      {empty && message.isStreaming && documents.length === 0 ? (
        <TypingDots />
      ) : (
        <>
          {documents.map((doc, i) => (
            <DocumentCard key={`${doc.name}-${i}`} name={doc.name} content={doc.content} />
          ))}
          {cleanText ? (
            <MarkdownText>{cleanText}</MarkdownText>
          ) : (
            documents.length > 0 ? null : <MarkdownText>{message.content}</MarkdownText>
          )}
          {message.isStreaming && <StreamCursor />}
          {media.length > 0 ? <MessageMedia media={media} align="left" /> : null}
        </>
      )}
    </div>
  );
}

function MessageMedia({
  media,
  align,
}: {
  media: UIMediaAttachment[];
  align: "left" | "right";
}) {
  if (media.length === 0) return null;
  const images = media
    .filter((item) => item.kind === "image")
    .map(({ url, name }) => ({ url, name }));
  const nonImages = media.filter((item) => item.kind !== "image");

  return (
    <div
      className={cn(
        "mt-2 flex flex-wrap gap-2",
        align === "right" ? "justify-end" : "justify-start",
      )}
    >
      {images.length > 0 ? <UserImages images={images} align={align} /> : null}
      {nonImages.map((item, i) => (
        <MediaCell key={`${item.url ?? item.name ?? item.kind}-${i}`} media={item} />
      ))}
    </div>
  );
}

function MediaCell({ media }: { media: UIMediaAttachment }) {
  const { t } = useTranslation();
  const hasUrl = typeof media.url === "string" && media.url.length > 0;

  if (media.kind === "video" && hasUrl) {
    return (
      <figure className="max-w-[min(100%,32rem)] overflow-hidden rounded-[14px] border border-border/60 bg-muted/40">
        <video
          src={media.url}
          controls
          preload="metadata"
          className="block max-h-[26rem] w-full bg-black"
          aria-label={media.name ? `${t("message.videoAttachment", { defaultValue: "Video attachment" })}: ${media.name}` : t("message.videoAttachment", { defaultValue: "Video attachment" })}
        />
        {media.name ? (
          <figcaption className="truncate px-3 py-1.5 text-[11.5px] text-muted-foreground">
            {media.name}
          </figcaption>
        ) : null}
      </figure>
    );
  }

  const label =
    media.kind === "video"
      ? t("message.videoAttachment", { defaultValue: "Video attachment" })
      : t("message.fileAttachment", { defaultValue: "File attachment" });
  const Icon = media.kind === "video" ? PlaySquare : FileIcon;

  return (
    <div
      className="flex max-w-[18rem] items-center gap-2 rounded-[14px] border border-border/60 bg-muted/40 px-3 py-2 text-xs text-muted-foreground"
      title={media.name ?? undefined}
      aria-label={label}
    >
      <Icon className="h-4 w-4 flex-none" aria-hidden />
      <span className="truncate">{media.name ?? label}</span>
    </div>
  );
}

/**
 * Right-aligned preview row for images attached to a user turn.
 *
 * Visual follows agent-chat-ui: a single wrapping row of fixed-size square
 * thumbnails that stay modest next to the text pill regardless of how many
 * images are attached.
 *
 * The URL is expected to be a self-contained ``data:`` URL (the Composer
 * hands the normalized base64 payload to the optimistic bubble so that the
 * preview survives React StrictMode double-mount — blob URLs would be
 * revoked by the Composer's cleanup before remount). Historical replays
 * have no URL (the backend strips data URLs before persisting), so we
 * render a labelled placeholder tile instead of a broken ``<img>``.
 */
function UserImages({
  images,
  align = "right",
}: {
  images: UIImage[];
  align?: "left" | "right";
}) {
  const { t } = useTranslation();
  // Only real-URL images can open in the lightbox; historical-replay
  // placeholders (no URL) have nothing to zoom into.
  const viewable = images
    .map((img, i) => ({ img, i }))
    .filter(({ img }) => typeof img.url === "string" && img.url.length > 0);
  const viewableImages = viewable.map(({ img }) => img);
  const originalToViewable = new Map<number, number>(
    viewable.map(({ i }, v) => [i, v]),
  );

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  return (
    <>
      <div
        className={cn(
          "flex flex-wrap items-end gap-2",
          align === "right" ? "ml-auto justify-end" : "mr-auto justify-start",
        )}
      >
        {images.map((img, i) => (
          <UserImageCell
            key={`${img.url ?? "placeholder"}-${i}`}
            image={img}
            placeholderLabel={t("message.imageAttachment")}
            openLabel={t("lightbox.open")}
            onOpen={
              originalToViewable.has(i)
                ? () => setLightboxIndex(originalToViewable.get(i)!)
                : undefined
            }
          />
        ))}
      </div>
      <ImageLightbox
        images={viewableImages}
        index={lightboxIndex}
        onIndexChange={setLightboxIndex}
        onOpenChange={(open) => {
          if (!open) setLightboxIndex(null);
        }}
      />
    </>
  );
}

function UserImageCell({
  image,
  placeholderLabel,
  openLabel,
  onOpen,
}: {
  image: UIImage;
  placeholderLabel: string;
  openLabel: string;
  onOpen?: () => void;
}) {
  const hasUrl = typeof image.url === "string" && image.url.length > 0;
  const tileClasses = cn(
    "relative h-24 w-24 overflow-hidden rounded-[14px] border border-border/60 bg-muted/40",
    "shadow-[0_6px_18px_-14px_rgba(0,0,0,0.45)]",
  );

  if (hasUrl && onOpen) {
    return (
      <button
        type="button"
        onClick={onOpen}
        aria-label={image.name ? `${openLabel}: ${image.name}` : openLabel}
        title={image.name ?? undefined}
        className={cn(
          tileClasses,
          "cursor-zoom-in transition-transform duration-150 motion-reduce:transition-none",
          "hover:scale-[1.02] hover:ring-2 hover:ring-primary/30",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
        )}
      >
        <img
          src={image.url}
          alt={image.name ?? ""}
          loading="lazy"
          decoding="async"
          draggable={false}
          className="h-full w-full object-cover"
        />
      </button>
    );
  }

  return (
    <div className={tileClasses} title={image.name ?? undefined}>
      <div
        className="flex h-full w-full flex-col items-center justify-center gap-1 px-2 text-[11px] text-muted-foreground"
        aria-label={placeholderLabel}
      >
        <ImageIcon className="h-4 w-4 flex-none" aria-hidden />
        <span className="line-clamp-2 text-center leading-tight">
          {image.name ?? placeholderLabel}
        </span>
      </div>
    </div>
  );
}

/** Blinking cursor appended at the end of streaming text. */
function StreamCursor() {
  const { t } = useTranslation();
  return (
    <span
      aria-label={t("message.streaming")}
      className={cn(
        "ml-0.5 inline-block h-[1em] w-[3px] translate-y-[2px] align-middle",
        "rounded-sm bg-foreground/70 animate-pulse",
      )}
    />
  );
}

/** Pre-token-arrival placeholder: three bouncing dots. */
function TypingDots() {
  const { t } = useTranslation();
  return (
    <span
      aria-label={t("message.assistantTyping")}
      className="inline-flex items-center gap-1 py-1"
    >
      <Dot delay="0ms" />
      <Dot delay="150ms" />
      <Dot delay="300ms" />
    </span>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      style={{ animationDelay: delay }}
      className={cn(
        "inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground/60",
        "animate-bounce",
      )}
    />
  );
}

function DocumentCard({ name, content, downloadUrl }: { name: string; content?: string; downloadUrl?: string }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const hasContent = !!content;

  const handleCopy = useCallback(async () => {
    try {
      const text = hasContent ? content! : (downloadUrl ? await (await fetch(downloadUrl)).text() : "");
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable
    }
  }, [content, downloadUrl, hasContent]);

  const handleDownload = useCallback(() => {
    if (downloadUrl) {
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } else if (content) {
      downloadDocument(name, content);
    }
  }, [name, content, downloadUrl]);

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-border/60 bg-card/80">
      <div className="flex items-center justify-between px-4 py-3">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-2 text-sm font-medium hover:text-foreground"
          disabled={!hasContent}
        >
          <FileText className="h-4 w-4 text-teal-500 shrink-0" />
          {name}
          {hasContent && (
            <ChevronRight
              className={cn(
                "h-3.5 w-3.5 text-muted-foreground transition-transform duration-200",
                expanded && "rotate-90",
              )}
            />
          )}
        </button>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            {copied ? (
              <>
                <span className="h-3.5 w-3.5 text-teal-500">&#10003;</span>
                已复制
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                复制
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Download className="h-3.5 w-3.5" />
            下载
          </button>
        </div>
      </div>
      {hasContent && expanded && (
        <div className="border-t border-border/50 px-4 pb-4 pt-3">
          <MarkdownText>{content}</MarkdownText>
        </div>
      )}
    </div>
  );
}

interface TraceGroupProps {
  message: UIMessage;
}

/**
 * Collapsible group of tool-call / progress breadcrumbs. Defaults to
 * expanded for discoverability; a single click on the header folds the
 * group down to a one-line summary so it never dominates the thread.
 */
function TraceGroup({ message }: TraceGroupProps) {
  const { t } = useTranslation();
  const lines = message.traces ?? [message.content];
  const count = lines.length;
  const [open, setOpen] = useState(true);
  return (
    <div className="w-full animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className={cn(
          "flex w-full cursor-pointer select-none items-center gap-2 rounded-md px-2 py-1.5",
          "text-xs text-muted-foreground transition-colors hover:bg-muted/45",
        )}
        aria-expanded={open}
      >
        <Wrench className="h-3.5 w-3.5 shrink-0" aria-hidden />
        <span className="font-medium">
          {count === 1
            ? t("message.toolSingle")
            : t("message.toolMany", { count })}
        </span>
        <ChevronRight
          aria-hidden
          className={cn(
            "ml-auto h-3.5 w-3.5 shrink-0 transition-transform duration-200",
            open && "rotate-90",
          )}
        />
      </button>
      {open && (
        <ul className="mt-1 space-y-0.5 border-l border-muted-foreground/20 pl-3">
          {lines.map((line, i) => (
            <li
              key={i}
              className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-foreground/70"
            >
              {line}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
