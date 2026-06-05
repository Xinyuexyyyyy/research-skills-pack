"use strict";

const PHRASES = [
  "这一段主要围绕",
  "继续展开",
  "可先看这几段"
];

module.exports = function rule(context) {
  const { Syntax, RuleError, report, getSource } = context;

  return {
    [Syntax.Str](node) {
      const text = getSource(node);
      for (const phrase of PHRASES) {
        const index = text.indexOf(phrase);
        if (index !== -1) {
          report(
            node,
            new RuleError(`Meta outline scaffolding detected: "${phrase}"`, {
              index
            })
          );
        }
      }
    }
  };
};
