-- Support common inline HTML tags that pandoc ignores by default.
-- Converts <sub>, <sup>, <mark>, <del>, <ins> to native pandoc elements.

function RawInline(el)
  if el.format == "html" then
    local tag = el.text:match("^<([a-zA-Z0-9]+)")
    if tag == "sub" then
      return pandoc.Subscript({})
    elseif tag == "sup" then
      return pandoc.Superscript({})
    elseif tag == "mark" then
      return pandoc.Span({}, pandoc.Attr("", {}, {["custom-style"] = "Highlighted"}))
    elseif tag == "del" then
      return pandoc.Strikeout({})
    elseif tag == "ins" then
      return pandoc.Underline({})
    end
  end
  return el
end
