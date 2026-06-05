"use strict";

const OPENERS = [
  "很多人一",
  "这条视频最有用的地方",
  "这件事最值得学的",
  "最值得带走的",
  "真正的问题是",
  "问题往往出在"
];

const FILLERS = [
  "它的核心其实很简单",
  "真正有价值的地方",
  "最值得带走的",
  "可以收成一句",
  "换句话说",
  "真正先",
  "这件事最值得学的"
];

const HYPE = [
  "更狠的判断",
  "攻击性",
  "神奇捷径",
  "花哨技巧",
  "真正先救你的"
];

module.exports = function rule(context) {
  const { Syntax, RuleError, report, getSource } = context;

  return {
    [Syntax.Str](node) {
      const text = getSource(node).trim();

      for (const opener of OPENERS) {
        if (text.startsWith(opener) && text.length < 45) {
          report(
            node,
            new RuleError(`Weak opener detected: "${opener}". Prefer stating the point directly.`, {
              index: 0
            })
          );
        }
      }

      for (const phrase of FILLERS) {
        const index = text.indexOf(phrase);
        if (index !== -1) {
          report(
            node,
            new RuleError(`Filler framing phrase detected: "${phrase}"`, {
              index
            })
          );
        }
      }

      for (const phrase of HYPE) {
        const index = text.indexOf(phrase);
        if (index !== -1) {
          report(
            node,
            new RuleError(`Hype-style phrase detected: "${phrase}"`, {
              index
            })
          );
        }
      }
    }
  };
};
