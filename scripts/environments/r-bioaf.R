# Install BiocManager and core packages
if (!require("BiocManager", quietly = TRUE))
    install.packages("BiocManager")

BiocManager::install(c(
    "Seurat",
    "SingleCellExperiment",
    "scater",
    "scran",
    "DESeq2",
    "edgeR",
    "MAST",
    "monocle3",
    "slingshot",
    "scDblFinder",
    "batchelor",
    "SingleR",
    "ComplexHeatmap",
    "pheatmap",
    "dittoSeq",
    "zellkonverter"
))

install.packages(c("ggplot2", "tidyverse", "uwot", "Rtsne", "presto"))
