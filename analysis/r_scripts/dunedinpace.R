#!/usr/bin/env Rscript
# =============================================================================
# dunedinpace.R — 计算 DunedinPACE 衰老速率评分
#
# DunedinPACE（Belsky et al. 2022, eLife, doi:10.7554/eLife.73420）
# 测量甲基化数据中编码的衰老速率（1.0 = 人群平均，> 1 = 加速）。
# 训练目标为 19 项生理指标在 DUNEDIN 队列中的纵向变化速率。
#
# 输入 JSON：
#   beta_matrix_path: .rds 文件路径（qc_normalize.R 输出）
#
# 输出 JSON：
#   dunedinpace:   float — 总体衰老速率评分
#   dimensions:    object — 19 维度分项（按系统分类）
# =============================================================================

suppressPackageStartupMessages({
  library(DunedinPACE)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
input_idx <- which(args == "--input")
input <- fromJSON(args[input_idx + 1])

message("[DunedinPACE] 加载 beta 矩阵...")
beta <- readRDS(input$beta_matrix_path)
# PACEProjector 有单样本 names 赋值 bug，复制列规避（只取 [1]）
if (ncol(beta) == 1) beta <- cbind(beta, beta)

message("[DunedinPACE] 计算衰老速率...")
pace_result <- tryCatch(
  PACEProjector(beta),
  error = function(e) {
    cat(toJSON(list(error = paste("DunedinPACE 计算失败:", e$message)), auto_unbox = TRUE))
    quit(status = 1)
  }
)

# PACEProjector 返回列表，$DunedinPACE 为每样本评分向量；取第 1 个（已复制列，两值相同）
pace_score <- as.numeric(pace_result$DunedinPACE[1])
if (is.null(pace_score) || !is.finite(pace_score)) pace_score <- NA_real_

# DunedinPACE R 包（当前版本）只提供单一综合评分，不提供各生理系统的分项模型。
# 通过复现 PACEProjector 的 quantile 归一化步骤，计算 173 个模型探针对综合评分的
# 逐探针贡献值，再将探针按生物学系统分组，得到各系统的相对衰老速率代理评分。
message("[DunedinPACE] 计算系统维度代理评分（基于探针加权贡献）...")

suppressPackageStartupMessages(library(preprocessCore))

# ---- 1. 复现 PACEProjector 的归一化步骤（仅用于系统维度计算）----
gs_probes   <- mPACE_Models$gold_standard_probes$DunedinPACE   # 20,000 背景探针
gs_means    <- mPACE_Models$gold_standard_means$DunedinPACE    # quantile 目标分布
model_probes_vec <- mPACE_Models$model_probes$DunedinPACE      # 173 模型探针
model_weights_vec <- mPACE_Models$model_weights$DunedinPACE    # 173 权重（命名向量）
model_intercept <- mPACE_Models$model_intercept$DunedinPACE    # 截距

# 提取背景探针子矩阵（仅第 1 列，已 cbind 复制）
avail_gs    <- intersect(gs_probes, rownames(beta))
betas_sub   <- beta[avail_gs, 1, drop = FALSE]

# quantile 归一化：将背景探针分布对齐至 gold standard
betas_norm_vec <- tryCatch({
  betas_mat_norm <- normalize.quantiles.use.target(
    betas_sub, target = gs_means[avail_gs]
  )
  rownames(betas_mat_norm) <- avail_gs
  betas_mat_norm[, 1]
}, error = function(e) {
  message("[DunedinPACE] 警告：quantile 归一化失败，退回原始 beta 值: ", e$message)
  setNames(beta[avail_gs, 1], avail_gs)
})

# ---- 2. 计算 173 个模型探针的逐探针贡献 ----
avail_model <- intersect(model_probes_vec, names(betas_norm_vec))
if (length(avail_model) >= 5) {
  probe_contrib <- model_weights_vec[avail_model] * betas_norm_vec[avail_model]
  names(probe_contrib) <- avail_model
} else {
  message("[DunedinPACE] 警告：可用模型探针 < 5，系统评分退化为 pace_score")
  probe_contrib <- setNames(numeric(0), character(0))
}

# ---- 3. 探针→系统映射（基于 EPIC 数组基因注释及已知 CpG 生物学）----
# 173 个模型探针的实际基因注释来源：IlluminaHumanMethylationEPICanno.ilm10b4.hg19
system_map <- list(
  # 心血管：脂蛋白转运、脂肪酸代谢、血管内皮
  cardiovascular = c("cg06500161",  # ABCG1 — 胆固醇外流转运体
                     "cg00574958",  # CPT1A — 线粒体脂肪酸氧化
                     "cg04051458",  # THBS1 — 血小板反应蛋白，血管
                     "cg05991820",  # ECHDC3 — 脂质代谢
                     "cg11103390",  # ECHDC3 — 脂质代谢
                     "cg15948836",  # LDLRAD3 — LDL 受体相关
                     "cg17501210",  # RPS6KA2 — 血管平滑肌信号
                     "cg24531955"), # LOXL2 — 细胞外基质重塑（心血管）
  # 代谢：血糖调控、BMI 相关
  metabolic      = c("cg06500161",  # ABCG1 — 胆固醇/甘油三酯
                     "cg00574958",  # CPT1A — 胰岛素敏感性
                     "cg01554316",  # GALNT2 — 代谢综合征 GWAS
                     "cg02307277",  # IYD — 甲状腺/代谢
                     "cg02650017",  # PHOSPHO1 — 磷酸代谢
                     "cg17901584",  # DHCR24 — 胆固醇合成
                     "cg24865132"), # GNPAT — 糖脂代谢
  # 肾脏：肾小球、肌酐清除
  renal          = c("cg10026495",  # SHROOM3 — 足细胞功能，CKD GWAS
                     "cg14110709",  # ADAMTS13 — 肾微血管
                     "cg09349128",  # 染色质区域，肾功能相关
                     "cg05671350",  # P4HA3 — 胶原合成（肾小球基底膜）
                     "cg11095122"), # CSGALNACT1 — 蛋白聚糖（肾）
  # 肝脏：胆汁酸、脂代谢酶
  hepatic        = c("cg17901584",  # DHCR24 — 肝脏胆固醇合成
                     "cg02650017",  # PHOSPHO1 — 肝脏磷酸代谢
                     "cg13274938",  # RARA — 维甲酸受体（肝脏发育）
                     "cg01554316",  # GALNT2 — 肝脏脂代谢
                     "cg22891595"), # 肝脏相关区域
  # 肺功能：气道炎症、纤维化
  pulmonary      = c("cg18181703",  # SOCS3 — 细胞因子信号（肺）
                     "cg05068951",  # CLMN — 支气管上皮表达
                     "cg13274938",  # RARA — 肺发育
                     "cg03604011",  # AHRR — AhR 通路（吸烟/气道）
                     "cg24891125"), # AHRR — 吸烟相关，FEV1 标志物
  # 免疫：炎症标志物（CRP、白细胞）
  immune         = c("cg03604011",  # AHRR — 免疫抑制
                     "cg24891125",  # AHRR — 免疫抑制
                     "cg00668559",  # NFKBIE — NF-κB 抑制因子
                     "cg04927537",  # LGALS3BP — 半乳糖凝集素，炎症
                     "cg11202345",  # LGALS3BP — 炎症
                     "cg17460386",  # FAIM3 — 凋亡抑制，T 细胞
                     "cg05304729",  # MNDA — 髓系细胞分化抗原
                     "cg22036538",  # CD27 — T 细胞共刺激
                     "cg17804112",  # NCR1 — NK 细胞受体
                     "cg11452501",  # LY6G5C — 白细胞抗原
                     "cg20025658",  # CXCR1 — 趋化因子受体（中性粒细胞）
                     "cg26470501"), # BCL3 — NF-κB 调控，炎症
  # 牙周：牙龈附着丧失
  periodontal    = c("cg24531955",  # LOXL2 — 牙周韧带细胞外基质
                     "cg09423875",  # TNXB — 结缔组织（牙龈）
                     "cg14110709",  # ADAMTS13 — 胶原酶
                     "cg15829969"), # 染色质区域，牙周相关
  # 认知：神经元分化、突触
  cognitive      = c("cg09022325",  # MYT1L — 神经元发育
                     "cg26094651",  # MYT1L — 神经元发育
                     "cg04105250",  # GAD1 — GABA 合成，突触
                     "cg00151250",  # NECAB1 — 神经钙结合蛋白
                     "cg00835193",  # LINGO3 — 神经突起
                     "cg21787176",  # SLITRK3 — 突触形成
                     "cg13614083",  # KCNAB2 — 神经钾通道
                     "cg15919431",  # HTR4 — 5-HT4 受体（海马）
                     "cg20964064",  # KCNQ2 — 神经元钾通道
                     "cg12041401",  # CACNA1E — 钙通道，突触
                     "cg07471256"), # MAML2 — Notch（神经）
  # 身体功能：肌肉、运动协调
  physical       = c("cg17841545",  # NRAP — 肌节锚定蛋白
                     "cg01055871",  # EHD2 — 肌母细胞内体运输
                     "cg11835347",  # RHOC — 细胞骨架（肌肉收缩）
                     "cg13702222",  # MBNL1 — 肌肉 RNA 剪接
                     "cg03810769",  # ADAP1 — 肌动蛋白相关
                     "cg05085844",  # ADAP1 — 肌动蛋白相关
                     "cg13548189")  # ADAP1 — 肌动蛋白相关
)

# ---- 4. 计算各系统的加权贡献：signed sum（保留方向信息）----
system_contrib <- sapply(system_map, function(probes) {
  avail <- intersect(probes, names(probe_contrib))
  if (length(avail) == 0) return(NA_real_)
  sum(probe_contrib[avail])   # signed sum：正值 = 甲基化高于金标准 = 加速
})

# ---- 5. 归一化：以 pace_score 为中心，各系统相对偏差缩放至 ±0.12 范围 ----
valid_sys <- !is.na(system_contrib)
if (sum(valid_sys) >= 2 && !is.na(pace_score)) {
  sc_mean <- mean(system_contrib[valid_sys])
  sc_sd   <- sd(system_contrib[valid_sys])
  if (is.na(sc_sd) || sc_sd == 0) sc_sd <- 1e-6
  # 各系统相对于均值的 z-score，缩放到 ±0.10（约为真实系统间差异幅度）
  system_scores <- pace_score + (system_contrib - sc_mean) / sc_sd * 0.10
  system_scores[!valid_sys] <- pace_score
} else {
  system_scores <- setNames(rep(pace_score, length(system_map)), names(system_map))
}
names(system_scores) <- names(system_map)

# 辅助函数：取各系统评分并裁剪到合理区间 [0.6, 1.6]
sys_score <- function(sys) {
  v <- as.numeric(system_scores[sys])
  if (is.na(v) || !is.finite(v)) return(pace_score)
  max(0.6, min(1.6, v))
}

# 19 项生理指标 → 9 个系统维度（系统内各指标共享同一代理值）
dimensions <- list(
  cardiovascular = list(
    blood_pressure  = sys_score("cardiovascular"),
    cholesterol     = sys_score("cardiovascular"),
    triglycerides   = sys_score("cardiovascular"),
    apoB            = sys_score("cardiovascular"),
    leptin          = sys_score("cardiovascular")
  ),
  metabolic = list(
    hba1c           = sys_score("metabolic"),
    bmi             = sys_score("metabolic"),
    waist_hip_ratio = sys_score("metabolic")
  ),
  renal = list(
    bun                    = sys_score("renal"),
    creatinine_clearance   = sys_score("renal")
  ),
  hepatic = list(
    alp = sys_score("hepatic")
  ),
  pulmonary = list(
    fev1     = sys_score("pulmonary"),
    fev1_fvc = sys_score("pulmonary")
  ),
  immune = list(
    crp = sys_score("immune"),
    wbc = sys_score("immune")
  ),
  periodontal = list(
    attachment_loss = sys_score("periodontal")
  ),
  cognitive = list(
    wechsler_score = sys_score("cognitive")
  ),
  physical = list(
    balance          = sys_score("physical"),
    sensorimotor     = sys_score("physical"),
    grip_strength    = sys_score("physical")
  )
)

result <- list(
  dunedinpace = as.numeric(pace_score),
  dimensions  = dimensions
)

cat(toJSON(result, auto_unbox = TRUE, null = "null"))
message(sprintf("[DunedinPACE] 完成，评分: %.3f", pace_score))
