# Determine script path (works with both Rscript and sourcing)
script_path <- function() {
  cmdArgs <- commandArgs(trailingOnly = FALSE)
  needle <- "--file="
  match <- grep(needle, cmdArgs)
  if (length(match) > 0) return(gsub(needle, "", cmdArgs[match]))
  if (sys.nframe() > 0 && !is.null(sys.frame(1)$ofile)) {
    return(sys.frame(1)$ofile)
  }
  NA_character_
}

SCRIPT_PATH <- script_path()
STYLES_PATH <- file.path(dirname(dirname(SCRIPT_PATH)),
                          "nhanes_server", "r_helpers", "nhanes_styles.R")
if (!file.exists(STYLES_PATH)) stop("nhanes_styles.R not found at: ", STYLES_PATH)
source(STYLES_PATH)

library(ggplot2)

# Test 1: theme_nhanes() produces a gg theme
p <- ggplot(mtcars, aes(x = wt, y = mpg)) + geom_point() + theme_nhanes()
stopifnot(inherits(p$theme, "theme"))
cat("PASS: theme_nhanes() returns a valid ggplot2 theme\n")

# Test 2: nhanes_palette() returns correct colors
pal5 <- nhanes_palette(5)
stopifnot(length(pal5) == 5)
stopifnot(pal5[1] == "#1a1a1a")
stopifnot(all(pal5 == c("#1a1a1a", "#4d4d4d", "#808080", "#b3b3b3", "#e0e0e0")))
pal2 <- nhanes_palette(2)
stopifnot(all(pal2 == c("#1a1a1a", "#808080")))
cat("PASS: nhanes_palette() returns correct grayscale values\n")

# Test 3: style functions are defined and callable
stopifnot(is.function(nhanes_table_style))
stopifnot(is.function(nhanes_flextable_style))
if (requireNamespace("gt", quietly = TRUE)) {
  styled_gt <- nhanes_table_style(gt::gt(data.frame(a = 1:2, b = 3:4)))
  stopifnot(inherits(styled_gt, "gt_tbl"))
  cat("PASS: nhanes_table_style() applies to a gt object\n")
} else {
  cat("SKIP: gt not installed — nhanes_table_style smoke test skipped\n")
}
if (requireNamespace("flextable", quietly = TRUE) && requireNamespace("officer", quietly = TRUE)) {
  styled_ft <- nhanes_flextable_style(flextable::flextable(data.frame(a = 1:3, b = 4:6)))
  stopifnot(inherits(styled_ft, "flextable"))
  cat("PASS: nhanes_flextable_style() applies to a flextable object\n")
} else {
  cat("SKIP: flextable/officer not installed — nhanes_flextable_style smoke test skipped\n")
}
cat("PASS: style functions are defined\n")

cat("\nAll style tests passed.\n")
