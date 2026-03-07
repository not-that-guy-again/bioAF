#' Upload a figure file to bioAF
#'
#' @param figure_path Path to the figure file
#' @return API response with file id
#' @keywords internal
.bioaf_upload_figure <- function(figure_path) {
  if (!file.exists(figure_path)) {
    stop("Figure file not found: ", figure_path)
  }
  .bioaf_post("/api/files/upload/simple", file_path = figure_path)
}

#' Upload a checkpoint (metadata + embeddings) as parquet
#'
#' @param obj A Seurat object
#' @return API response with file id
#' @keywords internal
.bioaf_upload_checkpoint <- function(obj) {
  if (!requireNamespace("arrow", quietly = TRUE)) {
    warning("arrow package required for checkpoint upload")
    return(NULL)
  }

  # Extract metadata and embeddings into a data.frame
  df <- obj@meta.data

  # Add embeddings
  for (red_name in Seurat::Reductions(obj)) {
    emb <- Seurat::Embeddings(obj, reduction = red_name)
    colnames(emb) <- paste0(red_name, "_", seq_len(ncol(emb)))
    df <- cbind(df, emb)
  }

  # Write to temp parquet file
  tmp_path <- tempfile(fileext = ".parquet")
  on.exit(unlink(tmp_path), add = TRUE)
  arrow::write_parquet(df, tmp_path)

  .bioaf_post("/api/files/upload/simple", file_path = tmp_path)
}
