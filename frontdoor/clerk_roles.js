export const clerkTenantRoles = Object.freeze({
  "org:member": {role: "reader", access_profile: "basic"},
  "org:reader": {role: "reader", access_profile: "full"},
  "org:operator": {role: "operator", access_profile: "full"},
  "org:admin": {role: "admin", access_profile: "full"}
});

// Association mappings come from the application's registry, never an org slug
// or user-editable metadata. An unrelated organization cannot claim a tenant.
export function membershipAccessProfile(user, memberships, associations, memberLinks = []) {
  const mappings = new Map();
  const mappedTenants = new Set();
  for (const association of associations) {
    const organizationId = association.clerk_organization_id;
    if (!organizationId) continue;
    // KV is eventually consistent; reject ambiguity even if a concurrent write
    // passed the registry's uniqueness check.
    if (mappings.has(organizationId) || mappedTenants.has(association.tenant_id)) {
      throw new Error("Ambiguous organization association mapping");
    }
    mappings.set(organizationId, association.tenant_id);
    mappedTenants.add(association.tenant_id);
  }
  const roles = [];
  const profiles = {};
  const seen = new Set();
  for (const membership of memberships) {
    const tenant = mappings.get(membership.organization.id);
    const grant = Object.hasOwn(clerkTenantRoles, membership.role) ? clerkTenantRoles[membership.role] : null;
    if (!tenant || !grant) continue;
    if (seen.has(tenant)) throw new Error("Multiple organizations map to one association");
    seen.add(tenant);
    roles.push({tenant_id: tenant, role: grant.role});
    profiles[tenant] = grant.access_profile;
  }
  return {
    status: user.banned || user.locked ? "disabled" : "active",
    global_role: "none",
    access_profile: "full",
    tenant_roles: roles,
    tenant_profiles: profiles,
    member_links: memberLinks.filter((item) => seen.has(item.tenant_id)),
    default_tenant: roles[0]?.tenant_id
  };
}

export async function listUserMemberships(client, userId) {
  const memberships = [];
  for (let offset = 0; ; offset += 100) {
    const page = await client.users.getOrganizationMembershipList({userId, limit: 100, offset});
    memberships.push(...page.data);
    if (memberships.length >= page.totalCount || page.data.length === 0) return memberships;
  }
}
