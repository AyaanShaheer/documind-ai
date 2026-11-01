variable "aws_region" {
  description = "AWS region for DocuMind AI"
  type        = string
  default     = "us-east-1"
}

variable "local_endpoint" {
  description = "Local Floci AWS endpoint"
  type        = string
  default     = "http://localhost:4566"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "documind"
}
