# nhanes_survey.R
# Canonical complex-survey helpers for the NHANES Assistant plugin.
#
# WHY THIS FILE EXISTS
# Every analysis should build the survey design and define analytic domains the
# SAME way. Routing all design construction and estimation through these helpers
# makes the generated R (a) correct by construction — the complex-survey rules are
# baked in — and (b) near-identical from run to run, so the analysis artifact is
# reproducible and easy to audit. The agent still chooses variables, populations,
# and models freely; only the mechanical survey boilerplate is standardized.
#
# This file is auto-sourced by the execute_r_script tool, so the functions below
# are available in every analysis script without an explicit source() call.

suppressMessages({
  library(survey)
  library(dplyr)
})

# Build the Taylor-linearization survey design on the FULL eligible sample.
#   data            : merged NHANES data frame (one row per participant)
#   weight_var      : name of the 2-year weight column, e.g. "WTDRD1"
#   n_cycles        : number of 2-year cycles combined; the raw weight is divided
#                     by this (the combined-cycle rule)
#   positive_weight : keep only rows with a usable, positive analysis weight. This
#                     defines the weighted analytic population ONCE, up front (e.g.
#                     the dietary subsample when weight_var = "WTDRD1").
#
# Never pre-filter to an age/sex subgroup here — analytic domains come later via
# subset() on the returned design object (see nh_subpop note in the agent guide).
nh_design <- function(data, weight_var, n_cycles = 1L, positive_weight = TRUE) {
  options(survey.lonely.psu = "adjust")
  stopifnot(weight_var %in% names(data),
            all(c("SDMVPSU", "SDMVSTRA") %in% names(data)))
  # Combined-cycle rule: divide the 2-year weight by the number of cycles combined.
  data[["W_ANALYSIS"]] <- data[[weight_var]] / n_cycles
  keep <- !is.na(data$SDMVPSU) & !is.na(data$SDMVSTRA) & !is.na(data[["W_ANALYSIS"]])
  if (positive_weight) keep <- keep & data[["W_ANALYSIS"]] > 0
  data <- data[keep, , drop = FALSE]
  svydesign(id = ~SDMVPSU, strata = ~SDMVSTRA, weights = ~W_ANALYSIS,
            nest = TRUE, data = data)
}

# Weighted mean of one numeric variable -> tidy one-row data frame
# (estimate, SE, 95% CI, unweighted N).
nh_mean <- function(design, var) {
  f  <- as.formula(paste0("~", var))
  m  <- svymean(f, design, na.rm = TRUE)
  ci <- confint(m)
  data.frame(
    variable = var,
    estimate = as.numeric(m),
    se       = as.numeric(SE(m)),
    ci_low   = as.numeric(ci[1]),
    ci_high  = as.numeric(ci[2]),
    n_unwtd  = tryCatch(as.integer(coef(unwtd.count(f, design))[1]),
                        error = function(e) NA_integer_),
    row.names = NULL
  )
}

# Weighted difference in a numeric variable between the two levels of `group`
# -> tidy one-row data frame (difference, 95% CI, p-value). Uses svyttest, which
# applies the complex-survey variance. The sign of `difference` follows the factor
# level ordering of `group`; state the direction explicitly in the conclusion.
nh_diff <- function(design, var, group) {
  f  <- as.formula(paste0(var, " ~ ", group))
  tt <- svyttest(f, design)
  ci <- as.numeric(confint(tt))
  data.frame(
    variable   = var,
    group      = group,
    difference = as.numeric(tt$estimate),
    ci_low     = ci[1],
    ci_high    = ci[2],
    p_value    = as.numeric(tt$p.value),
    row.names  = NULL
  )
}
