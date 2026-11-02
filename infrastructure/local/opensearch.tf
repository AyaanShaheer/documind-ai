
# ==========================================
# DOCUMIND AI - OPENSEARCH DOMAIN
# ==========================================

resource "aws_opensearch_domain" "documents" {

  domain_name    = "documind-search"
  engine_version = "OpenSearch_2.19"

  cluster_config {
    instance_type  = "m5.large.search"
    instance_count = 1
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp2"
    volume_size = 10
  }

  tags = {
    Name        = "DocuMind Search"
    Environment = "local"
    Project     = "DocuMind AI"
  }
}

