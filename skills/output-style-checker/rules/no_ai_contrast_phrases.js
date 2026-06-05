"use strict";

const DEFAULT_PATTERNS = [
  /不是[^。；\n]{0,40}而是[^。；\n]{0,40}/g,
  /不是因为[^。；\n]{0,40}而是(?:因为)?[^。；\n]{0,40}/g
];

module.exports = function rule(context) {
  const { Syntax, RuleError, report, getSource } = context;

  return {
    [Syntax.Str](node) {
      const text = getSource(node);
      for (const pattern of DEFAULT_PATTERNS) {
        let match;
        while ((match = pattern.exec(text)) !== null) {
          report(
            node,
            new RuleError("Avoid mechanical contrast phrasing. Rewrite the point directly.", {
              index: match.index
            })
          );
        }
      }
    }
  };
};

