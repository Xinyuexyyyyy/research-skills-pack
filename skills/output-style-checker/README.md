# Output Style Checker

`output-style-checker` is the minimal checker layer for `self-article`.

It does not generate articles.
It checks whether an article should be accepted, rejected, or sent back for revision.

## What this first version covers

- `textlint` rule layer
- small `promptfoo` eval scaffold
- a few sample files for regression

## Why this exists

We have been trying to solve too many problems with one prompt:

- generation
- de-AI wording
- structure cleanup
- quality judgment

This checker splits out the judgment layer.

## First version scope

This version only targets `self-article`.
It does not yet cover `self-tech` or `general`.

## Layout

- `.textlintrc.json`: textlint config
- `rules/`: local custom textlint rules
- `samples/`: small regression samples
- `regression/`: real-file regression manifest plus note files
- `scripts/lint-real-files.js`: lints known bad historical drafts directly
- `promptfoo/`: eval scaffold
- `scripts/`: convenience commands

## Commands

```bash
cd skills/output-style-checker
npm install
npm run lint:samples
npm run lint:fixtures
npm run lint:regression
npm run eval:samples
```

## Current validation status

- `textlint` sample check: working
- `promptfoo` sample eval: blocked by local Node runtime

Current machine:

- detected Node: `v22.12.0`
- promptfoo requires: `^20.20.0 || >=22.22.0`

So the rule layer is already usable, while the eval layer is scaffolded but not yet runnable on this machine without a newer Node version.

## Current philosophy

- use `textlint` to catch hard smells
- use `promptfoo` to define eval gates
- keep `knowledge note` as a post-process, not the main article

## Current local rules

- `no_ai_contrast_phrases`: catches mechanical `不是……而是……`
- `no_filler_force_language`: catches weak openers, filler framing, and fake-force wording
- `no_duplicate_paragraphs`: catches repeated paragraph-level spinning
- `require_final_takeaway`: warns when the ending does not clearly land
- `no_dense_term_listing`: catches dense term/label stacking without explanation
- `no_meta_outline_scaffolding`: catches report-template filler like `这一段主要围绕……继续展开`

## Notes

- The borrowed `textlint-ja` presets are Japanese-first. We are borrowing the rule ideas, not installing them blindly as-is for Chinese output.
- The local rules here are intentionally small. The first goal is to catch the bad patterns we have already seen in our own failed drafts.
