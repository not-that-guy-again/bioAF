\name{bioaf_connect}
\alias{bioaf_connect}
\title{Configure connection to bioAF API}
\usage{
bioaf_connect(api_url = NULL, token = NULL)
}
\arguments{
\item{api_url}{Base URL of the bioAF API (e.g., "https://bioaf.example.com")}
\item{token}{Authentication token}
}
\value{
Invisible NULL
}
\description{
Reads from environment variables if arguments are not provided:
BIOAF_API_URL, BIOAF_TOKEN, BIOAF_EXPERIMENT_ID, BIOAF_PROJECT_ID, BIOAF_SESSION_ID
}
