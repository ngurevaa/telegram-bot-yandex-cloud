terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  token     = var.yandex_oauth_token
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
  zone      = "ru-central1-a"
}

data "yandex_iam_service_account" "bot_sa" {
  service_account_id = var.service_account_id
}

resource "yandex_resourcemanager_folder_iam_member" "editor" {
  folder_id = var.folder_id
  role      = "editor"
  member    = "serviceAccount:${data.yandex_iam_service_account.bot_sa.id}"
}

resource "yandex_function" "bot" {
  name               = "telegram-bot"
  runtime            = "python311"
  entrypoint         = "simple_bot.handler"
  memory             = 128
  execution_timeout  = 30
  user_hash          = "telegram-bot-v3"
  service_account_id = data.yandex_iam_service_account.bot_sa.id

  environment = {
    TG_BOT_TOKEN = var.tg_bot_token
  }

  content {
    zip_filename = "../simple-bot-py.zip"
  }
}

resource "yandex_api_gateway" "gateway" {
  name = "bot-gateway"
  spec = <<-EOT
    openapi: "3.0.0"
    info:
      version: 1.0.0
      title: Telegram Bot API
    paths:
      /:
        post:
          x-yc-apigateway-integration:
            type: cloud_functions
            function_id: ${yandex_function.bot.id}
            service_account_id: ${data.yandex_iam_service_account.bot_sa.id}
  EOT
}

output "webhook_url" {
  value = "https://${yandex_api_gateway.gateway.domain}/"
}

output "setup_command" {
  value = "curl -X POST 'https://api.telegram.org/bot${var.tg_bot_token}/setWebhook?url=https://${yandex_api_gateway.gateway.domain}/'"
  sensitive = true
}
