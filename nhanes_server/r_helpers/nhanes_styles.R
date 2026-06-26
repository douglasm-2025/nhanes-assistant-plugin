theme_nhanes <- function(base_size = 11, base_family = "Arial") {
  ggplot2::theme_classic(base_size = base_size, base_family = base_family) +
    ggplot2::theme(
      plot.background    = ggplot2::element_rect(fill = "white", color = NA),
      panel.background   = ggplot2::element_rect(fill = "white", color = NA),
      panel.grid.major   = ggplot2::element_blank(),
      panel.grid.minor   = ggplot2::element_blank(),
      axis.line          = ggplot2::element_line(color = "#333333", linewidth = 0.5),
      axis.ticks         = ggplot2::element_line(color = "#333333"),
      axis.text          = ggplot2::element_text(size = base_size, color = "#333333"),
      axis.title         = ggplot2::element_text(size = base_size, color = "#333333"),
      plot.title         = ggplot2::element_text(size = base_size + 2, face = "bold",
                                                  hjust = 0),
      plot.caption       = ggplot2::element_text(size = base_size - 2, hjust = 0,
                                                  margin = ggplot2::margin(t = 5)),
      legend.position    = "bottom",
      legend.direction   = "horizontal",
      legend.title       = ggplot2::element_text(size = base_size),
      legend.text        = ggplot2::element_text(size = base_size - 1),
      legend.key         = ggplot2::element_rect(fill = "white", color = NA),
      plot.margin        = ggplot2::margin(10, 15, 10, 10)
    )
}

nhanes_palette <- function(n = 5) {
  pal <- c("#1a1a1a", "#4d4d4d", "#808080", "#b3b3b3", "#e0e0e0")
  if (n == 2) return(c("#1a1a1a", "#808080"))
  pal[seq_len(min(n, 5))]
}

scale_color_nhanes <- function(...) {
  ggplot2::scale_color_manual(values = nhanes_palette(), ...)
}

scale_fill_nhanes <- function(...) {
  ggplot2::scale_fill_manual(values = nhanes_palette(), ...)
}

nhanes_table_style <- function(tbl) {
  tbl |>
    gt::tab_options(
      table.font.names                   = "Arial",
      table.font.size                    = gt::px(11),
      table.border.top.color             = "#333333",
      table.border.bottom.color          = "#333333",
      column_labels.background.color     = "#333333",
      column_labels.font.weight          = "bold",
      column_labels.border.bottom.color  = "#333333",
      row.striping.background_color      = "#f2f2f2",
      row.striping.include_table_body    = TRUE,
      table_body.border.bottom.color     = "#333333",
      source_notes.font.size             = gt::px(9),
      footnotes.font.size                = gt::px(9)
    ) |>
    # White header text: gt 1.0.0 has no column_labels.font.color option,
    # so set it via tab_style/cell_text on the column-label cells.
    gt::tab_style(
      style     = gt::cell_text(color = "white"),
      locations = gt::cells_column_labels()
    ) |>
    gt::opt_row_striping()
}

nhanes_flextable_style <- function(ft) {
  # Compute even-numbered body rows dynamically — flextable rejects row
  # indices beyond nrow, so a fixed seq() would error on real tables.
  n_rows    <- nrow(ft$body$dataset)
  even_rows <- seq_len(n_rows)[seq_len(n_rows) %% 2 == 0]

  ft <- ft |>
    flextable::font(fontname = "Arial", part = "all") |>
    flextable::fontsize(size = 11, part = "all") |>
    flextable::bold(part = "header") |>
    flextable::bg(bg = "#333333", part = "header") |>
    flextable::color(color = "white", part = "header")

  if (length(even_rows) > 0) {
    ft <- flextable::bg(ft, bg = "#f2f2f2", i = even_rows, part = "body")
  }

  ft |>
    flextable::border_outer(
      part   = "all",
      border = officer::fp_border(color = "#333333", width = 1)
    ) |>
    flextable::border_inner_h(
      part   = "body",
      border = officer::fp_border(color = "#e8e8e8", width = 0.5)
    ) |>
    flextable::border_inner_v(
      part   = "all",
      border = officer::fp_border(color = "transparent", width = 0)
    ) |>
    flextable::set_table_properties(width = 1, layout = "autofit")
}
