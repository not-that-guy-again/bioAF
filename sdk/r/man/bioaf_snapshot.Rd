\name{bioaf_snapshot}
\alias{bioaf_snapshot}
\title{Capture an analysis snapshot and send to bioAF}
\usage{
bioaf_snapshot(obj, label, notes = NULL, figure = NULL,
  save_checkpoint = FALSE, experiment_id = NULL, project_id = NULL)
}
\arguments{
\item{obj}{A Seurat object (or any R object)}
\item{label}{Human-readable label for this snapshot}
\item{notes}{Optional free-text notes}
\item{figure}{Optional file path to a figure to attach}
\item{save_checkpoint}{If TRUE, save metadata + embeddings as parquet}
\item{experiment_id}{Override default from BIOAF_EXPERIMENT_ID}
\item{project_id}{Override default from BIOAF_PROJECT_ID}
}
\value{
Created snapshot response (list)
}
\description{
Capture an analysis snapshot from a Seurat object and send it to bioAF
for provenance tracking and comparison.
}
