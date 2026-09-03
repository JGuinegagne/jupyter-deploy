# ECR repositories for pre-built E2E test container images.
# Repos 1-6 map 1:1 to the OAuth app-dependent templates.
# Repos 7-9 back additional templates, which have NO OAuth app.
# one repo per concurrent trigger (PR/dispatch, release, canary) so simultaneous
# runs never share an image tag.
# Each repo maps to a distinct concurrency group, so separate repos prevent image
# tag conflicts between concurrent workflow runs.

module "ecr_e2e_image_1" {
  source = "./modules/ecr_repository"
  name   = "${var.secret_name_prefix}-${local.doc_postfix}/e2e-image-1"
  tags = merge(local.default_tags, {
    OAuthAppId  = var.github_oauth_app_1["app_id"]
    CallbackUrl = var.github_oauth_app_1["callback_url"]
  })
}

module "ecr_e2e_image_2" {
  source = "./modules/ecr_repository"
  name   = "${var.secret_name_prefix}-${local.doc_postfix}/e2e-image-2"
  tags = merge(local.default_tags, {
    OAuthAppId  = var.github_oauth_app_2["app_id"]
    CallbackUrl = var.github_oauth_app_2["callback_url"]
  })
}

module "ecr_e2e_image_3" {
  source = "./modules/ecr_repository"
  name   = "${var.secret_name_prefix}-${local.doc_postfix}/e2e-image-3"
  tags = merge(local.default_tags, {
    OAuthAppId  = var.github_oauth_app_3["app_id"]
    CallbackUrl = var.github_oauth_app_3["callback_url"]
  })
}

module "ecr_e2e_image_4" {
  source = "./modules/ecr_repository"
  name   = "${var.secret_name_prefix}-${local.doc_postfix}/e2e-image-4"
  tags = merge(local.default_tags, {
    OAuthAppId  = var.github_oauth_app_4["app_id"]
    CallbackUrl = var.github_oauth_app_4["callback_url"]
  })
}

module "ecr_e2e_image_5" {
  source = "./modules/ecr_repository"
  name   = "${var.secret_name_prefix}-${local.doc_postfix}/e2e-image-5"
  tags = merge(local.default_tags, {
    OAuthAppId  = var.github_oauth_app_5["app_id"]
    CallbackUrl = var.github_oauth_app_5["callback_url"]
  })
}

module "ecr_e2e_image_6" {
  source = "./modules/ecr_repository"
  name   = "${var.secret_name_prefix}-${local.doc_postfix}/e2e-image-6"
  tags = merge(local.default_tags, {
    OAuthAppId  = var.github_oauth_app_6["app_id"]
    CallbackUrl = var.github_oauth_app_6["callback_url"]
  })
}

# Repos 7-9 back additional templates (no OAuth app) — one per concurrent trigger
# so PR/dispatch, release, and canary runs never collide on an image tag.
module "ecr_e2e_image_7" {
  source = "./modules/ecr_repository"
  name   = "${var.secret_name_prefix}-${local.doc_postfix}/e2e-image-7"
  tags = merge(local.default_tags, {
    Template = "template3"
    Purpose  = "pr-dispatch"
  })
}

module "ecr_e2e_image_8" {
  source = "./modules/ecr_repository"
  name   = "${var.secret_name_prefix}-${local.doc_postfix}/e2e-image-8"
  tags = merge(local.default_tags, {
    Template = "template3"
    Purpose  = "release"
  })
}

module "ecr_e2e_image_9" {
  source = "./modules/ecr_repository"
  name   = "${var.secret_name_prefix}-${local.doc_postfix}/e2e-image-9"
  tags = merge(local.default_tags, {
    Template = "template3"
    Purpose  = "canary"
  })
}
