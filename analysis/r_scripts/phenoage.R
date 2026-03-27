#!/usr/bin/env Rscript
# =============================================================================
# phenoage.R — PhenoAge 表观遗传时钟
#
# 参考：Levine et al. (2018) Aging Cell, doi:10.1111/acel.12843
# 整合临床生化指标的表观遗传版本，使用 methylclock 中的纯甲基化实现。
#
# 输入 JSON：
#   beta_matrix_path: .rds 文件路径
#
# 输出 JSON：
#   phenoage_age: float — PhenoAge 生物学年龄（岁）
# =============================================================================

suppressPackageStartupMessages({
  library(methylclock)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
input_idx <- which(args == "--input")
input <- fromJSON(args[input_idx + 1])

message("[PhenoAge] 加载 beta 矩阵...")
beta <- readRDS(input$beta_matrix_path)  # probes×samples；DNAmAge 内部 t() 转为 samples×probes
# methylclock predAge 有单样本维度 drop bug，复制列规避（只取 [1]）
if (ncol(beta) == 1) beta <- cbind(beta, beta)

message("[PhenoAge] 计算生物学年龄...")
# methylclock 1.10 中 PhenoAge 时钟参数名为 "Levine"（Levine et al. 2018）
result <- tryCatch(
  DNAmAge(beta, clocks = "Levine", toBioage = FALSE, cell.count = FALSE),
  error = function(e) {
    cat(toJSON(list(error = paste("PhenoAge 计算失败:", e$message)), auto_unbox = TRUE))
    quit(status = 1)
  }
)

phenoage_age <- as.numeric(result$Levine[1])
if (!is.finite(phenoage_age)) phenoage_age <- NA_real_
message(sprintf("[PhenoAge] 完成，生物学年龄: %s 岁", if(is.na(phenoage_age)) "NA" else sprintf("%.1f", phenoage_age)))

cat(toJSON(list(phenoage_age = phenoage_age), auto_unbox = TRUE))
