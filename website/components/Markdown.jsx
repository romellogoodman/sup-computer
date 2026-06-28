import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

// GFM (tables, footnotes) + raw HTML (the reports' <picture> chart embeds).
export default function Markdown({ children }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
      {children}
    </ReactMarkdown>
  );
}
