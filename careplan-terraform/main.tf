# Dead Letter Queue 要先创建，因为主队列依赖它
resource "aws_sqs_queue" "careplan_dlq" {
  name                      = "careplan-dlq"
  message_retention_seconds = 1209600  # 14天
}

# 主队列
resource "aws_sqs_queue" "careplan_queue" {
  name                       = "careplan-queue"
  visibility_timeout_seconds = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.careplan_dlq.arn
    maxReceiveCount     = 3
  })
}

# 输出队列 URL，方便之后查看
output "queue_url" {
  value = aws_sqs_queue.careplan_queue.url
}



resource "aws_db_instance" "careplan_db" {
  identifier        = "careplan-db"
  engine            = "postgres"
  engine_version    = "15"
  instance_class    = "db.t3.micro"
  allocated_storage = 20

  db_name  = "careplan"
  username = "postgres"
  password = var.db_password

  publicly_accessible = true
  skip_final_snapshot = true
}

output "db_endpoint" {
  value = aws_db_instance.careplan_db.endpoint
}