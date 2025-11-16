variable "cloud_id" {
  type        = string
  description = "Yandex Cloud ID"
}

variable "folder_id" {
  type        = string
  description = "Yandex Folder ID"
}

variable "tg_bot_key" {
  type        = string
  description = "Telegram Bot API Token"
  sensitive   = true
}

variable "yandex_oauth_token" {
  type        = string
  description = "Yandex OAuth Token"
  sensitive   = true
}

variable "service_account_id" {
  type        = string
  description = "Service Account ID"
}
