// ~1KB syntax highlighter for Python & JavaScript (GDD §7: lightweight, no
// editor dependency). Returns HTML-escaped, span-wrapped markup.

const PY_KW = new Set([
  "def", "return", "if", "elif", "else", "for", "while", "in", "not", "and",
  "or", "None", "True", "False", "class", "import", "from", "as", "with",
  "try", "except", "finally", "raise", "lambda", "yield", "pass", "break",
  "continue", "is", "len", "range", "print",
]);
const JS_KW = new Set([
  "function", "return", "if", "else", "for", "while", "of", "in", "const",
  "let", "var", "new", "class", "this", "true", "false", "null", "undefined",
  "typeof", "instanceof", "try", "catch", "finally", "throw", "break",
  "continue", "switch", "case", "default", "do", "=>",
]);

function esc(s: string): string {
  return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]!);
}

const TOKEN =
  /(#.*|\/\/.*)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g;

export function highlightLine(line: string, lang: string): string {
  const kw = lang.startsWith("py") ? PY_KW : JS_KW;
  let out = "";
  let last = 0;
  let m: RegExpExecArray | null;
  TOKEN.lastIndex = 0;
  while ((m = TOKEN.exec(line))) {
    out += esc(line.slice(last, m.index));
    if (m[1]) out += `<span class="tok-cm">${esc(m[1])}</span>`;
    else if (m[2]) out += `<span class="tok-str">${esc(m[2])}</span>`;
    else if (m[3]) out += `<span class="tok-num">${esc(m[3])}</span>`;
    else {
      const w = m[4];
      if (kw.has(w)) out += `<span class="tok-kw">${esc(w)}</span>`;
      else if (line[TOKEN.lastIndex] === "(") out += `<span class="tok-fn">${esc(w)}</span>`;
      else out += esc(w);
    }
    last = TOKEN.lastIndex;
  }
  out += esc(line.slice(last));
  return out;
}
