// Renders a Markdown report (E7-08) as a formatted document (ADR-0014). react-markdown emits React
// elements and never raw HTML (no rehype-raw), so attacker text in the report stays inert text — the
// console's XSS guarantee. Styled with Tailwind tokens to match the console.
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

// `node` (the hast node) is pulled out of each so it is not spread onto the DOM element.
const REPORT_MD: Components = {
  h1: ({ node: _n, ...p }) => <h1 className="mb-2 text-base font-semibold tracking-tight" {...p} />,
  h2: ({ node: _n, ...p }) => (
    <h2 className="mt-4 mb-1.5 text-sm font-semibold tracking-tight" {...p} />
  ),
  h3: ({ node: _n, ...p }) => <h3 className="mt-3 mb-1 text-sm font-medium" {...p} />,
  p: ({ node: _n, ...p }) => <p className="my-2 text-sm leading-relaxed text-text/90" {...p} />,
  ul: ({ node: _n, ...p }) => (
    <ul className="my-2 list-disc space-y-1 pl-5 text-sm text-text/90" {...p} />
  ),
  ol: ({ node: _n, ...p }) => (
    <ol className="my-2 list-decimal space-y-1 pl-5 text-sm text-text/90" {...p} />
  ),
  li: ({ node: _n, ...p }) => <li className="leading-relaxed" {...p} />,
  table: ({ node: _n, ...p }) => <table className="my-2 w-full border-collapse text-sm" {...p} />,
  th: ({ node: _n, ...p }) => (
    <th className="border-b border-line px-2 py-1 text-left font-medium text-muted" {...p} />
  ),
  td: ({ node: _n, ...p }) => <td className="border-b border-line/60 px-2 py-1 align-top" {...p} />,
  code: ({ node: _n, ...p }) => (
    <code className="rounded bg-panel-2 px-1 py-0.5 font-mono text-xs break-all" {...p} />
  ),
  a: ({ node: _n, ...p }) => <a className="text-accent underline" {...p} />,
  hr: ({ node: _n, ...p }) => <hr className="my-3 border-line" {...p} />,
  strong: ({ node: _n, ...p }) => <strong className="font-semibold" {...p} />,
  em: ({ node: _n, ...p }) => <em className="italic" {...p} />,
};

export function ReportMarkdown({ markdown }: { markdown: string }) {
  return (
    <div className="max-w-none overflow-x-auto text-text">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={REPORT_MD}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
