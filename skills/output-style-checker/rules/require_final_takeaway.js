"use strict";

const TAKEAWAY_HINTS = [
  "结论",
  "意味着",
  "值得带走",
  "所以",
  "对我们",
  "可以直接",
  "最值得",
  "这说明",
  "先搭骨架",
  "先把理解组织起来",
  "学新东西时"
];

module.exports = function rule(context) {
  const { Syntax, RuleError, report, getSource } = context;

  return {
    [Syntax.Document](node) {
      const text = getSource(node).trim();
      if (!text) {
        return;
      }

      const tail = text.slice(Math.max(0, text.length - 220));
      const hasTakeaway = TAKEAWAY_HINTS.some((hint) => tail.includes(hint));
      if (!hasTakeaway) {
        report(
          node,
          new RuleError("Ending may not land clearly. Add a concrete takeaway or implication.", {
            index: Math.max(0, text.length - 1)
          })
        );
      }
    }
  };
};
