test_that("bioaf_connect sets config from arguments", {
  bioaf_connect(api_url = "https://test.example.com", token = "mytoken")
  expect_equal(.bioaf_env$api_url, "https://test.example.com")
  expect_equal(.bioaf_env$token, "mytoken")
})

test_that("bioaf_connect reads environment variables", {
  withr::with_envvar(
    c(
      BIOAF_API_URL = "https://env.example.com",
      BIOAF_TOKEN = "envtoken",
      BIOAF_EXPERIMENT_ID = "42",
      BIOAF_PROJECT_ID = "7",
      BIOAF_SESSION_ID = "99"
    ),
    {
      bioaf_connect()
      expect_equal(.bioaf_env$api_url, "https://env.example.com")
      expect_equal(.bioaf_env$token, "envtoken")
      expect_equal(.bioaf_env$experiment_id, "42")
      expect_equal(.bioaf_env$project_id, "7")
      expect_equal(.bioaf_env$session_id, "99")
    }
  )
})

test_that("bioaf_connect explicit args override env vars", {
  withr::with_envvar(
    c(BIOAF_API_URL = "https://env.example.com", BIOAF_TOKEN = "envtoken"),
    {
      bioaf_connect(api_url = "https://explicit.com", token = "explicittoken")
      expect_equal(.bioaf_env$api_url, "https://explicit.com")
      expect_equal(.bioaf_env$token, "explicittoken")
    }
  )
})
