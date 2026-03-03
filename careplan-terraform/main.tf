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

# IAM Role - 让 Lambda 有权限运行
resource "aws_iam_role" "lambda_role" {
  name = "careplan-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# 附加基础权限（写 CloudWatch 日志）
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


# 给 Lambda 添加 SQS 权限
resource "aws_iam_role_policy" "lambda_sqs_policy" {
  name = "lambda-sqs-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.careplan_queue.arn
      }
    ]
  })
}

# 给 Lambda 添加 RDS 权限
resource "aws_iam_role_policy" "lambda_rds_policy" {
  name = "lambda-rds-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["rds-db:connect"]
        Resource = aws_db_instance.careplan_db.arn
      }
    ]
  })
}

resource "aws_lambda_function" "create_order" {
  filename      = "lambda_functions/create_order.zip"
  source_code_hash = filebase64sha256("lambda_functions/create_order.zip")
  function_name = "create_order"
  role          = aws_iam_role.lambda_role.arn
  handler       = "create_order.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300

  environment {
    variables = {
      SQS_QUEUE_URL = aws_sqs_queue.careplan_queue.url
      DB_HOST       = aws_db_instance.careplan_db.address
      DB_NAME       = "careplan"
      DB_USER       = "postgres"
      DB_PASSWORD   = var.db_password
    }
  }
}

resource "aws_lambda_function" "generate_careplan" {
  filename      = "lambda_functions/generate_careplan.zip"
  source_code_hash = filebase64sha256("lambda_functions/generate_careplan.zip")
  function_name = "generate_careplan"
  role          = aws_iam_role.lambda_role.arn
  handler       = "generate_careplan.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300

  environment {
    variables = {
      SQS_QUEUE_URL = aws_sqs_queue.careplan_queue.url
      DB_HOST       = aws_db_instance.careplan_db.address
      DB_NAME       = "careplan"
      DB_USER       = "postgres"
      DB_PASSWORD   = var.db_password
      GOOGLE_API_KEY = var.google_api_key
    }
  }
}

resource "aws_lambda_function" "get_order" {
  filename      = "lambda_functions/get_order.zip"
  source_code_hash = filebase64sha256("lambda_functions/get_order.zip")
  function_name = "get_order"
  role          = aws_iam_role.lambda_role.arn
  handler       = "get_order.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300

  environment {
    variables = {
      DB_HOST     = aws_db_instance.careplan_db.address
      DB_NAME     = "careplan"
      DB_USER     = "postgres"
      DB_PASSWORD = var.db_password
    }
  }
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.careplan_queue.arn
  function_name    = aws_lambda_function.generate_careplan.arn
  batch_size       = 1
}

# 创建 API Gateway
resource "aws_apigatewayv2_api" "careplan_api" {
  name          = "careplan-api"
  protocol_type = "HTTP"
}

# 部署阶段（相当于"发布"）
resource "aws_apigatewayv2_stage" "careplan_stage" {
  api_id      = aws_apigatewayv2_api.careplan_api.id
  name        = "prod"
  auto_deploy = true
}

# 输出 API 的访问地址
output "api_endpoint" {
  value = aws_apigatewayv2_stage.careplan_stage.invoke_url
}

# create_order 的集成
resource "aws_apigatewayv2_integration" "create_order_integration" {
  api_id             = aws_apigatewayv2_api.careplan_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.create_order.invoke_arn
  payload_format_version = "2.0"
}

# get_order 的集成
resource "aws_apigatewayv2_integration" "get_order_integration" {
  api_id             = aws_apigatewayv2_api.careplan_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.get_order.invoke_arn
  payload_format_version = "2.0"
}

# POST /orders
resource "aws_apigatewayv2_route" "create_order_route" {
  api_id    = aws_apigatewayv2_api.careplan_api.id
  route_key = "POST /orders"
  target    = "integrations/${aws_apigatewayv2_integration.create_order_integration.id}"
}

# GET /orders/{id}
resource "aws_apigatewayv2_route" "get_order_route" {
  api_id    = aws_apigatewayv2_api.careplan_api.id
  route_key = "GET /orders/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.get_order_integration.id}"
}

# 允许 API Gateway 调用 create_order
resource "aws_lambda_permission" "apigw_create_order" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.careplan_api.execution_arn}/*/*"
}

# 允许 API Gateway 调用 get_order
resource "aws_lambda_permission" "apigw_get_order" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.careplan_api.execution_arn}/*/*"
}

# 获取默认 VPC 的 Security Group
data "aws_security_group" "default" {
  name = "default"
}

# 给 RDS 的 Security Group 添加 PostgreSQL 入站规则
resource "aws_security_group_rule" "rds_inbound" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = data.aws_security_group.default.id
}