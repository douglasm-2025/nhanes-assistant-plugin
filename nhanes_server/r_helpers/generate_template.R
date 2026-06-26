library(officer)

template_path <- Sys.getenv("TEMPLATE_PATH")
if (!nchar(template_path)) stop("TEMPLATE_PATH env var not set")

# ---------------------------------------------------------------------------
# Page margins: 1 inch on all sides (1 inch = 1440 twips in officer)
# ---------------------------------------------------------------------------
margins <- page_mar(
  top    = 1,   # inches
  bottom = 1,
  left   = 1,
  right  = 1,
  gutter = 0
)

section_props <- prop_section(page_mar = margins)

# ---------------------------------------------------------------------------
# Default paragraph style: Times New Roman 12 pt, double line spacing
# ---------------------------------------------------------------------------
# officer's fp_par / fp_text control inline paragraph formatting.
# We apply these to a seed paragraph on the Normal style.
# NOTE: Continuous line numbering is not cleanly supported by officer without
# direct XML editing. Enable line numbering manually in Word after opening
# the document (Layout > Line Numbers > Continuous).
# ---------------------------------------------------------------------------
para_format <- fp_par(
  line_spacing = 2          # double spacing (2 = double; officer uses a multiplier)
)

text_format <- fp_text(
  font.family = "Times New Roman",
  font.size   = 12
)

doc <- read_docx()

# Add a seed paragraph that establishes the default look; it can be deleted
# after opening in Word.
doc <- body_add_fpar(
  doc,
  fpar(
    ftext("", prop = text_format),
    fp_p = para_format
  ),
  style = "Normal"
)

# Apply the 1-inch page margins to the default section
doc <- body_set_default_section(doc, section_props)

print(doc, target = template_path)
cat("Template created at:", template_path, "\n")
