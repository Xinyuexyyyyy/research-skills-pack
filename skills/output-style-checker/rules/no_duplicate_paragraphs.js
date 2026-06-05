"use strict";

function normalizeParagraph(text) {
  return text.replace(/\s+/g, " ").trim();
}

module.exports = function rule(context) {
  const { Syntax, RuleError, report, getSource } = context;

  return {
    [Syntax.Document](node) {
      const text = getSource(node);
      const paragraphs = text
        .split(/\n\s*\n/)
        .map((raw) => normalizeParagraph(raw))
        .filter((raw) => raw.length >= 30);

      const seen = new Map();
      for (const paragraph of paragraphs) {
        if (seen.has(paragraph)) {
          const index = text.indexOf(paragraph, seen.get(paragraph) + 1);
          if (index !== -1) {
            report(
              node,
              new RuleError("Duplicate paragraph detected. The article may be spinning in place.", {
                index
              })
            );
          }
        } else {
          seen.set(paragraph, text.indexOf(paragraph));
        }
      }
    }
  };
};

