#' Extract metadata from a Seurat object
#'
#' Extracts cell/gene counts, embeddings, clusterings, command log,
#' layers, and metadata columns from a Seurat object.
#'
#' @param obj A Seurat object
#' @return A list of metadata suitable for snapshot submission
#' @export
extract_seurat_metadata <- function(obj) {
  if (!requireNamespace("Seurat", quietly = TRUE)) {
    warning("Seurat package not available. Returning minimal metadata.")
    return(list(
      object_type = "seurat",
      cell_count = NULL,
      gene_count = NULL
    ))
  }

  # Basic counts
  cell_count <- ncol(obj)
  gene_count <- nrow(obj)

  # Embeddings/reductions
  reductions <- Seurat::Reductions(obj)
  embeddings_json <- stats::setNames(lapply(reductions, function(r) {
    emb <- Seurat::Embeddings(obj, reduction = r)
    list(n_components = ncol(emb))
  }), reductions)

  # Clusterings from metadata
  meta <- obj@meta.data
  cluster_cols <- grep(
    "cluster|seurat_clusters|leiden|louvain|_snn_res",
    colnames(meta),
    ignore.case = TRUE,
    value = TRUE
  )
  clusterings_json <- stats::setNames(lapply(cluster_cols, function(col) {
    counts <- table(meta[[col]])
    list(
      n_clusters = length(counts),
      distribution = as.list(counts)
    )
  }), cluster_cols)

  # Command log
  cmds <- methods::slot(obj, "commands")
  command_log_json <- lapply(names(cmds), function(n) {
    cmd <- cmds[[n]]
    list(
      name = cmd@name,
      time.stamp = as.character(cmd@time.stamp),
      params = as.list(cmd@params)
    )
  })

  # Layers/assays
  layers_json <- tryCatch(
    Seurat::Layers(obj),
    error = function(e) Seurat::Assays(obj)
  )

  # Metadata columns
  metadata_columns_json <- colnames(obj@meta.data)

  list(
    object_type = "seurat",
    cell_count = cell_count,
    gene_count = gene_count,
    embeddings_json = embeddings_json,
    clusterings_json = clusterings_json,
    command_log_json = command_log_json,
    layers_json = layers_json,
    metadata_columns_json = metadata_columns_json
  )
}
