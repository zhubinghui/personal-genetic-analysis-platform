#!/usr/bin/env Rscript
# =============================================================================
# horvath_clock.R — Horvath 2013 表观遗传时钟
#
# 参考：Horvath (2013) Genome Biology, doi:10.1186/gb-2013-14-10-r115
# 基于 353 个 CpG 位点预测多组织生物学年龄。
#
# 输入 JSON：
#   beta_matrix_path: .rds 文件路径
#
# 输出 JSON：
#   horvath_age: float — 生物学年龄（岁）
# =============================================================================

suppressPackageStartupMessages({
  library(methylclock)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
input_idx <- which(args == "--input")
input <- fromJSON(args[input_idx + 1])

message("[Horvath] 加载 beta 矩阵...")
beta <- readRDS(input$beta_matrix_path)  # probes×samples；DNAmAge 内部 t() 转为 samples×probes
# methylclock predAge 有单样本维度 drop bug，复制列规避（只取 [1]）
if (ncol(beta) == 1) beta <- cbind(beta, beta)

message("[Horvath] 计算生物学年龄...")
result <- tryCatch(
  DNAmAge(beta, clocks = "Horvath", toBioage = FALSE, cell.count = FALSE),
  error = function(e) {
    cat(toJSON(list(error = paste("Horvath clock 计算失败:", e$message)), auto_unbox = TRUE))
    quit(status = 1)
  }
)

horvath_age <- as.numeric(result$Horvath[1])
if (!is.finite(horvath_age)) horvath_age <- NA_real_
message(sprintf("[Horvath] 完成，生物学年龄: %s 岁", if(is.na(horvath_age)) "NA" else sprintf("%.1f", horvath_age)))

cat(toJSON(list(horvath_age = horvath_age), auto_unbox = TRUE))
