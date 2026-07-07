variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "github_owner" {
  description = "GitHub repository owner (user or org name)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "TradingAgents"
}

variable "invoker_email" {
  description = "Google account email allowed to invoke the Cloud Run service"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy. Null uses a placeholder on first apply; CI owns the running image via gcloud run deploy thereafter."
  type        = string
  default     = null
}

variable "cloud_run_memory" {
  description = "Memory limit for the Cloud Run container"
  type        = string
  default     = "2Gi"
}

variable "cloud_run_cpu" {
  description = "CPU limit for the Cloud Run container"
  type        = string
  default     = "2"
}

variable "cloud_run_timeout_seconds" {
  description = "Per-request timeout in seconds (max 3600); analyses can take 10–30 min"
  type        = number
  default     = 3600
}

variable "secret_names" {
  description = "All Secret Manager secrets to create (empty stubs; populate values with gcloud)"
  type        = list(string)
  default = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "DASHSCOPE_API_KEY",
    "DASHSCOPE_CN_API_KEY",
    "ZHIPU_API_KEY",
    "ZHIPU_CN_API_KEY",
    "MINIMAX_API_KEY",
    "MINIMAX_CN_API_KEY",
    "OPENROUTER_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
  ]
}

variable "active_secrets" {
  description = "Subset of secret_names that have values and should be injected into Cloud Run as env vars"
  type        = list(string)
  default     = ["OPENAI_API_KEY"]
}
