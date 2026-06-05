-- Use image title (not alt text) as caption.
-- This matches the behavior of SiYuan, Yuque, and other note apps.
-- Also applies "Figure" style to images for centralized control.

function Image(img)
  local caption = img.caption
  if img.title and img.title ~= "" and img.title ~= "fig:" then
    caption = pandoc.Str(img.title)
  end
  return pandoc.Figure(
    pandoc.Image(caption, img.src, img.title, img.attr),
    { caption }
  )
end
