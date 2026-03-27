#!/usr/bin/env Rscript
# =============================================================================
# qc_normalize.R — 甲基化数据质量控制与归一化
#
# 输入 JSON 字段（从 --input 文件读取）：
#   array_type:       "EPIC" 或 "450K"
#   red_idat_path:    Red channel IDAT 临时文件路径（IDAT 上传时）
#   grn_idat_path:    Grn channel IDAT 临时文件路径
#   beta_csv_path:    beta 值矩阵 CSV 路径（CSV 上传时）
#
# 输出 JSON（写到 stdout）：
#   qc_passed:              bool
#   error:                  string（仅 qc_passed=false 时）
#   n_probes_before:        int
#   n_probes_after:         int
#   detection_p_failed_fraction: float
#   beta_matrix_path:       string（归一化后 .rds 文件路径，供下游脚本使用）
# =============================================================================

suppressPackageStartupMessages({
  library(minfi)
  library(jsonlite)
})

# ── 解析参数 ──────────────────────────────────────────────────
args <- commandArgs(trailingOnly = TRUE)
input_idx <- which(args == "--input")
if (length(input_idx) == 0) stop("缺少 --input 参数")
input <- fromJSON(args[input_idx + 1])

fail <- function(msg, extra = list()) {
  result <- c(list(qc_passed = FALSE, error = msg), extra)
  cat(toJSON(result, auto_unbox = TRUE))
  quit(status = 0)
}

# ── 加载数据 ──────────────────────────────────────────────────
if (!is.null(input$beta_csv_path)) {
  # CSV beta 矩阵输入（直接使用，跳过 IDAT 读取）
  message("[QC] 从 CSV 加载 beta 矩阵...")
  beta_raw <- tryCatch(
    as.matrix(read.csv(input$beta_csv_path, row.names = 1, check.names = FALSE)),
    error = function(e) fail(paste("CSV 读取失败:", e$message))
  )
  n_probes_before <- nrow(beta_raw)
  detection_p_failed_fraction <- 0  # CSV 模式无检测 p 值

  # 简单过滤：移除 CH 探针（非 CpG），保持 probes×samples 格式
  cpg_idx <- grepl("^cg", rownames(beta_raw))
  beta_filtered <- beta_raw[cpg_idx, , drop = FALSE]
  n_probes_after <- nrow(beta_filtered)

} else {
  # IDAT 输入
  if (is.null(input$red_idat_path) || is.null(input$grn_idat_path)) {
    fail("必须提供 red_idat_path 和 grn_idat_path，或 beta_csv_path")
  }

  message("[QC] 从 IDAT 加载数据...")

  # minfi 要求 basename（不含 _Red.idat / _Grn.idat 后缀）
  # 我们将 Red/Grn 文件放在同一目录，basename 相同
  base_path <- sub("_Red\\.idat$", "", input$red_idat_path)

  targets <- data.frame(
    Sample_Name = "sample",
    Basename = base_path,
    stringsAsFactors = FALSE
  )

  rgSet <- tryCatch(
    read.metharray.exp(targets = targets, force = TRUE),
    error = function(e) fail(paste("IDAT 读取失败:", e$message))
  )

  n_probes_before <- nrow(rgSet)

  # ── 检测 p 值 QC ──────────────────────────────────────────
  message("[QC] 计算检测 p 值...")
  det_p <- detectionP(rgSet)
  detection_p_failed_fraction <- sum(det_p > 0.01) / length(det_p)

  if (detection_p_failed_fraction > 0.05) {
    fail(
      sprintf(
        "质控失败：%.1f%% 的探针检测 p > 0.01（阈值 5%%）。样本质量不足。",
        detection_p_failed_fraction * 100
      ),
      list(
        detection_p_failed_fraction = detection_p_failed_fraction,
        n_probes_before = n_probes_before
      )
    )
  }

  # ── 归一化：Noob（背景校正）─────────────────────────────────
  message("[QC] Noob 归一化...")
  mSet_noob <- preprocessNoob(rgSet)

  # ── 探针过滤 ──────────────────────────────────────────────
  # 1. 移除失败探针（检测 p > 0.01）
  failed_probes <- rownames(det_p)[apply(det_p, 1, function(x) any(x > 0.01))]
  # 2. 移除 CH（非 CpG）探针
  ch_probes <- grep("^ch\\.", rownames(mSet_noob), value = TRUE)

  probes_to_remove <- unique(c(failed_probes, ch_probes))
  keep <- !rownames(mSet_noob) %in% probes_to_remove
  mSet_filtered <- mSet_noob[keep, ]
  # 3. 移除 SNP 相关探针（需先 mapToGenome，minfi 1.48+ 要求 GenomicMethylSet）
  mSet_filtered <- mapToGenome(mSet_filtered)
  mSet_filtered <- dropLociWithSnps(mSet_filtered, snps = c("SBE", "CpG"), maf = 0)

  # 保持 minfi 原始格式：行=探针，列=样本（PACEProjector 直接使用）
  # methylclock 的 DNAmAge 在调用前自行转置
  beta_filtered <- getBeta(mSet_filtered)
  n_probes_after <- nrow(beta_filtered)

  message(sprintf(
    "[QC] 过滤完成：%d → %d 探针（移除 %d）",
    n_probes_before, n_probes_after, n_probes_before - n_probes_after
  ))
}

# ── 保存归一化 beta 矩阵供下游脚本复用 ───────────────────────
# 优先使用 Python 传入的 output_dir（Python TemporaryDirectory 管理生命周期）
if (!is.null(input$output_dir)) {
  beta_out_path <- file.path(input$output_dir, "beta_normalized.rds")
} else {
  beta_out_path <- tempfile(pattern = "beta_normalized_", fileext = ".rds")
}
saveRDS(beta_filtered, beta_out_path)
message(sprintf("[QC] Beta 矩阵已保存: %s", beta_out_path))

# ── 输出结果 JSON ─────────────────────────────────────────────
result <- list(
  qc_passed                    = TRUE,
  n_probes_before              = n_probes_before,
  n_probes_after               = n_probes_after,
  detection_p_failed_fraction  = detection_p_failed_fraction,
  beta_matrix_path             = beta_out_path
)
cat(toJSON(result, auto_unbox = TRUE))
