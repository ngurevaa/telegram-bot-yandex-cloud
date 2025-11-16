terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
  zone      = "ru-central1-a"
  service_account_key_file = pathexpand("~/.yc-keys/key.json")
}

data "yandex_iam_service_account" "bot_sa" {
  service_account_id = var.service_account_id
}

resource "yandex_storage_bucket" "instructions" {
  bucket = "telegram-bot-instructions"
}

resource "yandex_storage_object" "classification_instruction" {
  bucket = yandex_storage_bucket.instructions.bucket
  key    = "classification_instruction.txt"
  source = "../instructions/classification_instruction.txt"
}

resource "yandex_storage_object" "answer_instruction" {
  bucket = yandex_storage_bucket.instructions.bucket
  key    = "answer_instruction.txt"
  source = "../instructions/answer_instruction.txt"
}

resource "yandex_function" "bot" {
  name               = "telegram-bot"
  runtime            = "python311"
  entrypoint         = "bot.handler"
  memory             = 128
  execution_timeout  = 30
  user_hash          = filesha256("../src/bot.zip")
  service_account_id = data.yandex_iam_service_account.bot_sa.id

  environment = {
    TG_BOT_TOKEN       = var.tg_bot_key
    FOLDER_ID          = var.folder_id
    BUCKET_NAME        = yandex_storage_bucket.instructions.bucket
    YANDEX_OAUTH_TOKEN = var.yandex_oauth_token
  }

  content {
    zip_filename = "../src/bot.zip"
  }
}

resource "yandex_api_gateway" "gateway" {
  name = "telegram-bot-gateway"
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

resource "null_resource" "set_webhook" {
  triggers = {
    api_gateway_domain = yandex_api_gateway.gateway.domain
  }

  provisioner "local-exec" {
    command = <<EOT
      curl -X POST "https://api.telegram.org/bot${var.tg_bot_key}/setWebhook?url=https://${yandex_api_gateway.gateway.domain}/"
    EOT
  }

  depends_on = [yandex_api_gateway.gateway]
}

resource "null_resource" "delete_webhook" {
  triggers = {
    tg_bot_key = var.tg_bot_key
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<EOT
      curl -X POST "https://api.telegram.org/bot${self.triggers.tg_bot_key}/deleteWebhook"
    EOT
  }
}

output "webhook_url" {
  value = "https://${yandex_api_gateway.gateway.domain}/"
}
