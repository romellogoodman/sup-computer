import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

// Pull remark-gfm footnotes out of the bottom "Footnotes" section and place each
// one inline as a right-margin sidenote, right after its reference marker. The
// marker stays in the text; CSS (.sidenote) floats the content into the margin.
// Runs after rehype-raw so the whole hast tree is built. No external deps —
// a plain recursive walk over the hast tree.
function rehypeSidenotes() {
  const hasProp = (node, key) =>
    node.properties && Object.prototype.hasOwnProperty.call(node.properties, key);
  const hasClass = (node, name) =>
    node.properties && [].concat(node.properties.className || []).includes(name);

  // Deep-clone hast nodes, dropping the "↩" back-reference links.
  const cleanClone = (node) => {
    if (node.type === "text") return { type: "text", value: node.value };
    if (node.type !== "element") return { ...node };
    if (node.tagName === "a" && hasProp(node, "dataFootnoteBackref")) return null;
    const children = (node.children || []).map(cleanClone).filter(Boolean);
    return { type: "element", tagName: node.tagName, properties: { ...node.properties }, children };
  };

  return (tree) => {
    // 1. Find the footnotes <section> and collect id -> content nodes.
    const defs = {};
    let footnotesSection = null;
    const collect = (node) => {
      if (!node.children) return;
      for (const child of node.children) {
        if (
          child.type === "element" &&
          child.tagName === "section" &&
          (hasProp(child, "dataFootnotes") || hasClass(child, "footnotes"))
        ) {
          footnotesSection = child;
          const ol = (child.children || []).find((c) => c.tagName === "ol");
          if (ol) {
            for (const li of ol.children) {
              if (li.type !== "element" || li.tagName !== "li" || !li.properties?.id) continue;
              // unwrap a single <p> so the sidenote content flows inline
              let kids = (li.children || []).map(cleanClone).filter(Boolean);
              const els = kids.filter((k) => k.type === "element");
              if (els.length === 1 && els[0].tagName === "p") kids = els[0].children;
              defs[li.properties.id] = kids;
            }
          }
        }
        collect(child);
      }
    };
    collect(tree);

    // 2. Walk again; after each footnote-ref <sup>, place its sidenote. A float
    //    can't escape a table cell, so footnotes inside a <table> are collected
    //    and emitted right after the table instead of inline.
    let n = 0;
    const tableStack = [];
    const makeSidenote = (id) => {
      n += 1;
      return {
        type: "element",
        tagName: "span",
        properties: { className: ["sidenote"] },
        children: [
          {
            type: "element",
            tagName: "span",
            properties: { className: ["sidenote__num"] },
            children: [{ type: "text", value: String(n) }],
          },
          ...defs[id],
        ],
      };
    };
    const transform = (node) => {
      if (!node.children) return;
      const out = [];
      for (const child of node.children) {
        if (child === footnotesSection) continue; // drop the bottom section

        if (child.type === "element" && child.tagName === "table") {
          tableStack.push([]);
          transform(child);
          const notes = tableStack.pop();
          out.push(child, ...notes);
          continue;
        }

        out.push(child);
        if (child.type === "element" && child.tagName === "sup") {
          const a = (child.children || []).find(
            (c) => c.tagName === "a" && hasProp(c, "dataFootnoteRef")
          );
          const id = a && (a.properties.href || "").replace(/^#/, "");
          if (id && defs[id]) {
            const sidenote = makeSidenote(id);
            if (tableStack.length) tableStack[tableStack.length - 1].push(sidenote);
            else out.push(sidenote);
            continue; // no need to descend into the marker
          }
        }
        transform(child);
      }
      node.children = out;
    };
    transform(tree);
  };
}

// The key-takeaways abstract box, built from `takeaways:` frontmatter
// (ADR-0031). Bullets are markdown strings; rendering is inline-only so a
// stray block element can't break the box.
function Takeaways({ items }) {
  if (!items?.length) return null;
  return (
    <div className="takeaways">
      <p className="takeaways-label">Key takeaways</p>
      <ul>
        {items.map((t, i) => (
          <li key={i}>
            <ReactMarkdown allowedElements={["a", "code", "em", "strong", "del"]} unwrapDisallowed>
              {t}
            </ReactMarkdown>
          </li>
        ))}
      </ul>
    </div>
  );
}

// GFM (tables, footnotes) + raw HTML (the reports' <picture> chart embeds) +
// footnotes rendered as margin sidenotes. `takeaways` (frontmatter bullets)
// opens the prose column as the abstract box.
export default function Markdown({ children, takeaways }) {
  return (
    <div className="prose">
      <Takeaways items={takeaways} />
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, rehypeSidenotes]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
