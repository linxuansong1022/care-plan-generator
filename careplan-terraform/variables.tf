# variables.tf（新建这个文件）
variable "db_password" {
  description = "RDS database password"
  type        = string
  sensitive   = true  # 这样 terraform plan 输出里不会显示密码
}