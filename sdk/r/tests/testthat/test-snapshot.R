test_that("bioaf_snapshot constructs correct payload structure", {
  # Mock the POST function to capture the payload
  captured_payload <- NULL
  mockery::stub(bioaf_snapshot, ".bioaf_post", function(path, body = NULL, ...) {
    captured_payload <<- body
    list(id = 1, label = body$label)
  })

  bioaf_connect(api_url = "https://test.com", token = "tok")

  # Create a minimal non-Seurat object
  obj <- list(class = "generic")

  result <- bioaf_snapshot(obj, label = "test_snap", experiment_id = 42L)

  expect_equal(captured_payload$label, "test_snap")
  expect_equal(captured_payload$experiment_id, 42L)
  expect_equal(captured_payload$object_type, "seurat")
})

test_that("bioaf_snapshot includes notes when provided", {
  captured_payload <- NULL
  mockery::stub(bioaf_snapshot, ".bioaf_post", function(path, body = NULL, ...) {
    captured_payload <<- body
    list(id = 1)
  })

  bioaf_connect(api_url = "https://test.com", token = "tok")
  obj <- list(class = "generic")

  bioaf_snapshot(obj, label = "snap", notes = "Over-clustered", experiment_id = 1L)

  expect_equal(captured_payload$notes, "Over-clustered")
})
