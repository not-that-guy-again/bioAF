#' @title bioAF Connection Configuration
#' @description Module-level environment for storing connection state.
#' @keywords internal
.bioaf_env <- new.env(parent = emptyenv())

#' Configure connection to bioAF API
#'
#' Reads from environment variables if arguments are not provided:
#' BIOAF_API_URL, BIOAF_TOKEN, BIOAF_EXPERIMENT_ID, BIOAF_PROJECT_ID, BIOAF_SESSION_ID
#'
#' @param api_url Base URL of the bioAF API (e.g., "https://bioaf.example.com")
#' @param token Authentication token
#' @return Invisible NULL
#' @export
bioaf_connect <- function(api_url = NULL, token = NULL) {
  .bioaf_env$api_url <- api_url %||% Sys.getenv("BIOAF_API_URL", "")
  .bioaf_env$token <- token %||% Sys.getenv("BIOAF_TOKEN", "")
  .bioaf_env$experiment_id <- Sys.getenv("BIOAF_EXPERIMENT_ID", "")
  .bioaf_env$project_id <- Sys.getenv("BIOAF_PROJECT_ID", "")
  .bioaf_env$session_id <- Sys.getenv("BIOAF_SESSION_ID", "")
  invisible(NULL)
}

#' @keywords internal
.bioaf_post <- function(path, body = NULL, file_path = NULL) {
  url <- paste0(.bioaf_env$api_url, path)

  if (!is.null(file_path)) {
    req <- httr2::request(url) |>
      httr2::req_auth_bearer_token(.bioaf_env$token) |>
      httr2::req_body_multipart(file = curl::form_file(file_path))
  } else {
    req <- httr2::request(url) |>
      httr2::req_auth_bearer_token(.bioaf_env$token) |>
      httr2::req_body_json(body)
  }

  resp <- httr2::req_perform(req)
  httr2::resp_body_json(resp)
}

#' @keywords internal
.bioaf_get <- function(path, params = NULL) {
  url <- paste0(.bioaf_env$api_url, path)
  req <- httr2::request(url) |>
    httr2::req_auth_bearer_token(.bioaf_env$token)

  if (!is.null(params)) {
    req <- httr2::req_url_query(req, !!!params)
  }

  resp <- httr2::req_perform(req)
  httr2::resp_body_json(resp)
}

#' Null-coalescing operator
#' @keywords internal
`%||%` <- function(x, y) if (is.null(x)) y else x
