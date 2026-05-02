import { useState } from "react";
import { Copy, Download, FileText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DocumentCardProps {
  title: string;
  content: string;
  defaultOpen?: boolean;
}

export function DocumentCard({ title, content, defaultOpen = false }: DocumentCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = title;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-xl border bg-card shadow-sm">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted/50 transition-colors rounded-t-xl"
      >
        <FileText className="h-4 w-4 shrink-0 text-teal-500" />
        <span className="flex-1 text-sm font-medium">{title}</span>
        <span
          className={cn(
            "text-xs text-muted-foreground transition-transform",
            open && "rotate-180",
          )}
        >
          ▼
        </span>
      </button>
      {open && (
        <div className="border-t px-4 py-3">
          <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground font-mono">
            {content.slice(0, 3000)}
            {content.length > 3000 && "\n\n... (truncated)"}
          </pre>
          <div className="mt-3 flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-7 gap-1.5 text-xs"
              onClick={handleCopy}
            >
              <Copy className="h-3 w-3" />
              {copied ? "Copied" : "Copy"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 gap-1.5 text-xs"
              onClick={handleDownload}
            >
              <Download className="h-3 w-3" />
              Download
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
