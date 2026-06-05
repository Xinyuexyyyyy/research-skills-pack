-- Preserve font color from HTML spans like <span style="color:red">red text</span>
-- Pandoc strips these by default; this filter converts them to native color attributes.

function Span(el)
  local style = el.attributes and el.attributes.style
  if style then
    local color = style:match("color:%s*([^;]+)")
    if color then
      -- Add color attribute that pandoc-docx will preserve
      el.attributes["custom-style"] = "ColoredText"
      -- Also set the color in a way docx understands
      return pandoc.Span(el.content, pandoc.Attr("", {}, {["color"] = color}))
    end
  end
  return el
end
