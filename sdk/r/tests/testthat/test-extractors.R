test_that("extract_seurat_metadata returns minimal when Seurat not available", {
  mockery::stub(extract_seurat_metadata, "requireNamespace", FALSE)

  result <- extract_seurat_metadata(list())

  expect_equal(result$object_type, "seurat")
  expect_null(result$cell_count)
  expect_null(result$gene_count)
})

test_that("extract_seurat_metadata works with Seurat object", {
  skip_if_not_installed("Seurat")

  # Create a minimal Seurat object
  counts <- matrix(rpois(200, 5), nrow = 20, ncol = 10)
  rownames(counts) <- paste0("Gene", 1:20)
  colnames(counts) <- paste0("Cell", 1:10)

  obj <- Seurat::CreateSeuratObject(counts = counts)
  obj <- Seurat::NormalizeData(obj, verbose = FALSE)
  obj <- Seurat::FindVariableFeatures(obj, verbose = FALSE)
  obj <- Seurat::ScaleData(obj, verbose = FALSE)
  obj <- Seurat::RunPCA(obj, npcs = 5, verbose = FALSE)

  result <- extract_seurat_metadata(obj)

  expect_equal(result$object_type, "seurat")
  expect_equal(result$cell_count, 10)
  expect_equal(result$gene_count, 20)
  expect_true("pca" %in% names(result$embeddings_json))
  expect_true(length(result$command_log_json) > 0)
  expect_true(length(result$metadata_columns_json) > 0)
})
