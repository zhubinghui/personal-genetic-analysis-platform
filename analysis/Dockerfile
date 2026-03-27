# rocker/r-ver 提供了稳定版本的 R + 所有 Bioconductor 系统依赖
FROM rocker/r-ver:4.4.0

# 安装 Python 3.10 和系统依赖（Ubuntu 22.04 内置 python3.10，无需 PPA）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    python3.10 python3.10-dev python3-pip python3-setuptools \
    libpq-dev gcc gfortran \
    libssl-dev libcurl4-openssl-dev libxml2-dev \
    libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
    libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev \
    libbz2-dev liblzma-dev \
    cmake \
    libhdf5-dev \
    libgit2-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置 python3.10 为默认
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

WORKDIR /app

# ── R 包安装 ────────────────────────────────────────────────
# 步骤 1：CRAN 工具包
RUN R -e "install.packages(c('BiocManager', 'remotes', 'jsonlite', 'optparse'), repos='https://cloud.r-project.org')"

# 步骤 2：Bioconductor 3.19 包（直接用 BiocManager，避免 renv URL bug）
RUN R -e "BiocManager::install(version='3.19', update=FALSE, ask=FALSE); \
    BiocManager::install(c( \
        'minfi', \
        'preprocessCore', \
        'methylclock', \
        'wateRmelon', \
        'IlluminaHumanMethylationEPICmanifest', \
        'IlluminaHumanMethylationEPICanno.ilm10b4.hg19', \
        'IlluminaHumanMethylation450kmanifest', \
        'IlluminaHumanMethylation450kanno.ilmn12.hg19' \
    ), update=FALSE, ask=FALSE)"

# 步骤 3：DunedinPACE 从 GitHub 安装（锁定 commit SHA）
RUN R -e "remotes::install_github('danbelsky/DunedinPACE@4b569983543e51d1022aecec9a25e694bb3a336a', upgrade='never')"

# 步骤 4：验证所有关键包可正常加载（任一失败则构建报错）
RUN R -e "library(minfi); library(methylclock); library(wateRmelon); library(DunedinPACE); message('All R packages OK')"

# renv.lock 保留供本地开发参考
COPY renv.lock .

# ── Python 依赖 ─────────────────────────────────────────────
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "-Q", "analysis", "--concurrency=1"]
