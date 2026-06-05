"use strict";

const fs = require("fs");
const path = require("path");

function parseArgs(argv) {
  const args = {
    mode: "obsidian-enhanced",
    all: false,
    input: null,
    output: null,
    outdir: null
  };

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--mode") {
      args.mode = argv[++i];
    } else if (token === "--input") {
      args.input = argv[++i];
    } else if (token === "--output") {
      args.output = argv[++i];
    } else if (token === "--outdir") {
      args.outdir = argv[++i];
    } else if (token === "--all") {
      args.all = true;
    } else if (!token.startsWith("-") && !args.input) {
      args.input = token;
    }
  }

  return args;
}

function normalizeMode(mode) {
  if (mode === "obsidian") return "obsidian-enhanced";
  return mode;
}

function supportedModes() {
  return ["obsidian-clean", "obsidian-enhanced", "obsidian-rich", "wechat", "xhs"];
}

function readInput(inputPath) {
  if (!inputPath || inputPath === "-") {
    return fs.readFileSync(0, "utf8");
  }
  return fs.readFileSync(inputPath, "utf8");
}

function splitSections(text) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  let title = "";
  let frontmatter = [];
  let intro = [];
  const sections = [];
  let current = null;
  let introStarted = false;

  for (const line of lines) {
    const titleMatch = line.match(/^#\s+(.+)$/);
    const sectionMatch = line.match(/^##\s+(.+)$/);

    if (titleMatch && !title) {
      title = titleMatch[1].trim();
      continue;
    }

    if (sectionMatch) {
      current = { heading: sectionMatch[1].trim(), lines: [] };
      sections.push(current);
      continue;
    }

    if (!title) {
      continue;
    }

    if (!current && !introStarted && line.trim().startsWith(">")) {
      frontmatter.push(line);
      continue;
    }

    if (!current) {
      if (line.trim()) {
        introStarted = true;
      }
      intro.push(line);
    } else {
      current.lines.push(line);
    }
  }

  return { title, frontmatter: trimBlankEdges(frontmatter), intro: trimBlankEdges(intro), sections };
}

function trimBlankEdges(lines) {
  const copy = [...lines];
  while (copy.length && !copy[0].trim()) copy.shift();
  while (copy.length && !copy[copy.length - 1].trim()) copy.pop();
  return copy;
}

function joinLines(lines) {
  return trimBlankEdges(lines).join("\n").trim();
}

function splitParagraphs(lines) {
  const blocks = [];
  let buf = [];

  for (const line of lines) {
    if (!line.trim()) {
      if (buf.length) {
        blocks.push(joinLines(buf));
        buf = [];
      }
      continue;
    }
    buf.push(line);
  }

  if (buf.length) {
    blocks.push(joinLines(buf));
  }

  return blocks.filter(Boolean);
}

function classifyHeading(heading) {
  if (/(结论|一句话|带走|目标效果|现在用户能做什么|下一步决策)/.test(heading)) {
    return "tip";
  }
  if (/(边界|保留|风险|未完成|阻塞)/.test(heading)) {
    return "warning";
  }
  if (/(核心信息|摘要|导语)/.test(heading)) {
    return "note";
  }
  return null;
}

function richCalloutType(heading) {
  if (/(结论|带走|一句话)/.test(heading)) return "success";
  if (/(边界|不解决|保留|风险)/.test(heading)) return "warning";
  if (/(方法|怎么做|为什么有用)/.test(heading)) return "important";
  if (/(乱|问题)/.test(heading)) return "danger";
  return "note";
}

function enhancedCalloutType(heading) {
  if (/(结论|带走|一句话)/.test(heading)) return "tip";
  if (/(边界|不解决|保留|风险)/.test(heading)) return "warning";
  if (/(方法|怎么做|为什么有用)/.test(heading)) return "important";
  if (/(乱|问题)/.test(heading)) return "note";
  return "note";
}

function emphasize(text) {
  const trimmed = text.trim();
  if (!trimmed) return trimmed;
  if (/^[-*]/.test(trimmed) || /^>/.test(trimmed) || /^#+\s/.test(trimmed)) {
    return trimmed;
  }

  const strong = /(结论|关键|最重要|先看|先拆|先做|真正|骨架|顺序|适合|必须|不要|记住)/;
  if (trimmed.length <= 80 && strong.test(trimmed)) {
    return `**${trimmed}**`;
  }

  const sentenceMatch = trimmed.match(/^(.+?[。！？])(.+)$/);
  if (sentenceMatch && sentenceMatch[1].length <= 40 && strong.test(sentenceMatch[1])) {
    return `**${sentenceMatch[1]}**${sentenceMatch[2]}`;
  }

  return trimmed;
}

function looksLikeShortStepLabel(block) {
  const oneLine = block.replace(/\n/g, " ").trim();
  return oneLine.length > 0 && oneLine.length <= 20 && /。$/.test(oneLine);
}

function extractStepPairs(bodyBlocks) {
  const pairs = [];
  const usedIndexes = new Set();
  let index = 0;

  while (index < bodyBlocks.length - 1) {
    const block = bodyBlocks[index];
    const next = bodyBlocks[index + 1];
    if (looksLikeShortStepLabel(block) && next) {
      pairs.push({
        labelIndex: index,
        contentIndex: index + 1,
        label: block.replace(/。$/, "").trim(),
        content: next.trim()
      });
      usedIndexes.add(index);
      usedIndexes.add(index + 1);
      index += 2;
      continue;
    }
    index += 1;
  }

  return { pairs, usedIndexes };
}

function renderIntro(intro, mode) {
  const blocks = splitParagraphs(intro);
  if (!blocks.length) return "";

  if (blocks.length > 3) {
    if (mode === "obsidian-clean" || mode === "obsidian-enhanced" || mode === "obsidian-rich") {
      return blocks.join("\n\n");
    }
    if (mode === "wechat") {
      return blocks.map((block) => emphasize(block)).join("\n\n");
    }
    if (mode === "xhs") {
      return blocks.map((block) => `- ${block.replace(/\n/g, " ")}`).join("\n");
    }
  }

  if (mode === "obsidian-clean" || mode === "obsidian-enhanced" || mode === "obsidian-rich") {
    return `> [!summary]\n> ${blocks.map((block) => block.replace(/\n/g, "\n> ")).join("\n>\n> ")}`;
  }

  if (mode === "wechat") {
    return blocks.map((block) => emphasize(block)).join("\n\n");
  }

  if (mode === "xhs") {
    return blocks.map((block) => `- ${block.replace(/\n/g, " ")}`).join("\n");
  }

  return `> **一句话看懂：** ${blocks[0].replace(/\n/g, " ")}`;
}

function renderFrontmatter(frontmatter, mode) {
  if (!frontmatter.length) return "";

  if (mode === "obsidian-clean" || mode === "obsidian-enhanced" || mode === "obsidian-rich") {
    return frontmatter.join("\n");
  }

  return frontmatter.join("\n");
}

function renderSection(section, mode) {
  const kind = classifyHeading(section.heading);
  const bodyBlocks = splitParagraphs(section.lines);
  const body = bodyBlocks.map((block) => emphasize(block)).join("\n\n");

  if (mode === "obsidian-clean") {
    if (kind) {
      const label = kind === "warning" ? "warning" : kind === "tip" ? "tip" : "note";
      const quoted = bodyBlocks
        .map((block) => {
          if (/^[-*]\s/m.test(block)) {
            return block.split("\n").map((line) => `> ${line}`).join("\n");
          }
          return `> ${block.replace(/\n/g, "\n> ")}`;
        })
        .join("\n>\n");
      return `## ${section.heading}\n\n> [!${label}]\n${quoted}`;
    }
    return `## ${section.heading}\n\n${body}`;
  }

  if (mode === "obsidian-enhanced") {
    const callout = enhancedCalloutType(section.heading);
    const { pairs: stepPairs, usedIndexes } = extractStepPairs(bodyBlocks);

    if (/(解决什么，不解决什么|边界|保留)/.test(section.heading) && bodyBlocks.length >= 2) {
      const first = emphasize(bodyBlocks[0]);
      const second = emphasize(bodyBlocks[1]);
      const extras = bodyBlocks.slice(2).map((block) => `> ${block.replace(/\n/g, "\n> ")}`).join("\n>\n");
      const tail = extras ? `\n>\n${extras}` : "";
      return `## ${section.heading}\n\n> [!tip] 适合用在哪\n> ${first.replace(/\n/g, "\n> ")}\n\n> [!warning] 它不解决什么\n> ${second.replace(/\n/g, "\n> ")}${tail}`;
    }

    if (stepPairs.length >= 2 && /(方法|为什么有用)/.test(section.heading)) {
      const introBlocks = bodyBlocks.filter((_, index) => !usedIndexes.has(index));
      const lead = introBlocks.length
        ? `${introBlocks.slice(0, 1).map((block) => `> ${block.replace(/\n/g, "\n> ")}`).join("\n>\n")}\n>\n`
        : "";
      const steps = stepPairs
        .map((pair, index) => `> ${index + 1}. **${pair.label}**\n> ${pair.content.replace(/\n/g, "\n> ")}`)
        .join("\n>\n");
      const closing = introBlocks.length > 1
        ? `\n>\n${introBlocks.slice(1).map((block) => `> ${emphasize(block).replace(/\n/g, "\n> ")}`).join("\n>\n")}`
        : "";
      return `## ${section.heading}\n\n> [!${callout}]\n${lead}${steps}${closing}`;
    }

    const quoted = bodyBlocks
      .map((block) => {
        if (/^[-*]\s/m.test(block)) {
          return block.split("\n").map((line) => `> ${line}`).join("\n");
        }
        return `> ${emphasize(block).replace(/\n/g, "\n> ")}`;
      })
      .join("\n>\n");
    return `## ${section.heading}\n\n> [!${callout}]\n${quoted}`;
  }

  if (mode === "obsidian-rich") {
    const callout = richCalloutType(section.heading);
    const { pairs: stepPairs } = extractStepPairs(bodyBlocks);

    if (stepPairs.length >= 2 && /(方法|为什么有用)/.test(section.heading)) {
      const leadBlocks = bodyBlocks.filter((block) => !looksLikeShortStepLabel(block)).slice(0, 1);
      const lead = leadBlocks.length
        ? `> [!${callout}]\n> ${leadBlocks.map((block) => block.replace(/\n/g, "\n> ")).join("\n>\n> ")}\n\n`
        : "";
      const tabs = [
        "```tabs",
        ...stepPairs.flatMap((pair) => [`---tab ${pair.label}`, emphasize(pair.content)])
      ].join("\n");
      return `## ${section.heading}\n\n${lead}${tabs}\n\`\`\``;
    }

    if (/(解决什么，不解决什么|边界|保留)/.test(section.heading) && bodyBlocks.length >= 2) {
      const left = emphasize(bodyBlocks[0]);
      const right = emphasize(bodyBlocks[1]);
      return `## ${section.heading}\n\n--- start-multi-column: ${section.heading.replace(/\s+/g, "-")}\n\`\`\`column-settings\nnumber of columns: 2\nlargest column: left\n\`\`\`\n\n> [!success]\n> ${left.replace(/\n/g, "\n> ")}\n\n--- end-column ---\n\n> [!warning]\n> ${right.replace(/\n/g, "\n> ")}\n\n--- end-multi-column`;
    }

    return `## ${section.heading}\n\n> [!${callout}]\n> ${bodyBlocks.map((block) => block.replace(/\n/g, "\n> ")).join("\n>\n> ")}`;
  }

  if (mode === "wechat") {
    const prefix = kind === "warning" ? "【边界】" : kind === "tip" ? "【结论】" : "";
    return `### ${prefix}${section.heading}\n\n${body}`;
  }

  const prefix = kind === "warning" ? "⚠ " : kind === "tip" ? "→ " : "";
  if (mode === "xhs") {
    const xhsBody = bodyBlocks.map((block) => `- ${block.replace(/\n/g, " ")}`).join("\n");
    return `### ${prefix}${section.heading}\n\n${xhsBody}`;
  }
  return `### ${prefix}${section.heading}\n\n${body}`;
}

function renderDoc(doc, mode) {
  const parts = [`# ${doc.title}`];
  if (mode === "obsidian-rich") {
    parts.push(
      "",
      "> [!note]",
      "> 这版是对比稿，依赖社区插件语法：`HTML Tabs` 和 `Multi-Column Markdown`。",
      "> 只适合看效果，不建议默认当成基础版。"
    );
  }
  const frontmatter = renderFrontmatter(doc.frontmatter, mode);
  if (frontmatter) {
    parts.push("", frontmatter);
  }
  const intro = renderIntro(doc.intro, mode);
  if (intro) {
    parts.push("", intro);
  }

  for (const section of doc.sections) {
    parts.push("", renderSection(section, mode));
  }

  return parts.join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
}

function writeOutput(targetPath, content) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.writeFileSync(targetPath, content, "utf8");
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  args.mode = normalizeMode(args.mode);
  if (!args.all && !supportedModes().includes(args.mode)) {
    throw new Error(`Unsupported mode: ${args.mode}`);
  }
  const inputText = readInput(args.input);
  const doc = splitSections(inputText);

  if (!doc.title) {
    throw new Error("No title line found. Start with a '# ' heading.");
  }

  const modes = args.all ? ["obsidian-clean", "obsidian-enhanced", "obsidian-rich"] : [args.mode];

  if (args.all) {
    if (!args.outdir) {
      throw new Error("--all requires --outdir");
    }
    for (const mode of modes) {
      const rendered = renderDoc(doc, mode);
      writeOutput(path.join(args.outdir, `${mode}.md`), rendered);
    }
    return;
  }

  const rendered = renderDoc(doc, args.mode);
  if (args.output) {
    writeOutput(args.output, rendered);
  } else {
    process.stdout.write(rendered);
  }
}

main();
