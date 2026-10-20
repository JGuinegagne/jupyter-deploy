data "aws_route53_zone" "domain" {
  name = var.domain
}

# ── Domain ownership guard ────────────────────────────────────────────────────
# Refuses a domain whose record already routes to another live deployment. Both
# clusters' external-dns would claim it (txtOwnerId is the domain, not the deployment),
# and sign-ins would land on whichever cluster's Dex the record points at. Allowed: no
# record; a record whose load balancer is gone (a torn-down deployment's, which
# external-dns reclaims); a record on this deployment's own load balancer, identified
# by its kubernetes.io/cluster/<cluster-name> tag. A load balancer in another account
# is invisible here and reads as gone.
data "aws_route53_records" "domain" {
  zone_id    = data.aws_route53_zone.domain.zone_id
  name_regex = "^${replace(lower(local.full_domain), ".", "\\.")}\\.?$"
}

locals {
  domain_record_targets = distinct([
    # null, not [], when nothing matches.
    for r in coalesce(data.aws_route53_records.domain.resource_record_sets, []) :
    trimsuffix(trimprefix(lower(try(coalesce(try(r.alias_target.dns_name, null), try(r.resource_records[0].value, null)), "")), "dualstack."), ".")
    if contains(["A", "AAAA", "CNAME"], r.type)
  ])

  # target => { name, region } for "<lb-name>-<id>.elb.<region>.amazonaws.com"; null for
  # anything else (an IP, another service), which is foreign by definition.
  domain_record_nlbs = {
    for t in local.domain_record_targets :
    t => try(regex("^(?P<name>.+)-[0-9a-f]+\\.elb\\.(?P<region>[a-z0-9-]+)\\.amazonaws\\.com$", t), null)
  }

  # target => ARN of the live load balancer, or null once it is gone. ARNs end in
  # loadbalancer/net/<lb-name>/<id>.
  domain_record_live_arns = {
    for t, lb in local.domain_record_nlbs : t => one([
      for arn in data.aws_lbs.domain_record[lb.region].arns : arn if split("/", arn)[2] == lb.name
    ]) if lb != null
  }

  # target => owning cluster name; null when nothing live answers on it.
  domain_record_owners = {
    for t, lb in local.domain_record_nlbs : t => (
      lb == null ? "not a load balancer" :
      local.domain_record_live_arns[t] == null ? null :
      coalesce(one([
        for k in keys(data.aws_lb.domain_record[t].tags) : trimprefix(k, "kubernetes.io/cluster/")
        if startswith(k, "kubernetes.io/cluster/")
      ]), "a load balancer of no cluster")
    )
  }

  domain_record_live_owners = [for t, owner in local.domain_record_owners : "${t} (${owner})" if owner != null]
}

data "aws_lbs" "domain_record" {
  for_each = toset([for lb in values(local.domain_record_nlbs) : lb.region if lb != null])
  region   = each.key
}

data "aws_lb" "domain_record" {
  for_each = { for t, arn in local.domain_record_live_arns : t => arn if arn != null }
  arn      = each.value
  region   = local.domain_record_nlbs[each.key].region
}
