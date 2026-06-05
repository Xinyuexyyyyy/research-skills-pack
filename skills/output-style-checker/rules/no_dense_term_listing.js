"use strict";

const SEPARATORS = /[、,，\/]/;
const CUE_PATTERNS = /(如|例如|包括|包含|比如|主要围绕|分为|有)/;

function isShortLabel(item) {
  return item.length >= 2 && item.length <= 10 && !/[。？！；：:]/.test(item);
}

module.exports = function rule(context) {
  const { Syntax, RuleError, report, getSource } = context;

  return {
    [Syntax.Str](node) {
      const text = getSource(node);
      const lines = text.split("\n");
      let offset = 0;

      for (const line of lines) {
        const trimmed = line.trim();
        const tokenLikeItems = trimmed
          .split(SEPARATORS)
          .map((item) => item.trim())
          .filter(Boolean);
        const shortLabels = tokenLikeItems.filter(isShortLabel);
        const separatorCount = (trimmed.match(SEPARATORS) || []).length;
        const hasCue = CUE_PATTERNS.test(trimmed);

        const looksLikeDenseList =
          separatorCount >= 4 &&
          shortLabels.length >= 4 &&
          !trimmed.startsWith("- ") &&
          !trimmed.startsWith("* ") &&
          !/^(#|>)/.test(trimmed) &&
          hasCue;

        if (looksLikeDenseList) {
          report(
            node,
            new RuleError("Dense term listing detected. Explain the grouping instead of stacking labels.", {
              index: offset
            })
          );
        }
        offset += line.length + 1;
      }
    }
  };
};
