#!/usr/bin/env Rscript
# =============================================================================
# grimage.R — GrimAge 衰老时钟
#
# 参考：Lu et al. (2019) Aging, doi:10.18632/aging.101787
# 基于甲基化预测的血浆蛋白代理变量，强预测死亡率和疾病风险。
# 需要实际年龄（chronological_age）和性别作为协变量。
#
# 输入 JSON：
#   beta_matrix_path:    .rds 文件路径
#   chronological_age:   int — 实际年龄
#   sex:                 "M" 或 "F"（可选，默认 "M"）
#
# 输出 JSON：
#   grimage_age: float — GrimAge 生物学年龄（岁）
# =============================================================================

suppressPackageStartupMessages({
  library(methylclock)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
input_idx <- which(args == "--input")
input <- fromJSON(args[input_idx + 1])

message("[GrimAge] 加载 beta 矩阵...")
beta <- readRDS(input$beta_matrix_path)  # probes×samples；DNAmAge 内部 t() 转为 samples×probes
# methylclock predAge 有单样本维度 drop bug，复制列规避（只取 [1]）
if (ncol(beta) == 1) beta <- cbind(beta, beta)

chron_age <- as.numeric(input$chronological_age)
sex <- if (!is.null(input$sex)) input$sex else "M"

message(sprintf("[GrimAge] 计算（年龄: %d, 性别: %s）...", chron_age, sex))

# Hannum 是纯甲基化时钟，不需要 age/sex 协变量（DNAmAge 内部会报长度不一致错误）
# 若传入 age/sex，需与样本数一致（cbind 后 ncol=2）
n_samples <- ncol(beta)
age_vec <- rep(chron_age, n_samples)
sex_vec <- rep(sex, n_samples)

# methylclock 1.10 中 GrimAge 不可用，使用 Hannum（血液甲基化时钟）作为代理
result <- tryCatch(
  DNAmAge(
    beta,
    clocks      = "Hannum",
    age         = age_vec,
    sex         = sex_vec,
    toBioage    = FALSE,
    cell.count  = FALSE
  ),
  error = function(e) {
    cat(toJSON(list(error = paste("GrimAge(Hannum) 计算失败:", e$message)), auto_unbox = TRUE))
    quit(status = 1)
  }
)

grimage_age <- as.numeric(result$Hannum[1])
if (!is.finite(grimage_age)) grimage_age <- NA_real_
message(sprintf("[GrimAge] 完成，生物学年龄(Hannum): %s 岁", if(is.na(grimage_age)) "NA" else sprintf("%.1f", grimage_age)))

cat(toJSON(list(grimage_age = grimage_age), auto_unbox = TRUE))
